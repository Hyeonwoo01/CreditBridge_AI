"""계정 성적표: 학생은 처음 들어오면 성적표부터 올리고, 한 번 올린 성적표를 모든 편입 요청이 함께 쓴다.
새로 올리면 아직 제출하지 않은 요청에만 반영되고, 요청 문서를 삭제해도 계정 성적표는 남는다."""

from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.models import PrivacyRequest, StudentTranscript, TranscriptEntry, TransferRequest, User
from tests.conftest import login, send_transcript
from tests.integration.test_pipeline import new_request, upload

TRANSCRIPT = (
    "Hankuk University Official Transcript\nName: Lee Jiwon\nStudent ID: 2022104455\n"
    "MATH 101 | Calculus I | 3 | A\nCSE 204 | Data Structures | 3 | B+\n"
)


def entries_of(db: Session, request_id: int) -> dict[str, TranscriptEntry]:
    db.expire_all()
    stmt = select(TranscriptEntry).where(TranscriptEntry.transfer_request_id == request_id)
    return {e.title: e for e in db.scalars(stmt)}


def without_transcript(db: Session, email: str) -> None:
    student = db.scalars(select(User).where(User.email == email)).one()
    db.execute(delete(StudentTranscript).where(StudentTranscript.student_id == student.id))
    db.commit()


def test_first_visit_asks_for_transcript_then_requests_reuse_it(client: TestClient, seeded: Session) -> None:
    without_transcript(seeded, "jiwon@student.example")
    token = login(client, "jiwon@student.example")
    r = client.get("/student", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/student/transcript"
    page = client.get("/student/transcript").text
    assert "편입 요청을 만들기 전에 성적표를 먼저 올려 주세요" in page and "성적표 올리기" in page
    assert "새 요청 만들기" not in page  # 요청은 학생이 만들지 않고 성적표에서 자동으로 생긴다

    r = send_transcript(client, token, TRANSCRIPT)
    assert r.headers["location"] == "/student"  # 처음 올리면 홈으로
    page = client.get("/student/transcript").text
    assert "Calculus I" in page and "과목 2개" in page and "성적표 바꾸기" in page

    first = new_request(client, seeded, token)  # 새 요청에 계정 성적표가 복사된다
    assert set(entries_of(seeded, first)) == {"Calculus I", "Data Structures"}
    upload(client, first, token, "calculus.txt")
    assert entries_of(seeded, first)["Calculus I"].syllabus_id is not None  # 강의계획서 분석 뒤 자동 연결
    page = client.get(f"/student/requests/{first}").text
    assert (
        "계정에 올린 성적표를 이 요청에 쓰고 있어요" in page
        and 'action="/student/requests/' + str(first) + '/transcript"' not in page
    )
    assert "성적표 올리기" not in client.get("/student").text


def test_new_transcript_applies_only_to_drafts(client: TestClient, seeded: Session) -> None:
    token = login(client, "jiwon@student.example")
    send_transcript(client, token, TRANSCRIPT)
    submitted = new_request(client, seeded, token)
    upload(client, submitted, token, "calculus.txt")
    client.post(f"/student/requests/{submitted}/submit", data={"csrf_token": token})
    draft = new_request(client, seeded, token)
    upload(client, draft, token, "data_structures.txt")

    send_transcript(client, token, TRANSCRIPT.replace("| 3 | A\n", "| 3 | B\n"))
    assert entries_of(seeded, draft)["Calculus I"].grade == "B"
    assert entries_of(seeded, submitted)["Calculus I"].grade == "A"  # 제출한 요청은 그때의 성적표 그대로

    # 제출한 요청은 성적표 연결도 바꿀 수 없다
    entry = entries_of(seeded, submitted)["Data Structures"]
    r = client.post(f"/student/requests/{submitted}/entries/{entry.id}", data={"syllabus_id": "", "csrf_token": token})
    assert "심사에 제출한 요청은 성적표 연결을 바꿀 수 없어요" in r.text
    assert "심사를 요청할 때의 성적표와 연결로 심사해요" in client.get(f"/student/requests/{submitted}").text


def test_submit_needs_transcript_on_request(client: TestClient, seeded: Session) -> None:
    token = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, token)
    upload(client, rid, token, "calculus.txt")
    request = seeded.get(TransferRequest, rid)
    assert request is not None
    request.transcript_copied_at = None  # 예: 계정 성적표가 아직 분석 중이라 복사되지 않음
    seeded.commit()
    r = client.post(f"/student/requests/{rid}/submit", data={"csrf_token": token})
    assert "성적표를 먼저 올려 주세요" in r.text
    seeded.expire_all()
    assert seeded.get(TransferRequest, rid).status == "draft"  # type: ignore[union-attr]


def test_document_deletion_keeps_account_transcript(client: TestClient, seeded: Session) -> None:
    token = login(client, "jiwon@student.example")
    send_transcript(client, token, TRANSCRIPT)
    rid = new_request(client, seeded, token)
    upload(client, rid, token, "calculus.txt")
    client.post(f"/student/requests/{rid}/submit", data={"csrf_token": token})
    client.post(f"/student/requests/{rid}/delete-documents", data={"csrf_token": token})
    token = login(client, "admin@msu.example")
    privacy = seeded.scalars(select(PrivacyRequest).where(PrivacyRequest.transfer_request_id == rid)).one()
    client.post(f"/admin/privacy/{privacy.id}", data={"csrf_token": token})

    assert entries_of(seeded, rid) == {}  # 요청의 사본은 지운다
    student = seeded.scalars(select(User).where(User.email == "jiwon@student.example")).one()
    transcript = seeded.scalars(select(StudentTranscript).where(StudentTranscript.student_id == student.id)).one()
    assert transcript.file_key and transcript.lines  # 계정 성적표는 남는다
    token = login(client, "jiwon@student.example")
    again = new_request(client, seeded, token)
    assert set(entries_of(seeded, again)) == {"Calculus I", "Data Structures"}
