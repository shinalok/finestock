import json
from loguru import logger
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
        res = self._throttled_request("GET", f"{self.DOMAIN}/{self.ACCOUNT}", headers=header, params=param, log_tag="KisV.get_balance")
        print(res)

        if res.get('rt_cd') != "0":
            logger.error(f"[KisV.get_balance] 잔고 조회 실패: {res}")
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

    def do_order(self, code, buy_flag, price, qty, excg_id_dvsn_cd="KRX"):
        # TR ID 변경 배경은 Kis.do_order 주석 참고(2025-03 NXT 도입 이후 개편).
        url = f"{self.DOMAIN}/{self.ORDER}"
        header = self.headers.copy()
        header["tr_id"] = "VTTC0012U" if buy_flag == finestock.ORDER_FLAG.BUY else "VTTC0011U" #[모의]매수: VTTC0012U, 매도: VTTC0011U
        dvsn = "01" if price == 0 else "00" #00: 지정가, 01:시장가

        param = {
            "CANO": self.account_num,
            "ACNT_PRDT_CD": self.account_num_sub,
            "PDNO": code,  # 종목코드
            "ORD_DVSN": dvsn,  # 주문구분(00: 지정가, 01:시장가)
            "ORD_QTY": str(qty),  # 주문수량
            "ORD_UNPR": str(price),  # 주문단가
            "EXCG_ID_DVSN_CD": excg_id_dvsn_cd,  # 거래소ID구분코드(KRX/NXT/SOR)
            "SLL_TYPE": "",  # 매도유형(매도 주문에서만 쓰임)
            "CNDT_PRIC": ""  # 조건가격(스탑지정가 등에서만 쓰임)
        }

        res = self._throttled_request("POST", url, headers=header, data=json.dumps(param), log_tag="KisV.do_order")
        print(res)

        if res.get('rt_cd') == "0":
            data = res['output']
            return finestock.Order(code, '', price, qty, buy_flag, data['ODNO'], data['ORD_TMD'],
                                   krx_fwdg_ord_orgno=data.get('KRX_FWDG_ORD_ORGNO'))

        logger.error(f"[KisV.do_order] 주문 실패: {res}")
        return None

    # get_order_status는 오버라이드하지 않는다 — koreainvestment/open-trading-api의
    # inquire_psbl_rvsecncl.py 원본에 env_dv(real/demo) 분기 자체가 없고 tr_id가
    # "TTTC0084R" 하나로 고정돼 있다(VTTC 변형이 존재하지 않는다).
    #
    # 다만 모의투자(openapivts) 서버에 TTTC0084R로 실제 호출해보면
    # rt_cd=1, msg_cd=EGW02006, msg1="모의투자 TR 이 아닙니다."로 거부된다 —
    # VTTC0084R도 rt_cd=1, msg_cd=OPSQ0002("없는 서비스 코드 입니다")로 거부됐다.
    # 즉 TR ID를 뭘 쓰든 문제가 아니라, 주식정정취소가능주문조회 자체가 KIS
    # 모의투자 서버에는 없는 기능으로 보인다(실전에서만 쓸 수 있을 것으로 예상되며,
    # 실전 계좌로는 아직 검증하지 못했다). 그래서 KisV로는 지금 이 메서드가 항상
    # 실패(빈 리스트)한다.

    def do_order_cancel(self, order_num, code, qty, krx_fwdg_ord_orgno="",
                        ord_dvsn="00", qty_all_ord_yn="Y", excg_id_dvsn_cd="KRX"):
        return self._order_rvsecncl("VTTC0013U", "02", order_num, code, 0, qty,
                                    krx_fwdg_ord_orgno, ord_dvsn, qty_all_ord_yn, excg_id_dvsn_cd)

    def do_order_modify(self, order_num, code, price, qty, krx_fwdg_ord_orgno="",
                        ord_dvsn="00", qty_all_ord_yn="Y", excg_id_dvsn_cd="KRX"):
        return self._order_rvsecncl("VTTC0013U", "01", order_num, code, price, qty,
                                    krx_fwdg_ord_orgno, ord_dvsn, qty_all_ord_yn, excg_id_dvsn_cd)

    '''
    async def connect(self):
        print("connecting...")
        print(uri)
        websocket = await websockets.connect(uri)
        print("success connection")
        return websocket
    '''