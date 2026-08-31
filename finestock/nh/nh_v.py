from loguru import logger
from finestock.nh import Nh


class NhV(Nh):
    """
    NH투자증권 모의투자(Mock). DOMAIN/DOMAIN_WS만 모의투자(moapi) 도메인으로 바뀌며
    (path.py 참고), 나머지 REST/WS 엔드포인트·필드는 운영과 동일하다.

    접근토큰발급(oauth2/token)은 모의투자에서 제공되지 않아 Nh.oauth()가 항상
    OAUTH_DOMAIN(운영)을 바라보도록 되어 있고, 여기서도 그대로 상속해 사용한다.
    """

    def __init__(self):
        super().__init__()
        print("create NhV Components")

    def __del__(self):
        logger.debug("Destroy NhV Components")
