"""후보 과목 선정 (FR-05). MVP는 임베딩 없이 학과로 후보를 거른 뒤 Claude가 직접 비교한다."""

import re
from typing import Protocol

# 한 번에 Claude에게 넘기는 후보 과목 수 상한 (기능명세서: 20~30개)
MAX_CANDIDATES = 30
_STOP = {"and", "of", "the", "for", "in", "studies", "department"}
_SYNONYMS = {
    "math": "mathematics",
    "maths": "mathematics",
    "cs": "computer science",
    "computing": "computer science",
    "informatics": "computer science",
    "software": "computer science",
    "physical": "physics",
    "writing": "english",
    "composition": "english",
}
# 추출 프롬프트는 분야를 영어로 쓰게 하지만, 한국어로 돌아와도 후보를 찾도록 흔한 학과명을 옮긴다
_KOREAN = {
    "수학": "mathematics",
    "응용수학": "mathematics",
    "통계": "statistics",
    "컴퓨터": "computer science",
    "컴퓨터공학": "computer science",
    "컴퓨터과학": "computer science",
    "전산": "computer science",
    "소프트웨어": "computer science",
    "물리": "physics",
    "화학": "chemistry",
    "생물": "biology",
    "생명과학": "biology",
    "역사": "history",
    "사학": "history",
    "한국사": "korean history",
    "영어": "english",
    "영문": "english",
    "글쓰기": "english",
    "경영": "business",
    "경제": "economics",
}


class CourseLike(Protocol):
    code: str

    @property
    def department_name(self) -> str: ...


def _korean(word: str) -> str:
    """'물리학과'·'수학과'처럼 학과 접미사가 붙어도 같은 분야로 옮긴다. 모르는 낱말은 그대로 둔다."""
    for stem in (word, word.removesuffix("학과"), word.removesuffix("과"), word.removesuffix("학")):
        if stem in _KOREAN:
            return _KOREAN[stem]
    return word


def _tokens(name: str) -> set[str]:
    text = name.lower()
    words = [_korean(w) if not w.isascii() else w for w in re.findall(r"[a-z]+|[가-힣]+", text)]
    expanded = " ".join(_SYNONYMS.get(w, w) for w in " ".join(words).split())
    return {w for w in expanded.split() if w not in _STOP}


def matches(discipline: str, department: str) -> bool:
    """분야명과 학과명이 같은 학문을 가리키는지: 한쪽 단어가 다른 쪽에 모두 포함되면 같다고 본다."""
    a, b = _tokens(discipline), _tokens(department)
    return bool(a and b) and (a <= b or b <= a)


def select[C: CourseLike](courses: list[C], disciplines: list[str], limit: int = MAX_CANDIDATES) -> list[C]:
    """강의계획서의 학문 분야와 맞는 학과의 과목만 고른다. 앞에 적힌 분야의 학과를 먼저 담는다."""
    picked: list[C] = []
    for discipline in disciplines:
        for course in courses:
            if course not in picked and matches(discipline, course.department_name):
                picked.append(course)
    return picked[:limit]
