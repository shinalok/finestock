class FinestockError(Exception):
    """finestock 공통 에러 베이스. 브로커별 원본 예외 대신 이 계층을 잡으면 된다."""


class FinestockNetworkError(FinestockError):
    """
    요청 자체가 실패한 경우(연결 실패, DNS 실패, 타임아웃 등).
    브로커 서버가 응답했지만 내용이 비정상인 경우는 FinestockAPIError를 쓴다.
    """


class FinestockAPIError(FinestockError):
    """
    브로커 서버가 응답은 했지만 내용을 신뢰할 수 없는 경우
    (JSON이 아닌 바디 등). HTTP 상태 코드/에러 판정 필드(rt_cd, rsp_cd 등)는
    브로커마다 달라 이 예외에서 강제하지 않고, 원인 파악에 필요한 정보만
    status_code/response_text에 담아 전달한다.
    """

    def __init__(self, message, status_code=None, response_text=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
