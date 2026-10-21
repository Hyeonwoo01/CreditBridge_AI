"""성적표 성적이 인정 최저 성적(C 이상·P/PASS/S) 미달인 과목은 교수 심사 없이 제외한다.
판정 기록은 만들지 않고(최종 판정은 사람만), 배정·심사 큐·예상 인정 학점에서 뺀다."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Decision, TransferRequest
from backend.repositories import evaluations as evaluation_repo
from backend.services.student import grade_failed
from scripts.make_demo_pdfs import text_to_pdf
from tests.conftest import login
from tests.integration.test_pipeline import latest, new_request, upload
from tests.integration.test_review_extras import notes_for
from tests.integration.test_workflow import reviewer_of


def transcript(calculus_grade: str) -> bytes:
    return text_to_pdf(
        "Hankuk University Official Transcript\nName: Lee Jiwon\nStudent ID: 2022104455\n"
        f"MATH 101 | Calculus I | 3 | {calculus_grade}\nCSE 204 | Data Structures | 3 | B+\n"
    )


def send_transcript(client: TestClient, rid: int, token: str, calculus_grade: str) -> None:
    client.post(
        f"/student/requests/{rid}/transcript",
        files={"file": ("transcript.pdf", transcript(calculus_grade), "application/pdf")},
        data={"csrf_token": token},
    )


def test_grade_rule_passes_c_and_above() -> None:
    assert not grade_failed(None) and not grade_failed("C") and not grade_failed(" c0 ") and not grade_failed("P")
    assert not grade_failed("C+") and not grade_failed("B-")
    assert grade_failed("C-") and grade_failed("D+") and grade_failed("F")


def test_failing_course_is_excluded_from_review(client: TestClient, seeded: Session) -> None:
    token = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, token)
    upload(client, rid, token, "calculus.txt", "data_structures.txt")
    send_transcript(client, rid, token, "C-")
    calc = latest(seeded, "calculus.txt", rid)

    page = client.get(f"/student/requests/{rid}").text
    assert "성적 기준 미달" in page and "성적이 C 미만(C- 이하)이라 인정 대상이 아니에요" in page
    assert "성적이 C 미만" in client.get(f"/student/evaluations/{calc.id}").text

    client.post(f"/student/requests/{rid}/submit", data={"csrf_token": token})
    seeded.expire_all()
    assert evaluation_repo.active_assignment(seeded, calc.id) is None  # 자동 배정하지 않는다
    structures = latest(seeded, "data_structures.txt", rid)
    assert evaluation_repo.active_assignment(seeded, structures.id) is not None
    assert not seeded.scalars(select(Decision).where(Decision.course_evaluation_id == calc.id)).all()

    token = login(client, "rachel@msu.example")
    board = client.get("/review?tab=all").text
    assert f'/review/evaluations/{calc.id}"' not in board  # 심사 큐에도 없다
    r = client.post(f"/review/evaluations/{calc.id}/assign", data={"reviewer_id": 1, "csrf_token": token})
    assert "판정 전인 소속 기관 심사 건만 배정할 수 있어요" in r.text


def test_request_is_decided_when_only_failing_courses_remain(client: TestClient, seeded: Session) -> None:
    token = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, token)
    upload(client, rid, token, "calculus.txt")
    send_transcript(client, rid, token, "F")
    client.post(f"/student/requests/{rid}/submit", data={"csrf_token": token})
    seeded.expire_all()
    assert seeded.get(TransferRequest, rid).status == "decided"  # type: ignore[union-attr]


def test_transcript_after_submit_releases_assignment(client: TestClient, seeded: Session) -> None:
    """성적표를 심사 요청 뒤에 올려 미달이 되면 이미 된 배정을 풀고 담당 교수에게 알린다."""
    token = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, token)
    upload(client, rid, token, "calculus.txt", "data_structures.txt")
    client.post(f"/student/requests/{rid}/submit", data={"csrf_token": token})
    calc = latest(seeded, "calculus.txt", rid)
    prof = reviewer_of(seeded, calc)

    send_transcript(client, rid, token, "D")
    seeded.expire_all()
    assert evaluation_repo.active_assignment(seeded, calc.id) is None
    assert any("성적 기준 미달로 심사 대상에서 빠져" in m for m in notes_for(seeded, prof.email))
    login(client, prof.email)
    assert f"/professor/evaluations/{calc.id}" not in client.get("/professor").text
    structures = latest(seeded, "data_structures.txt", rid)
    assert evaluation_repo.active_assignment(seeded, structures.id) is not None  # B+ 과목은 그대로
