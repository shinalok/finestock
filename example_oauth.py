"""
example_oauth.py — 앱키/시크릿을 설정하고 접근토큰을 발급받는 최소 예제.

기본 브로커는 KISV(한국투자증권 모의투자)이며, 다른 Provider로 테스트하려면
아래 PROVIDER 값을 바꾼다 (예: APIProvider.NH, APIProvider.NHV, APIProvider.LSV, ...).

사용법:
    .env.example을 .env로 복사해 APP_KEY/APP_SECRET 값을 채운 뒤 실행한다.
    (또는 PowerShell: $env:APP_KEY = "..."; $env:APP_SECRET = "...")
    python example_oauth.py

$env:LOG_LEVEL = "DEBUG"를 함께 설정하면 api._request()가 남기는 요청/응답 로그를
확인할 수 있다. appkey/appsecret/authorization 같은 민감한 값은 로그에 '***'로
마스킹되어 출력된다.
"""
import os
import sys
from loguru import logger

import finestock
from finestock import APIProvider
from finestock.comm.api_interface import AuthenticationProvider

# Windows 콘솔의 기본 코드페이지(cp949 등)에서는 한글 출력이 깨질 수 있어 표준출력을
# UTF-8로 강제한다.
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

# 기본 레벨은 INFO. api._request()가 남기는 요청/응답 로그(민감한 값은 '***'로
# 마스킹된 상태)를 보려면 LOG_LEVEL=DEBUG로 실행한다.
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logger.remove()
logger.add(sys.stdout, level=LOG_LEVEL)

PROVIDER = APIProvider.KISV


def main():
    finestock.print_version_info()

    print(f"Selected Provider: {PROVIDER.name}")

    # 실키/시크릿은 절대 코드에 하드코딩하지 말 것. 환경변수(.env 또는 $env:)로 주입한다.
    app_key = os.environ.get("APP_KEY", "YOUR_APP_KEY")
    app_secret = os.environ.get("APP_SECRET", "YOUR_APP_SECRET")

    if app_key == "YOUR_APP_KEY" or app_secret == "YOUR_APP_SECRET":
        print("APP_KEY/APP_SECRET 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    api = finestock.create_api(PROVIDER)

    # api는 여러 인터페이스(Authentication/MarketData/Trading/...)를 한 번에 구현한
    # 파사드 객체다. 로그인(oauth) 관련 메서드만 쓸 거라면 AuthenticationProvider로
    # 좁혀서 써도 된다 (런타임 제약은 아니고 IDE 자동완성을 위한 타입 힌트용 관례).
    auth_api: AuthenticationProvider = api
    auth_api.set_oauth_info(app_key, app_secret)

    try:
        token = auth_api.oauth()
    except finestock.FinestockNetworkError as e:
        # 타임아웃(기본: 연결 3초/응답 10초)이나 연결 실패 시 발생한다.
        print(f"[네트워크 오류] 브로커 서버에 연결하지 못했습니다: {e}")
        sys.exit(1)
    except finestock.FinestockAPIError as e:
        # 브로커가 응답은 했지만 JSON이 아닌 바디(502/HTML 에러 페이지 등)를 반환한 경우.
        print(f"[API 오류] status={e.status_code}, body={e.response_text!r}")
        sys.exit(1)

    print(f"응답: {token}")
    access_token = token.get("access_token")
    if access_token:
        print(f"발급된 access_token: {access_token}")
        print(f"token_type: {token.get('token_type')}")
        print("로그인 성공.")
    else:
        print("access_token이 설정되지 않았습니다. 위 응답 내용을 확인하세요.")


if __name__ == "__main__":
    main()
