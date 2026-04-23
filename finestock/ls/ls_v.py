from loguru import logger
from finestock.ls import LS

class LSV(LS):

    def __init__(self):
        super().__init__()
        print("create LS_V Components")

    def __del__(self):
        logger.debug("Destory LS_V Components")
