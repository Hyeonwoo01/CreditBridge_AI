"""강의계획서 버전 비교: 보완 자료로 다시 분석하면 바로 앞 분석과 달라진 점을 보여 준다."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import demo_pdf, login
from tests.integration.test_pipeline import latest
from tests.integration.test_workflow import professor_for


def test_supplement_reanalysis_shows_what_changed(client: TestClient, seeded: Session) -> None:
    ev, prof, token = professor_for(client, seeded, "linear_algebra_sparse.txt")
    assert "이전 분석과 달라진 점" not in client.get(f"/professor/evaluations/{ev.id}").text  # 첫 분석

    client.post(
        f"/professor/evaluations/{ev.id}/materials",
        data={"items": ["주차별 상세 강의 계획"], "note": "", "csrf_token": token},
    )
    student_token = login(client, "jiwon@student.example")
    client.post(
        f"/student/syllabi/{ev.syllabus_id}/supplement",
        files={"file": ("weekly_plan.pdf", demo_pdf("linear_algebra_detailed.txt"), "application/pdf")},
        data={"csrf_token": student_token},
    )
    new = latest(seeded, "linear_algebra_sparse.txt")
    assert new.id != ev.id

    page = client.get(f"/student/evaluations/{new.id}").text  # 학생도 본다
    assert "이전 분석과 달라진 점" in page and "보완 자료 1개 덧붙임" in page
    assert "정보 부족" in page and "직접 인정" in page and "▲ 좋아짐" in page
    assert "그 사이 덧붙인 보완 자료" in page and "weekly_plan.pdf" in page

    login(client, prof.email)
    page = client.get(f"/professor/evaluations/{new.id}").text
    assert "이전 분석과 달라진 점" in page and "개념별 변화" in page and "학생 근거 구절" in page
    # 이전 분석 화면에는 비교가 없다 (그보다 앞선 분석이 없으므로)
    login(client, "rachel@msu.example")
    assert "이전 분석과 달라진 점" not in client.get(f"/review/evaluations/{ev.id}").text
