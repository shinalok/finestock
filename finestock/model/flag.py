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

class MARKET_FLAG(Enum):
    KOSPI = 1
    KOSDAQ = 2
    #ETF = 3
    #ETN = 4

__all__ = ['TRADE_FLAG', 'ORDER_FLAG', 'MARKET_FLAG']