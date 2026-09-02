import asyncio
import json
import time
from datetime import datetime

import websockets
from loguru import logger
from websockets.exceptions import ConnectionClosedOK

import finestock
from finestock.comm import API


class Nh(API):
    """
    NH투자증권 나무(Namuh) Open API.

    - 모든 REST 호출은 POST + JSON, 요청은 {"Input_0": {...}}, 응답은
      rsp_cd/rsp_msg + Output_0(+Output_1...) + message 봉투를 사용한다.
    - 인증은 Authorization: Bearer {access_token} + x-client-id + x-client-secret 헤더.
    - 접근토큰발급(oauth2/token)은 모의투자 환경에서도 항상 운영 도메인(OAUTH_DOMAIN)에서만
      발급된다 — DOMAIN이 모의투자(moapi)로 바뀌는 NhV에서도 이 값은 고정이다.
    - 계좌번호(act_no)는 /n2/acctinfo 응답의 acct_no(11자리) 하나로 구성되며 별도의
      계좌상품코드 분리가 없다. set_account_info(account_num, account_num_sub)는 다른
      브로커와의 인터페이스 호환을 위해 유지하되, account_num_sub는 비워두거나(단일
      계좌번호를 account_num에 그대로 전달) 필요 시 account_num에 이어붙일 접미사로 쓴다.
    """

    RSP_OK = "00000"

    def __init__(self):
        super().__init__()
        self.is_run = True
        print("create Nh Components")

    def __del__(self):
        logger.debug("Destroy Nh Components")

    # ------------------------------------------------------------------
    # 인증
    # ------------------------------------------------------------------
    def set_oauth_info(self, app_key, app_secret):
        self.app_key = app_key
        self.app_secret = app_secret
        self.headers['x-client-id'] = app_key
        self.headers['x-client-secret'] = app_secret

    def oauth(self):
        # 접근토큰발급은 모의투자 미제공 — 항상 운영 도메인(OAUTH_DOMAIN)에서만 발급받는다.
        url = f"{self.OAUTH_DOMAIN}/{self.OAUTH}"
        header = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "appkey": self.app_key,
            "appsecretkey": self.app_secret,
            "grant_type": "client_credentials",
            "scope": "oob",
        }
        response = self._request("POST", url, headers=header, data=data, log_tag="Nh.oauth")
        try:
            res = response.json()
        except ValueError:
            res = response.text

        if response.status_code == 200 and isinstance(res, dict) and "access_token" in res:
            self.set_access_token(res['access_token'])
        return res

    def get_account_list(self):
        """/n2/acctinfo — 보유 계좌 목록([{acct_no, acct_type}, ...]) 조회. 인터페이스 외 헬퍼."""
        res = self._post(self.ACCOUNT_LIST, {})
        if res.get('rsp_cd') == self.RSP_OK:
            return res.get('Output_0', [])
        return []

    def _act_no(self):
        if self.account_num_sub:
            return f"{self.account_num}{self.account_num_sub}"
        return self.account_num

    def _post(self, path, input_0, extra_headers=None):
        url = f"{self.DOMAIN}/{path}"
        header = self.headers.copy()
        if extra_headers:
            header.update(extra_headers)
        body = {"Input_0": input_0}
        response = self._request("POST", url, headers=header, data=json.dumps(body), log_tag="Nh")
        res = self._json(response)
        self._last_response = response  # 연속조회(cts/cts_flag)는 body가 아니라 응답 헤더로 내려온다
        return res

    # ------------------------------------------------------------------
    # 시세
    # ------------------------------------------------------------------
    def get_price(self, code, market_cd="UNT"):
        input_0 = {"market_cd": market_cd, "iem_cd": code}
        res = self._post(self.PRICE, input_0)
        if res.get('rsp_cd') != self.RSP_OK:
            return None

        data = res.get('Output_0', {})
        today = datetime.now().strftime('%Y%m%d')
        price = float(data['stck_prpr'])
        return finestock.Price(today, code, price, float(data['stck_oprc']), float(data['stck_hgpr']),
                               float(data['stck_lwpr']), price, int(data['acml_vol']), int(data['acml_tr_pbmn']),
                               time=data.get('hoga_bsop_hour'))

    def get_ohlcv(self, code, frdate="", todate="", market_cd="UNT"):
        todate = todate or datetime.now().strftime('%Y%m%d')
        frdate = frdate or todate

        # NH의 기간별시세(period)는 LS/KIS와 달리 연속조회 키가 없다 — edate 기준으로
        # array_cnt만큼 한 번에 내려오는 값을 받아 frdate~todate로 클라이언트에서 자른다.
        input_0 = {
            "market_cd": market_cd,
            "iem_cd": code,
            "gubun": "1",  # 1:일 2:주 3:월 4:년
            "edate": todate,
            "array_cnt": "900",
        }
        res = self._post(self.CHART, input_0)

        ohlcvs = []
        if res.get('rsp_cd') == self.RSP_OK:
            for row in res.get('Output_1', []):
                bsop_date = row['bsop_date']
                if bsop_date < frdate or bsop_date > todate:
                    continue
                price = float(row['stck_prpr'])
                ohlcvs.append(finestock.Price(bsop_date, code, price, float(row['stck_oprc']), float(row['stck_hgpr']),
                                              float(row['stck_lwpr']), price, int(row['vol']), int(row['tr_pbmn'])))

        ohlcvs.sort(key=lambda p: p.workday)
        return ohlcvs

    def get_ohlcv_min(self, code, todate="", exchgubun="K", cts_date="", cts_time="", tr_cont_key=""):
        # NH는 분봉 전용 TR이 없고 기간별시세(period)를 gubun=5(분)로 재사용한다.
        # cts_date/cts_time/tr_cont_key는 NH가 분봉 연속조회를 지원하지 않아 사용하지
        # 않는다 — 다른 브로커와의 인터페이스 호환을 위해서만 받아둔다.
        todate = todate or datetime.now().strftime('%Y%m%d')
        market_cd = {"K": "KRX", "N": "NXT"}.get(exchgubun, "UNT")
        today_cls_code = "1" if todate == datetime.now().strftime('%Y%m%d') else "0"

        input_0 = {
            "market_cd": market_cd,
            "iem_cd": code,
            "gubun": "5",  # 5:분
            "xtick": "1",  # 1분봉
            "edate": todate,
            "array_cnt": "900",
            "today_cls_code": today_cls_code,
        }
        res = self._post(self.CHART, input_0)

        ohlcvs = []
        if res.get('rsp_cd') == self.RSP_OK:
            for row in res.get('Output_1', []):
                price = float(row['stck_prpr'])
                ohlcvs.append(finestock.Price(row['bsop_date'], code, price, float(row['stck_oprc']), float(row['stck_hgpr']),
                                              float(row['stck_lwpr']), price, int(row['vol']), int(row['tr_pbmn']),
                                              row.get('bsop_time')))
        return ohlcvs

    def get_index(self, code, frdate="", todate=""):
        # krstock(국내주식) API에는 지수 시세 TR이 없다 — 인터페이스 계약만 충족.
        print("Nh get_index not supported yet")
        return []

    def get_index_min(self, code, todate="", cts_date=" ", cts_time="", tr_cont_key=""):
        print("Nh get_index_min not supported yet")
        return []

    def get_orderbook(self, code, market_cd="UNT"):
        # NH는 호가 전용 TR이 없고 주식현재가시세(currentPrice) 응답에 10단계 호가가 포함된다.
        input_0 = {"market_cd": market_cd, "iem_cd": code}
        res = self._post(self.PRICE, input_0)
        if res.get('rsp_cd') != self.RSP_OK:
            return None

        data = res.get('Output_0', {})
        sells = [finestock.Hoga(int(data[f'askp{i}']), int(data[f'askp_rsqn{i}'])) for i in range(1, 11)]
        buys = [finestock.Hoga(int(data[f'bidp{i}']), int(data[f'bidp_rsqn{i}'])) for i in range(1, 11)]
        total_buy = int(data['total_bidp_rsqn'])
        total_sell = int(data['total_askp_rsqn'])
        return finestock.OrderBook(code, total_buy, total_sell, buys, sells)

    # ------------------------------------------------------------------
    # 주문
    # ------------------------------------------------------------------
    def do_order(self, code, buy_flag, price, qty, rmt_mkt_cd="KRX"):
        path = self.ORDER_CASH_BUY if buy_flag == finestock.ORDER_FLAG.BUY else self.ORDER_CASH_SELL
        nmn_pr_tp_cd = "05" if price == 0 else "01"  # 01:보통가(지정가) 05:시장가

        input_0 = {
            "act_no": self._act_no(),
            "iem_cd": code,
            "orr_qty": qty,
            "orr_pr": price,
            "nmn_pr_tp_cd": nmn_pr_tp_cd,
            "orr_cnd_dit_cd": "00",  # 00:없음 01:IOC 02:FOK
            "ssl_nmn_pr_dit_cd": "00",  # 00:정상(공매도 아님)
            "rmt_mkt_cd": rmt_mkt_cd,  # SOR/KRX/NXT
            "sor_mkt_sli_yn": "Y" if rmt_mkt_cd == "SOR" else "N",
        }
        res = self._post(path, input_0)
        if res.get('rsp_cd') != self.RSP_OK:
            return None

        data = res.get('Output_0', {})
        return finestock.Order(code, '', price, qty, buy_flag, str(data.get('mkt_orr_no')))

    def do_order_cancel(self, order_num, code, qty):
        all_pat_dit_cd = "1" if qty <= 0 else "2"  # 1:전체(전량) 2:일부(잔량)
        input_0 = {
            "act_no": self._act_no(),
            "org_mkt_orr_no": int(order_num),
            "all_pat_dit_cd": all_pat_dit_cd,
            "iem_cd": code,
        }
        if all_pat_dit_cd == "2":
            input_0["cor_qty"] = qty

        res = self._post(self.ORDER_CANCEL, input_0)
        if res.get('rsp_cd') != self.RSP_OK:
            return None

        data = res.get('Output_0', {})
        return finestock.Order(code, '', 0, qty, finestock.ORDER_FLAG.VIEW, str(data.get('mkt_orr_no')))

    def do_order_modify(self, order_num, code, price, qty):
        # TODO: NH 정정주문 TR 미연동. self.ORDER_MODIFY(path.py) 엔드포인트는
        # 이미 정의돼 있으나 요청 바디 스펙을 아직 검증하지 못해 우선 인터페이스
        # 계약만 충족한다.
        print("Nh do_order_modify not supported yet")
        return None

    # ------------------------------------------------------------------
    # 계좌
    # ------------------------------------------------------------------
    def get_balance(self, cts="", cts_flag=""):
        input_0 = {
            "act_no": self._act_no(),
            "bnc_bse_cd": "1",  # 1:주식관련 총 평가(체결기준) 5:주식잔고평가(현재가기준)
            "ltg_aot_dit_cd": "1",  # 1:상장종목 9:전체
            "aet_bse": "1",  # 1:순자산 2:총자산
            "qut_dit_cd": "UNT",  # UNT/KRX/NXT
        }
        # 연속조회는 body가 아니라 요청 헤더의 cts(연속거래키)/cts_flag(Y)로 이어받는다.
        extra_headers = {"cts": cts, "cts_flag": "Y"} if cts_flag == "Y" else None
        res = self._post(self.BALANCE, input_0, extra_headers)
        # 이 TR은 "성공"에 해당하는 rsp_cd가 하나로 고정돼 있지 않다 — 실제로 확인된 것만도
        # '00218'(연속조회 데이터 더 있음, rsp_msg: "계속 조회시 다음(연속조회) 버튼을 누르시기
        # 바랍니다.")과 '00166'(마지막 페이지, rsp_msg: "조회가 완료되었습니다.") 둘 다 정상
        # 응답이었다. rsp_cd를 화이트리스트로 고정하는 대신 Output_0가 실제로 왔는지(게이트웨이
        # 오류는 'IGW...' 코드로 오고 Output_0가 없다)로 성공 여부를 판단한다.
        if 'Output_0' not in res:
            return None

        data = res.get('Output_0', {})
        holds = []
        for h in res.get('Output_1', []):
            eal_amt = int(float(h.get('eal_amt') or 0))
            eal_pls_amt = int(float(h.get('eal_pls_amt') or 0))
            holds.append(finestock.Hold(h['iem_cd'], h['iem_nm'], int(float(h['phs_pr'])),
                                        int(float(h['itg_bnc_qty'])), eal_amt - eal_pls_amt,
                                        eal_amt))

        # Output_1은 페이지당 최대 10건 — 응답 헤더에 다음 페이지가 있다는 cts_flag=Y와
        # 연속거래키(cts)가 내려오면 이어서 조회해 보유종목을 전부 모은다. 순자산금액/
        # 총평가손익 등 계좌 합계 필드는 "보유한 잔고를 모두 조회한 이후"의 마지막 페이지
        # 응답에만 정상 값이 채워지므로(공식 문서 기재) 그 페이지의 Output_0을 쓴다.
        resp_headers = getattr(self._last_response, 'headers', {}) or {}
        next_cts = resp_headers.get('cts')
        next_cts_flag = resp_headers.get('cts_flag')
        if next_cts_flag == "Y" and next_cts:
            time.sleep(0.3)
            next_account = self.get_balance(next_cts, "Y")
            if next_account is None:
                return None
            return finestock.Account(self.account_num, self.account_num_sub, next_account.deposit,
                                     next_account.next_deposit, next_account.pay_deposit,
                                     holds + next_account.hold)

        return finestock.Account(self.account_num, self.account_num_sub, int(data.get('dca', 0)),
                                 int(data.get('nxt_dd_dca', 0)), int(data.get('nxt2_dd_dca', 0)), holds)

    def get_holds(self):
        balance = self.get_balance()
        return balance.hold if balance else []

    # ------------------------------------------------------------------
    # 종목/지수 목록 — NH는 전종목 조회 REST API가 없고 종목마스터 파일(.mst,
    # CP949 고정길이 바이너리, https://www.nhplug.com/instruments/)로만 제공된다.
    # ------------------------------------------------------------------
    def get_stock_list(self, mrkt_tp="0"):
        print("Nh get_stock_list not supported yet (see instruments/m_new_stock.mst)")
        return []

    def get_index_list(self):
        print("Nh get_index_list not supported yet")
        return []

    # ------------------------------------------------------------------
    # 실시간 (WebSocket)
    # ------------------------------------------------------------------
    async def connect(self):
        self.ws = await websockets.connect(self.DOMAIN_WS)

    async def disconnect(self):
        self.stop()
        if self.ws is not None:
            await self.ws.close()

    def stop(self):
        self.is_run = False

    async def _send(self, tr_cd, tr_key, status=True):
        header = {"token": self.access_token, "tr_type": "1" if status else "2"}
        body = {"tr_cd": tr_cd, "tr_key": tr_key}
        await self.ws.send(json.dumps({"header": header, "body": body}))

    async def recv_price(self, code, status=True):
        await self._send("oc", code, status)  # 국내주식 실시간체결가(KRX)

    async def recv_index(self, code, status=True):
        print("Nh recv_index not supported yet")

    async def recv_orderbook(self, code, status=True):
        await self._send("ob", code, status)  # 국내주식 실시간호가(KRX)

    async def recv_trade(self, code, status=True):
        # 체결통보('d2')는 종목코드가 아닌 userid를 tr_key로 구독하는 계좌 단위 통보라
        # code 기반의 이 시그니처로는 표현할 수 없다 — 인터페이스 계약만 충족.
        print("Nh recv_trade not supported yet (userid 기반 체결통보 채널 'd2' 참고)")

    async def run(self):
        self.is_run = True
        while self.is_run:
            try:
                res = await asyncio.wait_for(self.ws.recv(), timeout=1)
                res = json.loads(res)
                header = res.get('header', {})
                body = res.get('body')
                if not body:
                    continue

                if 'rsp_cd' in header:
                    # 구독/해제 등록 시 서버가 먼저 보내는 ack — {"tr_key": [code]}뿐인
                    # 실데이터 아닌 body라 파싱 대상이 아니다(공식 스펙 문서에는 이 ack
                    # 메시지가 나와 있지 않아 실제 응답을 보고서야 확인했다).
                    logger.debug(f"Nh WS ack (tr_cd={header.get('tr_cd')}): {header.get('rsp_msg')}")
                    continue

                tr_cd = header.get('tr_cd')
                code = header.get('tr_key', '')
                try:
                    if tr_cd in ("oc", "mc", "nc"):
                        self.add_data(self._parse_price(code, body))
                    elif tr_cd in ("ob", "mb", "nb"):
                        self.add_data(self._parse_orderbook(code, body))
                except Exception as parse_err:
                    # ack 이외의 사유(스펙과 실제 응답의 필드명 불일치 등)로 파싱이
                    # 실패해도 세션 전체를 끊지 않고 원본 페이로드를 남겨 원인 파악이
                    # 가능하게 한다.
                    logger.error(f"Nh WS parse error (tr_cd={tr_cd}): {parse_err} | raw={res}")
            except asyncio.TimeoutError:
                pass
            except ConnectionClosedOK as e:
                print(f"ConnectionClosedOK: {e}")
                self.is_run = False
            except Exception as e:
                print(f"Exception: {e}")
                self.is_run = False

        await self.ws.close()

    # 실시간호가 응답필드는 레벨2~10이 관례적 순번(offer, P_, S_, S4_..S10_)으로 붙는다.
    _ASK_LEVEL_PREFIXES = ('', 'P_', 'S_', 'S4_', 'S5_', 'S6_', 'S7_', 'S8_', 'S9_', 'S10_')

    def _parse_orderbook(self, code, data):
        sells = [finestock.Hoga(int(data[f'{p}offer']), int(data[f'{p}offerrem'])) for p in self._ASK_LEVEL_PREFIXES]
        buys = [finestock.Hoga(int(data[f'{p}bid']), int(data[f'{p}bidrem'])) for p in self._ASK_LEVEL_PREFIXES]
        total_sell = int(data.get('T_offerrem', 0))
        total_buy = int(data.get('T_bidrem', 0))
        return finestock.OrderBook(code, total_buy, total_sell, buys, sells)

    def _parse_price(self, code, data):
        today = datetime.now().strftime('%Y%m%d')
        price = float(data['price'])
        volume_amt = int(data.get('value_won', data.get('value', 0)))
        return finestock.Price(today, code, price, float(data['open']), float(data['high']), float(data['low']),
                               price, int(data['volume']), volume_amt, data.get('time'))
