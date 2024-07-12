import json
import requests
import finestock
from finestock.kis import Kis


class KisV(Kis):
    def __init__(self):
        super().__init__()
        print("create Kis_Test Components")


    def get_balance(self):
        header = self.headers.copy()
        header["tr_id"] = "VTTC8434R" # 모의: VTTC8434R, 실전:TTTC8434R
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
        print(header)
        response = requests.get(f"{self.DOMAIN}/{self.ACCOUNT}", headers=header, params=param)
        res = response.json()
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

    def do_order(self, code, buy_flag, price, qty):
        url = f"{self.DOMAIN}/{self.ORDER}"
        header = self.headers.copy()
        header["tr_id"] = "VTTC0802U" if buy_flag == finestock.ORDER_FLAG.BUY else "VTTC0801U" #[모의]매수: VTTC0802U, 매도: VTTC0801U
        dvsn = "01" if price == 0 else "00" #00: 지정가, 01:시장가

        param = {
            "CANO": self.account_num,
            "ACNT_PRDT_CD": self.account_num_sub,
            "PDNO": code,  # 종목코드
            "ORD_DVSN": dvsn,  # 주문구분(00: 지정가, 01:시장가)
            "ORD_QTY": str(qty),  # 주문수량(01: 대출일별, 02: 종목별)
            "ORD_UNPR": str(price)  # 주문단가(01: 기본값)
        }

        response = requests.post(url, headers=header, data=json.dumps(param))
        res = response.json()
        print(res)

        if res['rt_cd'] == "0":
            data = res['output']
            return finestock.Order(code, '', price, qty,
                         data['ODNO'], data['ORD_TMD'])

    def get_order_status(self, code):
        pass

    def do_order_cancle(self, order_num, code, qty):
        pass

    '''
    async def connect(self):
        print("connecting...")
        print(uri)
        websocket = await websockets.connect(uri)
        print("success connection")
        return websocket
    '''