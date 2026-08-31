from enum import Enum

class APIProvider(Enum):
    EBEST = "EBEST"
    LS = "LS"
    LSV = "LSV"
    KIS = "KIS"
    KISV = "KISV"
    KIWOOM = "KIWOOM"
    KIWOOMV = "KIWOOMV"
    NH = "NH"
    NHV = "NHV"

class APIFactory:
    @staticmethod
    def create_api(api_provider: APIProvider):
        if api_provider == APIProvider.EBEST:
            from .ebest import EBest
            return EBest()
        elif api_provider == APIProvider.LS:
            from .ls import LS
            return LS()
        elif api_provider == APIProvider.LSV:
            from .ls import LSV
            return LSV()
        elif api_provider == APIProvider.KIS:
            from .kis import Kis
            return Kis()
        elif api_provider == APIProvider.KISV:
            from .kis import KisV
            return KisV()
        elif api_provider == APIProvider.KIWOOM:
            from .kiwoom import Kiwoom
            return Kiwoom()
        elif api_provider == APIProvider.KIWOOMV:
             from .kiwoom import KiwoomV
             return KiwoomV()
        elif api_provider == APIProvider.NH:
            from .nh import Nh
            return Nh()
        elif api_provider == APIProvider.NHV:
            from .nh import NhV
            return NhV()
        else:
            raise ValueError("Unsupported API provider")