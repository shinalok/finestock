"""
example_price.py — 로그인 후 시세(get_price/get_ohlcv)를 조회해본다.

get_ohlcv는 frdate/todate를 생략하면 자동으로 오늘 날짜 기준으로 조회된다.

사용법:
    .env.example을 .env로 복사해 APP_KEY/APP_SECRET 값을 채운 뒤 실행한다.
    (또는 PowerShell: $env:APP_KEY = "..."; $env:APP_SECRET = "...")
    python example_price.py

다른 브로커/종목으로 테스트하려면 아래 PROVIDER/CODE 값을 바꾼다.
"""
import datetime
import os
import sys
import time
from loguru import logger

import finestock
from finestock import APIProvider

from dotenv import load_dotenv
load_dotenv()

sys.stdout.reconfigure(encoding="utf-8")

# 기본 레벨은 INFO. 요청/응답 등 상세 로그를 보려면 LOG_LEVEL=DEBUG로 실행한다.
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logger.remove()
logger.add(sys.stdout, level=LOG_LEVEL)

PROVIDER = APIProvider.KISV
CODE = "005930"  # 삼성전자

# KIS(모의투자)는 초당 거래건수 제한이 있어(EGW00201), 짧은 시간에 REST 호출을
# 연달아 보내면 제한에 걸릴 수 있다. 호출 사이에 넉넉히 쉬어준다.
RATE_LIMIT_DELAY = 1.1  # 초


def login(provider):
    app_key = os.environ.get("APP_KEY", "YOUR_APP_KEY")
    app_secret = os.environ.get("APP_SECRET", "YOUR_APP_SECRET")
    if app_key == "YOUR_APP_KEY" or app_secret == "YOUR_APP_SECRET":
        print("APP_KEY/APP_SECRET 환경변수가 설정되지 않았습니다. .env를 확인하세요.")
        sys.exit(1)

    api = finestock.create_api(provider)
    api.set_oauth_info(app_key, app_secret)

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


def print_price(label, price):
    if price is None:
        print(f"{label}: 조회 결과 없음")
        return
    print(f"{label}: {price.workday} 종가={price.close} 시가={price.open} "
          f"고가={price.high} 저가={price.low} 거래량={price.volume}")


def main():
    finestock.print_version_info()
    code = CODE
    api = login(PROVIDER)
    time.sleep(RATE_LIMIT_DELAY)  # oauth() 직후 바로 조회하면 같은 초에 걸릴 수 있어 한 텀 쉰다.

    # 1) get_price: 당일 시세 하나
    print(f"\n[get_price] 종목 {code} 당일 시세 조회...")
    price = api.get_price(code)
    print_price("get_price", price)

    # 2) get_ohlcv: frdate/todate를 생략하면 오늘 날짜 기준으로 조회된다.
    print(f"\n[get_ohlcv] 종목 {code} 기본 인자(오늘)로 두 번 연속 호출...")
    today = datetime.datetime.now().strftime("%Y%m%d")
    for i in (1, 2):
        time.sleep(RATE_LIMIT_DELAY)
        ohlcvs = api.get_ohlcv(code)
        got = ohlcvs[0].workday if ohlcvs else None
        print(f"  호출 {i}: 오늘={today}, 조회된 workday={got}, "
              f"레코드 수={len(ohlcvs) if ohlcvs else 0}")

    # 3) get_ohlcv: 명시적 기간 지정
    frdate = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y%m%d")
    todate = today
    print(f"\n[get_ohlcv] 종목 {code} 기간 조회 ({frdate} ~ {todate})...")
    time.sleep(RATE_LIMIT_DELAY)
    ohlcvs = api.get_ohlcv(code, frdate=frdate, todate=todate)
    print(f"  레코드 수: {len(ohlcvs) if ohlcvs else 0}")
    for p in (ohlcvs or [])[:5]:
        print_price("  ", p)


if __name__ == "__main__":
    main()
