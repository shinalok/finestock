from abc import ABC, abstractmethod


class IAPI(ABC):
    @abstractmethod
    def oauth(self):
        raise NotImplemented

    @abstractmethod
    def get_ohlcv(self, code, frdate, todate):
        raise NotImplemented

    @abstractmethod
    def get_index(self, code, frdate, todate):
        raise NotImplemented

    @abstractmethod
    def get_orderbook(self, code):
        raise NotImplemented

    @abstractmethod
    def set_queue(self, queue, condition):
        raise NotImplemented