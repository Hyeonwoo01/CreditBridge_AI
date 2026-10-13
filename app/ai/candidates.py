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


class CourseLike(Protocol):
    department: str
    code: str


def _tokens(name: str) -> set[str]:
    text = name.lower()
    words = re.findall(r"[a-z]+", text)
    expanded = " ".join(_SYNONYMS.get(w, w) for w in words)
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
            if course not in picked and matches(discipline, course.department):
                picked.append(course)
    return picked[:limit]
