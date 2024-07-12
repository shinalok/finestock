import asyncio
import datetime
import json
import logging
import requests
import websockets
import finestock
from finestock.comm import API

class LS(API):
    def __init__(self):
        super().__init__()
        print("create Ebest Components")
        self.headers["tr_cont"] = "N"
        self.headers["tr_cont_key"] = ""
        self.is_run = True

    def oauth(self):
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecretkey": self.app_secret,
            "scope": "oob"
        }
        return super().oauth(data=data)

    def get_ohlcv(self, code, frdate="", todate=""):
        url = f"{self.DOMAIN}/{self.CHART}"
        header = self.headers.copy()
        header["tr_cd"] = "t8410"

        body = {
            "t8410InBlock": {
                "shcode": code,
                "gubun": "2", #주기구분(2:일3:주4:월5:년)
                "qrycnt": 500, #요청건수(최대-압축:2000비압축:500)
                "sdate": frdate,
                "edate": todate,
                "cts_date": "",
                "comp_yn": "N",
                "sujung": "Y"
            }
        }

        response = requests.post(url, headers=header, data=json.dumps(body))
        res = response.json()
        logging.debug(f"[API: oauth]\n"
                      f"[URL: {url}]\n"
                      f"[header: {header}]\n"
                      f"[param: {body}]\n"
                      f"[response: {res}]")

        if res['rsp_cd'] == "00000":
            ohlcvs = []
            for price in res['t8410OutBlock1']:
                ohlcvs.append(finestock.Price(price['date'], code, price['close'], price['open'], price['high'],
                                              price['low'], price['close'], price['jdiff_vol'], price['value']))

            return ohlcvs

    def get_index(self, code, frdate="", todate=""):
        url = f"{self.DOMAIN}/{self.INDEX}"
        header = self.headers.copy()
        header["tr_cd"] = "t8419"

        body = {
            "t8419InBlock": {
                "shcode": code,
                "gubun": "2", #주기구분(2:일3:주4:월5:년)
                "qrycnt": 500, #요청건수(최대-압축:2000비압축:500)
                "sdate": frdate,
                "edate": todate,
                "cts_date": "",
                "comp_yn": "N",
                "sujung": "Y"
            }
        }

        response = requests.post(url, headers=header, data=json.dumps(body))
        res = response.json()
        logging.debug(f"[API: oauth]\n"
                      f"[URL: {url}]\n"
                      f"[header: {header}]\n"
                      f"[param: {body}]\n"
                      f"[response: {res}]")

        if res['rsp_cd'] == "00000":
            ohlcvs = []
            for price in res['t8419OutBlock1']:
                ohlcvs.append(finestock.Price(price['date'], code, price['close'], price['open'], price['high'],
                                              price['low'], price['close'], price['jdiff_vol'], price['value']))

            return ohlcvs

    def get_index_list(self):
        url = f"{self.DOMAIN}/{self.INDEX_LIST}"
        header = self.headers.copy()
        header["tr_cd"] = "t8424"


        body = {
            "t8424InBlock": {
                "gubun1": "", #주기구분(2:일3:주4:월5:년)
            }
        }

        response = requests.post(url, headers=header, data=json.dumps(body))
        res = response.json()
        logging.debug(f"[API: oauth]\n"
                      f"[URL: {url}]\n"
                      f"[header: {header}]\n"
                      f"[param: {body}]\n"
                      f"[response: {res}]")

    def get_orderbook(self, code):
        url = f"{self.DOMAIN}/{self.ORDERBOOK}"
        header = self.headers.copy()
        header["tr_cd"] = "t1101"

        body = {
            "t1101InBlock": {
                "shcode": code,
            }
        }

        response = requests.post(url, headers=header, data=json.dumps(body))
        res = response.json()
        logging.debug(f"[API: oauth]\n"
                      f"[URL: {url}]\n"
                      f"[header: {header}]\n"
                      f"[param: {body}]\n"
                      f"[response: {res}]")

        if res['rsp_cd'] == "00000":
            data = res['t1101OutBlock']
            sells = []
            for i in range(1, 11):
                sells.append(finestock.Hoga(int(data[f'offerho{i}']), int(data[f'offerrem{i}'])))

            buys = []
            for i in range(1, 11):
                buys.append(finestock.Hoga(int(data[f'bidho{i}']), int(data[f'bidrem{i}'])))

            code = data['shcode']
            total_buy = data['bid']
            total_sell = data['offer']
            order = finestock.OrderBook(code, total_buy, total_sell, buys, sells)

            return order

    def get_balance(self):
        url = f"{self.DOMAIN}/{self.ACCOUNT}"
        header = self.headers.copy()
        header["tr_cd"] = "CSPAQ12200"

        body = {
            "CSPAQ12200InBlock1": {
                "BalCreTp": "0",
            }
        }

        response = requests.post(url, headers=header, data=json.dumps(body))
        res = response.json()
        logging.debug(f"[API: oauth]\n"
                      f"[URL: {url}]\n"
                      f"[header: {header}]\n"
                      f"[param: {body}]\n"
                      f"[response: {res}]")

        if res['rsp_cd'] == "00136":
            data1 = res['CSPAQ12200OutBlock1']
            account = data1['AcntNo']
            account_num = account[:-2]
            account_num_sub = account[-2:]
            data2 = res['CSPAQ12200OutBlock2']
            pay_deposit = data2['MnyOrdAbleAmt']
            holds = self.get_holds()
            return finestock.Account(account_num, account_num_sub, int(data2["Dps"]), int(data2["D1Dps"]),
                                     int(data2["D2Dps"]), holds)

    def get_holds(self):
        url = f"{self.DOMAIN}/{self.ACCOUNT}"
        header = self.headers.copy()
        header["tr_cd"] = "t0424"

        body = {
            "t0424InBlock": {
                "prcgb": "",
                "chegb": "",
                "dangb": "",
                "charge": "",
                "cts_expcode": ""
            }
        }

        response = requests.post(url, headers=header, data=json.dumps(body))
        res = response.json()
        logging.debug(f"[API: oauth]\n"
                      f"[URL: {url}]\n"
                      f"[header: {header}]\n"
                      f"[param: {body}]\n"
                      f"[response: {res}]")

        if res['rsp_cd'] == "00000":
            data = res['t0424OutBlock1']
            holds = []
            for hold in data:
                holds.append(finestock.Hold(hold['expcode'], hold['hname'], hold['pamt'], hold['janqty'], hold['appamt']))
            return holds
    def do_order(self, code, buy_flag, price, qty):
        url = f"{self.DOMAIN}/{self.ORDER}"
        header = self.headers.copy()
        header["tr_cd"] = "CSPAT00601"
        order_code = "1" if buy_flag == finestock.ORDER_FLAG.SELL else "2"
        OrdprcPtnCode = "03" if price == 0 else "00" #00: 지정가, 03: 시장가
        body = {
            "CSPAT00601InBlock1": {
                "IsuNo": code,
                "OrdQty": qty,
                "OrdPrc": price,
                "BnsTpCode": order_code,
                "OrdprcPtnCode": OrdprcPtnCode,
                "MgntrnCode": "000",
                "LoanDt": "",
                "OrdCndiTpCode": "0"
            }
        }

        response = requests.post(url, headers=header, data=json.dumps(body))
        res = response.json()
        logging.debug(f"[API: oauth]\n"
                      f"[URL: {url}]\n"
                      f"[header: {header}]\n"
                      f"[param: {body}]\n"
                      f"[response: {res}]")

        if res['rsp_cd'] == "00040":
            data1 = res['CSPAT00601OutBlock1']
            data2 = res['CSPAT00601OutBlock2']
            return finestock.Order(data1['IsuNo'], data2['IsuNm'], data1['OrdPrc'], data1['OrdQty'],
                                   data2['OrdNo'], data2['OrdTime'])

    def get_order_status(self, code):
        url = f"{self.DOMAIN}/{self.ACCOUNT}"
        header = self.headers.copy()
        header["tr_cd"] = "t0425"
        body = {
            "t0425InBlock": {
                "expcode": code,
                "chegb": "0",
                "medosu": "0",
                "sortgb": "2",
                "cts_ordno": " "
            }
        }

        response = requests.post(url, headers=header, data=json.dumps(body))
        res = response.json()
        logging.debug(f"[API: oauth]\n"
                      f"[URL: {url}]\n"
                      f"[header: {header}]\n"
                      f"[param: {body}]\n"
                      f"[response: {res}]")

        if res['rsp_cd'] == "00000":
            data1 = res['t0425OutBlock']
            data2 = res['t0425OutBlock1']
            orders = []
            for order in data2:
                trade_code = order['status']
                if trade_code == "접수":
                    trade_flag = finestock.TRADE_FLAG.ORDER
                elif trade_code == "02":
                    trade_flag = finestock.TRADE_FLAG.MODIFY
                elif trade_code == "03":
                    trade_flag = finestock.TRADE_FLAG.CANCLE
                elif trade_code == "11":
                    trade_flag = finestock.TRADE_FLAG.COMPLETE
                orders.append(finestock.Trade(order['expcode'], "", order['price'], trade_flag, order['qty'],
                                              order['cheprice'], order['cheqty'], str(order['ordno']), order['ordtime']))
            return orders

    def do_order_cancle(self, order_num, code, qty):
        url = f"{self.DOMAIN}/{self.ORDER}"
        header = self.headers.copy()
        header["tr_cd"] = "CSPAT00801"
        body = {
            "CSPAT00801InBlock1": {
                "OrgOrdNo": int(order_num),
                "IsuNo": code,
                "OrdQty": qty
            }
        }

        response = requests.post(url, headers=header, data=json.dumps(body))
        res = response.json()
        logging.debug(f"[API: oauth]\n"
                      f"[URL: {url}]\n"
                      f"[header: {header}]\n"
                      f"[param: {body}]\n"
                      f"[response: {res}]")

        if res['rsp_cd'] == "00156":
            data1 = res['CSPAT00801OutBlock1']
            data2 = res['CSPAT00801OutBlock2']

            return finestock.Order(data1['IsuNo'], data2['IsuNm'], 0, 0,
                                   data1['OrgOrdNo'], data2['OrdTime'])

    async def connect(self):
        print("connecting...")
        #self.ws = await websockets.connect(self.DOMAIN_WS, ssl=ssl_context)
        self.ws = await websockets.connect(self.DOMAIN_WS)
        print("complete connect")

    async def recv_price(self, code):
        header = {
            "token": self.access_token,
            "tr_type": "3"
        }
        body = {
            "tr_cd": "S3_",
            "tr_key": code
        }
        data = json.dumps({"header": header, "body": body})
        print(data)
        await self.ws.send(data)

    async def recv_index(self, code):
        header = {
            "token": self.access_token,
            "tr_type": "3"
        }
        body = {
            "tr_cd": "IJ_",
            "tr_key": code
        }
        data = json.dumps({"header": header, "body": body})
        await self.ws.send(data)

    async def recv_orderbook(self, code):
        header = {
            "token": self.access_token,
            "tr_type": "3"
        }
        body = {
            "tr_cd": "H1_",
            "tr_key": code
        }
        data = json.dumps({"header": header, "body": body})
        await self.ws.send(data)

    async def recv_order_status(self):
        header = {
            "token": self.access_token,
            "tr_type": "1"
        }
        body = {
            "tr_cd": "SC1",
            "tr_key": ""
        }
        data = json.dumps({"header": header, "body": body})
        await self.ws.send(data)

    def stop(self):
        print(self.is_run)
        try:
            self.is_run = False
            #asyncio.run(self.ws.close())
            print(self.is_run)
        except Exception as e:
            print(e)

    async def run(self):
        print("RUN")

        while self.is_run:
            try:
                #res = await self.ws.recv()
                res = await asyncio.wait_for(self.ws.recv(), timeout=1)
                res = json.loads(res)
                print(res)
                header = res['header']
                body = res['body']
                tr_cd = header['tr_cd']
                if ("rsp_cd" in header) and (header["rsp_cd"] == "00000"):
                    rsp_cd = header["rsp_cd"]
                    rsp_msg = header["rsp_msg"]
                    print(f"[{rsp_cd}]:{rsp_msg}")
                    continue

                if body:
                    data = res["body"]
                    code = res["header"]['tr_key']
                    if tr_cd == "H1_":
                        order = self._parse_orderbook(code, data)
                        print(order)
                    elif tr_cd in "S3_":
                        price = self._parse_price(code, data)
                        print(price)

                    elif tr_cd == "IJ_":
                        price = self._parse_index(code, data)
                        print(price)

                    elif tr_cd == "SC1":
                        trade = self._parse_trade(code, data)
                        print(trade)

            except asyncio.TimeoutError as e:
                pass
            except Exception as e:
                print(f"Exception: {e}")

        await self.ws.close()

    def _parse_orderbook(self, code, data):
        sells = []
        for i in range(1, 11):
            sells.append(finestock.Hoga(int(data[f'offerho{i}']), int(data[f'offerrem{i}'])))

        buys = []
        for i in range(1, 11):
            buys.append(finestock.Hoga(int(data[f'bidho{i}']), int(data[f'bidrem{i}'])))

        total_buy = data['totbidrem']
        total_sell = data['totofferrem']
        return finestock.OrderBook(code, total_buy, total_sell, buys, sells)

    def _parse_price(self, code, data):
        today = datetime.datetime.now().strftime('%Y%m%d')
        return finestock.Price(today, code, data['price'], data['open'], data['high'],
                               data['low'], data['price'], data['cvolume'], data['value'])

    def _parse_index(self, code, data):
        today = datetime.datetime.now().strftime('%Y%m%d')
        return finestock.Price(today, code, data['jisu'], data['openjisu'], data['highjisu'],
                               data['lowjisu'], data['jisu'], data['volume'], data['value'])

    def _parse_trade(self, code, data):
        today = datetime.datetime.now().strftime('%Y%m%d')
        trade_code = data['ordxctptncode']
        trade_flag = ""
        if trade_code == "01":
            trade_flag = finestock.TRADE_FLAG.ORDER
        elif trade_code == "02":
            trade_flag = finestock.TRADE_FLAG.MODIFY
        elif trade_code == "03":
            trade_flag = finestock.TRADE_FLAG.CANCLE
        elif trade_code == "11":
            trade_flag = finestock.TRADE_FLAG.COMPLETE

        return finestock.Trade(data['shtnIsuno'], data['Isunm'], trade_flag, data['ordprc'], data['ordqty'],
                               data['execprc'], data['execqty'], str(data['orgordno']), data['exectime'])

