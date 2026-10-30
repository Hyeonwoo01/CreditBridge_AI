"""근거 구절 원문 검증. 원문에 실제로 있는 문자열만 근거로 저장한다 (FR-06, 근거 환각 0건).
학생 쪽 구절은 한 번 더 거른다: 원문에 있어도 선수과목·교재 칸이나 "다루지 않음" 같은 문장이면
가르쳤다는 근거가 아니다 (teaching_evidence).

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


@dataclass
class QuoteCounts:
    """한 번의 AI 비교에서 받은 인용 구절 수와 버린 수 (프롬프트 버전별 환각 지표, course_evaluations에 저장)."""

    total: int = 0
    unmatched: int = 0  # 원문에 없어서 버림 (지어낸 인용)
    non_teaching: int = 0  # 원문에는 있지만 선수과목·교재 칸이나 부정 문장이라 버림


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


def verify_quotes(text: str, quotes: list[str], *, context: str, counts: QuoteCounts | None = None) -> list[Span]:
    """검증된 구절만 반환하고, 폐기한 구절 수는 로그로 남긴다 (구절 내용은 남기지 않는다)."""
    spans: list[Span] = []
    rejected = 0
    for quote in quotes:
        span = locate(text, quote)
        if span is None:
            rejected += 1
        elif span not in spans:
            spans.append(span)
    if counts is not None:
        counts.total += len(quotes)
        counts.unmatched += rejected
    if rejected:
        logger.info("discarded unverified evidence quotes", extra={"context": context, "rejected": rejected})
    return spans


# 원문에 있어도 '이 과목에서 가르쳤다'는 근거가 되지 않는 칸의 제목 (선수과목·교재·참고문헌)
_NON_TEACHING_HEADING = re.compile(
    r"^[ \t>*#\-•·\d.)]*(?:"
    r"pre-?requisites?|co-?requisites?|required\s+(?:texts?|textbooks?|readings?|materials?)|textbooks?|"
    r"recommended\s+(?:texts?|readings?)|course\s+materials?|references?|bibliography|"
    r"선수\s*과목|선이수\s*과목|선수\s*학습|권장\s*선수|교재|주\s*교재|부\s*교재|참고\s*(?:문헌|도서|자료|교재)"
    r")(?![a-z])",
    re.IGNORECASE | re.MULTILINE,
)
# 칸이 끝나는 곳: 빈 줄, 또는 수업 내용 칸의 제목이 나오는 줄
_TEACHING_HEADING = re.compile(
    r"^[ \t>*#\-•·]*(?:week|wk\.?|session|lecture|module|unit|topic|schedule|course\s+(?:description|outline|"
    r"objectives?|content)|learning\s+(?:outcomes?|objectives?)|grading|assessment|evaluation|"
    r"\d+\s*주\s*차|제?\s*\d+\s*주|주차|강의\s*(?:개요|목표|계획|내용)|학습\s*목표|수업\s*(?:목표|계획|내용)|평가)",
    re.IGNORECASE | re.MULTILINE,
)
_BLANK_LINE = re.compile(r"\n[ \t]*\n")
MAX_SECTION_CHARS = 600
# 구절 안에 있으면 '가르치지 않음'·'다른 과목에서'·'이미 알아야 함'을 뜻하는 표현
_NEGATION = re.compile(
    r"\bnot\s+(?:be\s+)?(?:covered|taught|included|discussed|addressed|part\s+of)\b|\bwill\s+not\b|\bwon'?t\b|"
    r"\bexclud(?:e|es|ed|ing)\b|\b(?:outside|beyond|out\s+of)\s+(?:the\s+)?scope\b|"
    r"\b(?:next|following|later|subsequent|follow-?up)\s+(?:course|semester|term|class)\b|"
    r"\b(?:assumed|prior|assumes)\s+knowledge\b|\bshould\s+(?:already\s+)?(?:know|be\s+familiar)\b|"
    r"다루지\s*않|가르치지\s*않|포함(?:하지|되지)\s*않|제외|다음\s*학기|후속\s*(?:과목|강의|수업)|범위\s*(?:밖|외)|"
    r"사전\s*지식|선수\s*지식|이미\s*(?:알고|배운|이수)",
    re.IGNORECASE,
)


def non_teaching_regions(text: str, items: list[str]) -> list[Span]:
    """선수과목·교재·참고문헌 칸의 원문 위치. 제목 줄부터 빈 줄이나 수업 내용 칸 제목까지(최대 600자)이고,
    구조화 추출이 선수과목·교재로 뽑은 항목(items)이 원문에 있으면 그 위치도 더한다."""
    regions: list[Span] = []
    for heading in _NON_TEACHING_HEADING.finditer(text):
        start = heading.start()
        end = min(len(text), start + MAX_SECTION_CHARS)
        blank = _BLANK_LINE.search(text, heading.end(), end)
        if blank:
            end = blank.start()
        line_end = text.find("\n", heading.end(), end)
        if line_end >= 0:
            nxt = _TEACHING_HEADING.search(text, line_end + 1, end)
            if nxt:
                end = nxt.start()
        regions.append(Span(start, end))
    for item in items:
        span = locate(text, item)
        if span is not None:
            regions.append(span)
    return regions


def teaching_evidence(
    text: str, spans: list[Span], excluded: list[Span], *, context: str, counts: QuoteCounts | None = None
) -> list[Span]:
    """원문 검증을 통과한 학생 쪽 구절 중 '이 과목에서 가르쳤다'는 근거가 되는 것만 남긴다.
    선수과목·교재 칸 안에만 있는 구절, 부정·다른 과목 표현이 든 구절은 버린다 (단어 하나로 버려질 수 있지만,
    가르치지 않은 개념을 인정하는 쪽보다 '근거 부족'으로 교수에게 넘기는 쪽이 안전하다)."""
    kept: list[Span] = []
    rejected = 0
    for span in spans:
        inside = any(r.start <= span.start and span.end <= r.end for r in excluded)
        if inside or _NEGATION.search(text[span.start : span.end]):
            rejected += 1
        else:
            kept.append(span)
    if counts is not None:
        counts.non_teaching += rejected
    if rejected:
        logger.info("discarded non-teaching evidence quotes", extra={"context": context, "rejected": rejected})
    return kept


# 주차 표시: "Week 3", "Weeks 3-4", "Wk 3", "3주차", "3~4주차", "제3주"
_WEEK_MARK = re.compile(
    r"\b(?:weeks?|wk\.?)\s*(\d{1,2})(?:\s*(?:-|–|~|to|and|&)\s*(\d{1,2}))?(?!\d)"
    r"|(?:제\s*)?(\d{1,2})(?:\s*[-~–]\s*(\d{1,2}))?\s*주\s*차|제\s*(\d{1,2})\s*주",
    re.IGNORECASE,
)
# 한 주차 칸은 다음 주차 표시까지, 최대 이 글자 수 (주차 계획 뒤의 평가 방법 등을 마지막 주로 세지 않게)
MAX_WEEK_BLOCK = 400
MAX_WEEK_RANGE = 6


def _week_blocks(text: str) -> list[tuple[int, int, frozenset[int]]]:
    marks: list[tuple[int, frozenset[int]]] = []
    for m in _WEEK_MARK.finditer(text):
        first = m.group(1) or m.group(3) or m.group(5)
        last = m.group(2) or m.group(4) or first
        a, b = int(first), int(last)
        if a < 1 or b < a or b - a >= MAX_WEEK_RANGE:
            continue
        marks.append((m.start(), frozenset(range(a, b + 1))))
    blocks = []
    for i, (start, weeks) in enumerate(marks):
        nxt = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        blocks.append((start, min(nxt, start + MAX_WEEK_BLOCK), weeks))
    return blocks


def weeks_of(text: str, spans: list[Span]) -> int:
    """근거 구절들이 걸친 주차 수. 주차 표시가 없는 문서이거나 구절이 주차 계획 밖(학습 목표 등)에만 있으면 0."""
    blocks = _week_blocks(text)
    weeks: set[int] = set()
    for span in spans:
        for start, end, block_weeks in blocks:
            if start < span.end and span.start < end:
                weeks |= block_weeks
    return len(weeks)
