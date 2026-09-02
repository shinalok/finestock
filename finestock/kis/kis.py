import asyncio
from datetime import datetime
import json
import time
import websockets
from loguru import logger
import finestock
from finestock.comm import API


class Kis(API):
    # 초당 거래건수 제한(EGW00201) 대응. 요청 사이 최소 간격을 둬서 미리 제한에
    # 걸리지 않게 하고(쓰로틀링), 그래도 EGW00201 응답을 받으면 짧게 쉬었다가
    # 재시도한다. 모의투자(KisV)는 이 제한이 더 빡빡해서 특히 도움이 된다.
    _MIN_REQUEST_INTERVAL = 0.3  # 초
    _RATE_LIMIT_MSG_CD = "EGW00201"
    _MAX_RETRIES = 3

    def __init__(self):
        super().__init__()
        self.approval_key = None
        self.headers_rt = {"custtype": "P", "tr_type": "1", "content-type": "utf-8"}
        self._last_request_time = 0.0
        print("create Kis Components")

    def _throttle(self):
        elapsed = time.monotonic() - self._last_request_time
        wait = self._MIN_REQUEST_INTERVAL - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_time = time.monotonic()

    def _throttled_request(self, method, url, headers=None, params=None, data=None, log_tag=None):
        """
        KIS TR 공통 요청 헬퍼. self._request + self._json에 쓰로틀링/재시도를 얹은
        버전. 반환값은 self._json(response)와 동일(파싱된 JSON dict) — 호출부의
        기존 rt_cd 체크 로직은 그대로 둔다.
        """
        res = None
        for attempt in range(self._MAX_RETRIES + 1):
            self._throttle()
            response = self._request(method, url, headers=headers, params=params, data=data, log_tag=log_tag)
            res = self._json(response)
            if res.get("msg_cd") != self._RATE_LIMIT_MSG_CD:
                return res
            logger.warning(f"[{log_tag or self.api_type}] 초당 거래건수 제한({self._RATE_LIMIT_MSG_CD}) "
                            f"응답 ({attempt + 1}/{self._MAX_RETRIES + 1}회)")
        return res

    def oauth(self, header=None, data=None):
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        header = {"Content-Type": "application/json; charset=UTF-8"}
        return super().oauth(header=header, data=json.dumps(data))

    def approval(self):
        header = self.headers.copy()
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret
        }
        response = self._request("POST", f"{self.DOMAIN}/oauth2/Approval", headers=header, data=json.dumps(data), log_tag="Kis.approval")
        res = self._json(response)
        if response.status_code == 200 and "approval_key" in res:
            self.approval_key = res['approval_key']
        return res

    def get_price(self, code):
        today = datetime.now().strftime('%Y%m%d')
        res = self.get_ohlcv(code, frdate=today, todate=today)
        return res[0] if res else None

    def get_ohlcv(self, code, frdate=None, todate=None):
        # 기본값을 datetime.now()로 즉시 평가해 함수 시그니처에 박아두면 모듈을
        # import한 시점의 날짜로 영구히 고정되어버린다(파이썬 기본 인자는 함수
        # 정의 시 단 한 번만 평가됨). 그래서 None을 받아 호출마다 평가한다.
        frdate = frdate or datetime.now().strftime('%Y%m%d')
        todate = todate or datetime.now().strftime('%Y%m%d')
        header = self.headers.copy()
        header["tr_id"] = "FHKST03010100"
        param = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": code,
            "fid_input_date_1": frdate,
            "fid_input_date_2": todate,
            "fid_period_div_code": "D", #D:일봉, W:주봉, M:월봉, Y:년봉,
            "fid_org_adj_prc": "0" #0:수정주가, 1: 원주가
        }
        res = self._throttled_request("GET", f"{self.DOMAIN}/{self.CHART}", headers=header, params=param, log_tag="Kis.get_ohlcv")

        ohlcvs = []
        if res.get("rt_cd") == "0":
            data = res["output2"]
            print(data)
            for price in data:
                ohlcvs.append(finestock.Price(price["stck_bsop_date"], code, price["stck_clpr"], price["stck_oprc"], price["stck_hgpr"], price["stck_lwpr"], price["stck_clpr"], price["acml_vol"], price["acml_tr_pbmn"]))
        else:
            # rt_cd != "0"인 원인은 다양하다(레이트리밋 EGW00201, 잘못된 종목코드, 토큰
            # 만료 등) — 예전엔 여기서 조용히 빈 리스트를 반환해 "데이터가 없다"와
            # "조회가 실패했다"를 호출자가 구분할 수 없었다. 최소한 로그로는 남긴다.
            logger.error(f"[Kis.get_ohlcv] 시세 조회 실패: {res}")

        return ohlcvs

    def get_ohlcv_min(self, code, todate="", exchgubun="K", cts_date="", cts_time="", tr_cont_key=""):
        # TODO: KIS 분봉 조회 TR(FHKST03010200) 미연동. 우선 인터페이스 계약만 충족.
        print("Kis get_ohlcv_min not supported yet")
        return []

    def get_index(self, code, frdate=None, todate=None):
        # get_ohlcv와 동일한 이유로 None을 받아 호출마다 오늘 날짜를 평가한다.
        frdate = frdate or datetime.now().strftime('%Y%m%d')
        todate = todate or datetime.now().strftime('%Y%m%d')
        header = self.headers.copy()
        header["tr_id"] = "FHKUP03500100"
        param = {
            "fid_cond_mrkt_div_code": "U",
            "fid_input_iscd": code,
            "fid_input_date_1": frdate,
            "fid_input_date_2": todate,
            "fid_period_div_code": "D", #D:일봉, W:주봉, M:월봉, Y:년봉,
            "fid_org_adj_prc": "0" #0:수정주가, 1: 원주가
        }
        res = self._throttled_request("GET", f"{self.DOMAIN}/{self.INDEX}", headers=header, params=param, log_tag="Kis.get_index")
        ohlcvs = []
        if res.get("rt_cd") == "0":
            data = res["output2"]
            for price in data:
                ohlcvs.append(finestock.Price(price["stck_bsop_date"], code, price["bstp_nmix_prpr"], price["bstp_nmix_oprc"], price["bstp_nmix_hgpr"], price["bstp_nmix_lwpr"], price["bstp_nmix_prpr"], price["acml_vol"], price["acml_tr_pbmn"]))
        else:
            logger.error(f"[Kis.get_index] 지수 조회 실패: {res}")

        return ohlcvs

    def get_index_min(self, code, todate="", cts_date=" ", cts_time="", tr_cont_key=""):
        # TODO: KIS 지수 분봉 조회 TR 미연동. 우선 인터페이스 계약만 충족.
        print("Kis get_index_min not supported yet")
        return []

    def get_orderbook(self, code):
        header = self.headers.copy()
        header["tr_id"] = "FHKST01010200"
        param = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": code
        }
        res = self._throttled_request("GET", f"{self.DOMAIN}/{self.ORDERBOOK}", headers=header, params=param, log_tag="Kis.get_orderbook")

        if res.get('rt_cd') != "0":
            logger.error(f"[Kis.get_orderbook] 호가 조회 실패: {res}")
            return None

        output1 = res['output1']
        sells = []
        for i in range(1, 11):
            sells.append(finestock.Hoga(int(output1[f'askp{i}']), int(output1[f'askp_rsqn{i}'])))

        buys = []
        for i in range(1, 11):
            buys.append(finestock.Hoga(int(output1[f'bidp{i}']), int(output1[f'bidp_rsqn{i}'])))

        output2 = res['output2']
        code = output2['stck_shrn_iscd']
        total_buy = output1['total_bidp_rsqn']
        total_sell = output1['total_askp_rsqn']
        order = finestock.OrderBook(code, total_buy, total_sell, buys, sells)
        return order

    def get_balance(self):
        header = self.headers.copy()
        header["tr_id"] = "TTTC8434R" # 모의: VTTC8434R, 실전:TTTC8434R
        param = {
            "CANO": self.account_num,
            "ACNT_PRDT_CD": self.account_num_sub,
            "AFHR_FLPR_YN": "N",  # 시간외단일가여부(N: 기본값, Y: 시간외단일가)
            "OFL_YN": "",  # 공란
            "INQR_DVSN": "02",  # 조회구분(01: 대출일별, 02: 종목별)
            "UNPR_DVSN": "01",  # 단가구분(01: 기본값)
            "FUND_STTL_ICLD_YN": "N",  # 펀드결제분포함여부
            "FNCG_AMT_AUTO_RDPT_YN": "N",  # 융자금액자동상환여부
            "PRCS_DVSN": "00",  # 처리구분(00: 전일매매포함, 01: 전일매매비포함)
            "CTX_AREA_FK100": "",  # 연속조회검색조건100
            "CTX_AREA_NK100": ""  # 연속조회키100
        }
        res = self._throttled_request("GET", f"{self.DOMAIN}/{self.ACCOUNT}", headers=header, params=param, log_tag="Kis.get_balance")
        print(res)

        if res.get('rt_cd') != "0":
            logger.error(f"[Kis.get_balance] 잔고 조회 실패: {res}")
            return None

        hold = res["output1"]
        acc = res["output2"][0]

        holds = []
        for stock in hold:
            holds.append(
                finestock.Hold(stock['pdno'], stock['prdt_name'], float(stock['pchs_avg_pric']), int(stock['hldg_qty']), int(stock['pchs_amt']),
                     int(stock['evlu_amt'])))

        return finestock.Account(self.account_num, self.account_num_sub, int(acc["dnca_tot_amt"]), int(acc["nxdy_excc_amt"]),
                       int(acc["prvs_rcdl_excc_amt"]), holds)

    def get_holds(self):
        balance = self.get_balance()
        return balance.hold if balance else []

    def do_order(self, code, buy_flag, price, qty, excg_id_dvsn_cd="KRX"):
        # 2025-03 넥스트레이드(NXT) 도입 이후 KIS 주식주문(현금) TR이 거래소 라우팅을
        # 지원하는 TTTC0012U(매수)/TTTC0011U(매도)로 바뀌었다(구 TTTC0802U/TTTC0801U는
        # 더 이상 공식 예제에 등장하지 않는다 — koreainvestment/open-trading-api
        # examples_llm/domestic_stock/order_cash/order_cash.py 기준). excg_id_dvsn_cd로
        # 어느 거래소로 보낼지 고른다("KRX"/"NXT"/"SOR" — SOR은 스마트오더라우팅으로
        # 자동으로 유리한 거래소를 골라준다). 기본값은 기존 동작과 동일한 KRX.
        url = f"{self.DOMAIN}/{self.ORDER}"
        header = self.headers.copy()
        header["tr_id"] = "TTTC0012U" if buy_flag == finestock.ORDER_FLAG.BUY else "TTTC0011U" #[실전]매수: TTTC0012U, 매도: TTTC0011U
        dvsn = "01" if price == 0 else "00" #00: 지정가, 01:시장가

        param = {
            "CANO": self.account_num,
            "ACNT_PRDT_CD": self.account_num_sub,
            "PDNO": code,  # 종목코드
            "ORD_DVSN": dvsn,  # 주문구분(00: 지정가, 01:시장가)
            "ORD_QTY": str(qty),  # 주문수량
            "ORD_UNPR": str(price),  # 주문단가
            "EXCG_ID_DVSN_CD": excg_id_dvsn_cd,  # 거래소ID구분코드(KRX/NXT/SOR)
            "SLL_TYPE": "",  # 매도유형(매도 주문에서만 쓰임 — 01/02/05)
            "CNDT_PRIC": ""  # 조건가격(스탑지정가 등에서만 쓰임)
        }

        res = self._throttled_request("POST", url, headers=header, data=json.dumps(param), log_tag="Kis.do_order")
        print(res)

        if res.get('rt_cd') == "0":
            data = res['output']
            return finestock.Order(code, '', price, qty, buy_flag, data['ODNO'], data['ORD_TMD'],
                                   krx_fwdg_ord_orgno=data.get('KRX_FWDG_ORD_ORGNO'))

        logger.error(f"[Kis.do_order] 주문 실패: {res}")
        return None

    def get_order_status(self, code, tr_id="TTTC0084R"):
        """
        정정취소 가능한(=아직 미체결/일부체결로 남아있는) 주문을 조회한다 —
        주식정정취소가능주문조회(TTTC0084R). koreainvestment/open-trading-api
        examples_llm/domestic_stock/inquire_psbl_rvsecncl 기준으로 검증했고,
        정정취소(order-rvsecncl) 호출 전에 이 TR로 먼저 조회하라는 것이 KIS 공식
        가이드다. 원본 예제엔 env_dv(실전/모의) 분기가 아예 없고 tr_id가
        "TTTC0084R" 하나로 고정돼 있다 — 다른 KIS TR처럼 TTTC<->VTTC 접두어가 항상
        쌍으로 존재한다고 넘겨짚지 말 것.

        실제로 모의투자(openapivts) 서버에 TTTC0084R/VTTC0084R 둘 다 호출해보면
        각각 msg_cd=EGW02006("모의투자 TR 이 아닙니다")/OPSQ0002("없는 서비스
        코드 입니다")로 거부된다 — 즉 이 TR 자체가 KIS 모의투자 환경에서는 제공되지
        않는 것으로 보인다(자세한 내용은 kis_v.py의 관련 주석 참고).
        실전(Kis, TTTC0084R)에서 정상 동작하는지는 실전 계좌로 아직 검증하지 못했다.

        code가 주어지면 그 종목(pdno)만 걸러서 반환하고, None/빈 문자열이면 전체
        보유 미체결 주문을 반환한다.

        반환된 Order.krx_fwdg_ord_orgno는 응답의 ord_gno_brno(주문채번지점번호)를
        그대로 담은 값이다 — do_order()가 돌려주는 KRX_FWDG_ORD_ORGNO(한국거래소전송
        주문조직번호)와 같은 값일 것으로 보이지만(두 TR 모두 "이 주문을 낸 조직/지점
        번호"라는 같은 개념을 가리킴), KIS 공식 문서로 완전히 1:1 확인하지는 못했다 —
        do_order_cancel/do_order_modify에 넘기기 전에 한 번 검증해보는 걸 권장한다.

        ※ 연속조회(최대 50건/페이지, CTX_AREA_FK100/NK100)는 아직 구현하지 않았다
        — 미체결 주문이 50건을 넘으면 뒤쪽 페이지는 조회되지 않는다.
        """
        header = self.headers.copy()
        header["tr_id"] = tr_id
        param = {
            "CANO": self.account_num,
            "ACNT_PRDT_CD": self.account_num_sub,
            # 조회구분1/2의 정확한 코드 의미는 공식 문서로 확인 못 했다 — KIS 공식
            # 체크 예제(chk_inquire_psbl_rvsecncl.py)가 실제로 쓰는 값을 그대로 썼다.
            "INQR_DVSN_1": "1",
            "INQR_DVSN_2": "0",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }
        res = self._throttled_request("GET", f"{self.DOMAIN}/{self.INQUIRE_PSBL_RVSECNCL}",
                                       headers=header, params=param, log_tag="Kis.get_order_status")

        if res.get('rt_cd') != "0":
            logger.error(f"[Kis.get_order_status] 정정취소가능주문 조회 실패: {res}")
            return []

        orders = []
        for o in res.get('output', []):
            if code and o.get('pdno') != code:
                continue
            sll_buy = o.get('sll_buy_dvsn_cd')  # 00:전체 01:매도 02:매수
            if sll_buy == "01":
                order_flag = finestock.ORDER_FLAG.SELL
            elif sll_buy == "02":
                order_flag = finestock.ORDER_FLAG.BUY
            else:
                order_flag = finestock.ORDER_FLAG.VIEW
            orders.append(finestock.Order(
                o.get('pdno', code), o.get('prdt_name', ''), int(o.get('ord_unpr') or 0),
                int(o.get('ord_qty') or 0), order_flag, o.get('odno', ''), o.get('ord_tmd'),
                krx_fwdg_ord_orgno=o.get('ord_gno_brno')))
        return orders

    def _order_rvsecncl(self, tr_id, rvse_cncl_dvsn_cd, order_num, code, price, qty,
                         krx_fwdg_ord_orgno, ord_dvsn, qty_all_ord_yn, excg_id_dvsn_cd):
        """
        주식주문(정정취소) 공통 호출. KIS는 정정(01)과 취소(02)를 같은 TR/엔드포인트로
        처리한다 — koreainvestment/open-trading-api examples_llm/domestic_stock/
        order_rvsecncl/order_rvsecncl.py 기준. do_order_cancel/do_order_modify가
        rvse_cncl_dvsn_cd만 다르게 이 메서드를 호출한다.

        krx_fwdg_ord_orgno는 do_order()가 반환한 Order.krx_fwdg_ord_orgno 값을 그대로
        넘겨야 한다 — KIS가 브로커/지점 라우팅에 쓰는 값이라 임의로 채울 수 없다.
        """
        if not krx_fwdg_ord_orgno:
            logger.error(f"[{self.api_type}._order_rvsecncl] krx_fwdg_ord_orgno가 없습니다 — "
                         f"do_order()가 반환한 Order.krx_fwdg_ord_orgno를 넘겨주세요.")
            return None

        url = f"{self.DOMAIN}/{self.ORDER_RVSECNCL}"
        header = self.headers.copy()
        header["tr_id"] = tr_id
        param = {
            "CANO": self.account_num,
            "ACNT_PRDT_CD": self.account_num_sub,
            "KRX_FWDG_ORD_ORGNO": krx_fwdg_ord_orgno,  # 한국거래소전송주문조직번호(원주문 응답값)
            "ORGN_ODNO": order_num,  # 원주문번호
            "ORD_DVSN": ord_dvsn,  # 주문구분(00: 지정가, 01:시장가)
            "RVSE_CNCL_DVSN_CD": rvse_cncl_dvsn_cd,  # 정정취소구분코드(01: 정정, 02: 취소)
            "ORD_QTY": str(qty),  # 주문수량(잔량 전부면 QTY_ALL_ORD_YN=Y이므로 무시됨)
            "ORD_UNPR": str(price),  # 주문단가(취소면 의미 없음)
            "QTY_ALL_ORD_YN": qty_all_ord_yn,  # 잔량전부주문여부(Y: 전량, N: 일부)
            "EXCG_ID_DVSN_CD": excg_id_dvsn_cd  # 거래소ID구분코드(KRX/NXT/SOR)
        }

        res = self._throttled_request("POST", url, headers=header, data=json.dumps(param),
                                       log_tag=f"{self.api_type}._order_rvsecncl")
        print(res)

        if res.get('rt_cd') == "0":
            data = res['output']
            return finestock.Order(code, '', price, qty, finestock.ORDER_FLAG.VIEW, data['ODNO'], data['ORD_TMD'],
                                   krx_fwdg_ord_orgno=data.get('KRX_FWDG_ORD_ORGNO', krx_fwdg_ord_orgno))

        logger.error(f"[{self.api_type}._order_rvsecncl] 정정/취소 실패: {res}")
        return None

    def do_order_cancel(self, order_num, code, qty, krx_fwdg_ord_orgno="",
                        ord_dvsn="00", qty_all_ord_yn="Y", excg_id_dvsn_cd="KRX"):
        # qty_all_ord_yn="Y"(기본값)이면 잔량 전부를 취소하므로 qty는 무시된다.
        # 일부만 취소하려면 qty_all_ord_yn="N"과 함께 실제 취소 수량을 qty로 넘긴다.
        return self._order_rvsecncl("TTTC0013U", "02", order_num, code, 0, qty,
                                    krx_fwdg_ord_orgno, ord_dvsn, qty_all_ord_yn, excg_id_dvsn_cd)

    def do_order_modify(self, order_num, code, price, qty, krx_fwdg_ord_orgno="",
                        ord_dvsn="00", qty_all_ord_yn="Y", excg_id_dvsn_cd="KRX"):
        # 정정 가능 수량은 원주문 수량을 넘을 수 없다(원주문의 미체결 수량 이하만 가능).
        return self._order_rvsecncl("TTTC0013U", "01", order_num, code, price, qty,
                                    krx_fwdg_ord_orgno, ord_dvsn, qty_all_ord_yn, excg_id_dvsn_cd)

    def get_index_list(self):
        print("Kis not supported")

    def get_stock_list(self, mrkt_tp="0"):
        # TODO: KIS 종목 리스트 조회 TR 미연동. 우선 인터페이스 계약만 충족.
        print("Kis get_stock_list not supported yet")
        return []

    async def connect(self):
        self.approval()
        self.ws = await websockets.connect(self.DOMAIN_WS)

    async def recv_price(self, code, status=True):
        pass

    async def recv_index(self, code, status=True):
        pass

    async def recv_orderbook(self, code, status=True):
        pass

    async def recv_trade(self, code, status=True):
        pass

    '''
    async def connect(self):
        print("connecting...")
        print(uri)
        websocket = await websockets.connect(uri)
        print("success connection")
        return websocket
    '''
