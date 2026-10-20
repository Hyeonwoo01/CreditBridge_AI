"""LLM 호출 단일 진입점 (Claude: Anthropic SDK, GPT: OpenAI SDK). 다른 모듈에서 SDK를 직접 호출하지 않는다.

어느 쪽을 쓸지는 Settings.llm_provider로 고르고, 호출하는 쪽은 parse() 하나만 쓴다."""

import base64
import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from backend.config import Settings, get_settings
from backend.errors import LLMError, LLMNotConfiguredError, LLMRefusalError

logger = logging.getLogger(__name__)

Effort = Literal["low", "medium", "high"]

# 정책 거절 시 서버가 적합한 모델로 다시 시도한다 (모델 목록을 직접 관리하지 않음).
# 이 헤더는 `fallbacks: "default"` 요청 형태와 한 쌍이라 따로 바꾸면 400이 난다. 켜고 끄기만 Settings로 한다.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
# 구조화 출력이 지원하지 않는 키워드. 보내기 전에 지우고, 응답은 원래 Pydantic 모델로 다시 검증한다.
_METADATA_KEYS = {"title", "default"}
_CONSTRAINT_KEYS = {
    "minimum": "minimum",
    "maximum": "maximum",
    "exclusiveMinimum": "greater than",
    "exclusiveMaximum": "less than",
    "multipleOf": "multiple of",
    "minLength": "min length",
    "maxLength": "max length",
    "minItems": "min items",
    "maxItems": "max items",
}


@dataclass(frozen=True)
class LLMResult[T: BaseModel]:
    output: T
    model: str


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Pydantic 스키마를 구조화 출력용으로 정리: 모든 객체에 additionalProperties=false, 전 필드 required.

    지원하지 않는 수치·길이 제약은 지우는 대신 description 끝에 적어 모델이 범위를 알게 한다.
    지운 제약은 응답을 받은 뒤 원래 Pydantic 모델의 검증(실패 시 1회 재시도)이 그대로 강제한다.
    """

    def walk(node: Any) -> Any:
        if isinstance(node, list):
            return [walk(v) for v in node]
        if not isinstance(node, dict):
            return node
        out: dict[str, Any] = {}
        for key, value in node.items():
            if key in ("properties", "$defs"):
                # 필드 이름·정의 이름은 그대로 두고 그 안의 스키마만 정리한다
                out[key] = {name: walk(sub) for name, sub in value.items()}
            elif key not in _METADATA_KEYS and key not in _CONSTRAINT_KEYS:
                out[key] = walk(value)
        limits = [f"{label} {node[key]}" for key, label in _CONSTRAINT_KEYS.items() if key in node]
        if limits:
            note = f"({', '.join(limits)})"
            out["description"] = f"{out['description']} {note}" if out.get("description") else note
        if out.get("type") == "object" and "properties" in out:
            out["additionalProperties"] = False
            out["required"] = list(out["properties"].keys())
        return out

    result: dict[str, Any] = walk(model.model_json_schema())
    return result


@dataclass(frozen=True)
class _Reply:
    text: str
    truncated: bool  # 출력 토큰 상한에 걸려 잘림
    model: str


class LLMClient:
    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        """client는 테스트용 가짜 SDK 클라이언트. 없으면 고른 공급자의 SDK로 만든다
        (SDK는 실제로 쓸 때만 불러온다: 데모 모드는 메모리를 아낀다)."""
        self._provider = settings.llm_provider
        if self._provider == "openai":
            required = (("OPENAI_MODEL", settings.openai_model), ("OPENAI_API_KEY", settings.openai_api_key or client))
            self._model = settings.openai_model
        else:
            required = (
                ("CLAUDE_MODEL", settings.claude_model),
                ("ANTHROPIC_API_KEY", settings.anthropic_api_key or client),
            )
            self._model = settings.claude_model
        # 설정이 빠졌으면 여기서 멈추지 않고 부를 때 LLMNotConfiguredError를 낸다:
        # 작업이 예외로 끝나 화면이 "분석 중"에 멈추는 대신 분석 실패와 설정 안내를 보여 준다
        self._missing = [name for name, value in required if not value]
        # 서버 측 대체 모델은 Claude API에서만 쓸 수 있다. 다른 플랫폼이나 프록시를 거치면 끈다
        self._fallback = settings.claude_server_fallback
        self._send_effort = settings.openai_reasoning_effort
        self._client: Any
        if client is not None or self._missing:
            # 키가 없으면 SDK를 만들지 않는다 (OpenAI SDK는 키 없이 만들면 바로 예외를 낸다)
            self._client = client
        elif self._provider == "openai":
            import openai

            self._client = openai.OpenAI(api_key=settings.openai_api_key or None, max_retries=3)
        else:
            import anthropic

            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key or None, max_retries=3)

    @property
    def model(self) -> str:
        return self._model

    def parse[T: BaseModel](
        self,
        prompt: str,
        output_model: type[T],
        *,
        images: list[bytes] | None = None,
        effort: Effort = "medium",
        max_tokens: int = 16000,
    ) -> LLMResult[T]:
        """프롬프트를 보내고 결과를 Pydantic으로 검증한다. 검증 실패 시 1회 재시도한다."""
        if self._missing:
            raise LLMNotConfiguredError(f"not configured: {', '.join(self._missing)}")
        schema = strict_schema(output_model)
        call = self._call_openai if self._provider == "openai" else self._call_anthropic

        last_error: Exception | None = None
        for attempt in range(2):
            reply = call(prompt, images or [], schema, output_model.__name__, effort, max_tokens)
            try:
                if reply.truncated:
                    raise ValueError("output truncated at max_tokens")
                return LLMResult(output=output_model.model_validate(json.loads(reply.text)), model=reply.model)
            except (ValueError, ValidationError) as exc:
                last_error = exc
                logger.warning(
                    "llm output failed validation", extra={"attempt": attempt + 1, "model_type": output_model.__name__}
                )
        raise LLMError(f"output failed validation twice: {type(last_error).__name__}")

    def _call_anthropic(
        self, prompt: str, images: list[bytes], schema: dict[str, Any], name: str, effort: Effort, max_tokens: int
    ) -> _Reply:
        import anthropic

        content: list[dict[str, Any]] = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(img).decode()},
            }
            for img in images
        ]
        content.append({"type": "text", "text": prompt})
        params: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "output_config": {"effort": effort, "format": {"type": "json_schema", "schema": schema}},
            "messages": [{"role": "user", "content": content}],
        }
        if self._fallback:
            params["betas"] = [FALLBACK_BETA]
            params["fallbacks"] = "default"
        try:
            response = self._client.beta.messages.create(**params)
        except anthropic.APIError as exc:
            raise LLMError(f"Claude API error: {type(exc).__name__}") from exc
        if response.stop_reason == "refusal":
            raise LLMRefusalError("the model declined the request")
        text = "".join(block.text for block in response.content if block.type == "text")
        return _Reply(text, response.stop_reason == "max_tokens", response.model)

    def _call_openai(
        self, prompt: str, images: list[bytes], schema: dict[str, Any], name: str, effort: Effort, max_tokens: int
    ) -> _Reply:
        import openai

        content: list[dict[str, Any]] = [
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(img).decode()}}
            for img in images
        ]
        content.append({"type": "text", "text": prompt})
        params: dict[str, Any] = {
            "model": self._model,
            "max_completion_tokens": max_tokens,
            # strict: 스키마에 맞는 JSON만 돌려준다 (strict_schema가 맞춘 형태 그대로)
            "response_format": {"type": "json_schema", "json_schema": {"name": name, "schema": schema, "strict": True}},
            "messages": [{"role": "user", "content": content}],
        }
        if self._send_effort:
            params["reasoning_effort"] = effort
        try:
            response = self._client.chat.completions.create(**params)
        except openai.APIError as exc:
            raise LLMError(f"OpenAI API error: {type(exc).__name__}") from exc
        choice = response.choices[0]
        if choice.message.refusal or choice.finish_reason == "content_filter":
            raise LLMRefusalError("the model declined the request")
        return _Reply(choice.message.content or "", choice.finish_reason == "length", response.model)


@lru_cache
def get_llm() -> LLMClient:
    settings = get_settings()
    if settings.demo_mode:
        from backend.ai.demo_llm import DemoLLM  # demo_llm이 이 모듈을 가져오므로 여기서 가져온다

        return DemoLLM()
    return LLMClient(settings)
