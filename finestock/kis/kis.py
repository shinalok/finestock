import asyncio
from datetime import datetime
import json
import websockets
import finestock
from finestock.comm import API


class Kis(API):
    def __init__(self):
        super().__init__()
        self.approval_key = None
        self.headers_rt = {"custtype": "P", "tr_type": "1", "content-type": "utf-8"}
        print("create Kis Components")

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
        response = self._request("GET", f"{self.DOMAIN}/{self.CHART}", headers=header, params=param, log_tag="Kis.get_ohlcv")
        res = self._json(response)

        ohlcvs = []
        if res["rt_cd"] == "0":
            data = res["output2"]
            print(data)
            for price in data:
                ohlcvs.append(finestock.Price(price["stck_bsop_date"], code, price["stck_clpr"], price["stck_oprc"], price["stck_hgpr"], price["stck_lwpr"], price["stck_clpr"], price["acml_vol"], price["acml_tr_pbmn"]))

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
        response = self._request("GET", f"{self.DOMAIN}/{self.INDEX}", headers=header, params=param, log_tag="Kis.get_index")
        res = self._json(response)
        ohlcvs = []
        if res["rt_cd"] == "0":
            data = res["output2"]
            for price in data:
                ohlcvs.append(finestock.Price(price["stck_bsop_date"], code, price["bstp_nmix_prpr"], price["bstp_nmix_oprc"], price["bstp_nmix_hgpr"], price["bstp_nmix_lwpr"], price["bstp_nmix_prpr"], price["acml_vol"], price["acml_tr_pbmn"]))

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
        response = self._request("GET", f"{self.DOMAIN}/{self.ORDERBOOK}", headers=header, params=param, log_tag="Kis.get_orderbook")
        res = self._json(response)

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
        response = self._request("GET", f"{self.DOMAIN}/{self.ACCOUNT}", headers=header, params=param, log_tag="Kis.get_balance")
        res = self._json(response)
        print(res)

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

    def do_order(self, code, buy_flag, price, qty):
        url = f"{self.DOMAIN}/{self.ORDER}"
        header = self.headers.copy()
        header["tr_id"] = "TTTC0802U" if buy_flag == finestock.ORDER_FLAG.BUY else "TTTC0801U" #[실전]매수: TTTC0802U, 매도: TTTC0801U
        dvsn = "01" if price == 0 else "00" #00: 지정가, 01:시장가

        param = {
            "CANO": self.account_num,
            "ACNT_PRDT_CD": self.account_num_sub,
            "PDNO": code,  # 종목코드
            "ORD_DVSN": dvsn,  # 주문구분(00: 지정가, 01:시장가)
            "ORD_QTY": str(qty),  # 주문수량(01: 대출일별, 02: 종목별)
            "ORD_UNPR": str(price)  # 주문단가(01: 기본값)
        }

        response = self._request("POST", url, headers=header, data=json.dumps(param), log_tag="Kis.do_order")
        res = self._json(response)
        print(res)

        if res['rt_cd'] == "0":
            data = res['output']
            return finestock.Order(code, '', price, qty, buy_flag,
                         data['ODNO'], data['ORD_TMD'])


    def get_order_status(self, code):
        pass

    def do_order_cancel(self, order_num, code, qty):
        pass

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
