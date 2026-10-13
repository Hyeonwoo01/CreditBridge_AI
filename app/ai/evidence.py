"""근거 구절 원문 검증. 원문에 실제로 있는 문자열만 근거로 저장한다 (FR-06, 근거 환각 0건)."""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_EQUIV = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "})


@dataclass(frozen=True)
class Span:
    start: int
    end: int


def _normalize_with_map(text: str) -> tuple[str, list[int]]:
    """공백 연속을 한 칸으로 줄이고 따옴표·대시 표기를 통일한다. 정규화 위치 → 원문 위치 표를 함께 만든다."""
    chars: list[str] = []
    index: list[int] = []
    prev_space = False
    for i, ch in enumerate(text.translate(_EQUIV)):
        if ch.isspace():
            if prev_space or not chars:
                continue
            chars.append(" ")
            index.append(i)
            prev_space = True
        else:
            chars.append(ch)
            index.append(i)
            prev_space = False
    return "".join(chars), index


def locate(text: str, quote: str) -> Span | None:
    """quote가 text에 (공백·따옴표 표기 차이만 허용하고) 그대로 있으면 원문 위치를 돌려준다."""
    needle, _ = _normalize_with_map(quote.strip())
    if len(needle) < 4:
        return None
    haystack, index = _normalize_with_map(text)
    pos = haystack.find(needle)
    if pos < 0:
        return None
    return Span(start=index[pos], end=index[pos + len(needle) - 1] + 1)


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
