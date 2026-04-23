import requests
import queue
from loguru import logger
from finestock.path import _API_PATH_
from .api_interface import BaseProvider

class API(BaseProvider):
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

    def oauth(self, header=None, data=None):
        url = f"{self.DOMAIN}/{self.OAUTH}"
        _header = header or {"Content-Type": "application/x-www-form-urlencoded"}
        _data = data or {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecretkey": self.app_secret
        }
        response = requests.post(url, headers=_header, data=_data)

        try:
            res_json = response.json()
        except Exception:
            res_json = response.text

        logger.debug(f"[API: oauth]\n"
                      f"[URL: {url}]\n"
                      f"[header: {_header}]\n"
                      f"[param: {_data}]\n"
                      f"[response: {res_json}]")

        if response.status_code == 200:
            res = response.json()
            if "access_token" in res:
                self.access_token = res['access_token']
            if "token_type" in res:
                self.token_type = res['token_type']

            if (self.access_token is not None) and (self.token_type is not None):
                self.headers['authorization'] = f"{self.token_type} {self.access_token}"
            return res
        else:
            # self.print_error(response)
            return response.json()

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



