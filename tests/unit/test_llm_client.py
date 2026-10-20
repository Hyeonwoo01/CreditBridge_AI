from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from backend.ai.llm_client import FALLBACK_BETA, LLMClient, strict_schema
from backend.config import Settings
from backend.errors import LLMError, LLMNotConfiguredError, LLMRefusalError
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
    return LLMClient(Settings(llm_provider="anthropic", claude_model="configured-model"), client=fake), messages  # type: ignore[arg-type]


def test_model_comes_from_settings_and_request_shape() -> None:
    llm, messages = client_with([("end_turn", '{"answer": "ok"}')])
    result = llm.parse("hi", Out, effort="low")
    assert result.output.answer == "ok"
    call = messages.calls[0]
    assert call["model"] == "configured-model"
    assert call["betas"] == [FALLBACK_BETA] and call["fallbacks"] == "default"
    assert call["output_config"]["effort"] == "low"
    assert call["output_config"]["format"]["schema"]["additionalProperties"] is False


def test_missing_settings_fail_on_call_not_on_startup() -> None:
    # 작업이 시작부터 예외로 끝나 "분석 중"에 멈추지 않도록, 만들 때는 통과하고 부를 때 LLMError 계열로 알린다
    llm = LLMClient(Settings(llm_provider="anthropic", claude_model="", anthropic_api_key=""))
    with pytest.raises(LLMNotConfiguredError, match="CLAUDE_MODEL, ANTHROPIC_API_KEY"):
        llm.parse("hi", Out)
    with pytest.raises(LLMNotConfiguredError, match="ANTHROPIC_API_KEY"):
        LLMClient(Settings(llm_provider="anthropic", claude_model="m", anthropic_api_key="")).parse("hi", Out)


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
    settings = Settings(llm_provider="anthropic", claude_model="m", claude_server_fallback=False)
    LLMClient(settings, client=fake).parse("hi", Out)  # type: ignore[arg-type]
    assert "betas" not in messages.calls[0] and "fallbacks" not in messages.calls[0]


# ---------- OpenAI (GPT) ----------


class FakeCompletions:
    def __init__(self, replies: list[tuple[str, str | None, str | None]]) -> None:
        self.replies = replies  # (finish_reason, content, refusal)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        finish, content, refusal = self.replies.pop(0)
        message = SimpleNamespace(content=content, refusal=refusal)
        return SimpleNamespace(model="gpt-m", choices=[SimpleNamespace(finish_reason=finish, message=message)])


def openai_with(
    replies: list[tuple[str, str | None, str | None]], **settings: Any
) -> tuple[LLMClient, FakeCompletions]:
    completions = FakeCompletions(replies)
    fake = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    config = Settings(llm_provider="openai", openai_model="gpt-configured", **settings)
    return LLMClient(config, client=fake), completions


def test_openai_request_shape_and_result() -> None:
    llm, completions = openai_with([("stop", '{"answer": "ok"}', None)])
    result = llm.parse("hi", Out, images=[b"png"], effort="low")
    assert result.output.answer == "ok" and result.model == "gpt-m" and llm.model == "gpt-configured"
    call = completions.calls[0]
    assert call["model"] == "gpt-configured" and call["reasoning_effort"] == "low"
    fmt = call["response_format"]
    assert fmt["type"] == "json_schema" and fmt["json_schema"]["strict"] is True
    assert fmt["json_schema"]["name"] == "Out" and fmt["json_schema"]["schema"]["additionalProperties"] is False
    image, text = call["messages"][0]["content"]
    assert image["image_url"]["url"].startswith("data:image/png;base64,") and text == {"type": "text", "text": "hi"}
    assert "betas" not in call  # Claude 전용 서버 대체 모델은 보내지 않는다


def test_openai_retries_invalid_and_truncated_output_then_fails() -> None:
    llm, completions = openai_with([("length", '{"answer": "cut', None), ("stop", '{"answer": "fixed"}', None)])
    assert llm.parse("hi", Out).output.answer == "fixed" and len(completions.calls) == 2
    llm, _ = openai_with([("stop", "{}", None), ("stop", "not json", None)])
    with pytest.raises(LLMError):
        llm.parse("hi", Out)


def test_openai_refusal_is_not_retried() -> None:
    llm, completions = openai_with([("stop", None, "I can't help with that")])
    with pytest.raises(LLMRefusalError):
        llm.parse("hi", Out)
    assert len(completions.calls) == 1


def test_openai_missing_settings_and_effort_switch() -> None:
    with pytest.raises(LLMNotConfiguredError, match="OPENAI_MODEL, OPENAI_API_KEY"):
        LLMClient(Settings(llm_provider="openai", openai_model="", openai_api_key="")).parse("hi", Out)
    llm, completions = openai_with([("stop", '{"answer": "ok"}', None)], openai_reasoning_effort=False)
    llm.parse("hi", Out)
    assert "reasoning_effort" not in completions.calls[0]  # 추론 모델이 아닌 GPT용
