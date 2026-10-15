"""Anthropic SDK 호출 단일 진입점. 다른 모듈에서 SDK를 직접 호출하지 않는다."""

import base64
import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal

import anthropic
from pydantic import BaseModel, ValidationError

from backend.config import Settings, get_settings
from backend.errors import ConfigurationError, LLMError, LLMRefusalError

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


class LLMClient:
    def __init__(self, settings: Settings, client: anthropic.Anthropic | None = None) -> None:
        if not settings.claude_model:
            raise ConfigurationError("CLAUDE_MODEL is not set")
        self._model = settings.claude_model
        # 서버 측 대체 모델은 Claude API에서만 쓸 수 있다. 다른 플랫폼이나 프록시를 거치면 끈다
        self._fallback = settings.claude_server_fallback
        self._client = client or anthropic.Anthropic(api_key=settings.anthropic_api_key or None, max_retries=3)

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
        content: list[dict[str, Any]] = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(img).decode()},
            }
            for img in images or []
        ]
        content.append({"type": "text", "text": prompt})
        schema = strict_schema(output_model)

        last_error: Exception | None = None
        for attempt in range(2):
            try:
                params: dict[str, Any] = {
                    "model": self._model,
                    "max_tokens": max_tokens,
                    "output_config": {"effort": effort, "format": {"type": "json_schema", "schema": schema}},
                    "messages": [{"role": "user", "content": content}],
                }
                if self._fallback:
                    params["betas"] = [FALLBACK_BETA]
                    params["fallbacks"] = "default"
                response = self._client.beta.messages.create(**params)
            except anthropic.APIError as exc:
                raise LLMError(f"Claude API error: {type(exc).__name__}") from exc

            if response.stop_reason == "refusal":
                raise LLMRefusalError("the model declined the request")
            text = "".join(block.text for block in response.content if block.type == "text")
            try:
                if response.stop_reason == "max_tokens":
                    raise ValueError("output truncated at max_tokens")
                return LLMResult(output=output_model.model_validate(json.loads(text)), model=response.model)
            except (ValueError, ValidationError) as exc:
                last_error = exc
                logger.warning(
                    "llm output failed validation", extra={"attempt": attempt + 1, "model_type": output_model.__name__}
                )
        raise LLMError(f"output failed validation twice: {type(last_error).__name__}")


@lru_cache
def get_llm() -> LLMClient:
    return LLMClient(get_settings())
