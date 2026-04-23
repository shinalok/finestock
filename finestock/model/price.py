from dataclasses import dataclass, field
from typing import List

@dataclass(frozen=True)
class Price:
    workday: str
    code: str
    price: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    volume_amt: int
    time: str = None
    hightime: str = None
    lowtime: str = None

    @classmethod
    def from_values(cls, workday, code, price, open_, high, low, close, volume, volume_amt,
                    time=None, hightime=None, lowtime=None):
        return cls(
            workday=str(workday),
            code=str(code),
            price=float(price),
            open=float(open_),
            high=float(high),
            low=float(low),
            close=float(close),
            volume=int(volume),
            volume_amt=int(volume_amt),
            time=time,
            hightime=hightime,
            lowtime=lowtime
        )

    @classmethod
    def from_series(cls, series):
        """
        Converts a pandas Series (a row from a DataFrame) into a Price instance.
        If `code` is not provided, attempts to use series['code'].
        """
        return cls.from_values(
            workday=series['date'],
            code=series['code'],
            price=series['close'],
            open_=series['open'],
            high=series['high'],
            low=series['low'],
            close=series['close'],
            volume=series['volume'],
            volume_amt=series['volume_amt'],
            time=series.get('time', None),
            hightime=series.get('hightime', None),
            lowtime=series.get('lowtime', None)
        )


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

__all__ = ['Price', 'Hoga', 'OrderBook']