"""app/ai/prompts/*.md 템플릿 로더. 첫 줄의 <!-- version: ... --> 를 프롬프트 버전으로 쓴다."""

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from string import Template

PROMPT_DIR = Path(__file__).parent / "prompts"
_VERSION = re.compile(r"<!--\s*version:\s*([\w.-]+)\s*-->\s*\n?")


@dataclass(frozen=True)
class Prompt:
    name: str
    version: str
    template: str

    def render(self, **values: str) -> str:
        return Template(self.template).substitute(values)


@cache
def load_prompt(name: str) -> Prompt:
    raw = (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")
    match = _VERSION.match(raw)
    if not match:
        raise ValueError(f"prompt {name} has no version header")
    return Prompt(name=name, version=match.group(1), template=raw[match.end() :])
