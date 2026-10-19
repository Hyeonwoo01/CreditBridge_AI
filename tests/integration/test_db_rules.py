"""DB가 직접 지키는 규칙 (docs/ERD.md 6절): 값 허용 목록·범위 CHECK, "하나만" 유니크(부분 유니크 인덱스)."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from backend.db.base import utcnow
from backend.errors import DuplicateRowError
from backend.models import Appeal, Assignment, CourseEvaluation, Decision, PrivacyRequest, TransferRequest, User
from backend.repositories import appeals as appeal_repo
from backend.repositories import privacy as privacy_repo
from tests.integration.test_review_extras import approve
from tests.integration.test_workflow import professor_for


def rejected(db: Session, sql: str, **params: object) -> bool:
    try:
        db.execute(text(sql), params)
        db.flush()
    except DBAPIError:
        db.rollback()
        return True
    db.rollback()
    return False


def test_check_constraints_reject_unknown_codes_and_out_of_range_values(seeded: Session) -> None:
    user = seeded.scalars(select(User).where(User.email == "jiwon@student.example")).one()
    assert rejected(seeded, "UPDATE users SET role = 'root' WHERE id = :id", id=user.id)
    assert rejected(seeded, "UPDATE users SET locale = 'fr' WHERE id = :id", id=user.id)
    for table, change in [
        ("courses", "credits = -1"),
        ("course_evaluations", "coverage = 1.5"),
        ("course_evaluations", "recommendation = 'maybe'"),
        ("decisions", "result = 'partial'"),
    ]:
        assert rejected(seeded, f"UPDATE {table} SET {change} WHERE id = (SELECT min(id) FROM {table})")
    # 허용 값은 그대로 들어간다
    assert not rejected(seeded, "UPDATE users SET locale = 'en' WHERE id = :id", id=user.id)


def test_only_one_active_assignment_and_latest_evaluation(client: TestClient, seeded: Session) -> None:
    ev, prof, _ = professor_for(client, seeded, "linear_algebra_detailed.txt")
    seeded.expire_all()

    seeded.add(Assignment(course_evaluation_id=ev.id, reviewer_id=prof.id))
    with pytest.raises(DBAPIError):
        seeded.flush()
    seeded.rollback()

    seeded.add(CourseEvaluation(transfer_request_id=ev.transfer_request_id, syllabus_id=ev.syllabus_id, is_latest=True))
    with pytest.raises(DBAPIError):
        seeded.flush()
    seeded.rollback()

    # 비활성 배정·이전 분석은 여러 개여도 된다
    seeded.add_all(
        [
            Assignment(course_evaluation_id=ev.id, reviewer_id=prof.id, is_active=False),
            Assignment(course_evaluation_id=ev.id, reviewer_id=prof.id, is_active=False),
            CourseEvaluation(transfer_request_id=ev.transfer_request_id, syllabus_id=ev.syllabus_id, is_latest=False),
        ]
    )
    seeded.flush()
    seeded.rollback()


def test_only_one_open_appeal_and_privacy_request(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    approve(client, ev, token)
    seeded.expire_all()
    decision = seeded.scalars(select(Decision).where(Decision.course_evaluation_id == ev.id)).one()
    request = seeded.get(TransferRequest, ev.transfer_request_id)
    assert request is not None

    def appeal() -> Appeal:
        return Appeal(course_evaluation_id=ev.id, decision_id=decision.id, student_id=request.student_id, reason="r")

    first = appeal_repo.add(seeded, appeal())
    # 앱 검사를 지나 동시에 들어온 두 번째 요청은 DB가 막고, 세션은 계속 쓸 수 있다
    with pytest.raises(DuplicateRowError):
        appeal_repo.add(seeded, appeal())
    first.status = "dismissed"
    seeded.flush()
    appeal_repo.add(seeded, appeal())  # 처리가 끝난 뒤에는 다시 신청할 수 있다

    def privacy() -> PrivacyRequest:
        now = utcnow()
        return PrivacyRequest(
            transfer_request_id=request.id, student_id=request.student_id, due_at=now + timedelta(days=30)
        )

    done = privacy_repo.add(seeded, privacy())
    with pytest.raises(DuplicateRowError):
        privacy_repo.add(seeded, privacy())
    done.status = "completed"
    seeded.flush()
    privacy_repo.add(seeded, privacy())
    seeded.rollback()
