"""졸업 요건 배정 규칙 (리뷰 v3 P1-6)."""

from types import SimpleNamespace
from typing import Any

from backend.services import degree_audit as da


def req(area: str, credits: float, codes: list[str]) -> Any:
    return SimpleNamespace(area=area, required_credits=credits, course_codes=codes, name=area)


def rows() -> list[da.RequirementProgress]:
    return [
        da.RequirementProgress(req("major_required", 4, ["MATH 1151"])),
        da.RequirementProgress(req("free_elective", 6, [])),
    ]


def test_listed_course_goes_to_its_requirement_and_overflow_to_free() -> None:
    r = rows()
    assert da._place(r, "MATH 1151", 3, "confirmed") == 0
    assert da._place(r, "MATH 1151", 3, "confirmed") == 0  # 4학점 요건: 1학점만 더 들어가고 2학점은 일반 선택
    assert (r[0].confirmed, r[1].confirmed) == (4, 2)
    assert r[0].status == da.SATISFIED and r[1].status == da.IN_PROGRESS


def test_unlisted_and_elective_credit_go_to_free_elective_once() -> None:
    r = rows()
    da._place(r, None, 3, "confirmed")
    da._place(r, "CSE 9999", 2, "confirmed")
    assert (r[0].confirmed, r[1].confirmed) == (0, 5)  # 같은 학점을 두 요건에 세지 않는다
    assert r[0].status == da.UNMET


def test_pending_estimates_are_separate() -> None:
    r = rows()
    da._place(r, "MATH 1151", 3, "pending")
    assert r[0].confirmed == 0 and r[0].pending == 3 and r[0].status == da.PENDING_REVIEW and r[0].remaining == 4


def test_no_free_elective_leaves_unassigned() -> None:
    r = [da.RequirementProgress(req("major_required", 3, ["MATH 1151"]))]
    assert da._place(r, "MATH 1151", 5, "confirmed") == 2
