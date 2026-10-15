"""문서 속 숨은 지시 문구 탐지 (FR-14). 탐지한 줄은 경고하고 LLM 입력에서 제외한다."""

import re
from dataclasses import dataclass

_PATTERNS = [
    re.compile(
        r"\b(ignore|disregard|forget)\b.{0,40}\b(previous|above|prior|all|earlier)\b.{0,30}\b(instructions?|prompts?|rules)\b",
        re.I,
    ),
    re.compile(
        r"\b(approve|grant|accept|award|recommend)\b.{0,40}"
        r"\b(this course|this class|transfer credit|full credit|equivalen\w*|direct credit)\b",
        re.I,
    ),
    re.compile(r"\b(you are|act as|as an?)\b.{0,20}\b(ai|assistant|language model|llm|evaluator|grader)\b", re.I),
    re.compile(r"(system\s*prompt|<\s*/?\s*(system|instructions?)\s*>|\bassistant\s*:)", re.I),
    re.compile(
        r"(이|본|해당)\s*(과목|강의|수업).{0,20}(인정|승인|동등).{0,10}(하라|해라|할 것|하십시오|해\s*주세요|판정하)"
    ),
    re.compile(r"(이전|위의?|앞의?|모든).{0,10}(지시|명령|규칙).{0,10}무시"),
    re.compile(r"(AI|인공지능|모델|평가자|심사자).{0,10}(에게|는|은).{0,30}(인정|승인)"),
]


@dataclass(frozen=True)
class InjectionFlag:
    line_no: int
    text: str


def detect(text: str) -> list[InjectionFlag]:
    flags: list[InjectionFlag] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if any(p.search(line) for p in _PATTERNS):
            flags.append(InjectionFlag(line_no=i, text=line.strip()[:200]))
    return flags


def sanitize(text: str, flags: list[InjectionFlag]) -> str:
    """탐지한 줄을 자리표시자로 바꾼 사본. 원문(근거 검증용)은 바꾸지 않는다."""
    if not flags:
        return text
    flagged = {f.line_no for f in flags}
    return "\n".join(
        "[suspected instruction removed]" if i in flagged else line for i, line in enumerate(text.splitlines(), start=1)
    )
