"""기한 알림 (매일 Celery beat): 교수·심사관·관리자·학생에게 기한이 지났거나 다가온 일을 하루 한 번 알린다."""

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.db.base import utcnow
from backend.models import Assignment, MaterialRequest, Notification, PrivacyRequest, User
from backend.services import reminders
from tests.conftest import login
from tests.integration.test_pipeline import latest
from tests.integration.test_workflow import professor_for, submitted_request


def notes(db: Session, email: str, kind: str) -> list[Notification]:
    db.expire_all()
    user = db.scalars(select(User).where(User.email == email)).one()
    return list(db.scalars(select(Notification).where(Notification.user_id == user.id, Notification.kind == kind)))


def test_overdue_review_reminds_professor_and_evaluators_once_a_day(client: TestClient, seeded: Session) -> None:
    ev, prof, _ = professor_for(client, seeded, "calculus.txt")
    seeded.execute(
        update(Assignment)
        .where(Assignment.course_evaluation_id == ev.id)
        .values(assigned_at=utcnow() - timedelta(days=6))  # 판정 기한 5일 초과
    )
    seeded.commit()

    assert reminders.send_daily(seeded) >= 2
    mine = notes(seeded, prof.email, "reminder.review")
    assert len(mine) == 1 and "판정 기한이 지난 심사 1건" in mine[0].message and mine[0].link == "/professor"
    staff = notes(seeded, "rachel@msu.example", "reminder.evaluator")
    assert len(staff) == 1 and "판정 기한이 지난 심사 1건" in staff[0].message

    reminders.send_daily(seeded)  # 같은 날 다시 돌아도 쌓이지 않는다
    assert len(notes(seeded, prof.email, "reminder.review")) == 1
    reminders.send_daily(seeded, now=utcnow() + timedelta(hours=21))  # 다음 날에는 다시
    assert len(notes(seeded, prof.email, "reminder.review")) == 2

    login(client, "admin@msu.example")
    page = client.get("/admin/stats").text  # 관리자 콘솔의 오늘 기한 알림 대상 카드
    assert "기한 알림" in page and "자동 발송" in page and "판정 기한 지난 심사" in page
    login(client, prof.email)
    assert "기한 알림: 판정 기한이 지난 심사 1건" in client.get("/notifications").text


def test_due_soon_unassigned_materials_and_privacy(client: TestClient, seeded: Session) -> None:
    ev, prof, token = professor_for(client, seeded, "linear_algebra_sparse.txt")
    seeded.execute(
        update(Assignment)
        .where(Assignment.course_evaluation_id == ev.id)
        .values(assigned_at=utcnow() - timedelta(days=4, hours=12))  # 하루 안에 기한
    )
    # 교수가 보완 자료를 요청했는데 학생이 나흘째 답이 없다
    client.post(
        f"/professor/evaluations/{ev.id}/materials",
        data={"items": ["주차별 상세 강의 계획"], "note": "", "csrf_token": token},
    )
    seeded.execute(update(MaterialRequest).values(created_at=utcnow() - timedelta(days=4)))
    # 교수 배정 없이 사흘째 기다리는 과목
    rid = submitted_request(client, seeded, "general_chemistry.txt")
    waiting = latest(seeded, "general_chemistry.txt", rid)
    seeded.execute(update(Assignment).where(Assignment.course_evaluation_id == waiting.id).values(is_active=False))
    from backend.models import TransferRequest

    seeded.execute(
        update(TransferRequest).where(TransferRequest.id == rid).values(submitted_at=utcnow() - timedelta(days=3))
    )
    # 처리 기한이 이틀 남은 삭제 요청
    token = login(client, "jiwon@student.example")
    client.post(f"/student/requests/{ev.transfer_request_id}/delete-documents", data={"csrf_token": token})
    seeded.execute(update(PrivacyRequest).values(due_at=utcnow() + timedelta(days=2)))
    seeded.commit()

    reminders.send_daily(seeded)
    assert "내일까지 판정할 심사 1건" in notes(seeded, prof.email, "reminder.review")[0].message
    staff = notes(seeded, "rachel@msu.example", "reminder.evaluator")[0].message
    assert "교수 배정을 기다리는 과목 1개" in staff and "처리 기한이 다가온 삭제 요청 1건" in staff
    student = notes(seeded, "jiwon@student.example", "reminder.material")
    assert len(student) == 1 and "MATH 201" in student[0].message and student[0].link.startswith("/student/syllabi/")
    assert "jiwon" not in student[0].message.lower() and "이지원" not in student[0].message  # 개인정보 없음
    assert not notes(seeded, "admin@msu.example", "reminder.admin")  # 아직 심사관 처리 단계

    # 심사관이 처리하면 관리자 승인 기한 알림으로 넘어간다 (다음 날)
    privacy = seeded.scalars(select(PrivacyRequest)).one()
    token = login(client, "rachel@msu.example")
    client.post(f"/review/privacy/{privacy.id}", data={"csrf_token": token})
    seeded.expire_all()  # 작업 큐는 매번 새 세션으로 읽는다
    reminders.send_daily(seeded, now=utcnow() + timedelta(hours=21))
    admin = notes(seeded, "admin@msu.example", "reminder.admin")
    assert len(admin) == 1 and "승인 기한이 다가온 삭제 요청 1건" in admin[0].message


def test_reminders_skip_inactive_users_and_run_from_beat(client: TestClient, seeded: Session) -> None:
    from backend.workers import tasks
    from backend.workers.celery_app import celery_app

    ev, prof, _ = professor_for(client, seeded, "calculus.txt")
    seeded.execute(
        update(Assignment)
        .where(Assignment.course_evaluation_id == ev.id)
        .values(assigned_at=utcnow() - timedelta(days=6))
    )
    seeded.execute(update(User).where(User.email == "rachel@msu.example").values(is_active=False))
    seeded.commit()

    schedule = celery_app.conf.beat_schedule["daily-reminders"]
    assert schedule["task"] == "reminders.daily"
    tasks.send_daily_reminders()  # beat가 넣는 작업 그대로
    assert notes(seeded, prof.email, "reminder.review")
    assert not notes(seeded, "rachel@msu.example", "reminder.evaluator")  # 비활성 계정은 받지 않는다
