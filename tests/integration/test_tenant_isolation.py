"""기관(테넌트) 격리·객체 권한 (리뷰 v3 P0-7, 13.6).

다른 대학 계정(학생·심사관·교수·관리자)과 같은 대학의 다른 학생이 우리 대학 심사 건·요청·문서·이의 신청·정책의
id를 알아도 읽거나 바꿀 수 없어야 한다. 읽기는 403·404, 쓰기는 403·404이거나 거절 안내 후 DB가 그대로여야 한다.
"""

import hashlib

import pymupdf
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.models import (
    Appeal,
    AppealFile,
    CreditConversionRule,
    Department,
    Institution,
    PolicyRule,
    PrivacyRequest,
    User,
)
from backend.services.auth import hash_password
from scripts.seed_demo import DEMO_PASSWORD
from tests.conftest import login
from tests.integration.test_review_extras import reject
from tests.integration.test_workflow import professor_for

# 화면·처리 결과와 상관없는 기록(접속·알림·감사 로그)은 비교에서 뺀다
SKIP_TABLES = {"alembic_version", "audit_logs", "notifications", "push_subscriptions"}


def fingerprint(db: Session) -> dict[str, str]:
    db.expire_all()
    tables = db.execute(text("select tablename from pg_tables where schemaname = 'public' order by 1")).scalars()
    out = {}
    for table in tables:
        if table in SKIP_TABLES:
            continue
        rows = db.execute(text(f'select * from "{table}" order by 1')).all()
        if table == "users":  # 로그인 시각처럼 공격자 본인 행에서 바뀌는 칸은 빼고 남의 계정만 본다
            rows = [r for r in rows if not str(r.email).endswith("@other.example")]
        out[table] = hashlib.sha256(repr(rows).encode()).hexdigest()
    return out


def other_tenant(db: Session) -> dict[str, User]:
    other = Institution(name="Other State University", country="US", is_target=True, credit_system="us_semester")
    db.add(other)
    db.flush()
    dept = Department(institution_id=other.id, name="Mathematics")
    db.add(dept)
    db.flush()
    people = {}
    for role in ("student", "evaluator", "professor", "admin"):
        user = User(
            email=f"{role}@other.example",
            name=f"Other {role}",
            role=role,
            institution_id=other.id,
            department_id=dept.id if role in ("professor", "student") else None,
            password_hash=hash_password(DEMO_PASSWORD),
        )
        db.add(user)
        people[role] = user
    db.commit()
    return people


def msu_case(client: TestClient, db: Session) -> dict[str, int]:
    """MSU 학생 심사 건: 판정·이의 신청(근거 파일)·삭제 요청까지."""
    ev, _, token = professor_for(client, db, "calculus.txt")
    reject(client, ev, token)
    token = login(client, "jiwon@student.example")
    png = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 8, 8), False).tobytes("png")
    client.post(
        f"/student/evaluations/{ev.id}/appeal",
        data={"reason": "미분과 적분의 응용까지 15주 동안 배웠고 강의 노트로 증명할 수 있어요.", "csrf_token": token},
        files=[("files", ("note.png", png, "image/png"))],
    )
    appeal = db.scalars(select(Appeal).where(Appeal.course_evaluation_id == ev.id)).one()
    file = db.scalars(select(AppealFile).where(AppealFile.appeal_id == appeal.id)).one()
    assert ev.transfer_request_id is not None
    client.post(f"/student/requests/{ev.transfer_request_id}/delete-documents", data={"csrf_token": token})
    privacy = db.scalars(
        select(PrivacyRequest).where(PrivacyRequest.transfer_request_id == ev.transfer_request_id)
    ).one()
    msu = db.scalars(select(Institution).where(Institution.name == "Midwest State University")).one()
    policy = db.scalars(select(PolicyRule).where(PolicyRule.institution_id == msu.id)).first()
    rule = db.scalars(select(CreditConversionRule).where(CreditConversionRule.target_institution_id == msu.id)).first()
    prof = db.scalars(select(User).where(User.email == "dkim@msu.example")).one()
    course_id = db.execute(text("select id from courses where institution_id = :i limit 1"), {"i": msu.id}).scalar()
    return {
        "evaluation_id": ev.id,
        "request_id": ev.transfer_request_id,
        "syllabus_id": ev.syllabus_id,
        "appeal_id": appeal.id,
        "file_id": file.id,
        "privacy_id": privacy.id,
        "rule_id": policy.id if policy else 0,
        "conversion_rule_id": rule.id if rule else 0,
        "user_id": prof.id,
        "course_id": int(course_id or 0),
        "span_id": int(db.execute(text("select coalesce(max(id), 0) from evidence_spans")).scalar() or 0),
        "entry_id": int(db.execute(text("select coalesce(max(id), 0) from transcript_entries")).scalar() or 0),
    }


GETS = [
    "/evaluations/{evaluation_id}",
    "/evaluations/{evaluation_id}/report",
    "/evaluations/{evaluation_id}/report.pdf",
    "/evaluations/{evaluation_id}/original/student",
    "/appeal-files/{file_id}",
    "/review/evaluations/{evaluation_id}",
    "/professor/evaluations/{evaluation_id}",
    "/student/requests/{request_id}",
    "/student/syllabi/{syllabus_id}",
    "/student/evaluations/{evaluation_id}",
    "/student/evaluations/{evaluation_id}/appeal",
    "/admin/accounts/{user_id}",
    "/api/v1/evaluations/{evaluation_id}",
]

POSTS: list[tuple[str, dict[str, object]]] = [
    ("/professor/evaluations/{evaluation_id}/decision", {"action": "approve"}),
    ("/professor/evaluations/{evaluation_id}/evidence/{span_id}", {"verdict": "wrong"}),
    ("/professor/evaluations/{evaluation_id}/materials", {"items": ["강의 노트"]}),
    ("/review/evaluations/{evaluation_id}/assign", {"reviewer_id": "{user_id}"}),
    ("/review/evaluations/{evaluation_id}/materials", {"items": ["강의 노트"]}),
    (
        "/review/evaluations/{evaluation_id}/evidence-status",
        {"source_kind": "public_web", "authenticity": "rejected", "verification_note": "x"},
    ),
    ("/review/appeals/{appeal_id}", {"action": "dismiss", "note": "기각"}),
    ("/review/privacy/{privacy_id}", {"action": "approve"}),
    ("/evaluations/{evaluation_id}/notes", {"body": "다른 기관 메모"}),
    ("/admin/assignments/{evaluation_id}", {"reviewer_id": "{user_id}"}),
    ("/admin/accounts/{user_id}", {"name": "Hacked", "role": "admin"}),
    ("/admin/privacy/{privacy_id}", {"action": "approve"}),
    ("/admin/data/policies/{rule_id}/retire", {}),
    ("/admin/data/conversion-rules/{conversion_rule_id}/end", {}),
    ("/admin/data/courses/{course_id}/reference/remove", {}),
    ("/student/requests/{request_id}/counted", {"counted": "1"}),
    ("/student/requests/{request_id}/delete", {}),
    ("/student/requests/{request_id}/submit", {}),
    ("/student/requests/{request_id}/delete-documents", {}),
    ("/student/requests/{request_id}/entries/{entry_id}", {"action": "remove"}),
    (
        "/student/evaluations/{evaluation_id}/appeal",
        {"reason": "다른 사람의 판정에 이의를 신청해 봅니다. 스무 자 넘게 적어요."},
    ),
]


def fill(template: str, ids: dict[str, int]) -> str:
    return template.format(**ids)


def test_other_tenant_cannot_read_or_change_objects(client: TestClient, seeded: Session) -> None:
    ids = msu_case(client, seeded)
    others = other_tenant(seeded)
    attackers = [*(u.email for u in others.values()), "senior@student.example"]  # 마지막: 같은 대학 다른 학생
    leaks: list[str] = []
    for email in attackers:
        token = login(client, email)
        for path in GETS:
            url = fill(path, ids)
            r = client.get(url, follow_redirects=False)
            # 다른 역할 화면은 자기 홈으로 돌려보내기도 한다(303). 200이면 내용이 보인 것
            if r.status_code == 200:
                leaks.append(f"{email} GET {url} -> 200")
        before = fingerprint(seeded)
        for path, form in POSTS:
            url = fill(path, ids)
            data = {k: (fill(v, ids) if isinstance(v, str) else v) for k, v in form.items()}
            r = client.post(url, data={**data, "csrf_token": token}, follow_redirects=False)
            after = fingerprint(seeded)
            changed = [t for t in after if after[t] != before[t]]
            if changed:
                leaks.append(f"{email} POST {url} -> {r.status_code}, 바뀐 표 {changed}")
                before = after
    assert not leaks, "\n".join(leaks)

    # 대조: 권한 있는 본인·소속 계정이면 같은 주소가 열리고 실제로 바뀐다 (테스트가 헛돌지 않음)
    login(client, "jiwon@student.example")
    assert client.get(fill("/student/evaluations/{evaluation_id}", ids)).status_code == 200
    assert client.get(fill("/appeal-files/{file_id}", ids)).status_code == 200
    token = login(client, "rachel@msu.example")
    assert client.get(fill("/review/evaluations/{evaluation_id}", ids)).status_code == 200
    before = fingerprint(seeded)
    client.post(fill("/evaluations/{evaluation_id}/notes", ids), data={"body": "소속 메모", "csrf_token": token})
    assert fingerprint(seeded)["evaluation_notes"] != before["evaluation_notes"]


def test_api_decision_for_other_tenant_is_refused(client: TestClient, seeded: Session) -> None:
    ids = msu_case(client, seeded)
    others = other_tenant(seeded)
    token = login(client, others["professor"].email)
    before = fingerprint(seeded)
    r = client.post(
        "/api/v1/decisions",
        json={"evaluation_id": ids["evaluation_id"], "action": "approve"},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code in (403, 404)
    assert fingerprint(seeded) == before


def test_sis_export_and_queue_show_only_own_tenant(client: TestClient, seeded: Session) -> None:
    msu_case(client, seeded)
    others = other_tenant(seeded)
    login(client, others["evaluator"].email)
    assert "MATH 101" not in client.get("/review").text
    assert "MATH 101" not in client.get("/review/export.csv").text
    assert "미분과 적분" not in client.get("/review/appeals").text
    login(client, others["admin"].email)
    assert "dkim@msu.example" not in client.get("/admin/accounts").text
    assert "MATH 101" not in client.get("/admin/assignments?show=all").text
    login(client, others["professor"].email)
    assert "MATH 101" not in client.get("/professor").text
