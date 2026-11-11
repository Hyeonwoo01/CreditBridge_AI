"""증거 출처·진위·적용 학기 (리뷰 v3 P0-5)."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Decision, Notification, Syllabus, TranscriptEntry
from tests.conftest import login
from tests.integration.test_workflow import professor_for


def test_suspicious_evidence_holds_decision_and_status_is_recorded(client: TestClient, seeded: Session) -> None:
    ev, prof, _ = professor_for(client, seeded, "calculus.txt")
    syllabus = seeded.get(Syllabus, ev.syllabus_id)
    assert syllabus is not None and syllabus.source_kind == "student_uploaded" and syllabus.authenticity == "unverified"
    # 실제 수강 학기 (성적표 줄)
    entry = TranscriptEntry(
        transfer_request_id=ev.transfer_request_id, syllabus_id=syllabus.id, title="Calculus", term="2024 Fall"
    )
    seeded.add(entry)
    seeded.commit()

    token = login(client, "rachel@msu.example")
    page = client.get(f"/review/evaluations/{ev.id}").text
    assert "증거 상태" in page and "학생 제출" in page and "진위 미확인" in page
    url = f"/review/evaluations/{ev.id}/evidence-status"
    base = {"source_kind": "student_uploaded", "academic_term": "2023-2", "csrf_token": token}
    r = client.post(url, data={**base, "authenticity": "verified"})
    assert "확인 방법을 적어" in r.text  # 확인 방법 없이 '확인됨'은 안 됨
    r = client.post(url, data={**base, "authenticity": "suspicious"})
    assert "이유를 메모로" in r.text
    r = client.post(url, data={**base, "authenticity": "suspicious", "verification_note": "서식이 출신 대학 것과 다름"})
    assert "증거 상태를 저장했어요" in r.text
    seeded.expire_all()
    syllabus = seeded.get(Syllabus, ev.syllabus_id)
    assert syllabus is not None and syllabus.authenticity == "suspicious" and syllabus.applicability == "mismatch"
    student_note = seeded.scalars(select(Notification).where(Notification.kind == "evidence")).one()
    assert "서식" not in student_note.message  # 내부 메모는 학생 알림에 나가지 않는다

    # 진위 검토 중이면 판정 보류 (자동 불인정 아님)
    token = login(client, prof.email)
    r = client.post(f"/professor/evaluations/{ev.id}/decision", data={"action": "approve", "csrf_token": token})
    assert r.status_code == 422 and "진위를 검토하고 있어" in r.text
    assert seeded.scalars(select(Decision).where(Decision.course_evaluation_id == ev.id)).first() is None

    # 학생: 불이익이 아니라는 안내, 내부 메모는 안 보임, 다른 학기 자료 안내는 진위 안내가 우선
    login(client, "jiwon@student.example")
    page = client.get(f"/student/evaluations/{ev.id}").text
    assert "불이익으로 바로 이어지지 않아요" in page and "서식이 출신 대학" not in page

    # 확인되면 판정 가능, 판정에 증거 상태가 남는다
    token = login(client, "rachel@msu.example")
    client.post(
        url,
        data={
            **base,
            "academic_term": "2024-2",
            "authenticity": "verified",
            "verification_method": "출신 대학 포털과 대조",
            "csrf_token": token,
        },
    )
    token = login(client, prof.email)
    client.post(f"/professor/evaluations/{ev.id}/decision", data={"action": "approve", "csrf_token": token})
    seeded.expire_all()
    decision = seeded.scalars(select(Decision).where(Decision.course_evaluation_id == ev.id)).one()
    snap = decision.evidence_snapshot or {}
    assert (
        snap["authenticity"] == "verified"
        and snap["applicability"] == "applicable"
        and snap["taken_term"] == "2024 Fall"
    )

    # 학생·교수는 증거 상태를 바꿀 수 없다
    r = client.post(
        url,
        data={**base, "authenticity": "verified", "verification_method": "x", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303, 403)


def test_same_file_hash_does_not_copy_verification(client: TestClient, seeded: Session) -> None:
    ev, _, _ = professor_for(client, seeded, "calculus.txt")
    first = seeded.get(Syllabus, ev.syllabus_id)
    assert first is not None
    first.authenticity, first.source_kind = "verified", "registrar_issued"
    seeded.commit()
    ev2, _, _ = professor_for(client, seeded, "calculus.txt")  # 같은 파일을 다른 요청에 다시 올림
    seeded.expire_all()
    second = seeded.get(Syllabus, ev2.syllabus_id)
    assert second is not None and second.id != first.id and second.content_hash == first.content_hash
    assert (
        second.authenticity == "unverified" and second.source_kind == "student_uploaded"
    )  # 해시만으로 공식 문서가 되지 않음
    refs = seeded.scalars(select(Syllabus).where(Syllabus.transfer_request_id.is_(None))).all()
    assert refs and all(s.source_kind == "institution_reference" for s in refs)
