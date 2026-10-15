"""학생 대시보드(할 일·서류 준비율), 메뉴 상태 배지, 선배 인정 사례."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Appeal
from scripts.make_demo_pdfs import text_to_pdf
from tests.conftest import login
from tests.integration.test_pipeline import new_request, upload
from tests.integration.test_review_extras import approve
from tests.integration.test_workflow import professor_for

TRANSCRIPT = (
    "Hankuk University Official Transcript\nName: Lee Jiwon\nStudent ID: 2022104455\n"
    "MATH 101 | Calculus I | 3 | A\nCSE 204 | Data Structures | 3 | B+\n | Academic Writing | 2 | A\n"
)


def test_dashboard_lists_todos_and_readiness(client: TestClient, seeded: Session) -> None:
    token = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, token)
    home = client.get("/student").text
    assert "할 일" in home and "성적표 올리기" in home and "강의계획서 올리기" in home
    assert '서류 준비 <strong class="tabular-nums">0%</strong>' in home
    assert "채워야 할 서류 2건" in home  # 메뉴 배지(앰버)와 카드

    upload(client, rid, token, "calculus.txt", "data_structures.txt")
    client.post(
        f"/student/requests/{rid}/transcript",
        files={"file": ("transcript.pdf", text_to_pdf(TRANSCRIPT), "application/pdf")},
        data={"csrf_token": token},
    )
    home = client.get("/student").text
    assert "성적표 올리기" not in home
    assert "성적표 과목 연결 확인 1건" in home or "강의계획서 미등록 1건" in home  # Academic Writing
    assert f'href="/student/requests/{rid}#transcript"' in home or f'href="/student/requests/{rid}#upload"' in home
    assert "75%" in home  # 성적표 1 + 과목 3개 중 2개 연결
    assert "예상 인정 학점" in home and "판정 확정" in home
    assert "학사처에 심사 요청하기" not in home  # 채울 서류가 남아 있으면 제출 안내를 하지 않는다

    # 강의계획서 없이 확인하면(인정 신청하지 않는 과목) 준비 완료
    from backend.models import TranscriptEntry

    entry = seeded.scalars(
        select(TranscriptEntry).where(
            TranscriptEntry.transfer_request_id == rid, TranscriptEntry.link_confirmed.is_(False)
        )
    ).one()
    client.post(f"/student/requests/{rid}/entries/{entry.id}", data={"syllabus_id": "", "csrf_token": token})
    home = client.get("/student").text
    assert "100%" in home and "제출할 준비가 됐어요" in home
    assert f'href="/student/requests/{rid}#submit"' in home and "학사처에 심사 요청하기" in home
    assert "채워야 할 서류" not in home


def test_nav_badges_for_new_results_clear_when_viewed(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    approve(client, ev, token)

    token = login(client, "jiwon@student.example")
    home = client.get("/student").text
    assert "새 판정 결과 1건" in home and "새 판정 결과 확인" in home
    assert "새 판정 결과 1건" in client.get("/student/appeals").text  # 모든 학생 화면의 메뉴에
    client.get(f"/student/evaluations/{ev.id}")  # 결과를 열어 보면 배지가 사라진다
    assert "새 판정 결과" not in client.get("/student").text

    reason = "미분과 적분의 응용까지 15주 동안 배웠고 강의 노트와 시험지로 증명할 수 있어요."
    client.post(f"/student/evaluations/{ev.id}/appeal", data={"reason": reason, "csrf_token": token})
    appeal = seeded.scalars(select(Appeal).where(Appeal.course_evaluation_id == ev.id)).one()
    token = login(client, "rachel@msu.example")
    client.post(f"/review/appeals/{appeal.id}", data={"action": "dismiss", "note": "근거 충분", "csrf_token": token})

    login(client, "jiwon@student.example")
    assert "새 이의 신청 결과 1건" in client.get("/student").text
    assert "기각" in client.get("/student/appeals").text
    assert "새 이의 신청 결과" not in client.get("/student").text


def test_precedents_show_counts_without_who(client: TestClient, seeded: Session) -> None:
    ev, prof, token = professor_for(client, seeded, "calculus.txt")
    approve(client, ev, token)

    login(client, "senior@student.example")  # 다른 학생도 과목 단위 사례는 볼 수 있다
    page = client.get("/student/precedents").text
    assert "선배 인정 사례" in page and "MATH 101" in page and '판정 <span class="tabular-nums">1</span>건' in page
    assert "직접 인정" in page
    assert "Lee" not in page and "jiwon" not in page and prof.name not in page  # 누가 받았는지·판정자 없음
    assert "MATH 101" not in client.get("/student/precedents?q=chemistry").text
    assert "MATH 101" in client.get("/student/precedents?q=math").text

    token = login(client, "rachel@msu.example")
    assert client.get("/student/precedents").status_code == 403
    csv = (
        "source_institution,source_course,target_course,result,decided_on,note\n"
        "Hankuk University (한국대학교),CHEM 110 General Chemistry,,선택 인정,2021-02-01,내부 메모\n"
    )
    client.post(
        "/review/equivalencies", files={"file": ("eq.csv", csv.encode(), "text/csv")}, data={"csrf_token": token}
    )
    login(client, "senior@student.example")
    page = client.get("/student/precedents?q=chem").text
    assert "CHEM 110 General Chemistry" in page and "동등 과목표" in page and "2021-02" in page
    assert "선택 인정" in page and "내부 메모" not in page  # 기관 메모는 보여 주지 않는다
