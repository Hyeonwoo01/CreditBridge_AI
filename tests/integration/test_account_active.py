"""계정 비활성화: 로그인·세션·재설정 차단, 배정 대상 제외, 교수의 진행 중 심사 넘기기, 다시 활성화."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Assignment, AuditLog, User
from backend.services import auth
from tests.conftest import csrf_of, login
from tests.integration.test_pipeline import latest
from tests.integration.test_workflow import professor_for, reviewer_of, submitted_request


def deactivate(client: TestClient, email: str, action: str = "deactivate") -> str:
    token = login(client, "admin@msu.example")
    r = client.post("/admin/data/accounts/active", data={"email": email, "action": action, "csrf_token": token})
    assert r.status_code == 200
    return r.text


def test_deactivated_account_cannot_sign_in_and_can_be_restored(client: TestClient, seeded: Session) -> None:
    from backend.main import app

    with TestClient(app) as student:  # 다른 기기에 남은 학생 로그인
        login(student, "jiwon@student.example")
        assert student.get("/student").status_code == 200

        page = deactivate(client, "jiwon@student.example")
        assert "계정을 비활성화했어요" in page and "비활성 계정 1개는 빼고 셌어요" in page
        r = student.get("/student", follow_redirects=False)
        assert r.status_code in (302, 303) and r.headers["location"].startswith("/login")  # 세션이 끊긴다

    jiwon = seeded.scalars(select(User).where(User.email == "jiwon@student.example")).one()
    seeded.refresh(jiwon)
    assert not jiwon.is_active and jiwon.deactivated_at is not None

    client.cookies.clear()
    token = csrf_of(client)
    r = client.post("/login", data={"email": jiwon.email, "password": "demo1234", "csrf_token": token})
    assert r.status_code == 403 and "비활성화된 계정" in r.text
    r = client.post("/login", data={"email": jiwon.email, "password": "wrong-pass", "csrf_token": token})
    assert r.status_code == 401 and "비활성화" not in r.text  # 비밀번호를 모르면 일반 안내
    seeded.refresh(jiwon)
    assert jiwon.failed_logins == 0  # 실패로 세지 않아 재설정 메일도 가지 않는다
    assert auth.request_reset(seeded, jiwon.email) is None  # 비밀번호 찾기 메일 없음

    page = client.post(
        "/admin/data/accounts/active",
        data={"email": "admin@msu.example", "action": "deactivate", "csrf_token": login(client, "admin@msu.example")},
    ).text
    assert "본인 계정은 비활성화할 수 없어요" in page

    assert "다시 활성화했어요" in deactivate(client, jiwon.email, "reactivate")
    login(client, jiwon.email)  # 이전 비밀번호로 다시 로그인
    actions = [a.action for a in seeded.scalars(select(AuditLog).where(AuditLog.target_id == str(jiwon.id)))]
    assert "account.deactivate" in actions and "account.reactivate" in actions


def test_deactivating_professor_hands_over_reviews(client: TestClient, seeded: Session) -> None:
    ev, prof, _ = professor_for(client, seeded, "calculus.txt")
    colleague = seeded.scalars(
        select(User).where(User.department == prof.department, User.role == "professor", User.id != prof.id)
    ).one()

    page = deactivate(client, prof.email)
    assert "같은 학과 다른 교수에게 넘겼어요" in page
    assert reviewer_of(seeded, ev).id == colleague.id  # 같은 학과 다른 교수에게
    active = seeded.scalars(
        select(Assignment).where(Assignment.course_evaluation_id == ev.id, Assignment.is_active.is_(True))
    ).one()
    assert active.reassigned_from == prof.id
    login(client, colleague.email)
    assert "판정할 심사 1건" in client.get("/professor").text

    # 학과에 다른 교수가 없으면 배정을 비우고 심사관에게 알린다
    page = deactivate(client, colleague.email)
    assert "심사관이 다시 배정해야 해요" in page
    seeded.expire_all()
    assert not seeded.scalars(
        select(Assignment).where(Assignment.course_evaluation_id == ev.id, Assignment.is_active.is_(True))
    ).all()
    token = login(client, "rachel@msu.example")
    assert "교수 배정이 필요한 과목 1개" in client.get("/review").text
    r = client.post("/review/assign", data={"evaluation_ids": [ev.id], "csrf_token": token})
    assert "등록된 심사 교수가 없어요" in r.text  # 비활성 교수에게는 배정하지 않는다

    rid = submitted_request(client, seeded, "linear_algebra_detailed.txt")
    other = latest(seeded, "linear_algebra_detailed.txt", rid)
    token = login(client, "rachel@msu.example")
    client.post("/review/assign", data={"evaluation_ids": [other.id], "csrf_token": token})
    seeded.expire_all()
    assert not seeded.scalars(select(Assignment).where(Assignment.course_evaluation_id == other.id)).all()


def test_audit_log_page_shows_only_own_institution(client: TestClient, seeded: Session) -> None:
    """여러 대학이 함께 쓰므로 전체 감사 로그도 관리자 소속 기관 사용자의 기록만 보여 준다."""
    from backend.services import audit, views
    from backend.services.institution_data import bootstrap_admin

    bootstrap_admin(seeded, "Other State University", "US", "admin@osu.edu", "OSU 관리자")
    osu = seeded.scalars(select(User).where(User.email == "admin@osu.edu")).one()
    msu = seeded.scalars(select(User).where(User.email == "admin@msu.example")).one()
    audit.record(seeded, osu, "institution.create", "institution", "999", country="KR")
    seeded.commit()
    login(client, "rachel@msu.example")  # MSU 기록 하나 (로그인)

    mine = views.recent_audit(seeded, msu)
    assert mine and all(log.actor_id is not None for log in mine)
    actors = {u.id: u for u in seeded.scalars(select(User).where(User.id.in_({log.actor_id for log in mine})))}
    assert all(a.institution_id == msu.institution_id for a in actors.values())
    assert not any(log.actor_id == osu.id for log in mine)
    assert {log.actor_id for log in views.recent_audit(seeded, osu)} == {osu.id}

    login(client, msu.email)
    page = client.get("/admin/audit").text
    assert '"999"' not in page and "institution.create" not in page
