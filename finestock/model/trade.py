from dataclasses import dataclass, field
from typing import List
from enum import Enum

class TRADE_FLAG(Enum):
    ORDER = 1
    MODIFY = 2
    CANCLE = 3
    COMPLETE = 4

class ORDER_FLAG(Enum):
    BUY = 1
    SELL = 2
    VIEW = 3

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
    order_num: str
    order_time: str

@dataclass(frozen=True)
class Trade:
    code: str
    name: str
    trade_flag: TRADE_FLAG
    price: int
    qty: int
    trade_price: int
    trade_qty: int
    order_num: str
    order_time: str