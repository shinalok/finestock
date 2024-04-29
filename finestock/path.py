_EBEST_ = {
    "DOMAIN": "https://openapi.ebestsec.co.kr:8080",
    "DOMAIN_WS": "wss://openapi.ebestsec.co.kr:9443/websocket",
    "OAUTH": "oauth2/token",
    "REVOKE": "oauth2/revoke",
    "CHART": "stock/chart",
    "INDEX": "indtp/chart",
    "ORDERBOOK": "stock/market-data",
    "ACCOUNT": 	"stock/accno",
    "ORDER": "stock/order",
    "INDEX_LIST": "indtp/market-data",
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
_API_PATH_ = {
    "EBest": {**_EBEST_},
    "Kis": {**_KIS_},
    "KisV": {**_KIS_V_},
}