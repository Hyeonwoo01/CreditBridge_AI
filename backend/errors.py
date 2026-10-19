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


class DuplicateRowError(Exception):
    """DB 유니크 규칙에 걸려 행을 넣지 못함 (동시에 같은 요청이 들어온 경우). 서비스가 업무 오류로 바꿔 보여 준다."""


def is_duplicate(exc: Exception) -> bool:
    """IntegrityError가 유니크 키 중복(PostgreSQL SQLSTATE 23505)인지."""
    orig = getattr(exc, "orig", None)
    return getattr(orig, "sqlstate", None) == "23505"


class LLMError(Exception):
    """LLM 호출 실패 또는 출력 검증 실패."""


class LLMRefusalError(LLMError):
    pass


class LLMNotConfiguredError(LLMError):
    """Claude 설정(ANTHROPIC_API_KEY·CLAUDE_MODEL)이 없어 AI를 부를 수 없음. 분석은 실패로 표시하고 안내한다."""
