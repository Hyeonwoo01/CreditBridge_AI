"""P2·P3 심사 업무: 보완 자료 요청(FR-22), 이의 신청(FR-23), 삭제 요청(FR-13), 알림(FR-19·20),
학사정보 연동(FR-24), 근거 위치 이동(FR-25), 동등 과목표(FR-26), 운영 통계(FR-27)."""

import csv
import io

import pymupdf
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import (
    Appeal,
    AppealFile,
    Assignment,
    AuditLog,
    CourseEvaluation,
    Decision,
    Department,
    MaterialRequest,
    Notification,
    PrivacyRequest,
    SupplementFile,
    Syllabus,
    User,
)
from tests.conftest import demo_pdf, login
from tests.fakes import FakeStorage
from tests.integration.test_pipeline import latest, new_request, upload
from tests.integration.test_workflow import professor_for, reviewer_of, submitted_request


def notes_for(db: Session, email: str) -> list[str]:
    db.expire_all()
    user = db.scalars(select(User).where(User.email == email)).one()
    return [n.message for n in db.scalars(select(Notification).where(Notification.user_id == user.id))]


def reject(client: TestClient, ev: CourseEvaluation, token: str) -> None:
    """불인정 판정 (직접 인정은 이의 신청을 받지 않으므로 이의 신청 테스트는 이 판정으로 한다)."""
    r = client.post(
        f"/professor/evaluations/{ev.id}/decision",
        data={"action": "reject", "reason_codes": ["no_lab"], "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text


def approve(client: TestClient, ev: CourseEvaluation, token: str) -> None:
    r = client.post(
        f"/professor/evaluations/{ev.id}/decision",
        data={"action": "approve", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text


# ---------- FR-22 보완 자료 요청 ----------


def test_material_request_flow_keeps_assignment(client: TestClient, seeded: Session) -> None:
    ev, prof, token = professor_for(client, seeded, "linear_algebra_sparse.txt")
    assert ev.recommendation == "insufficient"
    page = client.get(f"/professor/evaluations/{ev.id}").text
    assert "학생에게 보완 자료 요청" in page

    # 학생은 제출 뒤에는 요청 없이 보완 자료를 올릴 수 없다
    student_token = login(client, "jiwon@student.example")
    r = client.post(
        f"/student/syllabi/{ev.syllabus_id}/supplement",
        files={"file": ("plan.pdf", demo_pdf("linear_algebra_detailed.txt"), "application/pdf")},
        data={"csrf_token": student_token},
    )
    assert "보완 자료 요청이 있을 때만" in r.text

    token = login(client, prof.email)
    r = client.post(
        f"/professor/evaluations/{ev.id}/materials",
        data={"items": ["주차별 상세 강의 계획"], "note": "고유값 단원 자료", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert any("보완 자료 요청" in m for m in notes_for(seeded, "jiwon@student.example"))

    student_token = login(client, "jiwon@student.example")
    request_page = client.get(f"/student/requests/{ev.transfer_request_id}").text
    assert "보완 자료를 요청한 과목이 1개" in request_page
    page = client.get(f"/student/evaluations/{ev.id}").text
    assert "요청받은 보완 자료 제출" in page and "고유값 단원 자료" in page
    r = client.post(
        f"/student/syllabi/{ev.syllabus_id}/supplement",
        files={"file": ("plan.pdf", demo_pdf("linear_algebra_detailed.txt"), "application/pdf")},
        data={"csrf_token": student_token},
        follow_redirects=False,
    )
    assert r.status_code == 303

    seeded.expire_all()
    material = seeded.scalars(select(MaterialRequest).where(MaterialRequest.syllabus_id == ev.syllabus_id)).one()
    assert material.status == "fulfilled" and material.fulfilled_at is not None
    assert seeded.scalars(select(SupplementFile).where(SupplementFile.material_request_id == material.id)).one()
    assert any("보완 자료가 도착" in m for m in notes_for(seeded, prof.email))

    # 다시 분석한 결과에 같은 교수 배정이 이어지고, 바로 판정할 수 있다
    new = latest(seeded, "linear_algebra_sparse.txt")
    assert new.id != ev.id and new.recommendation == "direct"
    assert reviewer_of(seeded, new).id == prof.id
    token = login(client, prof.email)
    assert f"/professor/evaluations/{new.id}" in client.get("/professor").text
    approve(client, new, token)


def test_evaluator_can_request_materials_but_not_after_decision(client: TestClient, seeded: Session) -> None:
    ev, _, _ = professor_for(client, seeded, "calculus.txt")
    token = login(client, "rachel@msu.example")
    r = client.post(f"/review/evaluations/{ev.id}/materials", data={"items": [], "note": "", "csrf_token": token})
    assert "하나 이상" in r.text
    r = client.post(
        f"/review/evaluations/{ev.id}/materials", data={"items": ["시험지 또는 과제 샘플"], "csrf_token": token}
    )
    assert "보완 자료를 요청했어요" in r.text
    # 다른 학과 교수는 요청할 수 없다
    login(client, "mbrown@msu.example")
    r = client.post(f"/professor/evaluations/{ev.id}/materials", data={"items": ["x"], "csrf_token": ""})
    assert r.status_code == 403
    # 판정 뒤에는 요청할 수 없다
    prof_token = login(client, reviewer_of(seeded, ev).email)
    approve(client, ev, prof_token)
    token = login(client, "rachel@msu.example")
    r = client.post(
        f"/review/evaluations/{ev.id}/materials", data={"items": ["시험지 또는 과제 샘플"], "csrf_token": token}
    )
    assert "판정 전에만" in r.text


# ---------- FR-23 이의 신청 ----------


def test_appeal_accept_and_redecide_keeps_original_decision(client: TestClient, seeded: Session) -> None:
    ev, prof, token = professor_for(client, seeded, "calculus.txt")
    r = client.post(
        f"/professor/evaluations/{ev.id}/decision",
        data={"action": "modify", "result": "elective", "reason_codes": ["level_difference"], "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303
    first = seeded.scalars(select(Decision).where(Decision.course_evaluation_id == ev.id)).one()
    assert any("판정 결과가 확정" in m for m in notes_for(seeded, "jiwon@student.example"))

    student_token = login(client, "jiwon@student.example")
    page = client.post(
        f"/student/evaluations/{ev.id}/appeal", data={"reason": "짧음", "csrf_token": student_token}
    ).text
    assert "20자 이상" in page
    reason = "미분과 적분의 응용까지 15주 동안 배웠고 강의 노트와 시험지로 증명할 수 있어요."
    page = client.post(
        f"/student/evaluations/{ev.id}/appeal", data={"reason": reason, "csrf_token": student_token}
    ).text
    assert "이의 신청을 접수했어요" in page
    page = client.post(
        f"/student/evaluations/{ev.id}/appeal", data={"reason": reason, "csrf_token": student_token}
    ).text
    assert "이미 처리 중인 이의 신청" in page
    assert any("이의 신청이 접수" in m for m in notes_for(seeded, "rachel@msu.example"))

    token = login(client, "rachel@msu.example")
    appeal = seeded.scalars(select(Appeal).where(Appeal.course_evaluation_id == ev.id)).one()
    page = client.get("/review/appeals").text
    assert reason in page and f'value="{prof.id}" selected' in page  # 원 판정 교수가 기본값
    r = client.post(
        f"/review/appeals/{appeal.id}",
        data={"action": "accept", "reviewer_id": prof.id, "note": "자료 재검토", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert any("재판정이 배정" in m for m in notes_for(seeded, prof.email))

    token = login(client, prof.email)
    assert "이의 신청 재판정" in client.get("/professor").text
    page = client.get(f"/professor/evaluations/{ev.id}").text
    assert "재판정하기" in page and reason in page
    approve(client, ev, token)

    seeded.expire_all()
    decisions = seeded.scalars(
        select(Decision).where(Decision.course_evaluation_id == ev.id).order_by(Decision.id)
    ).all()
    assert [d.result for d in decisions] == ["elective", "direct"]  # 원 판정은 지워지지 않는다
    assert decisions[1].appeal_id == appeal.id
    seeded.refresh(appeal)
    assert appeal.status == "redecided"
    assert any("재판정 결과가 확정" in m for m in notes_for(seeded, "jiwon@student.example"))
    # 재판정 뒤에는 다시 판정할 수 없다
    r = client.post(f"/professor/evaluations/{ev.id}/decision", data={"action": "approve", "csrf_token": token})
    assert r.status_code == 422

    # 내보내기는 현재 판정만, 대체한 판정 번호와 함께
    login(client, "rachel@msu.example")
    rows = list(csv.DictReader(io.StringIO(client.get("/review/export.csv").text)))
    mine = [row for row in rows if row["source_course"] == "MATH 101"]
    assert len(mine) == 1 and mine[0]["result"] == "direct" and mine[0]["replaces_decision_id"] == str(first.id)
    report = client.get(f"/evaluations/{ev.id}/report").text
    assert "판정·이의 신청 경과" in report and "재판정" in report


def test_appeal_dismiss_requires_note(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    reject(client, ev, token)
    student_token = login(client, "jiwon@student.example")
    client.post(
        f"/student/evaluations/{ev.id}/appeal",
        data={
            "reason": "학점 차이를 고려해 다시 검토해 주시면 좋겠습니다. 실험 보고서가 있어요.",
            "csrf_token": student_token,
        },
    )
    appeal = seeded.scalars(select(Appeal).where(Appeal.course_evaluation_id == ev.id)).one()
    token = login(client, "rachel@msu.example")
    page = client.post(f"/review/appeals/{appeal.id}", data={"action": "dismiss", "note": "", "csrf_token": token}).text
    assert "사유를 적어" in page
    client.post(
        f"/review/appeals/{appeal.id}",
        data={"action": "dismiss", "note": "원 판정의 근거가 충분해요", "csrf_token": token},
    )
    seeded.expire_all()
    assert seeded.get(Appeal, appeal.id).status == "dismissed"  # type: ignore[union-attr]
    login(client, "jiwon@student.example")
    page = client.get(f"/student/evaluations/{ev.id}").text
    assert "원 판정의 근거가 충분해요" in page and "기각" in page


# ---------- FR-13 삭제 요청 ----------


def test_privacy_request_review_and_admin_approval(
    client: TestClient, seeded: Session, fake_storage: FakeStorage
) -> None:
    token = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, token)
    upload(client, rid, token, "linear_algebra_sparse.txt")
    ev = latest(seeded, "linear_algebra_sparse.txt")
    client.post(
        f"/student/syllabi/{ev.syllabus_id}/supplement",
        files={"file": ("plan.pdf", demo_pdf("linear_algebra_detailed.txt"), "application/pdf")},
        data={"csrf_token": token},
    )
    assert any(k.startswith("supplements/") for k in fake_storage.objects)

    client.post(f"/student/requests/{rid}/delete-documents", data={"csrf_token": token})
    page = client.post(f"/student/requests/{rid}/delete-documents", data={"csrf_token": token}).text
    assert "이미 처리 중인 삭제 요청" in page
    privacy = seeded.scalars(select(PrivacyRequest).where(PrivacyRequest.transfer_request_id == rid)).one()
    assert (privacy.due_at - privacy.created_at).days == 30
    assert any("문서 삭제 요청" in m for m in notes_for(seeded, "rachel@msu.example"))

    # 학생·심사관은 승인할 수 없다
    assert client.post(f"/admin/privacy/{privacy.id}", data={"csrf_token": token}).status_code == 403
    token = login(client, "rachel@msu.example")
    assert "기한" in client.get("/review/privacy").text
    client.post(f"/review/privacy/{privacy.id}", data={"csrf_token": token})
    assert any("승인을 기다려요" in m for m in notes_for(seeded, "admin@msu.example"))
    assert fake_storage.objects  # 아직 삭제 전

    token = login(client, "admin@msu.example")
    assert "심사관 처리 완료" in client.get("/admin/privacy").text
    r = client.post(f"/admin/privacy/{privacy.id}", data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code == 303
    assert not fake_storage.objects  # 강의계획서·보완 자료 원본 모두 삭제
    seeded.expire_all()
    syllabus = seeded.get(Syllabus, ev.syllabus_id)
    assert syllabus is not None and syllabus.raw_text == "" and syllabus.status == "deleted"
    assert seeded.get(PrivacyRequest, privacy.id).status == "completed"  # type: ignore[union-attr]
    assert any("삭제를 마쳤어요" in m for m in notes_for(seeded, "jiwon@student.example"))


# ---------- FR-19·20 알림 ----------


def test_notifications_for_assignment_and_delegation(client: TestClient, seeded: Session) -> None:
    submitted_request(client, seeded, "calculus.txt")
    calc = latest(seeded, "calculus.txt")
    token = login(client, "rachel@msu.example")
    client.post("/review/assign", data={"evaluation_ids": [calc.id], "csrf_token": token})
    prof = reviewer_of(seeded, calc)
    assert any("새 심사가 배정" in m for m in notes_for(seeded, prof.email))

    colleague = seeded.scalars(
        select(User)
        .join(Department, Department.id == User.department_id)
        .where(Department.name == "Mathematics", User.id != prof.id)
    ).one()
    token = login(client, prof.email)
    assert client.get("/notifications/count").text.count("notify-count") == 1
    client.post("/professor/away", data={"days": 7, "delegate_id": colleague.id, "csrf_token": token})
    assert any("대리 재배정" in m for m in notes_for(seeded, "rachel@msu.example"))  # TC-15 심사관 알림
    assert any("대리 배정" in m for m in notes_for(seeded, colleague.email))

    login(client, colleague.email)
    page = client.get("/notifications").text
    assert "대리 배정" in page
    assert client.get("/notifications/count").text == ""  # 열어 보면 읽음 처리


# ---------- FR-24 학사정보 연동 ----------


def test_sis_api_requires_admin_issued_token(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    approve(client, ev, token)
    client.cookies.clear()
    assert client.get("/api/v1/sis/decisions").status_code == 401
    assert client.get("/api/v1/sis/decisions", headers={"Authorization": "Bearer cbsis_wrong"}).status_code == 401

    login(client, "rachel@msu.example")
    assert client.get("/admin/sis").status_code == 403
    token = login(client, "admin@msu.example")
    page = client.post("/admin/sis", data={"action": "issue", "csrf_token": token}).text
    issued = page.split("cbsis_", 1)[1].split("<", 1)[0]
    secret = "cbsis_" + issued.strip()

    client.cookies.clear()
    r = client.get("/api/v1/sis/decisions", headers={"Authorization": f"Bearer {secret}"})
    assert r.status_code == 200
    body = r.json()
    assert body["institution"] == "Midwest State University"
    calc = [d for d in body["decisions"] if d["source_course"] == "MATH 101"]
    assert calc and calc[0]["target_course"] == "MATH 1151" and calc[0]["result"] == "direct"
    later = client.get(
        "/api/v1/sis/decisions?since=2999-01-01T00:00:00Z", headers={"Authorization": f"Bearer {secret}"}
    )
    assert later.json()["count"] == 0
    assert "Deprecation" not in r.headers
    # 버전 없는 옛 경로도 같은 결과를 주되, 폐기 예정과 새 경로를 헤더로 알린다
    legacy = client.get("/api/sis/decisions?since=2000-01-01T00:00:00Z", headers={"Authorization": f"Bearer {secret}"})
    assert legacy.status_code == 200 and legacy.json()["count"] == body["count"]
    assert legacy.headers["Deprecation"] == "true"
    assert legacy.headers["Link"] == '</api/v1/sis/decisions>; rel="successor-version"'

    token = login(client, "admin@msu.example")
    client.post("/admin/sis", data={"action": "revoke", "csrf_token": token})
    client.cookies.clear()
    assert client.get("/api/v1/sis/decisions", headers={"Authorization": f"Bearer {secret}"}).status_code == 401


# ---------- FR-25 근거 위치 이동 ----------


def test_evidence_links_jump_to_source_positions(client: TestClient, seeded: Session) -> None:
    token = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, token)
    upload(client, rid, token, "calculus.txt")
    ev = latest(seeded, "calculus.txt")
    page = client.get(f"/student/evaluations/{ev.id}").text
    result = ev.coverage_json or {}
    first = result["candidates"][0]["concepts"][0]["source_evidence"][0]
    anchor = f"src-{first['char_start']}-{first['char_end']}"
    assert f'href="#{anchor}"' in page and f'id="{anchor}"' in page
    assert 'id="source-text"' in page and 'id="target-text"' in page and "tgt-" in page


# ---------- FR-26 동등 과목표 ----------


def test_equivalency_import_shows_in_history_without_blocking(client: TestClient, seeded: Session) -> None:
    token = login(client, "rachel@msu.example")
    bad = (
        "source_institution,source_course,target_course,result,decided_on,note\n"
        "No Such Univ,MATH 101,,maybe,2020-13-01,\n"
    )
    r = client.post(
        "/review/equivalencies", files={"file": ("eq.csv", bad.encode(), "text/csv")}, data={"csrf_token": token}
    )
    assert r.status_code == 422 and "2행" in r.text and "등록되지 않은 출신 대학" in r.text
    good = (
        "source_institution,source_course,target_course,result,decided_on,note\n"
        "Hankuk University (한국대학교),MATH 101,,불인정,2019-08-30,구 교육과정\n"
    )
    r = client.post(
        "/review/equivalencies",
        files={"file": ("eq.csv", good.encode("cp949"), "text/csv")},  # 한국어 엑셀 기본 인코딩
        data={"csrf_token": token},
    )
    assert "1건을 가져왔어요" in r.text

    ev, _, token = professor_for(client, seeded, "calculus.txt")
    page = client.get(f"/professor/evaluations/{ev.id}").text
    assert "기존 동등 과목표" in page and "구 교육과정" in page
    approve(client, ev, token)  # 결과가 달라도 강의계획서 비교가 불가능해 경보 없이 확정 (303)


# ---------- FR-27 운영 통계 ----------


def test_stats_page_counts_decisions_and_disagreement(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    client.post(
        f"/professor/evaluations/{ev.id}/decision",
        data={"action": "reject", "reason_codes": ["no_lab"], "csrf_token": token},
    )
    login(client, "admin@msu.example")
    page = client.get("/admin/stats").text
    assert "AI-교수 불일치율" in page and "반려 1" in page
    login(client, "rachel@msu.example")
    assert client.get("/review/stats").status_code == 200
    login(client, "jiwon@student.example")
    assert client.get("/review/stats").status_code == 403


def test_history_is_scoped_to_target_institution(client: TestClient, seeded: Session) -> None:
    """다른 대상 대학이 내린 판정은 과거 이력·경보에 섞이지 않는다."""
    from backend.models import Institution, TransferRequest

    other = Institution(name="Other State", country="US", is_target=True)
    seeded.add(other)
    seeded.flush()
    past = seeded.scalars(select(TransferRequest).where(TransferRequest.status == "decided")).one()
    past.target_institution_id = other.id
    seeded.commit()
    ev, _, _ = professor_for(client, seeded, "linear_algebra_detailed.txt")
    assert "같은 과목의 과거 판정" not in client.get(f"/professor/evaluations/{ev.id}").text
    assert seeded.scalars(select(Assignment)).first() is not None


# ---------- 화면: 심사 큐 검색·경보 필터, 학생 과목 필터, 사유 선택 창, 관리자 콘솔 ----------


def test_queue_search_and_conflict_filter(client: TestClient, seeded: Session) -> None:
    submitted_request(client, seeded, "calculus.txt", "linear_algebra_detailed.txt")
    login(client, "rachel@msu.example")
    page = client.get("/review").text
    assert "미처리 2건" in page and "MATH 101" in page and "MATH 201" in page
    page = client.get("/review?q=calculus").text
    assert "MATH 101" in page and "MATH 201" not in page
    page = client.get("/review?tab=conflict").text  # 선형대수 과거 판정(직접 인정)은 AI 추천과 같아 경보 아님
    assert "MATH 201" not in page and "MATH 101" not in page
    assert client.get("/review?tab=nope").status_code == 422
    chips = client.get("/notifications/workspace").text
    assert "심사 대기 <b>2</b>" in chips
    login(client, "jiwon@student.example")
    assert client.get("/notifications/workspace").text.strip() == ""


def test_student_report_filters_courses(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    approve(client, ev, token)
    login(client, "jiwon@student.example")
    rid = ev.transfer_request_id
    page = client.get(f"/student/requests/{rid}").text
    assert "편입 학점 시뮬레이션 리포트" in page and "심사 진행 현황" in page and "승인 완료 · 직접 인정" in page
    assert "MATH 101" in client.get(f"/student/requests/{rid}?show=approved").text
    assert "이 조건에 해당하는 과목이 없어요" in client.get(f"/student/requests/{rid}?show=supplement").text
    assert client.get(f"/student/requests/{rid}?show=bad").status_code == 422


def test_reason_dialog_reopens_on_validation_error(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    page = client.get(f"/professor/evaluations/{ev.id}").text
    assert 'id="reason-dialog"' in page and "실험·실습이 출신 과목에 없어요" in page
    assert "data-autoopen" not in page
    r = client.post(f"/professor/evaluations/{ev.id}/decision", data={"action": "reject", "csrf_token": token})
    assert r.status_code == 422 and "data-autoopen" in r.text and "학점 불인정 사유 선택 및 소명" in r.text


def test_admin_console_shows_recent_audit_without_student_names(client: TestClient, seeded: Session) -> None:
    ev, prof, token = professor_for(client, seeded, "calculus.txt")
    client.post(
        f"/professor/evaluations/{ev.id}/decision",
        data={"action": "reject", "reason_codes": ["no_lab"], "csrf_token": token},
    )
    login(client, "admin@msu.example")
    page = client.get("/admin/stats").text
    assert "관리자 콘솔" in page and "AI 추천 수용률" in page and "학과별 심사 처리 지표" in page
    assert "판정 확정 · 불인정" in page and prof.name in page and "실험·실습 미포함" in page
    assert "LOG-" in page and "데이터 보존 및 파기 정책" in page
    student = seeded.scalars(select(User).where(User.email == "jiwon@student.example")).one()
    assert student.name not in page
    login(client, "rachel@msu.example")
    page = client.get("/review/stats").text
    assert "운영 통계" in page and "최근 감사 로그" not in page


# ---------- 학생 이의 신청 목록, 리포트에서 돌아가기 ----------


def test_student_sees_own_appeals_and_report_links_back(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    reject(client, ev, token)
    report = f"/evaluations/{ev.id}/report"
    assert f'href="/professor/evaluations/{ev.id}"' in client.get(report).text  # 교수 → 판정 화면

    student_token = login(client, "jiwon@student.example")
    page = client.get("/student/appeals").text
    assert "아직 낸 이의 신청이 없어요" in page and 'href="/student/appeals"' in page  # 학생 메뉴에 있다
    assert "이의 신청할 수 있는 과목" in page and f'href="/student/evaluations/{ev.id}/appeal"' in page
    reason = "학점 차이를 고려해 다시 검토해 주시면 좋겠습니다. 실험 보고서가 있어요."
    client.post(f"/student/evaluations/{ev.id}/appeal", data={"reason": reason, "csrf_token": student_token})
    page = client.get("/student/appeals").text
    assert "MATH 101" in page and "접수됨" in page and "학사처가 검토하고 있어요" in page
    assert "이의 신청할 수 있는 과목" not in page  # 처리 중이면 다시 낼 수 없다
    assert f'href="/student/evaluations/{ev.id}"' in client.get(report).text  # 학생 → 과목 결과

    appeal = seeded.scalars(select(Appeal).where(Appeal.course_evaluation_id == ev.id)).one()
    token = login(client, "rachel@msu.example")
    assert f'href="/review/evaluations/{ev.id}"' in client.get(report).text  # 심사관 → 심사 건
    client.post(
        f"/review/appeals/{appeal.id}",
        data={"action": "dismiss", "note": "원 판정의 근거가 충분해요", "csrf_token": token},
    )
    login(client, "jiwon@student.example")
    page = client.get("/student/appeals").text
    assert "기각" in page and "원 판정의 근거가 충분해요" in page and "원 판정이 그대로 유지돼요" in page
    login(client, "senior@student.example")  # 다른 학생에게는 보이지 않는다
    assert "MATH 101 Calculus" not in client.get("/student/appeals").text
    login(client, "rachel@msu.example")
    assert client.get("/student/appeals").status_code == 403


def test_appeal_form_with_evidence_files(client: TestClient, seeded: Session, fake_storage: FakeStorage) -> None:
    """이의 신청 작성 화면: 원 판정 요약, 근거 자료 첨부, 내려받기 권한, 삭제 요청 시 함께 삭제 (FR-23·FR-13)."""
    ev, prof, token = professor_for(client, seeded, "calculus.txt")
    reject(client, ev, token)

    token = login(client, "jiwon@student.example")
    form = f"/student/evaluations/{ev.id}/appeal"
    assert form in client.get(f"/student/evaluations/{ev.id}").text  # 과목 결과에서 작성 화면으로
    page = client.get(form).text
    assert "이의 신청 작성" in page and "이의를 신청할 판정" in page and "불인정" in page
    assert 'name="files"' in page and 'enctype="multipart/form-data"' in page

    reason = "미분과 적분의 응용까지 15주 동안 배웠고 강의 노트와 시험지로 증명할 수 있어요."
    pdf = demo_pdf("calculus.txt")
    png = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 8, 8), False).tobytes("png")
    r = client.post(
        form,
        data={"reason": reason, "csrf_token": token},
        files=[("files", ("notes.exe", b"MZ", "application/octet-stream"))],
    )
    assert r.status_code == 422 and reason in r.text  # 실패해도 적은 사유가 남는다
    assert not seeded.scalars(select(Appeal).where(Appeal.course_evaluation_id == ev.id)).all()
    r = client.post(
        form,
        data={"reason": reason, "csrf_token": token},
        files=[("files", (f"note{i}.pdf", pdf, "application/pdf")) for i in range(4)],
    )
    assert r.status_code == 422 and "3개까지" in r.text

    r = client.post(
        form,
        data={"reason": reason, "csrf_token": token},
        files=[
            ("files", ("강의노트.pdf", pdf, "application/pdf")),
            ("files", ("시험지.png", png, "image/png")),
        ],
        follow_redirects=False,
    )
    assert r.status_code == 303 and r.headers["location"] == "/student/appeals"
    seeded.expire_all()
    appeal = seeded.scalars(select(Appeal).where(Appeal.course_evaluation_id == ev.id)).one()
    files = seeded.scalars(select(AppealFile).where(AppealFile.appeal_id == appeal.id).order_by(AppealFile.id)).all()
    assert [f.original_filename for f in files] == ["강의노트.pdf", "시험지.png"]
    assert all(f.file_key and f.file_key.startswith("appeals/") for f in files)
    page = client.get("/student/appeals").text
    assert "이의 신청을 접수했어요" in page and "강의노트.pdf" in page
    assert "이미 처리 중인 이의 신청" in client.get(form).text  # 작성 화면 대신 안내

    url = f"/appeal-files/{files[0].id}"
    r = client.get(url)
    assert r.status_code == 200 and r.content == pdf
    assert r.headers["content-type"] == "application/pdf" and "attachment" in r.headers["content-disposition"]
    assert r.headers["cache-control"] == "no-store"

    login(client, "rachel@msu.example")
    assert url in client.get("/review/appeals").text
    assert client.get(url).status_code == 200
    login(client, prof.email)
    assert url in client.get(f"/professor/evaluations/{ev.id}").text
    assert client.get(url).status_code == 200
    login(client, "senior@student.example")
    assert client.get(url).status_code == 403  # 다른 학생
    assert client.get(f"/student/evaluations/{ev.id}/appeal").status_code in (403, 404)

    # 열람할 때마다 감사 로그 (권한 없는 시도는 남지 않음), 관리자 감사 로그에 표시
    seeded.expire_all()
    views = seeded.scalars(
        select(AuditLog).where(AuditLog.action == "appeal_file.download").order_by(AuditLog.id)
    ).all()
    viewers = seeded.scalars(select(User).where(User.id.in_([v.actor_id for v in views]))).all()
    assert len(views) == 3 and {u.email for u in viewers} == {"jiwon@student.example", "rachel@msu.example", prof.email}
    assert all(v.target_id == str(files[0].id) and v.payload_json["appeal"] == appeal.id for v in views)
    assert "강의노트" not in str([v.payload_json for v in views])  # 파일 이름은 남기지 않는다
    login(client, "admin@msu.example")
    assert "이의 신청 근거 자료 열람" in client.get("/admin/stats").text  # 관리자 콘솔 최근 감사 로그
    assert "appeal_file.download" in client.get("/admin/audit").text

    # 개인정보 삭제 요청이 승인되면 근거 자료 원본도 지운다
    token = login(client, "jiwon@student.example")
    client.post(f"/student/requests/{ev.transfer_request_id}/delete-documents", data={"csrf_token": token})
    privacy = seeded.scalars(
        select(PrivacyRequest).where(PrivacyRequest.transfer_request_id == ev.transfer_request_id)
    ).one()
    token = login(client, "rachel@msu.example")
    client.post(f"/review/privacy/{privacy.id}", data={"csrf_token": token})
    token = login(client, "admin@msu.example")
    client.post(f"/admin/privacy/{privacy.id}", data={"csrf_token": token})
    assert not any(k.startswith("appeals/") for k in fake_storage.objects)
    seeded.expire_all()
    assert all(f.file_key is None for f in seeded.scalars(select(AppealFile)).all())
    login(client, "jiwon@student.example")
    assert client.get(url).status_code == 404
    assert "(삭제됨)" in client.get("/student/appeals").text
