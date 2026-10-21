"""공개 데모용 예시 시나리오 (DEMO_MODE=true에서만). 실행: uv run python -m scripts.demo_scenario

데모 카탈로그·계정(scripts.seed_demo)을 넣은 뒤, 화면을 실제로 눌러 진행한 것처럼 앱 경로를 차례로 부른다.
- 학생 이지원(출신 대학·편입 전공은 계정에 정해 둠): 성적표를 올리면 성적 C 이상 과목마다 요청이 생긴다
  (C프로그래밍은 D라 제외). 미적분·선형대수(자료 부족)·자료구조·일반물리·한국사는 강의계획서를 올려 심사 요청,
  일반화학은 올리기만 한 사전 시뮬레이션
- 제출 때 정보가 충분한 과목(미적분·자료구조·일반물리)은 학과 교수에게 자동 배정, 심사관은 일괄 배정(남은 건만)과
  정보가 부족한 선형대수에 보완 자료 요청
- 교수: 미적분 승인, 자료구조는 선택 인정으로 수정 → 학생이 자료구조 판정에 이의 신청
- 일반물리는 Mike Brown 교수(데모 교수 계정)가 판정할 차례로, 한국사는 대응 과목이 없어 미배정으로 남는다
이미 요청이 있으면 아무것도 하지 않는다.
"""

import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.config import get_settings
from backend.db.session import SessionLocal
from backend.models import Assignment, CourseEvaluation, Syllabus, TransferRequest, User
from scripts.make_demo_pdfs import text_to_pdf
from scripts.seed_demo import seed

DEMO = Path(__file__).parent / "demo_data"
PASSWORD = "demo1234"
# 예시 성적표 (demo_data/transcript.txt, 예시 AI는 "코드 | 과목명 | 학점 | 성적" 줄을 읽는다).
# 과목 코드는 demo_data 강의계획서와 같고, C프로그래밍은 D라 요청이 생기지 않는다
TRANSCRIPT = (DEMO / "transcript.txt").read_text(encoding="utf-8")
# 과목 요청 키 → 올릴 강의계획서 (demo_data/*.pdf)
COURSES = {
    "code:MATH101": "calculus",
    "code:MATH201": "linear_algebra_sparse",
    "code:CSE204": "data_structures",
    "code:PHY101": "general_physics",
    "code:HIS110": "korean_history",
    "code:CHEM101": "general_chemistry",
}


def _token(html: str) -> str:
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    if not m:
        raise RuntimeError("csrf token not found")
    return m.group(1)


def _login(client: TestClient, email: str) -> str:
    client.cookies.clear()
    token = _token(client.get("/login").text)
    r = client.post("/login", data={"email": email, "password": PASSWORD, "csrf_token": token}, follow_redirects=False)
    if r.status_code != 303:
        raise RuntimeError(f"demo login failed: {email}")
    return _token(client.get(r.headers["location"]).text)


def _ok(response_status: int, step: str) -> None:
    if response_status >= 400:
        raise RuntimeError(f"demo step failed ({response_status}): {step}")


def _course_requests(email: str) -> dict[str, int]:
    """성적표를 올려 자동으로 생긴 과목 요청: 과목 키 → 요청 id."""
    with SessionLocal() as session:
        student = session.scalars(select(User.id).where(User.email == email)).one()
        rows = session.scalars(
            select(TransferRequest).where(
                TransferRequest.student_id == student, TransferRequest.course_key.is_not(None)
            )
        )
        return {r.course_key or "": r.id for r in rows}


def _upload(client: TestClient, token: str, rid: int, name: str, submit: bool) -> None:
    upload = [("files", (f"{name}.pdf", (DEMO / f"{name}.pdf").read_bytes(), "application/pdf"))]
    _ok(client.post(f"/student/requests/{rid}/syllabi", files=upload, data={"csrf_token": token}).status_code, name)
    if submit:
        _ok(client.post(f"/student/requests/{rid}/submit", data={"csrf_token": token}).status_code, f"submit {name}")


def _latest(rid: int, filename: str) -> CourseEvaluation:
    with SessionLocal() as session:
        syllabus = session.scalars(
            select(Syllabus).where(Syllabus.transfer_request_id == rid, Syllabus.original_filename == filename)
        ).one()
        return session.scalars(
            select(CourseEvaluation).where(
                CourseEvaluation.syllabus_id == syllabus.id, CourseEvaluation.is_latest.is_(True)
            )
        ).one()


def _reviewer_email(evaluation_id: int) -> str:
    with SessionLocal() as session:
        assignment = session.scalars(
            select(Assignment).where(Assignment.course_evaluation_id == evaluation_id, Assignment.is_active.is_(True))
        ).one()
        reviewer = session.get(User, assignment.reviewer_id)
        assert reviewer is not None
        return reviewer.email


def run() -> None:
    if not get_settings().demo_mode:
        sys.exit("demo_scenario는 DEMO_MODE=true일 때만 실행해요.")
    with SessionLocal() as session:
        seed(session)
        jiwon = session.scalars(select(User.id).where(User.email == "jiwon@student.example")).one()
        if session.scalars(select(TransferRequest).where(TransferRequest.student_id == jiwon)).first() is not None:
            print("demo scenario already exists")
            return

    from backend.main import app

    with TestClient(app) as client:
        token = _login(client, "jiwon@student.example")  # 처음 들어오면 성적표 화면부터
        transcript = [("file", ("transcript.pdf", text_to_pdf(TRANSCRIPT), "application/pdf"))]
        _ok(client.post("/student/transcript", files=transcript, data={"csrf_token": token}).status_code, "transcript")
        requests = _course_requests("jiwon@student.example")
        for key, name in COURSES.items():
            _upload(client, token, requests[key], name, submit=key != "code:CHEM101")
        calc, sparse, ds, physics = (
            _latest(requests[key], f"{COURSES[key]}.pdf")
            for key in ("code:MATH101", "code:MATH201", "code:CSE204", "code:PHY101")
        )

        token = _login(client, "rachel@msu.example")
        ids = [e.id for e in (calc, sparse, ds, physics)]
        _ok(client.post("/review/assign", data={"evaluation_ids": ids, "csrf_token": token}).status_code, "assign")
        _ok(
            client.post(
                f"/review/evaluations/{sparse.id}/materials",
                data={
                    "items": ["주차별 상세 강의 계획"],
                    "note": "9~12주차 고유값 단원 강의 자료",
                    "csrf_token": token,
                },
            ).status_code,
            "material request",
        )

        token = _login(client, _reviewer_email(calc.id))
        url = f"/professor/evaluations/{calc.id}/decision"
        _ok(client.post(url, data={"action": "approve", "csrf_token": token}).status_code, "approve")
        token = _login(client, _reviewer_email(ds.id))
        _ok(
            client.post(
                f"/professor/evaluations/{ds.id}/decision",
                data={
                    "action": "modify",
                    "result": "elective",
                    "reason_codes": ["level_difference"],
                    "csrf_token": token,
                },
            ).status_code,
            "modify decision",
        )

        token = _login(client, "jiwon@student.example")
        reason = "자료구조 강의에서 트리·그래프·해시까지 15주 동안 배웠고, 과제와 시험지로 증명할 수 있어요."
        _ok(
            client.post(
                f"/student/evaluations/{ds.id}/appeal", data={"reason": reason, "csrf_token": token}
            ).status_code,
            "appeal",
        )
    print(f"demo scenario ready: {len(requests)} course requests")


if __name__ == "__main__":
    run()
