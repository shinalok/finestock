from .ebest import EBest
from .ls import LS
from .kis import Kis, KisV

class APIFactory:
    @staticmethod
    def create_api(api_type):
        if api_type == "EBest":
            return EBest()
        elif api_type == "LS":
            return LS()
        elif api_type == "Kis":
            return Kis()
        elif api_type == "KisV":
            return KisV()
        else:
            raise ValueError("Unsupported api type")