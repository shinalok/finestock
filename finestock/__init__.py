__version__ = '0.0.4'

from .api_fcatory import APIFactory
from .model import *
from .ebest import *
from .kis import *

__all__ = ['APIFactory', 'model',]


APIS = ["EBEST", "KIS", "LS"]

def print_version_info():
    print(f"The version of this stock finance API is {__version__}.")

def create_api(api_type):
    return APIFactory.create_api(api_type)