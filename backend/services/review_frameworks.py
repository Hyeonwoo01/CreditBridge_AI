"""학문 분야별 교수 심사 체크리스트 (리뷰 v3 P1-1, 13.8).

교수 판단을 대신하는 점수가 아니라 검토 누락을 줄이는 확인 항목이다. 대상 과목(없으면 AI 후보 과목) 학과 이름으로
분야를 고르고, 교수가 확인한 항목과 '자료 없음' 항목을 판정 기록(decisions.review_checklist)에 남긴다.
항목 문구는 N_ 한국어 원문이고 화면에서 번역한다. 항목을 바꾸면 VERSION을 올린다 (지난 판정 기록과 구분).
"""

from dataclasses import dataclass
from typing import Any

from backend.i18n import N_

VERSION = "frameworks-v1"
COMMON = "common"


@dataclass(frozen=True)
class Framework:
    key: str
    label: str
    items: tuple[tuple[str, str], ...]  # (항목 키, 한국어 원문)


_COMMON_ITEMS = (
    ("outcomes", N_("양쪽 학습 목표를 나란히 비교했다")),
    ("weeks", N_("주차별 내용과 이론·실습 비중을 비교했다")),
    ("credit_hours", N_("학점·수업 시간·학기 길이와 학점 단위를 확인했다")),
    ("evidence", N_("근거 원문(쪽·주차)을 직접 열어 확인했다")),
    ("ai_inferred", N_("자료가 없는 항목과 AI가 추론한 항목을 구분했다")),
)

FRAMEWORKS: dict[str, Framework] = {
    f.key: f
    for f in (
        Framework(COMMON, N_("공통"), _COMMON_ITEMS),
        Framework(
            "math",
            N_("수학·통계"),
            (
                *_COMMON_ITEMS,
                ("proofs", N_("정리·증명을 다루는 범위와 깊이를 확인했다")),
                ("problem_types", N_("문제 유형과 수학적 난도를 확인했다 (과제·시험 범위)")),
                ("prerequisites", N_("선수지식(예: 미적분·선형대수)이 같은지 확인했다")),
            ),
        ),
        Framework(
            "computing",
            N_("컴퓨터공학"),
            (
                *_COMMON_ITEMS,
                ("algorithms", N_("알고리즘·자료구조 범위를 확인했다")),
                ("tools", N_("사용 언어·도구와 실습 시간을 확인했다")),
                ("projects", N_("과제·프로젝트 난도를 확인했다 (과제 명세)")),
            ),
        ),
        Framework(
            "lab_science",
            N_("실험 과학 (화학·생명과학)"),
            (
                *_COMMON_ITEMS,
                ("lab_hours", N_("실험실 시간을 확인했다 (이론만 비교하지 않음)")),
                ("lab_skills", N_("실험 기법·설계·데이터 해석 역량을 확인했다 (실험 목록·보고서)")),
                ("safety", N_("실험 안전 교육·요건을 확인했다")),
            ),
        ),
        Framework(
            "physics",
            N_("물리"),
            (
                *_COMMON_ITEMS,
                ("math_tools", N_("쓰는 수학적 도구(미적분 기반 여부)를 확인했다")),
                ("lab_or_computation", N_("실험·계산 실습 여부와 시간을 확인했다")),
                ("problem_sets", N_("문제 세트 수준과 선수과목을 확인했다")),
            ),
        ),
        Framework(
            "business",
            N_("경영·경제"),
            (
                *_COMMON_ITEMS,
                ("quant", N_("이론·정량 분석 비중을 확인했다")),
                ("cases", N_("사례 적용·프로젝트를 확인했다")),
                ("data_models", N_("모델·데이터 활용 과제를 확인했다")),
            ),
        ),
        Framework(
            "health",
            N_("간호·보건"),
            (
                *_COMMON_ITEMS,
                ("clinical_hours", N_("임상·실습 시간을 확인했다 (실습 기록)")),
                ("competency", N_("역량·안전 요건을 확인했다 (역량 체크리스트)")),
            ),
        ),
        Framework(
            "humanities",
            N_("인문·사회"),
            (
                *_COMMON_ITEMS,
                ("methods", N_("방법론과 텍스트·자료 분석 방식을 확인했다")),
                ("readings", N_("읽기 목록 분량·수준을 확인했다")),
                ("writing", N_("글쓰기·연구 과제를 확인했다 (에세이·보고서)")),
            ),
        ),
    )
}

# AI가 학생 강의계획서에서 찾아 미리 표시할 수 있는 항목과 찾을 내용 (영어, 프롬프트용). 'evidence'·'ai_inferred'처럼
# 교수가 직접 하는 확인은 빼고, 문서에 적혀 있는지로 답할 수 있는 항목만 둔다. 바꾸면 평가 프롬프트 버전도 올린다
LOOK_FOR: dict[str, str] = {
    "outcomes": "stated learning outcomes or course objectives",
    "weeks": "a weekly schedule of topics, or the split between lectures and labs/practice",
    "credit_hours": "credits, contact hours per week, or the length of the term",
    "proofs": "proofs or theorems taught (for example 'prove', 'theorem', 'derivation')",
    "problem_types": "types of problems, homework, quizzes or exams and what they cover",
    "prerequisites": "stated prerequisite courses or prior knowledge",
    "algorithms": "specific algorithms or data structures taught",
    "tools": "programming languages, software tools, or lab/practice hours",
    "projects": "programming assignments or projects and their scope",
    "lab_hours": "laboratory sessions or lab hours",
    "lab_skills": "lab techniques, experiment design, lab reports or data analysis",
    "safety": "lab safety training or safety requirements",
    "math_tools": "the mathematics used (for example calculus-based or algebra-based)",
    "lab_or_computation": "lab work or computational exercises and their hours",
    "problem_sets": "problem sets and their level, or prerequisite courses",
    "quant": "quantitative or theoretical analysis (models, statistics, calculations)",
    "cases": "case studies or applied projects",
    "data_models": "assignments that use data, spreadsheets or models",
    "clinical_hours": "clinical or practicum hours",
    "competency": "competency or safety requirements students must meet",
    "methods": "research methods or how texts and sources are analyzed",
    "readings": "a reading list or the amount of required reading",
    "writing": "essays, papers or research writing assignments",
}


def findable(framework: Framework) -> list[tuple[str, str]]:
    """분야 항목 중 AI가 문서에서 찾아볼 수 있는 것 (항목 키, 찾을 내용)."""
    return [(k, LOOK_FOR[k]) for k, _ in framework.items if k in LOOK_FOR]


# 학과 이름 키워드 → 분야 (영어 학과명 기준, 소문자 비교). 앞에서부터 처음 맞는 것
_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("math", ("math", "statistic", "수학", "통계")),
    ("computing", ("computer", "computing", "software", "information", "컴퓨터", "소프트웨어")),
    ("lab_science", ("chemistry", "biology", "biochem", "life science", "화학", "생명", "생물")),
    ("physics", ("physics", "물리")),
    ("business", ("business", "econom", "management", "finance", "accounting", "operations", "경영", "경제")),
    ("health", ("nursing", "health", "medic", "간호", "보건")),
    (
        "humanities",
        ("english", "history", "philosoph", "sociolog", "psycholog", "literature", "society", "역사", "문학"),
    ),
)


def for_department(department: str | None) -> Framework:
    name = (department or "").lower()
    for key, words in _KEYWORDS:
        if any(w in name for w in words):
            return FRAMEWORKS[key]
    return FRAMEWORKS[COMMON]


def label(framework_key: str, item_key: str) -> str:
    """기록된 항목 키의 한국어 원문 (화면에서 번역). 모르는 키는 그대로."""
    framework = FRAMEWORKS.get(framework_key, FRAMEWORKS[COMMON])
    return dict(framework.items).get(item_key, item_key)


def record(framework: Framework, checked: list[str], missing: list[str]) -> dict[str, Any]:
    """판정에 남길 체크리스트 기록. 목록에 없는 키는 버린다. 한 항목이 둘 다면 '자료 없음'으로 본다."""
    keys = [k for k, _ in framework.items]
    missing_set = {k for k in missing if k in keys}
    return {
        "version": VERSION,
        "framework": framework.key,
        "checked": [k for k in keys if k in set(checked) and k not in missing_set],
        "missing_evidence": [k for k in keys if k in missing_set],
    }
