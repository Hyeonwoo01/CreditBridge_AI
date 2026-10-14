"""심사 워크플로우와 권한 (TS-03~05, TC-11, TC-14~18, TC-20, NF-04~06, NF-10)."""

from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Assignment, AuditLog, CourseEvaluation, Decision, TransferRequest, User
from app.services.decisions import SIMILARITY_MIN, similarity
from scripts.make_demo_pdfs import text_to_pdf
from tests.conftest import demo_text, login
from tests.integration.test_pipeline import latest, new_request, upload


def submitted_request(client: TestClient, db: Session, *files: str) -> int:
    token = login(client, "jiwon@student.example")
    rid = new_request(client, db, token)
    upload(client, rid, token, *files)
    r = client.post(f"/student/requests/{rid}/submit", data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code == 303
    return rid


def assign(client: TestClient, *evaluations: CourseEvaluation) -> None:
    token = login(client, "rachel@msu.example")
    r = client.post(
        "/review/assign",
        data={"evaluation_ids": [e.id for e in evaluations], "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303


def reviewer_of(db: Session, ev: CourseEvaluation) -> User:
    db.expire_all()
    a = db.scalars(
        select(Assignment).where(Assignment.course_evaluation_id == ev.id, Assignment.is_active.is_(True))
    ).one()
    user = db.get(User, a.reviewer_id)
    assert user is not None
    return user


def test_queue_tabs_and_department_assignment(client: TestClient, seeded: Session) -> None:
    submitted_request(client, seeded, "calculus.txt", "data_structures.txt", "linear_algebra_sparse.txt")
    token = login(client, "rachel@msu.example")
    high = client.get("/review?tab=high").text
    assert "MATH 101" in high and "CSE 204" in high
    insufficient = client.get("/review?tab=insufficient").text
    assert "Linear Algebra" in insufficient

    calc, ds = latest(seeded, "calculus.txt"), latest(seeded, "data_structures.txt")
    client.post("/review/assign", data={"evaluation_ids": [calc.id, ds.id], "csrf_token": token})
    assert reviewer_of(seeded, calc).department == "Mathematics"
    assert reviewer_of(seeded, ds).department == "Computer Science and Engineering"


def test_away_professor_is_replaced_by_delegate(client: TestClient, seeded: Session) -> None:
    submitted_request(client, seeded, "calculus.txt")
    calc = latest(seeded, "calculus.txt")
    assign(client, calc)
    first = reviewer_of(seeded, calc)
    colleague = seeded.scalars(select(User).where(User.department == "Mathematics", User.id != first.id)).one()

    token = login(client, first.email)
    r = client.post(
        "/professor/away",
        data={"days": 14, "delegate_id": colleague.id, "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303
    now = reviewer_of(seeded, calc)
    assert now.id == colleague.id
    a = seeded.scalars(
        select(Assignment).where(Assignment.course_evaluation_id == calc.id, Assignment.is_active.is_(True))
    ).one()
    assert a.reassigned_from == first.id
    login(client, "rachel@msu.example")
    assert "대리 재배정" in client.get("/review?tab=high").text


def test_professor_decision_rules_and_portal(client: TestClient, seeded: Session) -> None:
    rid = submitted_request(client, seeded, "calculus.txt")
    calc = latest(seeded, "calculus.txt")
    assign(client, calc)
    prof = reviewer_of(seeded, calc)
    token = login(client, prof.email)

    page = client.get(f"/professor/evaluations/{calc.id}")
    assert page.status_code == 200 and "학생 강의계획서" in page.text

    # 반려는 사유 코드 없이 저장 불가, '기타'는 메모 필수 (TC-17)
    url = f"/professor/evaluations/{calc.id}/decision"
    r = client.post(url, data={"action": "reject", "csrf_token": token})
    assert r.status_code == 422 and "사유" in r.text
    r = client.post(url, data={"action": "reject", "reason_codes": ["other"], "reason_memo": " ", "csrf_token": token})
    assert r.status_code == 422 and "메모" in r.text
    r = client.post(url, data={"action": "reject", "reason_codes": ["not-a-code"], "csrf_token": token})
    assert r.status_code == 422
    assert seeded.scalars(select(Decision).where(Decision.course_evaluation_id == calc.id)).first() is None

    r = client.post(
        f"/professor/evaluations/{calc.id}/decision",
        data={"action": "approve", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303
    decision = seeded.scalars(select(Decision).where(Decision.course_evaluation_id == calc.id)).one()
    assert decision.decided_by == prof.id and decision.result == "direct"
    assert decision.ai_recommendation_snapshot["recommendation"] == "direct"
    assert seeded.scalars(select(AuditLog).where(AuditLog.action == "decision.create")).first() is not None

    # 학생 포털에 확정 반영 (TC-20), 요청 상태 완료
    login(client, "jiwon@student.example")
    assert "승인 완료 · 직접 인정" in client.get(f"/student/requests/{rid}").text
    seeded.expire_all()
    assert seeded.scalars(select(TransferRequest).where(TransferRequest.id == rid)).one().status == "decided"

    # 확정 결과 내보내기 (NF-10)
    login(client, "rachel@msu.example")
    csv = client.get("/review/export.csv").text
    assert "MATH 101" in csv and "MATH 1151" in csv and "direct" in csv


def professor_for(
    client: TestClient, db: Session, filename: str, text_pdf: bytes | None = None
) -> tuple[CourseEvaluation, User, str]:
    token = login(client, "jiwon@student.example")
    rid = new_request(client, db, token)
    if text_pdf is None:
        upload(client, rid, token, filename)
    else:
        client.post(
            f"/student/requests/{rid}/syllabi",
            files=[("files", (filename, text_pdf, "application/pdf"))],
            data={"csrf_token": token},
        )
    client.post(f"/student/requests/{rid}/submit", data={"csrf_token": token})
    ev = latest(db, filename, rid)
    assign(client, ev)
    prof = reviewer_of(db, ev)
    return ev, prof, login(client, prof.email)


def test_consistency_alert_for_conflicting_past_decision(client: TestClient, seeded: Session) -> None:
    ev, prof, token = professor_for(client, seeded, "linear_algebra_detailed.txt")

    page = client.get(f"/professor/evaluations/{ev.id}").text
    assert "같은 과목의 과거 판정 1건" in page and "강의계획서 유사도" in page  # 작년 직접 인정 이력

    data = {
        "action": "reject",
        "reason_codes": ["weeks_insufficient", "other"],
        "reason_memo": "고유값 단원이 부족함",
        "csrf_token": token,
    }
    r = client.post(f"/professor/evaluations/{ev.id}/decision", data=data)
    assert r.status_code == 409 and "과거 판정" in r.text
    assert seeded.scalars(select(Decision).where(Decision.course_evaluation_id == ev.id)).first() is None

    r = client.post(
        f"/professor/evaluations/{ev.id}/decision",
        data={**data, "acknowledge_conflict": "true"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    decision = seeded.scalars(select(Decision).where(Decision.course_evaluation_id == ev.id)).one()
    assert decision.conflict_acknowledged and decision.result == "none"
    assert decision.reason_codes == ["weeks_insufficient", "other"] and decision.reason_memo == "고유값 단원이 부족함"

    report = client.get(f"/evaluations/{ev.id}/report").text
    assert "주차 범위 부족" in report and "고유값 단원이 부족함" in report
    assert "판정 당시 AI 추천" in report and prof.name in report


def test_same_result_raises_no_alert(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "linear_algebra_detailed.txt")
    assert ev.recommendation == "direct"
    r = client.post(
        f"/professor/evaluations/{ev.id}/decision",
        data={"action": "approve", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303
    decision = seeded.scalars(select(Decision).where(Decision.course_evaluation_id == ev.id)).one()
    assert not decision.conflict_acknowledged and decision.reason_codes == []


def test_revised_syllabus_raises_no_alert(client: TestClient, seeded: Session) -> None:
    """같은 과목 코드라도 강의계획서가 개편됐으면(유사도 미달) 과거 판정과 달라도 경보를 띄우지 않는다."""
    revised = (
        "Hankuk University\nMATH 201 Linear Algebra\nCredits: 3\n\nCourse Description (revised 2026)\n"
        "A computation-first course built around numerical methods with Python notebooks: LU and QR factorizations, "
        "conditioning and floating point error, iterative solvers, singular value decomposition and principal "
        "component analysis, with applications to image compression and recommender systems.\n\nTextbook\n"
        "Gilbert Strang, Introduction to Linear Algebra, 6th edition\n\nWeekly Schedule\n"
        + "\n".join(
            f"Week {i}: {topic}"
            for i, topic in enumerate(
                [
                    "Python and NumPy setup, vectors as arrays",
                    "Linear systems: row reduction and LU factorization with pivoting",
                    "Matrix operations and inverses in NumPy, conditioning",
                    "QR factorization with Householder reflections",
                    "Iterative solvers: Jacobi and Gauss-Seidel",
                    "Eigenvalues and eigenvectors by power iteration and the QR algorithm",
                    "Vector spaces, subspaces, basis, dimension and rank through the SVD",
                    "Midterm project presentations",
                    "Principal component analysis on real data",
                    "Image compression with low-rank approximation",
                    "Sparse matrices and graph Laplacians",
                    "Recommender systems and matrix completion",
                    "Final project workshop",
                ],
                start=1,
            )
        )
        + "\n\nAssessment\nNotebooks 40%, Projects 60%\n"
    )
    assert similarity(revised, demo_text("linear_algebra_detailed.txt")) < SIMILARITY_MIN
    ev, _, token = professor_for(client, seeded, "math201_revised.pdf", text_to_pdf(revised))
    page = client.get(f"/professor/evaluations/{ev.id}").text
    assert "개편된 강의계획서" in page

    data = {"action": "reject", "reason_codes": ["level_difference"], "csrf_token": token}
    r = client.post(f"/professor/evaluations/{ev.id}/decision", data=data, follow_redirects=False)
    assert r.status_code == 303
    decision = seeded.scalars(select(Decision).where(Decision.course_evaluation_id == ev.id)).one()
    assert not decision.conflict_acknowledged


def test_no_decision_without_assigned_professor(client: TestClient, seeded: Session) -> None:
    submitted_request(client, seeded, "calculus.txt")
    calc = latest(seeded, "calculus.txt")
    body = {"evaluation_id": calc.id, "action": "approve"}

    # 로그인 없이 API 호출 → 거부 (TC-16)
    client.cookies.clear()
    assert client.post("/api/decisions", json=body).status_code == 401
    # 학생·심사관도 확정 불가
    for email in ("jiwon@student.example", "rachel@msu.example"):
        token = login(client, email)
        r = client.post("/api/decisions", json=body, headers={"X-CSRF-Token": token})
        assert r.status_code == 403
    # 배정되지 않은 교수도 불가
    assign(client, calc)
    other = seeded.scalars(select(User).where(User.department == "Physics")).first()
    assert other is not None
    token = login(client, other.email)
    assert client.post("/api/decisions", json=body, headers={"X-CSRF-Token": token}).status_code == 403
    assert seeded.scalars(select(Decision).where(Decision.course_evaluation_id == calc.id)).first() is None

    prof = reviewer_of(seeded, calc)
    token = login(client, prof.email)
    r = client.post("/api/decisions", json=body, headers={"X-CSRF-Token": token})
    assert r.status_code == 201 and r.json()["decided_by"] == prof.id


def test_role_based_access(client: TestClient, seeded: Session) -> None:
    submitted_request(client, seeded, "calculus.txt")
    calc = latest(seeded, "calculus.txt")

    # 다른 학생은 볼 수 없다
    login(client, "senior@student.example")
    assert client.get(f"/student/evaluations/{calc.id}").status_code == 403
    assert client.get(f"/api/evaluations/{calc.id}").status_code == 403
    # 배정 전 교수는 볼 수 없다
    login(client, "dkim@msu.example")
    assert client.get(f"/professor/evaluations/{calc.id}").status_code == 403
    # 학생은 심사 큐에 들어갈 수 없다
    login(client, "jiwon@student.example")
    assert client.get("/review").status_code == 403
    # 관리자는 판정 원문 대신 감사 로그만
    login(client, "admin@msu.example")
    assert client.get(f"/evaluations/{calc.id}/report").status_code == 403
    assert client.get("/admin/audit").status_code == 200


def test_csrf_required(client: TestClient, seeded: Session) -> None:
    login(client, "jiwon@student.example")
    r = client.post("/student/requests", data={"source_institution_id": 1, "major": "Mathematics", "csrf_token": "bad"})
    assert r.status_code == 403


def test_privacy_delete_needs_approval_before_files_go(client: TestClient, seeded: Session, fake_storage) -> None:  # type: ignore[no-untyped-def]
    """학생의 삭제 요청만으로는 지워지지 않는다. 전체 흐름은 test_review_extras 참고."""
    token = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, token)
    upload(client, rid, token, "calculus.txt")
    page = client.post(f"/student/requests/{rid}/delete-documents", data={"csrf_token": token}).text
    assert "삭제 요청을 접수했어요" in page and "요청됨" in page
    assert fake_storage.objects  # 승인 전에는 그대로


def test_decisions_table_has_no_update_path(seeded: Session) -> None:
    """decisions·audit_logs 저장소 코드에는 UPDATE/DELETE가 없다 (추가 전용)."""
    import inspect

    from app.repositories import audit, decisions

    for module in (audit, decisions):
        source = inspect.getsource(module)
        assert "update(" not in source and "delete(" not in source and ".delete" not in source
    # DB 권한 예시: 운영 계정에는 이 두 테이블의 UPDATE/DELETE 권한을 주지 않는다 (docs 참고)
    assert seeded.execute(text("SELECT COUNT(*) FROM decisions")).scalar() == 1  # 시드 이력
