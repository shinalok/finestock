_EBEST_ = {
    "DOMAIN": "https://openapi.ebestsec.co.kr:8080",
    "DOMAIN_WS": "wss://openapi.ebestsec.co.kr:9443/websocket",
    "OAUTH": "oauth2/token",
    "REVOKE": "oauth2/revoke",
    "CHART": "stock/chart",
    "INDEX": "indtp/chart",
    "ORDERBOOK": "stock/market-data",
    "PRICE": "stock/market-data",
    "ACCOUNT": 	"stock/accno",
    "ORDER": "stock/order",
    "INDEX_LIST": "indtp/market-data",
    "STOCK_LIST": "stock/etc",
    "CONDITION_LIST": "stock/item-search",
}

_LS_ = {
    "DOMAIN": "https://openapi.ls-sec.co.kr:8080",
    "DOMAIN_WS": "wss://openapi.ls-sec.co.kr:9443/websocket",
    "OAUTH": "oauth2/token",
    "REVOKE": "oauth2/revoke",
    "CHART": "stock/chart",
    "INDEX": "indtp/chart",
    "ORDERBOOK": "stock/market-data",
    "PRICE": "stock/market-data",
    "ACCOUNT": 	"stock/accno",
    "ORDER": "stock/order",
    "INDEX_LIST": "indtp/market-data",
    "STOCK_LIST": "stock/etc",
    "CONDITION": "stock/item-search",
}
_LS_V_ = {
    **_LS_,
    "DOMAIN_WS":"wss://openapi.ls-sec.co.kr:29443/websocket"
}
_KIS_ = {
    "DOMAIN": "https://openapi.koreainvestment.com:9443",
    "DOMAIN_WS": "ws://ops.koreainvestment.com:21000",
    "OAUTH": "oauth2/tokenP",
    "REVOKE": "oauth2/revokeP",
    "CHART": "uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
    "ACCOUNT": 	"uapi/domestic-stock/v1/trading/inquire-balance",
    "ORDER": "uapi/domestic-stock/v1/trading/order-cash",
    "INDEX": "uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice",
    "ORDERBOOK": "uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn",
}
_KIS_V_ = {
    **_KIS_,
    "DOMAIN":"https://openapivts.koreainvestment.com:29443",
}

_KIWOOM_ = {
    "DOMAIN": "https://api.kiwoom.com",
    "DOMAIN_WS": "wss://api.kiwoom.com:10000/api/dostk/websocket",
    "OAUTH": "oauth2/token",
    "REVOKE": "oauth2/revoke",
    "STOCK_CHART": "api/dostk/chart",
    "INDEX_CHART": "api/dostk/chart", # Using same endpoint based on research
    "STOCK_INFO": "api/dostk/stkinfo",
    "STOCK_ORDERBOOK": "api/dostk/mrkcond", # TR ka10004
    "CHART": "uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice", # Placeholder to keep compatibility if used elsewhere
    "ACCOUNT": 	"uapi/domestic-stock/v1/trading/inquire-balance", # Placeholder
    "ORDER": "uapi/domestic-stock/v1/trading/order-cash", # Placeholder
}

_KIWOOM_V_ = {
    **_KIWOOM_,
    "DOMAIN": "https://api.kiwoom.com", # Default is https://api.kiwoom.com ??? Wait, main DOMAIN is api.kiwoom.com
    # User said: mockapi.kiwoom.com in previous example.
    # Let's verify standard. 
    # If main is api.kiwoom.com (Production), then mock is likely openapi.kiwoom.com or mockapi.kiwoom.com.
    # User's example said: #host = 'https://mockapi.kiwoom.com' # 모의투자
    # So I will use that.
    "DOMAIN": "https://mockapi.kiwoom.com",
    "DOMAIN_WS": "wss://mockapi.kiwoom.com:10000/api/dostk/websocket",
}

_NH_ = {
    "DOMAIN": "https://api.nhplug.com:8443",
    "DOMAIN_WS": "wss://api.nhplug.com:7070",
    # 접근토큰발급(oauth2/token)은 모의투자 미제공 — 항상 운영 도메인에서만 발급.
    # NhV(모의투자)에서도 이 값은 바뀌지 않는다.
    "OAUTH_DOMAIN": "https://api.nhplug.com:8443",
    "OAUTH": "oauth2/token",
    "ACCOUNT_LIST": "n2/acctinfo",
    "ORDER_CASH_BUY": "krstock/order/v1/cashBuy",
    "ORDER_CASH_SELL": "krstock/order/v1/cashSell",
    "ORDER_CANCEL": "krstock/order/v1/cancel",
    "ORDER_MODIFY": "krstock/order/v1/modify",
    "BALANCE": "krstock/inquiry/v1/balance",
    "PRICE": "krstock/quote/v1/currentPrice",
    "CHART": "krstock/quote/v1/period",
}
_NH_V_ = {
    **_NH_,
    "DOMAIN": "https://moapi.nhplug.com:8443",
    "DOMAIN_WS": "wss://moapi.nhplug.com:17070",
}

_API_PATH_ = {
    "EBest": {**_EBEST_},
    "LS": {**_LS_},
    "LSV": {**_LS_V_},
    "Kis": {**_KIS_},
    "KisV": {**_KIS_V_},
    "Kiwoom": {**_KIWOOM_},
    "KiwoomV": {**_KIWOOM_V_},
    "Nh": {**_NH_},
    "NhV": {**_NH_V_},
}