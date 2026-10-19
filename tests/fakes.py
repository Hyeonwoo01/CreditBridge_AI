"""테스트용 대역: Claude, S3. 외부 API는 테스트에서 호출하지 않는다 (실제 호출은 tests/eval)."""

from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from backend.ai.demo_llm import UNVERIFIABLE_QUOTE as FABRICATED_QUOTE
from backend.ai.demo_llm import DemoLLM, tokens
from backend.ai.llm_client import LLMResult

__all__ = ["FABRICATED_QUOTE", "FakeLLM", "FakeStorage", "tokens"]


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    @staticmethod
    def new_key(kind: str, filename: str) -> str:
        return f"{kind}/{uuid4()}/{filename}"

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = data

    def get(self, key: str) -> bytes:
        return self.objects[key]

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)


class FakeLLM(DemoLLM):
    """데모용 예시 AI에 테스트 기능을 더한 것: 보낸 프롬프트를 calls에 남기고, fail_with로 실패를 흉내 낸다."""

    MODEL = "fake-claude"
    REASON = "테스트 판단"
    REASON_EN = "Test judgment"
    SUMMARY = "요약"
    SUMMARY_EN = "Summary"

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, str]] = []
        self.fail_with: Exception | None = None

    def parse(self, prompt: str, output_model: type[BaseModel], **kwargs: Any) -> LLMResult[Any]:  # type: ignore[override]
        self.calls.append((output_model.__name__, prompt))
        if self.fail_with:
            raise self.fail_with
        return super().parse(prompt, output_model, **kwargs)

    def prompts(self, kind: str) -> list[str]:
        return [p for k, p in self.calls if k == kind]
