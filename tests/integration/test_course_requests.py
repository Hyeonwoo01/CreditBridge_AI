"""성적표 과목 요청: 처음 들어와 성적표를 올리면 성적이 C 이상인 과목마다 편입 요청이 자동으로 생기고,
학생은 과목마다 강의계획서를 올린다. 편입 학점 상한을 넘으면 졸업 학점에 넣을 과목을 고른다."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Institution, TranscriptEntry, TransferRequest, User
from tests.conftest import login, send_transcript
from tests.integration.test_pipeline import latest, upload

TRANSCRIPT = (
    "Hankuk University Official Transcript\nName: Lee Jiwon\nStudent ID: 2022104455\n"
    "MATH 101 | Calculus I | 3 | A\nCSE 204 | Data Structures | 3 | B+\nHIST 110 | Korean History | 3 | C-\n"
)


def course_requests(db: Session) -> dict[str, TransferRequest]:
    db.expire_all()
    student = db.scalars(select(User).where(User.email == "jiwon@student.example")).one()
    stmt = select(TransferRequest).where(
        TransferRequest.student_id == student.id, TransferRequest.course_key.is_not(None)
    )
    return {r.course_key or "": r for r in db.scalars(stmt)}


def entry_of(db: Session, request_id: int) -> TranscriptEntry:
    return db.scalars(select(TranscriptEntry).where(TranscriptEntry.transfer_request_id == request_id)).one()


def test_courses_graded_c_or_above_become_requests(client: TestClient, seeded: Session) -> None:
    token = login(client, "jiwon@student.example")
    send_transcript(client, token, TRANSCRIPT)
    found = course_requests(seeded)
    assert set(found) == {"code:MATH101", "code:CSE204"}  # C- 과목은 요청을 만들지 않는다
    page = client.get("/student/transcript").text
    assert "Korean History" in page and "C- · 성적 기준 미달" in page

    home = client.get("/student").text
    assert "새 요청 만들기" not in home
    assert "MATH 101 Calculus I" in home and "CSE 204 Data Structures" in home and "Korean History" not in home
    assert "이 과목의 강의계획서를 올려 주세요" in home
    # 할 일에는 과목마다가 아니라 한 줄로
    todo = home[home.index('id="todo-title"') : home.index('id="requests"')]
    assert "강의계획서 올리기 2과목" in todo and 'href="/student#requests"' in todo
    assert "MATH 101 강의계획서 올리기" not in todo

    math = found["code:MATH101"]
    page = client.get(f"/student/requests/{math.id}").text
    assert "이 과목의 강의계획서 올리기" in page and "성적 A" in page and " multiple " not in page
    upload(client, math.id, token, "calculus.txt")
    seeded.expire_all()
    entry = entry_of(seeded, math.id)
    assert entry.syllabus_id is not None and entry.link_confirmed  # 어느 과목인지 알므로 바로 연결
    r = upload(client, math.id, token, "data_structures.txt")
    assert "이 과목에는 강의계획서를 한 건만 올려요" in r

    # 심사 요청·자동 배정은 과목 요청마다 그대로
    r = client.post(f"/student/requests/{math.id}/submit", data={"csrf_token": token})
    assert "학과 교수에게 바로 배정됐어요" in r.text
    assert latest(seeded, "calculus.txt", math.id).recommendation == "direct"


def test_new_transcript_updates_drafts_without_duplicates(client: TestClient, seeded: Session) -> None:
    token = login(client, "jiwon@student.example")
    send_transcript(client, token, TRANSCRIPT)
    found = course_requests(seeded)
    math_id, structures_id = found["code:MATH101"].id, found["code:CSE204"].id
    upload(client, math_id, token, "calculus.txt")
    client.post(f"/student/requests/{math_id}/submit", data={"csrf_token": token})

    # 자료구조가 빠지고 미적분 성적이 바뀐 성적표: 제출한 미적분은 그대로, 강의계획서 없는 자료구조 요청은 지운다
    send_transcript(
        client, token, TRANSCRIPT.replace("| 3 | A\n", "| 3 | B\n").replace("CSE 204 | Data Structures | 3 | B+\n", "")
    )
    found = course_requests(seeded)
    assert set(found) == {"code:MATH101"} and seeded.get(TransferRequest, structures_id) is None
    assert entry_of(seeded, math_id).grade == "A"

    send_transcript(client, token, TRANSCRIPT)  # 다시 올려도 같은 과목 요청을 또 만들지 않는다
    found = course_requests(seeded)
    assert set(found) == {"code:MATH101", "code:CSE204"} and found["code:MATH101"].id == math_id


def test_transfer_cap_lets_student_choose_courses(client: TestClient, seeded: Session) -> None:
    token = login(client, "admin@msu.example")
    r = client.post("/admin/data/transfer-cap", data={"cap": "4", "csrf_token": token})
    assert "편입 학점 상한을 4학점으로 정했어요" in r.text
    msu = seeded.scalars(select(Institution).where(Institution.name == "Midwest State University")).one()
    seeded.refresh(msu)
    assert msu.max_transfer_credits == 4

    token = login(client, "jiwon@student.example")
    send_transcript(client, token, TRANSCRIPT)
    found = course_requests(seeded)
    upload(client, found["code:MATH101"].id, token, "calculus.txt")
    upload(client, found["code:CSE204"].id, token, "data_structures.txt")
    home = client.get("/student").text
    total = home[home.index('id="total-title"') : home.index('aria-label="편입 요청 목록"')]
    assert "편입 학점 상한(4학점)을 넘어요" in total and "편입 학점 상한 4학점까지만" in total
    assert "4.0 <span" in total or "~4.0" in total  # 예상 인정 학점은 상한으로 자른다

    # 자료구조를 졸업 학점에서 빼면 합계에서 빠지고, 다시 넣을 수 있다
    structures = found["code:CSE204"]
    client.post(f"/student/requests/{structures.id}/counted", data={"counted": "0", "csrf_token": token})
    seeded.expire_all()
    assert not seeded.get(TransferRequest, structures.id).counted  # type: ignore[union-attr]
    home = client.get("/student").text
    total = home[home.index('id="total-title"') : home.index('aria-label="편입 요청 목록"')]
    assert "/ 1과목" in total and "졸업 학점에서 뺌" in total and "다시 넣기" in total
    assert "졸업 학점에서 뺌" in home[home.index('aria-label="편입 요청 목록"') :]

    other = login(client, "senior@student.example")
    r = client.post(f"/student/requests/{structures.id}/counted", data={"counted": "1", "csrf_token": other})
    assert r.status_code == 403  # 다른 학생의 요청은 바꿀 수 없다


def test_document_deletion_keeps_course_card(client: TestClient, seeded: Session) -> None:
    """과목 요청의 문서를 지워도 그 과목 카드는 목록의 같은 자리에 남아 다시 제출할 수 있다."""
    from backend.models import PrivacyRequest

    token = login(client, "jiwon@student.example")
    send_transcript(client, token, TRANSCRIPT)
    found = course_requests(seeded)
    math_id = found["code:MATH101"].id
    upload(client, math_id, token, "calculus.txt")
    client.post(f"/student/requests/{math_id}/submit", data={"csrf_token": token})
    client.post(f"/student/requests/{math_id}/delete-documents", data={"csrf_token": token})
    token = login(client, "admin@msu.example")
    privacy = seeded.scalars(select(PrivacyRequest).where(PrivacyRequest.transfer_request_id == math_id)).one()
    client.post(f"/admin/privacy/{privacy.id}", data={"csrf_token": token})

    seeded.expire_all()
    assert seeded.get(TransferRequest, math_id).status == "closed"  # type: ignore[union-attr]
    fresh = course_requests(seeded)["code:MATH101"]  # 닫힌 요청 대신 같은 과목의 새 초안
    assert fresh.id != math_id and fresh.status == "draft" and entry_of(seeded, fresh.id).grade == "A"

    login(client, "jiwon@student.example")
    home = client.get("/student").text
    cards = home[home.index('aria-label="편입 요청 목록"') :]
    assert cards.index("MATH 101 Calculus I") < cards.index("CSE 204 Data Structures")  # 성적표 순서 그대로
    assert cards.index(f'href="/student/requests/{fresh.id}"') < cards.index("<details")  # 진행 중 목록에
    assert "문서 삭제로 종료된 요청 1건" in cards
    page = client.get(f"/student/requests/{math_id}").text
    assert "새 요청으로 다시 준비돼 있어요" in page
