from loguru import logger
import datetime
import asyncio
import websockets
import json
import requests
import finestock
from websockets.exceptions import ConnectionClosedOK
from finestock.comm.api import API

class Kiwoom(API):
    def __init__(self):
        super().__init__()
        self.headers["content-type"] = "application/json"

    def _parse_int(self, val):
        try:
            return int(val)
        except:
            return 0

    def _parse_float(self, val):
        try:
            return float(val)
        except:
            return 0.0

    async def _send_subscription(self, code, tr_type, status=True):
        msg = json.dumps({
            "trnm": "REG",
            "grp_no": "1",
            "refresh": "1" if status else "0",
            "data": [{
                "item": [code],
                "type": [tr_type]
            }]
        })
        logger.info(f"[Kiwoom WS] Sending Subscription ({tr_type}): {msg}")
        await self.ws.send(msg)

    def oauth(self):
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret,
        }
        header = {"Content-Type": "application/json; charset=UTF-8"}
        res = super().oauth(header=header, data=json.dumps(data))
        
        if res and 'token' in res:
             self.access_token = res['token']
             self.token_type = res.get('token_type', 'Bearer')
             self.headers['authorization'] = f"{self.token_type} {self.access_token}"
             
        return res
              
    def get_price(self, code):
        today = datetime.datetime.now().strftime("%Y%m%d")
        res = self.get_ohlcv(code, frdate=today, todate=today)
        return res[0] if res else None

    def get_ohlcv(self, code, frdate="", todate="", cts_date="", tr_cont_key=""):
        # TR: ka10081 (Stock Daily Chart)
        # params: {stk_cd, base_dt, upd_stkpc_tp}
        params = {
            "stk_cd": code,
            "base_dt": todate if todate else datetime.datetime.now().strftime("%Y%m%d"),
            "upd_stkpc_tp": "0" # 0:raw, 1:adjusted
        }
        return self._get_chart_sync("ka10081", params, frdate=frdate)

    def _get_chart_sync(self, tr_code, params, next_key="", frdate=""):
        url = f"{self.DOMAIN}/{self.STOCK_CHART}"
        
        cont_yn = "Y" if next_key else "N"
        
        header = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"{self.token_type} {self.access_token}",
            "api-id": tr_code,
            "cont-yn": cont_yn,
            "next-key": next_key
        }
        
        # logger.debug(f"[Kiwoom] Request URL: {url}")
        # logger.debug(f"[Kiwoom] Request Headers: {header}")
        # logger.debug(f"[Kiwoom] Request Body: {params}")

        response = requests.post(url, headers=header, data=json.dumps(params))
        
        # logger.debug(f"[Kiwoom] Response Status: {response.status_code}")
        # logger.debug(f"[Kiwoom] Response Body: {response.text}")

        if response.status_code == 200:
            try:
                res = response.json()
                if res.get('rt_cd', '0') == '0': # Assume success if rt_cd is missing
                    # If output field exists, use it. Otherwise, use the whole response.
                    data = res.get('output', res) 
                    ohlcvs = self._parse_ohlcv(data, tr_code)
                    
                    # Filter by frdate if provided
                    if frdate:
                        ohlcvs = [x for x in ohlcvs if x.workday >= frdate]
                    
                    return ohlcvs
                else:
                    logger.error(f"[Kiwoom] Error Code: {res.get('rt_cd')}")
                    logger.error(f"[Kiwoom] Full Response: {res}")
                    logger.error(f"[Kiwoom] Error Msg: {res.get('msg1')} {res.get('msg2')}")
            except Exception as e:
                logger.error(f"[Kiwoom] JSON Parse Error: {e}")
                pass
        return []

    def get_ohlcv_min(self, code, todate="", exchgubun="K", cts_date="", cts_time="", tr_cont_key=""):
        # TR: ka10080 (Stock Minute Chart)
        # params: {stk_cd, base_dt, tic_scope, upd_stkpc_tp}
        params = {
            "stk_cd": code,
            "base_dt": todate if todate else datetime.datetime.now().strftime("%Y%m%d"),
            "tic_scope": "1", # 1 minute
            "upd_stkpc_tp": "0" # 0:raw, 1:adjusted
        }
        # Note: Minute chart filtering by daily frdate might need implicit logic (e.g. only date part)
        # Since fine_stock.Price.workday for minute data might be "YYYYMMDD", string comparison works if frdate is "YYYYMMDD"
        return self._get_chart_sync("ka10080", params, next_key=tr_cont_key, frdate=cts_date if cts_date.strip() else "")

        return self._get_chart_sync("ka10080", params, next_key=tr_cont_key, frdate=cts_date if cts_date.strip() else "")

    def get_stock_list(self, mrkt_tp="0"):
        # TR: ka10099 (Stock Info)
        # params: {mrkt_tp} 0:KOSPI, 10:KOSDAQ
        url = f"{self.DOMAIN}/{self.STOCK_INFO}"
        
        header = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"{self.token_type} {self.access_token}",
            "api-id": "ka10099",
            "cont-yn": "N",
            "next-key": ""
        }
        
        params = {
            "mrkt_tp": mrkt_tp
        }
        
        response = requests.post(url, headers=header, data=json.dumps(params))
        
        if response.status_code == 200:
            try:
                res = response.json()
                if res.get('rt_cd', '0') == '0': # Note: User example says return_code, but standard Kiwoom is rt_cd usually. Wait, User example shows "return_code":0.
                    # Let's check user example again.
                    # User example response: 
                    # { "return_msg":..., "return_code":0, "list": [...] }
                    # Standard Kiwoom usually uses rt_cd. But user example shows return_code. 
                    # I should handle both or trust user example for this specific TR.
                    # Actually, for consistency, I will check return_code or rt_cd.
                    # The user example shows "return_code": 0 (integer).
                    
                    # Logic:
                    if str(res.get('return_code', res.get('rt_cd', '1'))) == '0':
                        data_list = res.get('list', [])
                        stocks = []
                        for item in data_list:
                            # Mapping
                            # code: "005930"
                            # name: "삼성전자"
                            # marketName: "코스닥" (Wait, 005930 is KOSPI, example says KOSDAQ? Example might be mock/mixed)
                            # state: "관리종목" / "증거금100%"
                            # auditInfo: "투자주의환기종목" / "정상"
                            
                            code = item.get('code', '')
                            name = item.get('name', '')
                            market = item.get('marketName', '')
                            
                            # Simple mapping for bool flags
                            is_suspended = item.get('auditInfo') != '정상'
                            is_admin = item.get('state') == '관리종목'
                            
                            stocks.append(finestock.Stock(code, name, market, is_suspended, is_admin))
                        
                        logger.info(f"[Kiwoom] get_stock_list received {len(stocks)} items")
                        return stocks
                    else:
                        logger.error(f"[Kiwoom] Stock List Error: {res.get('return_msg', res.get('msg1'))}")
                else: # fallback if return_code is not present check rt_cd
                     pass
            except Exception as e:
                logger.error(f"[Kiwoom] JSON Parse Error: {e}")
        else:
             logger.error(f"[Kiwoom] HTTP Error: {response.status_code} {response.text}")
        return []

    def get_index_list(self, mrkt_tp="0"):
        # TR: ka10101 (Index Info)
        # params: {mrkt_tp} 0:KOSPI, 1:KOSDAQ, ...
        url = f"{self.DOMAIN}/{self.STOCK_INFO}"
        
        header = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"{self.token_type} {self.access_token}",
            "api-id": "ka10101",
            "cont-yn": "N",
            "next-key": ""
        }
        
        params = {
            "mrkt_tp": mrkt_tp
        }
        
        response = requests.post(url, headers=header, data=json.dumps(params))
        
        if response.status_code == 200:
            try:
                res = response.json()
                # User example uses return_code. Standard Kiwoom uses rt_cd.
                # Logic: Check return_code first, then rt_cd.
                return_code = str(res.get('return_code', res.get('rt_cd', '1')))
                
                if return_code == '0':
                    data_list = res.get('list', [])
                    indices = []
                    for item in data_list:
                        # Mapping
                        # marketCode: "0"
                        # code: "001"
                        # name: "종합(KOSPI)"
                        # group: "1"
                        
                        code = item.get('code', '')
                        name = item.get('name', '')
                        market = item.get('marketCode', '0')
                        group = item.get('group', '')
                        
                        indices.append(finestock.Index(code, name, market, group))
                        
                    logger.info(f"[Kiwoom] get_index_list received {len(indices)} items")
                    return indices
                else:
                    logger.error(f"[Kiwoom] Index List Error: {res.get('return_msg', res.get('msg1'))}")
            except Exception as e:
                logger.error(f"[Kiwoom] JSON Parse Error: {e}")
        else:
             logger.error(f"[Kiwoom] HTTP Error: {response.status_code} {response.text}")
        return []

    def get_index(self, code, frdate="", todate="", cts_date="", tr_cont_key=""):
        # TR: ka20006 (Index Daily Chart)
        # params: {inds_cd, base_dt}
        params = {
            "inds_cd": code,
            "base_dt": todate if todate else datetime.datetime.now().strftime("%Y%m%d"),
        }
        return self._get_chart_sync("ka20006", params, next_key=tr_cont_key, frdate=frdate)

    def get_index_min(self, code, todate="", cts_date=" ", cts_time="", tr_cont_key=""):
        # TR: ka20005 (Index Minute Chart)
        # params: {inds_cd, base_dt, tic_scope}
        params = {
            "inds_cd": code,
            "base_dt": todate if todate else datetime.datetime.now().strftime("%Y%m%d"),
            "tic_scope": "1" # 1 minute
        }
        return self._get_chart_sync("ka20005", params, next_key=tr_cont_key, frdate=cts_date if cts_date.strip() else "")

    def _parse_ohlcv(self, data, tr_code):
        ohlcvs = []
        
        # Determine list data based on TR code if directly in data dict
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            if tr_code == "ka10081":
                items = data.get('stk_dt_pole_chart_qry', [])
            elif tr_code == "ka10080":
                 items = data.get('stk_min_pole_chart_qry', [])
            elif tr_code == "ka20006":
                 items = data.get('inds_dt_pole_qry', [])
            elif tr_code == "ka20005":
                 items = data.get('inds_min_pole_qry', [])
        
        for item in items:
            try:
                # Mapping depends on TR code
                if tr_code == "ka10081": # Stock Daily
                    ohlcvs.append(finestock.Price(
                        item['dt'], "", item['cur_prc'], item['open_pric'], item['high_pric'],
                        item['low_pric'], item['cur_prc'], item['trde_qty'], item['trde_prica']
                    ))
                elif tr_code == "ka10080": # Stock Minute
                    ohlcvs.append(finestock.Price(
                        "", "", item['cur_prc'], item['open_pric'], item['high_pric'],
                        item['low_pric'], item['cur_prc'], item['trde_qty'], "",
                        item['cntr_tm'] # Time
                    ))
                elif tr_code == "ka20006": # Index Daily
                    if not item['dt']: continue
                    ohlcvs.append(finestock.Price.from_values(
                        item['dt'], "", 
                        float(item['cur_prc']) / 100, 
                        float(item['open_pric']) / 100, 
                        float(item['high_pric']) / 100,
                        float(item['low_pric']) / 100, 
                        float(item['cur_prc']) / 100, 
                        item['trde_qty'], 
                        item.get('trde_prica', 0)
                    ))
                elif tr_code == "ka20005": # Index Minute
                     ohlcvs.append(finestock.Price.from_values(
                        "", "", 
                        float(item['cur_prc']) / 100, 
                        float(item['open_pric']) / 100, 
                        float(item['high_pric']) / 100,
                        float(item['low_pric']) / 100, 
                        float(item['cur_prc']) / 100, 
                        item['trde_qty'], "",
                        item['cntr_tm'] # Time
                    ))
            except Exception as e:
                logger.warning(f"Parse error for item {item}: {e}")
                continue
        return ohlcvs

    def get_orderbook(self, code):
        # TR: ka10004 (Stock Quote - Hoga)
        # Endpoint: /api/dostk/mrkcond
        # params: {stk_cd}
        url = f"{self.DOMAIN}/{self.STOCK_ORDERBOOK}"
        
        header = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"{self.token_type} {self.access_token}",
            "api-id": "ka10004",
            "cont-yn": "N",
            "next-key": ""
        }
        
        params = {
            "stk_cd": code
        }
        
        response = requests.post(url, headers=header, data=json.dumps(params))
        
        if response.status_code == 200:
            try:
                res = response.json()
                # Debug logging to see structure if needed
                # logger.debug(f"[Kiwoom] Orderbook Response: {res}")
                
                if res.get('rt_cd', '0') == '0':
                    # Parse OrderBook
                    # Response body contains fields directly? Or in output?
                    # Based on search, it seems fields are in the body (or 'output' if consistent with chart)
                    # Let's check if 'output' exists, otherwise use 'res'.
                    # Reference [1] says response body has the fields. Kiwoom REST often wraps in 'output' or 'list'.
                    # For ka10004, let's assume 'output' block based on previous patterns.
                    data = res.get('output', res)
                    
                    buys = []
                    sells = []
                    
                    # 10 levels
                    for i in range(1, 11):
                        # Sell side: sel_1st_pre_bid ... sel_10th_pre_bid
                        # Buy side: buy_1st_pre_bid ... buy_10th_pre_bid
                        # Quantities: sel_1st_pre_req ...
                        
                        try:
                            if i == 1:
                                s_price = data.get('sel_fpr_bid', '0')
                                s_qty = data.get('sel_fpr_req', '0')
                                b_price = data.get('buy_fpr_bid', '0')
                                b_qty = data.get('buy_fpr_req', '0')
                            else:
                                s_price = data.get(f'sel_{i}th_pre_bid', '0')
                                s_qty = data.get(f'sel_{i}th_pre_req', '0')
                                b_price = data.get(f'buy_{i}th_pre_bid', '0')
                                b_qty = data.get(f'buy_{i}th_pre_req', '0')
                            
                            if s_price and int(s_price) > 0:
                                sells.append(finestock.Hoga(int(s_price), int(s_qty)))
                            if b_price and int(b_price) > 0:
                                buys.append(finestock.Hoga(int(b_price), int(b_qty)))
                        except:
                            pass
                            
                    total_sell = int(data.get('tot_sel_req', '0'))
                    total_buy = int(data.get('tot_buy_req', '0'))
                    
                    return finestock.OrderBook(
                        code=code,
                        total_buy=total_buy,
                        total_sell=total_sell,
                        buy=buys,
                        sell=sells
                    )
                else:
                    logger.error(f"[Kiwoom] Error Code: {res.get('rt_cd')}")
                    logger.error(f"[Kiwoom] Error Msg: {res.get('msg1')} {res.get('msg2')}")
            except Exception as e:
                logger.error(f"[Kiwoom] JSON Parse Error: {e}")
        return None

    async def connect(self, callback=None):
        logger.info(f"[Kiwoom API] connecting to {self.DOMAIN_WS}...")
        try:
            self.ws = await websockets.connect(self.DOMAIN_WS)
            logger.info("[Kiwoom API] complete connect")
            
            if self.access_token:
                await self.login()
                
            if callback is not None:
                callback()
        except Exception as e:
            logger.error(f"[Kiwoom API] Connection Failed: {e}")

    async def login(self):
        msg = json.dumps({
            "trnm": "LOGIN",
            "token": self.access_token
        })
        logger.info(f"[Kiwoom WS] Sending Login: {msg}")
        await self.ws.send(msg)

    async def disconnect(self, callback=None):
        self.stop()
        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                logger.error(f"[Kiwoom API] Disconnect error: {e}")
        logger.info("[Kiwoom API] complete disconnect")
        if callback is not None:
            callback()

    def stop(self):
        self.is_run = False

    async def run(self):
        logger.info(f"Kiwoom API Run Loop Started")
        self.is_run = True
        while self.is_run:
            try:
                # Wait for message
                res = await self.ws.recv()
                
                try:
                    res_json = json.loads(res)
                    trnm = res_json.get('trnm')
                    
                    if trnm == 'LOGIN':
                        if res_json.get('return_code') != 0:
                            logger.error(f"[Kiwoom WS] Login Failed: {res_json.get('return_msg')}")
                            self.stop()
                        else:
                            logger.info("[Kiwoom WS] Login Success")
                            
                    elif trnm == 'PING':
                        await self.ws.send(res) # Echo back
                        
                    elif trnm == 'REAL':
                        # Realtime Data
                        # Structure: {'data': [{'values': {'20': '...', '10': '...'}, 'type': '0B', ...}], 'trnm': 'REAL'}
                        
                        data_list = res_json.get('data', [])
                        for item in data_list:
                            if item.get('type') == '0B':
                                self._parse_real_price(item)
                            elif item.get('type') == '0J': # Index Realtime
                                self._parse_real_index(item)
                            elif item.get('type') == '0D': # Orderbook Realtime
                                self._parse_real_orderbook(item)
                            elif item.get('type') == '00': # Order Status Realtime
                                self._parse_real_order_status(item)

                except json.JSONDecodeError:
                    logger.warning(f"[Kiwoom WS] Received non-JSON message: {res}")
                    
            except asyncio.TimeoutError:
                pass
            except ConnectionClosedOK:
                logger.info("[Kiwoom WS] Connection Closed")
                self.is_run = False
                break
            except Exception as e:
                logger.error(f"[Kiwoom WS] Error: {e}")
                # self.is_run = False # Don't stop on minor errors?

    def _parse_real_price(self, item):
        values = item.get('values', {})
        code = item.get('item', '')
        
        # Mapping based on standard Kiwoom FIDs (approximate)
        # 10: Current Price (cur_prc)
        # 11: Fluctuation (diff)
        # 12: Fluctuation Rate (diff_rate)
        # 13: Accumulated Volume (trde_qty) ? 
        # 14: Accumulated Volume Value ?
        # 15: Transaction Volume (tick_qty) ?
        # 16: Open (oprc)
        # 17: High (hgpr)
        # 18: Low (lwpr)
        # 20: Time (tr_tm)
        
        today = datetime.datetime.now().strftime("%Y%m%d")
        cur_prc = values.get('10', '0')
        time_str = values.get('20', '')
        
        # Prices are often signed (+/-), remove sign for float conversion
        # And check if need /100. REST API needed it. 
        # If 181300 is Samsung, it seems raw won.
        
        price = abs(self._parse_int(cur_prc))
        open_p = abs(self._parse_int(values.get('16', '0')))
        high_p = abs(self._parse_int(values.get('17', '0')))
        low_p = abs(self._parse_int(values.get('18', '0')))
        
        p = finestock.Price(
            today, code, price, 
            open_p, high_p, low_p, price,
            self._parse_int(values.get('13', '0')), # Vol
            self._parse_int(values.get('14', '0')), # Val
            time_str
        )
        self.add_price(p)

    def _parse_real_index(self, item):
        values = item.get('values', {})
        code = item.get('item', '')
        
        # Mapping for Index (0J)
        # 10: Current Index
        # 11: Diff
        # 12: Rate
        # 13: Vol
        # 14: Val
        # 20: Time
        
        time_str = values.get('20', '')
        cur_val_str = values.get('10', '0')
        
        price = abs(self._parse_float(cur_val_str))
        open_p = abs(self._parse_float(values.get('16', '0')))
        high_p = abs(self._parse_float(values.get('17', '0')))
        low_p = abs(self._parse_float(values.get('18', '0')))
        
        p = finestock.Price(
            datetime.datetime.now().strftime("%Y%m%d"), 
            code, 
            price, 
            open_p, high_p, low_p, price,
            self._parse_int(values.get('13', '0')), # Vol
            self._parse_int(values.get('14', '0')), # Val
            time_str
        )
        self.add_price(p)

    def _parse_real_orderbook(self, item):
        values = item.get('values', {})
        code = item.get('item', '')
        
        # Kiwoom Realtime Hoga (0D) FIDs
        # Sell Price 1~10: 41~50
        # Buy Price 1~10: 51~60
        # Sell Qty 1~10: 61~70
        # Buy Qty 1~10: 71~80
        # Total Sell Qty: 121
        # Total Buy Qty: 125
        
        buys = []
        sells = []
        
        for i in range(10):
            s_price_fid = str(41 + i)
            b_price_fid = str(51 + i)
            s_qty_fid = str(61 + i)
            b_qty_fid = str(71 + i)
            
            s_price = values.get(s_price_fid, '0')
            b_price = values.get(b_price_fid, '0')
            s_qty = values.get(s_qty_fid, '0')
            b_qty = values.get(b_qty_fid, '0')
            
            if self._parse_int(s_price) != 0:
                sells.append(finestock.Hoga(abs(self._parse_int(s_price)), self._parse_int(s_qty)))
            if self._parse_int(b_price) != 0:
                buys.append(finestock.Hoga(abs(self._parse_int(b_price)), self._parse_int(b_qty)))
        
        total_sell = self._parse_int(values.get('121', '0'))
        total_buy = self._parse_int(values.get('125', '0'))
        
        ob = finestock.OrderBook(
            code=code,
            total_buy=total_buy,
            total_sell=total_sell,
            buy=buys,
            sell=sells
        )
        self.add_orderbook(ob)

    def _parse_real_order_status(self, item):
        values = item.get('values', {})
        
        # Mapping for Order Status (00)
        status_str = values.get('913', '')
        trade_flag = finestock.TRADE_FLAG.ORDER
        if isinstance(status_str, str):
            if '체결' in status_str:
                trade_flag = finestock.TRADE_FLAG.COMPLETE
            elif '취소' in status_str:
                trade_flag = finestock.TRADE_FLAG.CANCLE
            elif '정정' in status_str:
                trade_flag = finestock.TRADE_FLAG.MODIFY
            
        buysell_str = values.get('905', '')
        order_flag = finestock.ORDER_FLAG.BUY
        if isinstance(buysell_str, str) and '매도' in buysell_str:
            order_flag = finestock.ORDER_FLAG.SELL
        
        trade = finestock.Trade(
            code=values.get('9001', ''),
            name=values.get('302', ''),
            trade_flag=trade_flag,
            order_flag=order_flag,
            price=self._parse_int(values.get('901', '0')),
            qty=self._parse_int(values.get('900', '0')),
            trade_price=self._parse_int(values.get('910', '0')),
            trade_qty=self._parse_int(values.get('911', '0')),
            order_num=values.get('9203', '').strip(),
            order_time=values.get('908', '')
        )
        self.add_trade(trade)

    async def recv_price(self, code, status=True):
        # Subscription Packet (REG)
        await self._send_subscription(code, "0B", status)

    async def recv_index(self, code, status=True):
        # Subscription Packet (REG) for Index (0J)
        await self._send_subscription(code, "0J", status)

    async def recv_orderbook(self, code, status=True):
        # Subscription Packet (REG) for Orderbook (0D)
        await self._send_subscription(code, "0D", status)

    async def recv_trade(self, code, status=True):
        # Subscription Packet (REG) for Realtime Trade/Price (0B)
        # In Kiwoom, '0B' (Realtime Conclusion) includes both price update and trade tick.
        # This is essentially the same as recv_price.
        await self._send_subscription(code, "0B", status)

    async def recv_order_status(self, status=True):
        # Subscription Packet (REG) for Order Status (00)
        await self._send_subscription("", "00", status)

    def do_order(self, code, buy_flag, price, qty):
        # Determine TR Code
        if buy_flag == finestock.ORDER_FLAG.BUY:
            api_id = "kt10000"
        elif buy_flag == finestock.ORDER_FLAG.SELL:
            api_id = "kt10001"
        else:
            logger.error(f"[Kiwoom] Invalid buy_flag: {buy_flag}")
            return None

        # Determine Price Type
        if price == 0:
            trde_tp = "3" # Market
            ord_uv = ""
        else:
            trde_tp = "0" # Limit
            ord_uv = str(price)

        url = f"{self.DOMAIN}/api/dostk/ordr" # Endpoint for Order

        header = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"{self.token_type} {self.access_token}",
            "api-id": api_id,
            "cont-yn": "N",
            "next-key": ""
        }

        params = {
            "dmst_stex_tp": "KRX",
            "stk_cd": code,
            "ord_qty": str(qty),
            "ord_uv": ord_uv,
            "trde_tp": trde_tp,
            "cond_uv": ""
        }

        response = requests.post(url, headers=header, data=json.dumps(params))
        
        if response.status_code == 200:
            try:
                res = response.json()
                if res.get('rt_cd', '0') == '0':
                    logger.info(f"[Kiwoom] Order Success: {res.get('msg1')} {res.get('msg2')}")
                    # Return res for now as structure of output is not fully defined
                    return res
                else:
                    logger.error(f"[Kiwoom] Order Error: {res.get('msg1')} {res.get('msg2')}")
                    return res
            except Exception as e:
                logger.error(f"[Kiwoom] JSON Parse Error: {e}")
        else:
             logger.error(f"[Kiwoom] HTTP Error: {response.status_code} {response.text}")
        return None

    def do_order_cancel(self, order_num, code, qty):
        url = f"{self.DOMAIN}/api/dostk/ordr"

        header = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"{self.token_type} {self.access_token}",
            "api-id": "kt10003",
            "cont-yn": "N",
            "next-key": ""
        }

        params = {
            "dmst_stex_tp": "KRX",
            "orig_ord_no": str(order_num),
            "stk_cd": code,
            "cncl_qty": str(qty)
        }

        response = requests.post(url, headers=header, data=json.dumps(params))
        
        if response.status_code == 200:
            try:
                res = response.json()
                if res.get('rt_cd', '0') == '0':
                    logger.info(f"[Kiwoom] Cancel Success: {res.get('msg1')} {res.get('msg2')}")
                    return res
                else:
                    logger.error(f"[Kiwoom] Cancel Error: {res.get('msg1')} {res.get('msg2')}")
                    return res
            except Exception as e:
                logger.error(f"[Kiwoom] JSON Parse Error: {e}")
        else:
             logger.error(f"[Kiwoom] HTTP Error: {response.status_code} {response.text}")
        return None

    def get_balance(self):
        url = f"{self.DOMAIN}/api/dostk/acnt"

        header = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"{self.token_type} {self.access_token}",
            "api-id": "kt00001",
            "cont-yn": "N",
            "next-key": ""
        }

        params = {
            "qry_tp": "3" # 3: Estimated, 2: General
        }

        response = requests.post(url, headers=header, data=json.dumps(params))
        print(response.text)
        
        if response.status_code == 200:
            try:
                res = response.json()
                print(res)
                if res.get('rt_cd', '0') == '0' or res.get('return_code') == 0:
                    # Kiwoom REST API for account often puts fields at the root level
                    output = res.get('output', res)
                    logger.info(f"[Kiwoom] Balance Response: {output}")
                    
                    # Placeholder mapping based on user example:
                    # entr: deposit (예수금)
                    # d1_entra: D+1 예수금
                    # d2_entra: D+2 예수금
                    # ord_alow_amt: 주문가능금액
                    
                    deposit = int(output.get('entr', '0'))
                    next_deposit = int(output.get('d2_entra', '0')) # D+2 is standard for "next deposit" in Korea
                    pay_deposit = int(output.get('ord_alow_amt', '0')) # Trade allowed amount
                    
                    return finestock.Account(self.account_num, "", deposit, next_deposit, pay_deposit, [])
                else:
                    logger.error(f"[Kiwoom] Balance Error: {res.get('msg1')} {res.get('msg2')}")
            except Exception as e:
                logger.error(f"[Kiwoom] JSON Parse Error: {e}")
        else:
             logger.error(f"[Kiwoom] HTTP Error: {response.status_code} {response.text}")
        return None

    def get_holds(self):
        url = f"{self.DOMAIN}/api/dostk/acnt"

        header = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"{self.token_type} {self.access_token}",
            "api-id": "kt00004",
            "cont-yn": "N",
            "next-key": ""
        }

        params = {
            "qry_tp": "0", # 0: All, 1: Exclude Delisting]\

            "dmst_stex_tp": "KRX"
        }

        response = requests.post(url, headers=header, data=json.dumps(params))
        
        if response.status_code == 200:
            try:
                res = response.json()
                if res.get('rt_cd', '0') == '0' or res.get('return_code') == 0:
                    logger.info(f"[Kiwoom] Holds Response: {res}")
                    
                    holds = []
                    
                    data_list = res.get('stk_acnt_evlt_prst', [])
                    
                    for item in data_list:
                        # Mapping based on typical Kiwoom REST Account mapping (kt00004)
                        # stk_cd: Code
                        # stk_nm: Name
                        # avg_prc: Buying Price (Unit Price)
                        # rmnd_qty: Holding Qty
                        # evlt_amt: Evaluation Amount
                        # pl_amt: Profit/Loss
                        
                        code = item.get('stk_cd', '').strip().replace('A', '')  # Remove 'A' prefix if present
                        name = item.get('stk_nm', '').strip()
                        price = int(self._parse_int(item.get('avg_prc', '0')))
                        qty = int(self._parse_int(item.get('rmnd_qty', '0')))
                        total = int(self._parse_int(item.get('evlt_amt', '0')))
                        eval_pl = int(self._parse_int(item.get('pl_amt', '0')))
                        
                        if code:
                            holds.append(finestock.Hold(code, name, price, qty, total, eval_pl))
                            
                    return holds
                else:
                    logger.error(f"[Kiwoom] Holds Error: {res.get('msg1')} {res.get('msg2')}")
            except Exception as e:
                logger.error(f"[Kiwoom] JSON Parse Error: {e}")
        else:
             logger.error(f"[Kiwoom] HTTP Error: {response.status_code} {response.text}")
        return []
