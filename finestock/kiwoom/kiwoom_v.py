from loguru import logger
from finestock.kiwoom.kiwoom import Kiwoom

class KiwoomV(Kiwoom):
    """
    Kiwoom Mock Investment Version
    """
    def __init__(self):
        super().__init__()
        print("create KiwoomV Components")

    def __del__(self):
        logger.debug("Destroy KiwoomV Components")
