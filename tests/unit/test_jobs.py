"""작업 오류 분류와 재시도 정책 (리뷰 v3 P1-3)."""

from backend.errors import DocumentParseError, LLMError, LLMNotConfiguredError, LLMRefusalError
from backend.services import jobs


def test_error_codes() -> None:
    assert jobs.error_code(LLMError("Claude API error: RateLimitError")) == "llm_rate_limit"
    assert jobs.error_code(LLMError("OpenAI API error: APITimeoutError")) == "llm_timeout"
    assert jobs.error_code(LLMError("Claude API error: APIConnectionError")) == "llm_connection"
    assert jobs.error_code(LLMError("Claude API error: InternalServerError")) == "llm_server"
    assert jobs.error_code(LLMError("output failed validation twice: ValidationError")) == "llm_invalid_output"
    assert jobs.error_code(LLMRefusalError("declined")) == "llm_refusal"
    assert jobs.error_code(LLMNotConfiguredError("x")) == "not_configured"
    assert jobs.error_code(DocumentParseError("page 2")) == "document_unreadable"
    assert jobs.error_code(KeyError("x")) == "unexpected:KeyError"


def test_only_transient_errors_retry() -> None:
    assert {"llm_rate_limit", "llm_timeout", "llm_server", jobs.TASK_TIMEOUT} <= jobs.RETRYABLE
    assert not {"not_configured", "document_unreadable", "llm_refusal"} & jobs.RETRYABLE


def test_percentile() -> None:
    assert jobs._percentile([], 0.5) is None
    assert jobs._percentile([5, 1, 3], 0.5) == 3
    assert jobs._percentile(list(range(1, 101)), 0.95) == 95
