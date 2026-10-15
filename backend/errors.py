"""사용자 정의 예외. 메시지에는 이름·학번·성적 같은 개인정보를 넣지 않는다."""


class CreditBridgeError(Exception):
    """사용자에게 그대로 보여줄 수 있는 업무 오류."""


class NotFoundError(CreditBridgeError):
    pass


class PermissionDeniedError(CreditBridgeError):
    pass


class UploadRejectedError(CreditBridgeError):
    pass


class DecisionValidationError(CreditBridgeError):
    pass


class LLMError(Exception):
    """LLM 호출 실패 또는 출력 검증 실패."""


class LLMRefusalError(LLMError):
    pass


class ConfigurationError(Exception):
    pass
