"""근거 구절 원문 검증. 원문에 실제로 있는 문자열만 근거로 저장한다 (FR-06, 근거 환각 0건).

LLM이 인용할 때 흔히 생기는 표기 차이만 허용한다: 공백·줄바꿈, 대소문자, 따옴표·대시 모양, 문장부호,
그리고 중간을 "..."로 줄인 인용. 단어가 하나라도 다르면(바꿔 말하기, 조사 변경, 지어낸 문장) 버린다.
저장하는 위치는 언제나 원문 기준이라 화면에 보이는 근거는 원문 문자열 그대로다.
편집 거리 기반 유사 일치는 쓰지 않는다: "covered"와 "not covered"처럼 뜻이 반대인 인용을 받아들일 수 있다.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_EQUIV = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "})
# 문장부호지만 뜻이 있는 기호는 그대로 비교한다 (40%, C#, R&D, @)
_KEEP = set("%#&@")
_ELLIPSIS = re.compile(r"\s*(?:\.{3,}|…)\s*")
MIN_CHARS = 4
# 생략 인용("A ... B")의 조각마다 이 글자 수 이상이어야 한다. "이수 ... 인정"처럼 짧은 조각은
# 원문 아무 데서나 맞아 여러 주차를 하나의 근거로 묶어 버린다
MIN_ELLIPSIS_PART = 8
# 앞뒤 조각 사이 거리(비교용 글자 수)와 근거 구간 전체 길이(원문 글자 수) 상한
MAX_ELLIPSIS_GAP = 200
MAX_ELLIPSIS_SPAN = 400


@dataclass(frozen=True)
class Span:
    start: int
    end: int


def _fold(ch: str) -> str:
    """비교용 한 글자: 문장부호는 공백, 영문은 소문자 (원문 위치 표를 유지하려고 한 글자는 한 글자로)."""
    if ch.isspace() or (unicodedata.category(ch).startswith("P") and ch not in _KEEP and ch != "'"):
        return " "
    lowered = ch.lower()
    return lowered if len(lowered) == 1 else ch


def _normalize_with_map(text: str) -> tuple[str, list[int]]:
    """비교용 문자열과 (비교용 위치 → 원문 위치) 표. 공백 연속은 한 칸으로 줄인다."""
    chars: list[str] = []
    index: list[int] = []
    for i, raw in enumerate(text.translate(_EQUIV)):
        ch = _fold(raw)
        if ch == " " and (not chars or chars[-1] == " "):
            continue
        chars.append(ch)
        index.append(i)
    while chars and chars[-1] == " ":
        chars.pop()
        index.pop()
    return "".join(chars), index


def _word_char(ch: str) -> bool:
    # 영문·숫자만 단어 경계를 본다. 한국어는 조사가 붙어 쓰이므로("미분과") 경계를 따지지 않는다
    return ch.isascii() and ch.isalnum()


def _find(haystack: str, needle: str, start: int = 0) -> int:
    """영문 단어 중간에서 시작하거나 끝나는 일치는 받지 않는다 ("rule"이 "rules"의 앞부분과 맞는 경우)."""
    pos = haystack.find(needle, start)
    while pos >= 0:
        before = haystack[pos - 1] if pos > 0 else " "
        end = pos + len(needle)
        after = haystack[end] if end < len(haystack) else " "
        if not (_word_char(before) and _word_char(needle[0])) and not (_word_char(after) and _word_char(needle[-1])):
            return pos
        pos = haystack.find(needle, pos + 1)
    return -1


def locate(text: str, quote: str) -> Span | None:
    """quote가 text에 (표기 차이만 허용하고) 그대로 있으면 원문 위치를 돌려준다."""
    parts = [p for p in _ELLIPSIS.split(quote.strip()) if p.strip()]
    needles = [_normalize_with_map(p)[0] for p in parts]
    needles = [n for n in needles if n]
    if not needles or len("".join(needles)) < MIN_CHARS:
        return None
    if len(needles) > 1 and any(len(n) < MIN_ELLIPSIS_PART for n in needles):
        return None
    haystack, index = _normalize_with_map(text)
    first = _find(haystack, needles[0])
    while first >= 0:
        end = first + len(needles[0])
        for needle in needles[1:]:
            nxt = _find(haystack, needle, end)
            if nxt < 0 or nxt - end > MAX_ELLIPSIS_GAP:
                break
            end = nxt + len(needle)
        else:
            span = Span(start=index[first], end=index[end - 1] + 1)
            if len(needles) == 1 or span.end - span.start <= MAX_ELLIPSIS_SPAN:
                return span
        first = _find(haystack, needles[0], first + 1)
    return None


def verify_quotes(text: str, quotes: list[str], *, context: str) -> list[Span]:
    """검증된 구절만 반환하고, 폐기한 구절 수는 로그로 남긴다 (구절 내용은 남기지 않는다)."""
    spans: list[Span] = []
    rejected = 0
    for quote in quotes:
        span = locate(text, quote)
        if span is None:
            rejected += 1
        elif span not in spans:
            spans.append(span)
    if rejected:
        logger.info("discarded unverified evidence quotes", extra={"context": context, "rejected": rejected})
    return spans
