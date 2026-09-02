"""
example_trade.py — 로그인 후 지정가 매수 주문을 넣고, 정정(do_order_modify)한
뒤 취소(do_order_cancel)까지 한 번씩 실행해본다.

⚠ 기본 브로커(KISV, 한국투자증권 모의투자)라도 가상의 자금/계좌 상태가 실제로
바뀐다. 그래서 CONFIRM_TRADE = False인 동안은 무엇을 보낼지만 출력하고 실제
주문은 내지 않는다 — 실행하려면 아래 CONFIRM_TRADE를 True로 바꿔야 한다.

시장가 주문은 즉시 체결돼버려 정정/취소를 보여줄 수 없으므로, 호가창(매수 호가
10단계)에서 가장 낮은 매수호가를 지정가로 넣어 미체결 상태로 남긴다(정정/취소
대상이 있어야 하니). 현재가에서 임의로 몇 % 뺀 값으로 반올림하면 KRX 호가단위
(가격대별로 다름)에 안 맞아 "호가단위 오류"가 날 수 있어서, 거래소가 이미
유효하다고 알려준 호가창의 실제 가격을 그대로 쓴다.

사용법:
    .env.example을 .env로 복사해 APP_KEY/APP_SECRET/ACCOUNT_NUM 값을 채운 뒤 실행한다.
    (또는 PowerShell: $env:APP_KEY = "..."; $env:APP_SECRET = "..."; $env:ACCOUNT_NUM = "...")
    python example_trade.py

다른 브로커/종목으로 테스트하려면 아래 PROVIDER/CODE 값을 바꾼다.
"""
import os
import sys
from loguru import logger

import finestock
from finestock import APIProvider, ORDER_FLAG
from finestock.comm.api_interface import MarketDataProvider, TradingProvider

from dotenv import load_dotenv
load_dotenv()

sys.stdout.reconfigure(encoding="utf-8")

# 기본 레벨은 INFO. 요청/응답 등 상세 로그를 보려면 LOG_LEVEL=DEBUG로 실행한다.
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logger.remove()
logger.add(sys.stdout, level=LOG_LEVEL)

PROVIDER = APIProvider.KISV
CODE = "005930"  # 삼성전자
QTY = 1

# True로 바꿔야 실제로 주문이 나간다. False면 무엇을 보낼지만 출력하고 끝낸다 —
# 모의투자라도 이 스크립트를 재실행할 때마다 뜻하지 않게 주문이 쌓이지 않도록
# 하는 안전장치다.
CONFIRM_TRADE = True


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
    # 파사드 객체다. 시세 조회/주문만 쓸 거라면 MarketDataProvider/TradingProvider로
    # 좁혀서 써도 된다(런타임 제약은 아니고 IDE 자동완성을 위한 타입 힌트용 관례).
    market_api: MarketDataProvider = api
    trading_api: TradingProvider = api

    orderbook = market_api.get_orderbook(CODE)
    if not orderbook or not orderbook.buy:
        print(f"{CODE} 호가 조회 실패 — 주문을 진행할 수 없습니다.")
        return

    # 매수 호가 10단계(buy[0]=1호가/가장 높음 ~ buy[9]=10호가/가장 낮음) 전부 KRX가
    # 이미 유효하다고 인정한 가격이라, 여기서 그대로 골라 쓰면 호가단위 오류가 나지
    # 않는다. 가장 낮은 매수호가로 넣어 체결 위험 없이 미체결로 남기고, 정정
    # 데모에서는 그보다 한 단계 위(그래도 매수 진영 안쪽) 호가로 옮긴다.
    buy_levels = sorted({h.price for h in orderbook.buy if h.price > 0}, reverse=True)
    if len(buy_levels) < 2:
        print(f"{CODE} 매수 호가가 충분하지 않습니다({len(buy_levels)}단계) — 주문을 진행할 수 없습니다.")
        return
    buy_price = buy_levels[-1]      # 가장 낮은(먼) 매수호가 — 안전하게 미체결
    modify_price = buy_levels[-2]   # 그보다 한 호가 위 — 여전히 매수 진영 안쪽

    print(f"\n[do_order] 종목 {CODE} 매수호가 10단계 중 최저가 {buy_price}원에 {QTY}주 지정가 매수 주문 예정...")
    if not CONFIRM_TRADE:
        print("CONFIRM_TRADE = False — 실제로 주문을 보내지 않습니다.")
        print("실행하려면 파일 상단의 CONFIRM_TRADE를 True로 바꾸세요.")
        return

    try:
        order = trading_api.do_order(CODE, ORDER_FLAG.BUY, buy_price, QTY)
    except finestock.FinestockNetworkError as e:
        print(f"[네트워크 오류] 주문 실패: {e}")
        sys.exit(1)
    except finestock.FinestockAPIError as e:
        print(f"[API 오류] 주문 실패: status={e.status_code}, body={e.response_text!r}")
        sys.exit(1)

    if not order:
        print("주문 실패(브로커 응답을 LOG_LEVEL=DEBUG로 확인할 수 있습니다).")
        return
    print(f"주문 성공: order_num={order.order_num}, order_time={order.order_time}")

    print(f"\n[do_order_modify] 주문가를 {buy_price}원 -> {modify_price}원으로 정정...")
    try:
        modified = trading_api.do_order_modify(order.order_num, CODE, modify_price, QTY,
                                               krx_fwdg_ord_orgno=order.krx_fwdg_ord_orgno)
    except finestock.FinestockNetworkError as e:
        print(f"[네트워크 오류] 정정 실패: {e}")
        modified = None
    except finestock.FinestockAPIError as e:
        print(f"[API 오류] 정정 실패: status={e.status_code}, body={e.response_text!r}")
        modified = None

    if modified:
        print(f"정정 성공: order_num={modified.order_num}")
    else:
        print("정정 실패 또는 이 브로커에는 아직 미구현(None 반환).")

    # KIS는 정정 후에도 원주문번호/거래소전송조직번호로 취소할 수 있지만, 정정 응답이
    # 새 값을 내려줬다면 그쪽을 우선한다(브로커에 따라 정정 시 주문번호가 바뀔 수 있다).
    cancel_order_num = modified.order_num if modified else order.order_num
    cancel_krx_fwdg_ord_orgno = modified.krx_fwdg_ord_orgno if modified else order.krx_fwdg_ord_orgno

    print(f"\n[do_order_cancel] 주문(order_num={cancel_order_num}) 취소...")
    try:
        cancel = trading_api.do_order_cancel(cancel_order_num, CODE, QTY,
                                             krx_fwdg_ord_orgno=cancel_krx_fwdg_ord_orgno)
    except finestock.FinestockNetworkError as e:
        print(f"[네트워크 오류] 취소 실패: {e}")
        return
    except finestock.FinestockAPIError as e:
        print(f"[API 오류] 취소 실패: status={e.status_code}, body={e.response_text!r}")
        return

    if cancel:
        print(f"취소 성공: order_num={cancel.order_num}")
    else:
        # 취소가 안 됐다면 주문이 계좌에 그대로 남아있으니 직접 확인/정리해야 한다.
        print("취소 실패 또는 이 브로커에는 아직 미구현(None 반환) — 계좌에서 직접 확인하세요.")


if __name__ == "__main__":
    main()
