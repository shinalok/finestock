from dataclasses import dataclass, field
from typing import List

from finestock.model.flag import TRADE_FLAG, ORDER_FLAG


@dataclass(frozen=True)
class Stock:
    code: str
    name: str # Name
    market: str # Market Name
    is_trading_suspended: bool = False # auditInfo or state mapping?
    is_administrative: bool = False # state mapping?

@dataclass(frozen=True)
class Index:
    code: str
    name: str
    market: str = "0" # marketCode
    group: str = ""

@dataclass(frozen=True)
class Hold:
    code: str
    name: str
    price: int
    qty: int
    total: int
    eval: int

@dataclass(frozen=True)
class Account:
    account_num: str
    account_num_sub: str
    deposit: int
    next_deposit: int
    pay_deposit: int
    hold: List[Hold] = field(default_factory=list)

@dataclass(frozen=True)
class Order:
    code: str
    name: str
    price: int
    qty: int
    order_flag: str
    order_num: str
    order_time: str = None
    id: str = None
    account_num: str = None
    # KIS 정정/취소(order-rvsecncl) 호출 시 필요한 "한국거래소전송주문조직번호".
    # do_order() 응답에 함께 내려오며, 다른 브로커는 이 개념이 없어 None으로 둔다.
    krx_fwdg_ord_orgno: str = None

@dataclass(frozen=True)
class Trade:
    code: str
    name: str
    trade_flag: TRADE_FLAG
    order_flag: ORDER_FLAG
    price: int
    qty: int
    trade_price: int
    trade_qty: int
    order_num: str
    order_time: str

__all__ = ['Hold', 'Account', 'Order', 'Trade', 'Stock', 'Index']