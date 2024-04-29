from dataclasses import dataclass, field
from typing import List

@dataclass(frozen=True)
class Price:
    workday: str
    code: str
    price: int
    open: int
    high: int
    low: int
    close: int
    volume: int
    volume_amt: int

@dataclass(frozen=True)
class Hoga:
    price: int
    qty: int

@dataclass(frozen=True)
class OrderBook:
    code: str
    total_buy: int
    total_sell: int
    buy: List[Hoga] = field(default_factory=list)
    sell: List[Hoga] = field(default_factory=list)