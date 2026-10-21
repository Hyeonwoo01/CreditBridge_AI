"""학생 대시보드(할 일·서류 준비율), 역할별 메뉴 숫자 배지, 선배 인정 사례."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Appeal
from scripts.make_demo_pdfs import text_to_pdf
from tests.conftest import login
from tests.integration.test_pipeline import latest, new_request, upload
from tests.integration.test_review_extras import approve, reject
from tests.integration.test_workflow import assign, professor_for, reviewer_of, submitted_request

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
    assert "채워야 할 서류 2건 </span>2</span>" in home and "!2" not in home  # 배지는 숫자만

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
    reject(client, ev, token)  # 직접 인정은 이의 신청을 받지 않아 불인정으로 확정

    token = login(client, "jiwon@student.example")
    home = client.get("/student").text
    assert "새 판정 결과 1건" in home and "새 판정 결과 확인" in home
    assert "새 판정 결과 1건" in client.get("/student/appeals").text  # 모든 학생 화면의 메뉴에
    client.get(f"/student/evaluations/{ev.id}")  # 결과를 열어 보면 배지가 사라진다
    home = client.get("/student").text
    assert "새 판정 결과" not in home
    assert "이의 신청할 수 있는 과목 1개" in home  # 이의 신청 메뉴의 중립 숫자 배지

    reason = "미분과 적분의 응용까지 15주 동안 배웠고 강의 노트와 시험지로 증명할 수 있어요."
    client.post(f"/student/evaluations/{ev.id}/appeal", data={"reason": reason, "csrf_token": token})
    assert "이의 신청할 수 있는 과목" not in client.get("/student").text  # 처리 중이면 셀 대상이 아님
    appeal = seeded.scalars(select(Appeal).where(Appeal.course_evaluation_id == ev.id)).one()
    token = login(client, "rachel@msu.example")
    client.post(f"/review/appeals/{appeal.id}", data={"action": "dismiss", "note": "근거 충분", "csrf_token": token})

    login(client, "jiwon@student.example")
    assert "새 이의 신청 결과 1건" in client.get("/student").text
    assert "기각" in client.get("/student/appeals").text
    home = client.get("/student").text
    assert "새 이의 신청 결과" not in home
    assert "이의 신청할 수 있는 과목" not in home  # 과목당 한 번: 기각된 과목은 다시 셈하지 않는다


def test_precedents_show_only_institution_equivalency_table(client: TestClient, seeded: Session) -> None:
    ev, _, token = professor_for(client, seeded, "calculus.txt")
    approve(client, ev, token)  # 다른 학생의 확정 판정은 사례로 보이지 않는다

    login(client, "senior@student.example")
    page = client.get("/student/precedents").text
    assert "선배 인정 사례" in page and "MATH 101 Calculus I" not in page
    assert "동등 과목표에 아직 이 대학 과목이 없어요" in page

    token = login(client, "rachel@msu.example")
    assert client.get("/student/precedents").status_code == 403
    csv = (
        "source_institution,source_course,target_course,result,decided_on,note\n"
        "Hankuk University (한국대학교),CHEM 110 General Chemistry,,선택 인정,2021-02-01,내부 메모\n"
        "Hankuk University (한국대학교),CHEM 110 General Chemistry,,선택 인정,2023-03-02,\n"
        "Hankuk University (한국대학교),MATH 101,,불인정,2019-08-30,구 교육과정\n"
    )
    client.post(
        "/review/equivalencies", files={"file": ("eq.csv", csv.encode(), "text/csv")}, data={"csrf_token": token}
    )
    login(client, "senior@student.example")
    page = client.get("/student/precedents").text
    assert page.count("CHEM 110 General Chemistry") == 1 and "2023-03-02" in page  # 같은 기준은 한 줄, 최근 날짜
    assert "선택 인정" in page and "불인정" in page
    assert "내부 메모" not in page and "구 교육과정" not in page  # 기관 메모는 보여 주지 않는다
    assert "MATH 1151" not in page  # 확정 판정에서 온 행 없음
    page = client.get("/student/precedents?q=chem").text
    assert "CHEM 110" in page and ">MATH 101<" not in page


def test_staff_nav_badges_count_their_own_work(client: TestClient, seeded: Session) -> None:
    """교수·심사관·관리자 메뉴 숫자 배지: 기관 전체가 아니라 그 사람이 처리할 일만."""
    from backend.models import PrivacyRequest, User
    from backend.services import institution_data

    rid = submitted_request(client, seeded, "linear_algebra_sparse.txt")  # 정보 부족이라 자동 배정되지 않는다
    ev = latest(seeded, "linear_algebra_sparse.txt", rid)
    token = login(client, "rachel@msu.example")
    page = client.get("/review").text
    assert "교수 배정이 필요한 과목 1개" in page
    assert "교수 배정이 필요한 과목 1개" in client.get("/notifications").text  # 공용 화면의 메뉴에도
    assign(client, ev)
    assert "교수 배정이 필요한 과목" not in client.get("/review").text

    prof = reviewer_of(seeded, ev)
    token = login(client, prof.email)
    assert "판정할 심사 1건" in client.get("/professor").text
    r = client.post(  # 정보 부족 건은 그대로 승인할 수 없어 사유를 골라 반려한다
        f"/professor/evaluations/{ev.id}/decision",
        data={"action": "reject", "reason_codes": ["weeks_insufficient"], "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text
    assert "판정할 심사" not in client.get("/professor").text

    token = login(client, "jiwon@student.example")
    reason = "미분과 적분의 응용까지 15주 동안 배웠고 강의 노트와 시험지로 증명할 수 있어요."
    client.post(f"/student/evaluations/{ev.id}/appeal", data={"reason": reason, "csrf_token": token})
    client.post(f"/student/requests/{rid}/delete-documents", data={"csrf_token": token})

    token = login(client, "rachel@msu.example")
    page = client.get("/review").text
    assert "처리할 이의 신청 1건" in page and "처리할 삭제 요청 1건" in page
    privacy = seeded.scalars(select(PrivacyRequest).where(PrivacyRequest.transfer_request_id == rid)).one()
    client.post(f"/review/privacy/{privacy.id}", data={"csrf_token": token})
    assert "처리할 삭제 요청" not in client.get("/review").text

    login(client, "admin@msu.example")
    page = client.get("/admin/stats").text
    assert "승인할 삭제 요청 1건" in page
    admin = seeded.scalars(select(User).where(User.email == "admin@msu.example")).one()
    overview = institution_data.overview(seeded, admin)
    setup = overview.missing_reference + len(overview.departments_without_professor)
    assert (f"준비가 필요한 항목 {setup}건" in page) == (setup > 0)


def test_progress_marks_only_the_next_step_as_current(client: TestClient, seeded: Session) -> None:
    """분석이 끝났지만 심사 요청 전: '최종 확정'이 진행 중으로 보이면 안 된다 (다음 할 일은 심사 요청)."""
    token = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, token)
    upload(client, rid, token, "calculus.txt")
    page = client.get(f"/student/requests/{rid}").text
    aside = page[page.index('aria-label="심사 진행 현황"') :]
    assert "진행 중" not in aside.split("</ol>")[0]
    assert "학사처에 심사를 요청하면 시작돼요" in aside

    client.post(f"/student/requests/{rid}/submit", data={"csrf_token": token})
    steps = client.get(f"/student/requests/{rid}").text
    steps = steps[steps.index('aria-label="심사 진행 현황"') :].split("</ol>")[0]
    assert steps.count("진행 중") == 1 and steps.index("진행 중") < steps.index("최종 확정")  # 학과 교수 심사가 진행 중


def test_total_merges_requests_and_counts_same_course_once(client: TestClient, seeded: Session) -> None:
    """맨 위 전체 합계: 요청을 합치되 같은 과목은 한 번만, 문서 삭제로 종료된 요청은 빼고.
    남은 학기는 합계에만 (요청 카드에는 없음)."""
    from backend.models import TransferRequest

    token = login(client, "jiwon@student.example")
    assert "전체 합계" not in client.get("/student").text  # 과목이 없으면 숨김

    first = new_request(client, seeded, token)
    upload(client, first, token, "calculus.txt", "korean_history.txt")
    second = new_request(client, seeded, token)
    assert second != first
    upload(client, second, token, "calculus.txt", "data_structures.txt")

    def total_and_cards() -> tuple[str, str]:
        home = client.get("/student").text
        split = home.index('aria-label="편입 요청 목록"')
        return home[home.index('id="total-title"') : split], home[split:]

    total, cards = total_and_cards()
    assert "편입 요청 2건을 합친 예상치예요" in total
    assert "/ 3과목" in total and "남은 학기(예상)" in total  # 미적분학은 두 요청에 있어도 한 번
    assert "예상 인정 학점" in cards and "판정 확정" in cards and "남은 학기" not in cards

    request = seeded.get(TransferRequest, first)
    assert request is not None
    request.status = "closed"  # 문서 삭제 승인으로 종료된 요청 (절차는 test_privacy_close)
    seeded.commit()
    total, cards = total_and_cards()
    assert "편입 요청 1건을 합친 예상치예요" in total and "/ 2과목" in total  # 한국사는 빠진다
    assert "문서 삭제로 종료" in cards  # 카드는 그대로 보인다
