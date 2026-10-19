"""권한 매트릭스(docs/spec.md 4장)와 코드 맞춤: 관리자 교수 배정·재배정, 심사관의 학생 대신 문서 업로드."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Assignment, AuditLog, MaterialRequest, Notification, SupplementFile, User
from tests.conftest import demo_pdf, login
from tests.integration.test_pipeline import latest
from tests.integration.test_workflow import reviewer_of, submitted_request


def user_of(db: Session, email: str) -> User:
    return db.scalars(select(User).where(User.email == email)).one()


def test_admin_assigns_and_reassigns_without_seeing_ai_results(client: TestClient, seeded: Session) -> None:
    rid = submitted_request(client, seeded, "calculus.txt", "data_structures.txt")
    calc, ds = latest(seeded, "calculus.txt", rid), latest(seeded, "data_structures.txt", rid)

    token = login(client, "admin@msu.example")
    page = client.get("/admin/assignments").text
    assert "교수 배정" in page and f"#{rid}" in page and "Mathematics" in page
    table = page[page.index("<table") : page.index("</table>")]
    assert all(
        w not in table for w in ("직접 인정", "선택 인정", "정보 부족", "신뢰도", "%")
    )  # 관리자는 AI 결과를 안 본다
    assert "admin/assignments" in client.get("/admin/stats").text  # 메뉴

    # 자동 배정: 학과 교수에게
    r = client.post("/admin/assignments/auto", data={"evaluation_ids": [calc.id], "csrf_token": token})
    assert "1건을 학과 담당 교수에게 배정했어요" in r.text
    first = reviewer_of(seeded, calc)
    assert first.department_name == "Mathematics"

    # 특정 교수로 바꾸기: 이전 배정은 기록으로 남고 두 교수 모두 알림
    other = user_of(seeded, "lchen@msu.example" if first.email != "lchen@msu.example" else "dkim@msu.example")
    r = client.post(f"/admin/assignments/{calc.id}", data={"reviewer_id": other.id, "csrf_token": token})
    assert f"{other.name} 교수에게 배정했어요" in r.text
    assert reviewer_of(seeded, calc).id == other.id
    rows = seeded.scalars(select(Assignment).where(Assignment.course_evaluation_id == calc.id)).all()
    assert len(rows) == 2 and sum(a.is_active for a in rows) == 1
    kinds = {n.kind for n in seeded.scalars(select(Notification).where(Notification.user_id == first.id))}
    assert "assignment.moved" in kinds
    log = seeded.scalars(select(AuditLog).where(AuditLog.action == "assignment.create")).all()[-1]
    assert log.actor_id == user_of(seeded, "admin@msu.example").id and log.payload_json["previous"] == first.id

    r = client.post(f"/admin/assignments/{calc.id}", data={"reviewer_id": other.id, "csrf_token": token})
    assert "이미 그 교수에게 배정돼 있어요" in r.text
    student = user_of(seeded, "jiwon@student.example")
    r = client.post(f"/admin/assignments/{ds.id}", data={"reviewer_id": student.id, "csrf_token": token})
    assert "활성 교수를 골라 주세요" in r.text
    assert "미배정" in client.get("/admin/assignments").text  # ds는 아직 미배정

    # 심사관도 같은 규칙으로 특정 교수 배정 가능, 학생·교수는 불가
    login(client, other.email)
    assert client.get("/admin/assignments").status_code == 403


def test_evaluator_uploads_supplement_for_student(client: TestClient, seeded: Session) -> None:
    rid = submitted_request(client, seeded, "linear_algebra_sparse.txt")
    ev = latest(seeded, "linear_algebra_sparse.txt", rid)
    token = login(client, "rachel@msu.example")
    page = client.get(f"/review/evaluations/{ev.id}").text
    assert "학생 대신 보완 자료 올리기" in page
    client.post(
        f"/review/evaluations/{ev.id}/materials",
        data={"items": ["주차별 상세 강의 계획"], "csrf_token": token},
    )

    r = client.post(
        f"/review/evaluations/{ev.id}/supplement",
        files={"file": ("weekly.pdf", demo_pdf("linear_algebra_detailed.txt"), "application/pdf")},
        data={"csrf_token": token},
    )
    assert r.status_code == 200 and "보완 자료를 올렸어요" in r.text
    seeded.expire_all()
    assert seeded.scalars(select(SupplementFile).where(SupplementFile.syllabus_id == ev.syllabus_id)).one()
    assert seeded.scalars(select(MaterialRequest)).one().status == "fulfilled"  # 열린 요청은 처리됨
    after = latest(seeded, "linear_algebra_sparse.txt", rid)
    assert after.id != ev.id and after.recommendation != "insufficient"  # 다시 분석
    student = user_of(seeded, "jiwon@student.example")
    kinds = {n.kind for n in seeded.scalars(select(Notification).where(Notification.user_id == student.id))}
    assert "material.uploaded_by_staff" in kinds
    log = seeded.scalars(select(AuditLog).where(AuditLog.action == "syllabus.supplement")).all()[-1]
    assert log.payload_json == {"by_staff": True}

    # 이전 분석 화면에서는 올릴 수 없다
    r = client.post(
        f"/review/evaluations/{ev.id}/supplement",
        files={"file": ("again.pdf", demo_pdf("linear_algebra_detailed.txt"), "application/pdf")},
        data={"csrf_token": token},
    )
    assert "최신 분석 화면에서 올려 주세요" in r.text

    # 교수·학생은 이 경로를 쓸 수 없다
    login(client, "jiwon@student.example")
    r = client.post(
        f"/review/evaluations/{after.id}/supplement",
        files={"file": ("x.pdf", demo_pdf("linear_algebra_detailed.txt"), "application/pdf")},
        data={"csrf_token": "x"},
    )
    assert r.status_code in (400, 403)
