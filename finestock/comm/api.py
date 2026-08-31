import json
import requests
import queue
from loguru import logger
from finestock.path import _API_PATH_
from .api_interface import BaseProvider
from .errors import FinestockNetworkError, FinestockAPIError

# 로깅 시 마스킹할 민감 필드 이름(소문자 비교). 브로커별로 appkey/appsecret/token
# 헤더 이름이 조금씩 다르므로(appkey/appsecret/appsecretkey/secretkey/x-client-id/
# x-client-secret/authorization/access_token/token) 전부 나열해둔다.
_SENSITIVE_KEYS = {
    "appkey", "appsecret", "appsecretkey", "secretkey",
    "authorization", "access_token", "token",
    "x-client-id", "x-client-secret",
}


def redact(value):
    """
    dict(헤더/응답 등)를 로깅하기 전에 민감 필드 값을 '***'로 마스킹한 사본을 반환한다.
    브로커에 따라 body를 dict가 아니라 json.dumps()된 문자열로 넘기는 경우(Kis/Kiwoom
    등)도 있어, 문자열이면 JSON 파싱을 시도한 뒤 재귀적으로 마스킹한다. dict도
    JSON 문자열도 아니면 그대로 반환한다(HTML 에러 페이지 등 비-JSON 응답 포함).
    """
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            return value
        return redact(parsed)
    if not isinstance(value, dict):
        return value
    return {
        k: ("***" if k.lower() in _SENSITIVE_KEYS else v)
        for k, v in value.items()
    }


class API(BaseProvider):
    # 서브클래스에서 self._redact(header_or_res)로 바로 쓸 수 있게 노출.
    _redact = staticmethod(redact)

    # (connect, read) 초. 브로커 서버가 응답을 지연/무응답하면 스레드가 무기한
    # 블록되는 걸 막는다. 필요하면 _request(..., timeout=(c, r))로 호출별 오버라이드.
    DEFAULT_TIMEOUT = (3, 10)

    def __init__(self):
        self.api_type = type(self).__name__
        self.app_secret = None
        self.app_key = None
        self.access_token = None
        self.token_type = None
        self.account_num = None
        self.account_num_sub = None
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "text/plain",
            "charset": "UTF-8"
        }
        self.headers_rt = {}
        self.ws = None
        self.queue = None 
        self._init_path()

    def __del__(self):
        logger.debug("Destroy API Components")

    def _init_path(self):
        self.path = _API_PATH_[self.api_type]
        for key, value in self.path.items():
            setattr(self, key, value)

    def set_oauth_info(self, app_key, app_secret):
        self.app_key = app_key
        self.app_secret = app_secret
        self.headers['appkey'] = app_key
        self.headers['appsecret'] = app_secret

    def set_access_token(self, token):
        self.access_token = token
        self.token_type = "Bearer"
        self.headers['authorization'] = f"Bearer {token}"

    def get_access_token(self):
        return self.access_token

    def set_account_info(self, account_num, account_num_sub):
        self.account_num = account_num
        self.account_num_sub = account_num_sub

    def _request(self, method, url, headers=None, params=None, data=None, timeout=None, log_tag=None):
        """
        공통 HTTP 요청 헬퍼.
        - timeout을 강제한다(지정 안 하면 DEFAULT_TIMEOUT) — 브로커 서버가 응답을
          지연/무응답해도 무기한 블록되지 않는다.
        - 연결 실패/타임아웃 등 네트워크 예외는 FinestockNetworkError로 감싸 던진다
          (원인이 로그에 남고, 호출부가 finestock.FinestockNetworkError 하나만
          잡으면 되게 통일한다).
        - 요청/응답을 민감정보 마스킹(self._redact) 후 표준 포맷으로 디버그 로깅한다.
        - HTTP 상태 코드/브로커별 성공 판정 필드(rt_cd, rsp_cd 등)는 체크하지 않고
          raw Response를 그대로 반환한다 — 판정 로직은 브로커마다 달라 호출부 몫으로
          남긴다. JSON 파싱만 안전하게 하려면 self._json(response)를 함께 쓴다.
        """
        tag = log_tag or self.api_type
        try:
            response = requests.request(
                method, url, headers=headers, params=params, data=data,
                timeout=timeout or self.DEFAULT_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"[{tag}] network error: {method} {url} | {e}")
            raise FinestockNetworkError(f"{method} {url} failed: {e}") from e

        body_for_log = data if data is not None else params
        logger.debug(f"[{tag}]\n"
                      f"[URL: {method} {url}]\n"
                      f"[header: {self._redact(headers)}]\n"
                      f"[param: {self._redact(body_for_log)}]\n"
                      f"[status: {response.status_code}]\n"
                      f"[response: {self._redact(response.text[:2000])}]")
        return response

    def _json(self, response, log_tag=None):
        """
        response.json()을 안전하게 파싱한다. 실패(브로커가 502/503이나 HTML 에러
        페이지처럼 비-JSON 바디를 반환하는 경우)해도 raw JSONDecodeError가 그대로
        전파되는 대신, 원인을 로그에 남기고 FinestockAPIError로 감싸 던진다.
        """
        try:
            return response.json()
        except ValueError as e:
            tag = log_tag or self.api_type
            text = response.text[:500]
            logger.error(f"[{tag}] non-JSON response (status={response.status_code}): {text}")
            raise FinestockAPIError(
                f"non-JSON response (status={response.status_code})",
                status_code=response.status_code, response_text=text,
            ) from e

    def oauth(self, header=None, data=None):
        url = f"{self.DOMAIN}/{self.OAUTH}"
        _header = header or {"Content-Type": "application/x-www-form-urlencoded"}
        _data = data or {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecretkey": self.app_secret
        }
        response = self._request("POST", url, headers=_header, data=_data, log_tag=f"{self.api_type}.oauth")
        res = self._json(response)

        if response.status_code == 200:
            if "access_token" in res:
                self.access_token = res['access_token']
            if "token_type" in res:
                self.token_type = res['token_type']

            if (self.access_token is not None) and (self.token_type is not None):
                self.headers['authorization'] = f"{self.token_type} {self.access_token}"

        return res

    def set_data_queue(self, queue):
        """
        Inject a queue for receiving realtime data.
        """
        self.queue = queue

    def add_data(self, data):
        if self.queue is not None:
            self.queue.put(data)

    def add_price(self, data):
        self.add_data(data)

    def add_trade(self, data):
        self.add_data(data)

    def add_orderbook(self, data):
        self.add_data(data)



