from abc import ABC, abstractmethod
from typing import Any, List, Optional

class AuthenticationProvider(ABC):
    @abstractmethod
    def oauth(self) -> Any:
        raise NotImplementedError

    @abstractmethod
    def set_oauth_info(self, app_key: str, app_secret: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_access_token(self, token: str) -> None:
        raise NotImplementedError

class MarketDataProvider(ABC):
    @abstractmethod
    def get_price(self, code: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def get_ohlcv(self, code: str, frdate: str, todate: str) -> List[Any]:
        raise NotImplementedError

    @abstractmethod
    def get_ohlcv_min(self, code: str, todate: str = "", exchgubun: str = "K", 
                      cts_date: str = "", cts_time: str = "", tr_cont_key: str = "") -> List[Any]:
        raise NotImplementedError

    @abstractmethod
    def get_index(self, code: str, frdate: str, todate: str) -> List[Any]:
        raise NotImplementedError

    @abstractmethod
    def get_index_min(self, code: str, todate: str, cts_date: str = " ", 
                      cts_time: str = "", tr_cont_key: str = "") -> List[Any]:
        raise NotImplementedError

    @abstractmethod
    def get_orderbook(self, code: str) -> Any:
        raise NotImplementedError

class TradingProvider(ABC):
    @abstractmethod
    def do_order(self, code: str, buy_flag: Any, price: int, qty: int) -> Any:
        raise NotImplementedError

    @abstractmethod
    def do_order_cancel(self, order_num: str, code: str, qty: int) -> Any:
        raise NotImplementedError

class RealtimeProvider(ABC):
    @abstractmethod
    def set_data_queue(self, queue: Any) -> None:
        """
        Inject a queue to receive realtime data.
        The queue should support a .put(item) method.
        """
        raise NotImplementedError

    @abstractmethod
    async def recv_price(self, code: str, status: bool = True) -> None:
        raise NotImplementedError

    @abstractmethod
    async def recv_index(self, code: str, status: bool = True) -> None:
        raise NotImplementedError

    @abstractmethod
    async def recv_orderbook(self, code: str, status: bool = True) -> None:
        raise NotImplementedError

    @abstractmethod
    async def recv_trade(self, code: str, status: bool = True) -> None:
        raise NotImplementedError

class AccountProvider(ABC):
    @abstractmethod
    def get_balance(self) -> Any:
        raise NotImplementedError

    @abstractmethod
    def get_holds(self) -> List[Any]:
        raise NotImplementedError

class InfoProvider(ABC):
    @abstractmethod
    def get_stock_list(self, mrkt_tp: str = "0") -> List[Any]:
        raise NotImplementedError

    @abstractmethod
    def get_index_list(self) -> List[Any]:
        raise NotImplementedError

class BaseProvider(AuthenticationProvider, MarketDataProvider, TradingProvider, RealtimeProvider, AccountProvider, InfoProvider):
    """
    Composite interface for backward compatibility or full implementation.
    """
    pass
