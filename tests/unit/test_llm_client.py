from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from backend.ai.llm_client import FALLBACK_BETA, LLMClient, strict_schema
from backend.config import Settings
from backend.errors import ConfigurationError, LLMError, LLMRefusalError
from backend.schemas.transcript import TranscriptExtraction


class Out(BaseModel):
    answer: str


class FakeMessages:
    def __init__(self, replies: list[tuple[str, str]]) -> None:
        self.replies = replies
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        stop, text = self.replies.pop(0)
        return SimpleNamespace(stop_reason=stop, model="m", content=[SimpleNamespace(type="text", text=text)])


def client_with(replies: list[tuple[str, str]]) -> tuple[LLMClient, FakeMessages]:
    messages = FakeMessages(replies)
    fake = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    return LLMClient(Settings(claude_model="configured-model"), client=fake), messages  # type: ignore[arg-type]


def test_model_comes_from_settings_and_request_shape() -> None:
    llm, messages = client_with([("end_turn", '{"answer": "ok"}')])
    result = llm.parse("hi", Out, effort="low")
    assert result.output.answer == "ok"
    call = messages.calls[0]
    assert call["model"] == "configured-model"
    assert call["betas"] == [FALLBACK_BETA] and call["fallbacks"] == "default"
    assert call["output_config"]["effort"] == "low"
    assert call["output_config"]["format"]["schema"]["additionalProperties"] is False


def test_missing_model_is_a_configuration_error() -> None:
    with pytest.raises(ConfigurationError):
        LLMClient(Settings(claude_model=""))


def test_retries_once_on_invalid_output_then_fails() -> None:
    llm, messages = client_with([("end_turn", "not json"), ("end_turn", '{"answer": "fixed"}')])
    assert llm.parse("hi", Out).output.answer == "fixed"
    assert len(messages.calls) == 2

    llm, _ = client_with([("end_turn", "{}"), ("end_turn", '{"wrong": 1}')])
    with pytest.raises(LLMError):
        llm.parse("hi", Out)


def test_refusal_is_not_retried() -> None:
    llm, messages = client_with([("refusal", "")])
    with pytest.raises(LLMRefusalError):
        llm.parse("hi", Out)
    assert len(messages.calls) == 1


def test_strict_schema_keeps_property_named_title() -> None:
    schema = strict_schema(TranscriptExtraction)
    line = schema["$defs"]["TranscriptLine"]
    assert "title" in line["properties"] and "title" in line["required"]
    assert "title" not in line  # 스키마 메타데이터 title은 제거


def test_stripped_constraints_are_written_into_description() -> None:
    from backend.schemas.evaluation import ConceptJudgment

    coverage = strict_schema(ConceptJudgment)["properties"]["coverage"]
    assert "minimum" not in coverage and "maximum" not in coverage  # 구조화 출력이 지원하지 않는 키워드
    assert coverage["description"].endswith("(minimum 0, maximum 100)")


def test_out_of_range_value_is_still_rejected_by_pydantic() -> None:
    from pydantic import Field

    class Score(BaseModel):
        value: int = Field(ge=0, le=100)

    llm, messages = client_with([("end_turn", '{"value": 150}'), ("end_turn", '{"value": 90}')])
    assert llm.parse("hi", Score).output.value == 90 and len(messages.calls) == 2


def test_server_fallback_can_be_turned_off() -> None:
    messages = FakeMessages([("end_turn", '{"answer": "ok"}')])
    fake = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    settings = Settings(claude_model="m", claude_server_fallback=False)
    LLMClient(settings, client=fake).parse("hi", Out)  # type: ignore[arg-type]
    assert "betas" not in messages.calls[0] and "fallbacks" not in messages.calls[0]
