"""중복 저장 값 정합성 점검 (ERD R2, open-issues H8).

실제 흐름(분석·판정·배분 원장·이의 신청·삭제 요청·보완 자료·메모)으로 만든 데이터는 어긋남이 없어야 하고,
점검마다 일부러 어긋나게 만든 행을 잡아내야 한다 (점검이 헛돌지 않음). 어긋나게 만든 변경은 커밋하지 않고 되돌린다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.models import CreditAllocation, User
from backend.repositories import integrity as integrity_repo
from backend.services import integrity
from scripts import integrity_check
from tests.conftest import login
from tests.integration.test_case_state import case_token
from tests.integration.test_review_extras import approve
from tests.integration.test_tenant_isolation import msu_case
from tests.integration.test_workflow import professor_for


@pytest.fixture
def workflow(client: TestClient, seeded: Session) -> dict[str, int]:
    ids = msu_case(client, seeded)  # 불인정 판정 · 이의 신청 · 삭제 요청
    ev, prof, _ = professor_for(client, seeded, "linear_algebra_detailed.txt")
    evaluator = login(client, "rachel@msu.example")  # 판정 전에 보완 자료 요청·메모
    page = client.get(f"/review/evaluations/{ev.id}").text
    r = client.post(
        f"/review/evaluations/{ev.id}/materials",
        data={"items": ["강의 노트"], "case_token": case_token(page), "csrf_token": evaluator},
    )
    assert "보완 자료를 요청했어요" in r.text
    client.post(f"/evaluations/{ev.id}/notes", data={"body": "메모", "csrf_token": evaluator})
    approve(client, ev, login(client, prof.email))  # 배분 원장 줄이 생긴다
    seeded.expire_all()
    assert seeded.scalars(select(CreditAllocation)).first() is not None
    other = seeded.scalars(select(User.id).where(User.email == "senior@student.example")).one()
    other_syllabus = seeded.execute(
        text("SELECT id FROM syllabi WHERE id <> :s ORDER BY id LIMIT 1"), {"s": ids["syllabus_id"]}
    ).scalar_one()
    return {**ids, "other_student": other, "other_syllabus": other_syllabus, "approved_eval": ev.id}


def test_workflow_data_is_consistent(
    workflow: dict[str, int], seeded: Session, capsys: pytest.CaptureFixture[str]
) -> None:
    for table in ("appeals", "privacy_requests", "material_requests", "evaluation_notes", "evidence_spans"):
        assert seeded.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() > 0, table  # 점검할 행이 있다
    assert integrity.run(seeded) == []
    assert integrity_check.main() == 0
    assert "어긋난 점검 0개" in capsys.readouterr().out


BREAKS = {
    "evaluation_request": "UPDATE course_evaluations SET transfer_request_id = NULL WHERE id = :evaluation_id",
    "appeal_student": "UPDATE appeals SET student_id = :other_student WHERE id = :appeal_id",
    "privacy_student": "UPDATE privacy_requests SET student_id = :other_student WHERE id = :privacy_id",
    "material_syllabus": "UPDATE material_requests SET syllabus_id = :other_syllabus",
    "note_syllabus": "UPDATE evaluation_notes SET syllabus_id = :other_syllabus",
    "span_source_syllabus": "UPDATE evidence_spans SET syllabus_id = :other_syllabus "
    "WHERE side = 'source' AND course_evaluation_id = :approved_eval",
    "span_range": "UPDATE evidence_spans SET char_end = char_end + 1000000 WHERE course_evaluation_id = :approved_eval",
    "allocation_student": "UPDATE credit_allocations SET student_id = :other_student",
}


def test_every_check_has_a_break_case() -> None:
    assert set(BREAKS) == {c.name for c in integrity_repo.CHECKS}


@pytest.mark.parametrize("name", sorted(BREAKS))
def test_check_catches_mismatch(name: str, workflow: dict[str, int], seeded: Session) -> None:
    sql = BREAKS[name]
    params = {k: v for k, v in workflow.items() if f":{k}" in sql}
    try:
        assert seeded.execute(text(sql), params).rowcount > 0  # type: ignore[attr-defined]
        found = {p.name: p for p in integrity.run(seeded)}
        assert name in found, found
        problem = found[name]  # id는 앞쪽 20개까지만 보여 준다
        assert problem.count >= len(problem.ids) > 0 and len(problem.ids) <= 20
    finally:
        seeded.rollback()
    assert integrity.run(seeded) == []
