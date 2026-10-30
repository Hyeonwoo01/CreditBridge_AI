"""AI 근거 품질: 인용 수 기록, 교수의 근거 맞음·틀림, 운영 통계의 프롬프트 버전별 지표."""

import re

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import EvidenceFeedback, EvidenceSpan
from tests.conftest import login
from tests.integration.test_workflow import professor_for


def test_professor_marks_evidence_and_stats_show_quality(client: TestClient, seeded: Session) -> None:
    ev, prof, token = professor_for(client, seeded, "calculus.txt")
    seeded.refresh(ev)
    assert ev.quotes_total and ev.quotes_total > 0  # 새로 AI를 불렀으니 인용 수가 남는다
    assert ev.quotes_unmatched is not None and ev.quotes_non_teaching is not None

    page = client.get(f"/professor/evaluations/{ev.id}").text
    span_ids = [int(n) for n in re.findall(rf"/professor/evaluations/{ev.id}/evidence/(\d+)", page)]
    assert span_ids and 'aria-pressed="true"' not in page
    assert "다룬 주차: 학생" in page  # 데모 강의계획서는 주차 계획이 있어 근거 주차 수를 보여 준다
    first, second = sorted(set(span_ids))[:2]

    r = client.post(
        f"/professor/evaluations/{ev.id}/evidence/{first}",
        data={"verdict": "correct", "csrf_token": token},
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200 and f'id="fb-{first}"' in r.text and 'aria-pressed="true"' in r.text
    # 마음을 바꾸면 같은 행을 고친다
    client.post(f"/professor/evaluations/{ev.id}/evidence/{first}", data={"verdict": "wrong", "csrf_token": token})
    r = client.post(
        f"/professor/evaluations/{ev.id}/evidence/{second}",
        data={"verdict": "correct", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303
    seeded.expire_all()
    rows = seeded.scalars(select(EvidenceFeedback).where(EvidenceFeedback.user_id == prof.id)).all()
    assert sorted((f.evidence_span_id, f.verdict) for f in rows) == [(first, "wrong"), (second, "correct")]
    assert page.count("fb-") > 0 and "border-reject/20" in client.get(f"/professor/evaluations/{ev.id}").text

    # 잘못된 값·다른 분석의 구절·CSRF 없음은 막는다
    assert (
        client.post(
            f"/professor/evaluations/{ev.id}/evidence/{first}", data={"verdict": "maybe", "csrf_token": token}
        ).status_code
        == 404
    )
    other = seeded.scalars(select(EvidenceSpan).where(EvidenceSpan.course_evaluation_id != ev.id)).first()
    if other is not None:
        assert (
            client.post(
                f"/professor/evaluations/{ev.id}/evidence/{other.id}", data={"verdict": "correct", "csrf_token": token}
            ).status_code
            == 404
        )
    assert (
        client.post(f"/professor/evaluations/{ev.id}/evidence/{first}", data={"verdict": "correct"}).status_code == 403
    )

    # 학생·심사관 화면에는 버튼이 없고, 누를 수도 없다
    student_token = login(client, "jiwon@student.example")
    assert "/evidence/" not in client.get(f"/student/evaluations/{ev.id}").text
    assert (
        client.post(
            f"/professor/evaluations/{ev.id}/evidence/{first}", data={"verdict": "correct", "csrf_token": student_token}
        ).status_code
        == 403
    )

    login(client, "rachel@msu.example")
    stats = client.get("/review/stats").text
    assert "AI 근거 품질" in stats and "evaluation-v3" in stats
    assert "50%" in stats and "1/2건" in stats  # 교수가 확인한 근거 2개 중 맞음 1개
