"""학칙 정책 엔진 (리뷰 v3 P0-4). 규칙은 데이터(policy_rules)이고 이 모듈은 결정론적으로 평가만 한다.

- 승인된(approved) 규칙 중 그날 유효하고 학생의 범위(학과·입학연도)에 맞는 것만 본다. 초안·끝난 규칙은 쓰지 않는다.
- 범위가 더 구체적인 규칙이 이긴다 (학과·입학연도를 정한 수). 같은 구체성에서 값이 다르면 충돌(conflict)로 보류한다.
- 맞는 규칙이 없으면 기본값을 쓰지 않고 미정(unresolved)으로 돌려준다. 화면은 그 값을 계산하지 않고 안내한다.
- 판정에는 그때 적용한 규칙을 스냅샷으로 남긴다. 정책이 바뀌어도 지난 판정은 다시 계산하지 않는다.
정책 엔진은 학문적 동등성이나 예외 승인을 대신하지 않는다 (최종 판정은 교수).
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from backend.db.base import utcnow
from backend.i18n import N_
from backend.models import CourseEvaluation, PolicyRule, Syllabus, TransferRequest, User
from backend.models.enums import PolicyRuleType, PolicyStatus
from backend.repositories import evaluations as evaluation_repo
from backend.repositories import policies as policy_repo
from backend.repositories import requests as request_repo
from backend.repositories import users as user_repo

RESOLVED = "resolved"
UNRESOLVED = "unresolved"
CONFLICT = "conflict"

TYPE_LABELS = {
    PolicyRuleType.MIN_GRADE: N_("인정 최저 성적"),
    PolicyRuleType.TRANSFER_CAP: N_("편입 학점 상한"),
    PolicyRuleType.DEGREE_CREDITS: N_("졸업 학점"),
    PolicyRuleType.SEMESTER_LOAD: N_("학기당 이수 학점"),
}

# 성적 단계 (높을수록 좋음). 표에 없는 성적(W·I·NP 등)은 통과로 보지 않는다
GRADE_LEVELS = {
    "A+": 12, "A": 11, "A0": 11, "A-": 10,
    "B+": 9, "B": 8, "B0": 8, "B-": 7,
    "C+": 6, "C": 5, "C0": 5, "C-": 4,
    "D+": 3, "D": 2, "D0": 2, "D-": 1,
    "F": 0,
}  # fmt: skip
PASS_GRADES = frozenset({"P", "PASS", "S"})


@dataclass(frozen=True)
class Context:
    """규칙을 고를 학생의 범위."""

    institution_id: int
    department_id: int | None = None
    admission_year: int | None = None


@dataclass(frozen=True)
class Resolution:
    rule_type: str
    status: str
    rule: PolicyRule | None = None
    conflicting: tuple[int, ...] = ()

    @property
    def params(self) -> dict[str, Any]:
        return dict(self.rule.parameters) if self.rule is not None else {}

    @property
    def credits(self) -> int | None:
        value = self.params.get("credits")
        return int(value) if self.status == RESOLVED and isinstance(value, int | float) else None


def _matches(rule: PolicyRule, ctx: Context, on: date) -> bool:
    return (
        rule.status == PolicyStatus.APPROVED
        and rule.institution_id == ctx.institution_id
        and rule.effective_from <= on
        and (rule.effective_to is None or rule.effective_to >= on)
        and (rule.department_id is None or rule.department_id == ctx.department_id)
        and (rule.admission_year is None or rule.admission_year == ctx.admission_year)
    )


def specificity(rule: PolicyRule) -> int:
    return int(rule.department_id is not None) + int(rule.admission_year is not None)


def resolve(rules: Iterable[PolicyRule], rule_type: str, ctx: Context, on: date) -> Resolution:
    candidates = [r for r in rules if r.rule_type == rule_type and _matches(r, ctx, on)]
    if not candidates:
        return Resolution(rule_type, UNRESOLVED)
    best = max(specificity(r) for r in candidates)
    top = [r for r in candidates if specificity(r) == best]
    if len({_freeze(r.parameters) for r in top}) > 1:
        return Resolution(rule_type, CONFLICT, conflicting=tuple(sorted(r.id for r in top)))
    return Resolution(rule_type, RESOLVED, min(top, key=lambda r: r.id))


def _freeze(params: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((k, repr(v)) for k, v in params.items()))


def grade_passes(grade: str | None, resolution: Resolution) -> bool | None:
    """성적이 인정 최저 성적을 넘는지. 성적이 없으면 True(따지지 않음), 정책이 미정·충돌이면 None(판단 보류)."""
    if grade is None or not grade.strip():
        return True
    if resolution.status != RESOLVED:
        return None
    value = grade.strip().upper()
    if value in PASS_GRADES:
        return bool(resolution.params.get("accept_pass", False))
    minimum = GRADE_LEVELS.get(str(resolution.params.get("min_grade", "")).upper())
    level = GRADE_LEVELS.get(value)
    if minimum is None:
        return None
    return level is not None and level >= minimum


@dataclass
class StudentPolicy:
    """한 학생에게 적용되는 정책 묶음 (규칙을 한 번만 읽는다)."""

    ctx: Context
    resolutions: dict[str, Resolution] = field(default_factory=dict)

    def get(self, rule_type: str) -> Resolution:
        return self.resolutions[rule_type]

    def grade_failed(self, grade: str | None) -> bool:
        """성적 기준 미달이 확실할 때만 True (정책이 미정·충돌이면 빼지 않고 교수 심사로 넘긴다)."""
        return grade_passes(grade, self.get(PolicyRuleType.MIN_GRADE)) is False

    def snapshot(self) -> dict[str, Any]:
        """판정에 남길 정책 스냅샷: 규칙 종류 → 상태·규칙 id·값."""
        return {
            t: {
                "status": r.status,
                "rule_id": r.rule.id if r.rule else None,
                "params": r.params,
                "conflict": list(r.conflicting),
            }
            for t, r in self.resolutions.items()
        }


def for_context(rules: list[PolicyRule], ctx: Context, on: date | None = None) -> StudentPolicy:
    day = on or utcnow().date()
    return StudentPolicy(ctx, {t: resolve(rules, t, ctx, day) for t in PolicyRuleType})


def for_student(session: Session, student: User, institution_id: int | None = None) -> StudentPolicy:
    """학생의 편입 대학(없으면 institution_id) 정책. 학과는 학생 계정의 편입 전공, 입학연도는 계정 값."""
    target = institution_id or student.institution_id or 0
    rules = policy_repo.of_institution(session, target)
    return for_context(rules, Context(target, student.department_id, student.admission_year))


# ---------- 성적 기준 (여러 학생에 걸친 조회) ----------


def grade_failed_syllabus_ids(session: Session, syllabus_ids: list[int]) -> set[int]:
    """성적표 성적이 그 학생의 인정 최저 성적에 못 미치는 강의계획서 (정책이 미정·충돌이면 빼지 않음)."""
    cache: dict[tuple[int, int], StudentPolicy] = {}
    failed: set[int] = set()
    for syllabus_id, grade, student_id, institution_id in request_repo.grades_with_student(session, syllabus_ids):
        key = (student_id, institution_id)
        if key not in cache:
            student = user_repo.get_by_id(session, student_id)
            if student is None:
                continue
            cache[key] = for_student(session, student, institution_id)
        if cache[key].grade_failed(grade):
            failed.add(syllabus_id)
    return failed


def review_queue(
    session: Session, target_institution_id: int
) -> list[tuple[CourseEvaluation, Syllabus, TransferRequest]]:
    """심사 큐: 판정 전 최신 분석 결과 중 성적 기준 미달 과목을 뺀 것."""
    rows = evaluation_repo.unfiltered_review_queue(session, target_institution_id)
    failed = grade_failed_syllabus_ids(session, [s.id for _, s, _ in rows])
    return [(e, s, r) for e, s, r in rows if s.id not in failed]
