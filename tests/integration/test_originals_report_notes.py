"""FR-25 원본 PDF 페이지로 이동, 판정 근거 리포트 PDF 내려받기, 심사 건 내부 메모."""

import re

import pymupdf
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import AuditLog, EvaluationNote, PrivacyRequest, Syllabus
from scripts.make_demo_pdfs import LINES_PER_PAGE, text_to_pdf
from tests.conftest import demo_text, login
from tests.integration.test_review_extras import approve
from tests.integration.test_workflow import professor_for

# 1쪽은 표지(과목 코드와 안내문)만, 미적분 강의계획서 본문은 2쪽부터 시작하는 PDF
COVER = "MATH 101 Calculus I\n" + "\n".join(f"Course packet notice {i}" for i in range(LINES_PER_PAGE - 1)) + "\n"


def calculus_on_page_two(client: TestClient, db: Session):  # type: ignore[no-untyped-def]
    pdf = text_to_pdf(COVER + demo_text("calculus.txt"))
    return professor_for(client, db, "calculus.pdf", pdf)


def test_evidence_links_open_original_pdf_page(client: TestClient, seeded: Session) -> None:
    ev, prof, _ = calculus_on_page_two(client, seeded)
    syllabus = seeded.get(Syllabus, ev.syllabus_id)
    assert syllabus is not None and syllabus.page_offsets and len(syllabus.page_offsets) >= 3

    page = client.get(f"/professor/evaluations/{ev.id}").text
    pages = {int(n) for n in re.findall(rf"/evaluations/{ev.id}/original/source#page=(\d+)", page)}
    assert pages and min(pages) >= 2  # 근거 구절은 모두 2쪽부터
    assert "원본 2쪽" in page or "원본 3쪽" in page
    assert "원본 파일(calculus.pdf)" in page

    r = client.get(f"/evaluations/{ev.id}/original/source")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"].startswith("inline") and r.headers["cache-control"] == "no-store"
    assert pymupdf.open("pdf", r.content).page_count == len(syllabus.page_offsets) - 1
    seeded.expire_all()
    views = seeded.scalars(select(AuditLog).where(AuditLog.action == "syllabus.original_view")).all()
    assert len(views) == 1 and views[0].actor_id == prof.id and "calculus" not in str(views[0].payload_json)
    # 시드의 기준 강의계획서는 텍스트로만 등록돼 원본 파일이 없다
    assert client.get(f"/evaluations/{ev.id}/original/target").status_code == 404
    assert client.get(f"/evaluations/{ev.id}/original/other").status_code == 404

    login(client, "jiwon@student.example")  # 학생 본인은 열 수 있다
    assert client.get(f"/evaluations/{ev.id}/original/source").status_code == 200
    login(client, "senior@student.example")
    assert client.get(f"/evaluations/{ev.id}/original/source").status_code == 403
    login(client, "admin@msu.example")
    assert client.get(f"/evaluations/{ev.id}/original/source").status_code == 403


def test_report_pdf_download(client: TestClient, seeded: Session) -> None:
    ev, _, token = calculus_on_page_two(client, seeded)
    client.post(f"/evaluations/{ev.id}/notes", data={"body": "학과장 확인 완료", "csrf_token": token})
    approve(client, ev, token)

    login(client, "jiwon@student.example")
    assert f'href="/evaluations/{ev.id}/report.pdf"' in client.get(f"/evaluations/{ev.id}/report").text
    r = client.get(f"/evaluations/{ev.id}/report.pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"] == f'attachment; filename="creditbridge-report-MATH101-{ev.id}.pdf"'
    assert r.headers["cache-control"] == "no-store"
    doc = pymupdf.open("pdf", r.content)
    text = "".join(p.get_text() for p in doc)
    assert "판정 근거 리포트" in text and "MATH 101" in text and "직접 인정" in text
    assert "개념별 근거" in text and re.search(r"원본 \d+쪽", text)
    assert "UTC" in text and "최종 판정은 학과 교수" in text
    assert "학과장 확인 완료" not in text  # 내부 메모는 리포트에 넣지 않는다
    assert "Lee Jiwon" not in text and "2022104455" not in text

    login(client, "senior@student.example")
    assert client.get(f"/evaluations/{ev.id}/report.pdf").status_code == 403
    login(client, "admin@msu.example")
    assert client.get(f"/evaluations/{ev.id}/report.pdf").status_code == 403


def test_internal_notes_for_staff_only(client: TestClient, seeded: Session, fake_storage) -> None:  # type: ignore[no-untyped-def]
    ev, prof, token = professor_for(client, seeded, "calculus.txt")
    r = client.post(
        f"/evaluations/{ev.id}/notes", data={"body": "실험 시수 자료를 다시 받기로 함", "csrf_token": token}
    )
    assert r.status_code == 200 and "메모를 남겼어요" in r.text and "실험 시수 자료를 다시 받기로 함" in r.text
    assert "내부 메모" in r.text and prof.name in r.text
    assert (
        "메모 내용을 적어 주세요"
        in client.post(f"/evaluations/{ev.id}/notes", data={"body": "   ", "csrf_token": token}).text
    )
    assert (
        "1000자까지" in client.post(f"/evaluations/{ev.id}/notes", data={"body": "가" * 1001, "csrf_token": token}).text
    )

    token = login(client, "rachel@msu.example")
    page = client.get(f"/review/evaluations/{ev.id}").text
    assert "실험 시수 자료를 다시 받기로 함" in page and "심사관과 담당 교수만 봐요" in page
    r = client.post(f"/evaluations/{ev.id}/notes", data={"body": "학과장 확인 중", "csrf_token": token})
    assert r.url.path == f"/review/evaluations/{ev.id}" and "학과장 확인 중" in r.text

    seeded.expire_all()
    audit = seeded.scalars(select(AuditLog).where(AuditLog.action == "note.create")).all()
    assert len(audit) == 2 and all("학과장" not in str(a.payload_json) for a in audit)  # 내용은 남기지 않는다

    token = login(client, "jiwon@student.example")
    assert "학과장 확인 중" not in client.get(f"/student/evaluations/{ev.id}").text
    assert "학과장 확인 중" not in client.get(f"/evaluations/{ev.id}/report").text
    r = client.post(f"/evaluations/{ev.id}/notes", data={"body": "인정해 주세요", "csrf_token": token})
    assert r.status_code == 403
    token = login(client, "admin@msu.example")
    assert client.post(f"/evaluations/{ev.id}/notes", data={"body": "x", "csrf_token": token}).status_code == 403

    # 개인정보 삭제 요청이 승인되면 문서와 함께 메모도 지운다
    token = login(client, "jiwon@student.example")
    client.post(f"/student/requests/{ev.transfer_request_id}/delete-documents", data={"csrf_token": token})
    privacy = seeded.scalars(select(PrivacyRequest)).one()
    token = login(client, "rachel@msu.example")
    client.post(f"/review/privacy/{privacy.id}", data={"csrf_token": token})
    token = login(client, "admin@msu.example")
    client.post(f"/admin/privacy/{privacy.id}", data={"csrf_token": token})
    seeded.expire_all()
    assert not seeded.scalars(select(EvaluationNote)).all()
    syllabus = seeded.get(Syllabus, ev.syllabus_id)
    assert syllabus is not None and syllabus.page_offsets is None
    login(client, "rachel@msu.example")
    assert client.get(f"/evaluations/{ev.id}/original/source").status_code == 404


def test_backfill_page_offsets_for_older_uploads(client: TestClient, seeded: Session, fake_storage) -> None:  # type: ignore[no-untyped-def]
    from backend.services.analysis import backfill_page_offsets

    ev, _, _ = calculus_on_page_two(client, seeded)
    syllabus = seeded.get(Syllabus, ev.syllabus_id)
    assert syllabus is not None
    expected = list(syllabus.page_offsets or [])
    syllabus.page_offsets = None  # 0007 이전 업로드처럼
    seeded.commit()

    assert backfill_page_offsets(seeded, fake_storage) == (1, 0)
    seeded.expire_all()
    assert seeded.get(Syllabus, ev.syllabus_id).page_offsets == expected  # type: ignore[union-attr]
    assert backfill_page_offsets(seeded, fake_storage) == (0, 0)  # 이미 채운 문서는 다시 보지 않는다
