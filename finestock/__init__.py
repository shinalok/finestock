__version__ = '1.0.1.0'

from .api_factory import APIFactory, APIProvider
from .model import Price, OrderBook, Hoga, Hold, Account, Order, Trade, Stock, Index, TRADE_FLAG, ORDER_FLAG
from .comm.errors import FinestockError, FinestockNetworkError, FinestockAPIError

__all__ = ['Price', 'OrderBook', 'Hoga', 'Hold', 'Account', 'Order', 'Trade', 'Stock', 'Index', 'TRADE_FLAG', 'ORDER_FLAG', 'APIFactory', 'APIProvider', 'create_api',
           'FinestockError', 'FinestockNetworkError', 'FinestockAPIError']

def print_version_info():
    print(f"The version of this stock finance API is {__version__}.")

def create_api(api_provider: APIProvider):
    return APIFactory.create_api(api_provider)