"""
example_balance.py — 로그인 후 계좌 잔고/보유종목을 조회해본다.

사용법:
    .env.example을 .env로 복사해 APP_KEY/APP_SECRET/ACCOUNT_NUM 값을 채운 뒤 실행한다.
    (또는 PowerShell: $env:APP_KEY = "..."; $env:APP_SECRET = "..."; $env:ACCOUNT_NUM = "...")
    python example_balance.py

다른 브로커로 테스트하려면 아래 PROVIDER 값을 바꾼다 (예: APIProvider.NH).
"""
import os
import sys
from loguru import logger

import finestock
from finestock import APIProvider
from finestock.comm.api_interface import AccountProvider

from dotenv import load_dotenv
load_dotenv()

sys.stdout.reconfigure(encoding="utf-8")

# 기본 레벨은 INFO. 요청/응답 등 상세 로그를 보려면 LOG_LEVEL=DEBUG로 실행한다.
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logger.remove()
logger.add(sys.stdout, level=LOG_LEVEL)

PROVIDER = APIProvider.KISV


def login(provider):
    app_key = os.environ.get("APP_KEY", "YOUR_APP_KEY")
    app_secret = os.environ.get("APP_SECRET", "YOUR_APP_SECRET")
    account_num = os.environ.get("ACCOUNT_NUM", "YOUR_ACCOUNT_NUM")
    account_num_sub = os.environ.get("ACCOUNT_NUM_SUB", "01")

    if app_key == "YOUR_APP_KEY" or app_secret == "YOUR_APP_SECRET":
        print("APP_KEY/APP_SECRET 환경변수가 설정되지 않았습니다. .env를 확인하세요.")
        sys.exit(1)
    if account_num == "YOUR_ACCOUNT_NUM":
        print("ACCOUNT_NUM 환경변수가 설정되지 않았습니다. .env를 확인하세요.")
        sys.exit(1)

    api = finestock.create_api(provider)
    api.set_oauth_info(app_key, app_secret)
    api.set_account_info(account_num, account_num_sub)

    # .env에 ACCESS_TOKEN이 이미 있으면 그걸 그대로 쓰고 oauth() 재발급을 생략한다.
    # (매 실행마다 새로 로그인하면 브로커의 초당/일일 토큰 발급 제한에 걸리기 쉽다.)
    access_token = os.environ.get("ACCESS_TOKEN", "").strip()
    if access_token:
        api.set_access_token(access_token)
        print(f"로그인 성공 ({provider.name}) — ACCESS_TOKEN 환경변수 재사용, oauth() 생략.")
        return api

    try:
        api.oauth()
    except finestock.FinestockNetworkError as e:
        print(f"[네트워크 오류] 로그인 실패: {e}")
        sys.exit(1)
    except finestock.FinestockAPIError as e:
        print(f"[API 오류] 로그인 실패: status={e.status_code}, body={e.response_text!r}")
        sys.exit(1)

    if not api.access_token:
        print("로그인 실패: access_token이 발급되지 않았습니다.")
        sys.exit(1)
    print(f"로그인 성공 ({provider.name}) — oauth()로 새로 발급.")
    return api


def main():
    finestock.print_version_info()
    api = login(PROVIDER)

    # api는 여러 인터페이스(Authentication/MarketData/Trading/...)를 한 번에 구현한
    # 파사드 객체다. 잔고/보유종목 조회만 쓸 거라면 AccountProvider로 좁혀서 써도 된다
    # (런타임 제약은 아니고 IDE 자동완성을 위한 타입 힌트용 관례).
    account_api: AccountProvider = api

    print("\n[get_balance] 계좌 잔고 조회...")
    try:
        balance = account_api.get_balance()
    except finestock.FinestockNetworkError as e:
        print(f"[네트워크 오류] 잔고 조회 실패: {e}")
        sys.exit(1)
    except finestock.FinestockAPIError as e:
        print(f"[API 오류] 잔고 조회 실패: status={e.status_code}, body={e.response_text!r}")
        sys.exit(1)

    if not balance:
        print("잔고 조회 결과 없음(LOG_LEVEL=DEBUG로 실행하면 브로커 응답을 로그에서 확인할 수 있습니다).")
        return

    print(f"계좌: {balance.account_num}-{balance.account_num_sub}")
    print(f"예수금(deposit): {balance.deposit}")
    print(f"익일정산금(next_deposit): {balance.next_deposit}")
    print(f"가수도정산금(pay_deposit): {balance.pay_deposit}")
    print(f"보유종목 수: {len(balance.hold)}")

    if balance.hold:
        print(f"\n{'코드':<10} | {'종목명':<20} | {'평단가':>10} | {'수량':>8} | {'평가금액':>14}")
        print("-" * 72)
        for h in balance.hold:
            print(f"{h.code:<10} | {h.name:<20} | {h.price:>10} | {h.qty:>8} | {h.eval:>14}")
    else:
        print("보유종목 없음.")


if __name__ == "__main__":
    main()
