"""공개 데모용 예시 시나리오 (DEMO_MODE=true에서만). 실행: uv run python -m scripts.demo_scenario

데모 카탈로그·계정(scripts.seed_demo)을 넣은 뒤, 화면을 실제로 눌러 진행한 것처럼 앱 경로를 차례로 부른다.
- 학생 이지원: 심사 요청 1건(미적분·선형대수(자료 부족)·자료구조·일반물리·한국사) + 사전 시뮬레이션 초안 1건
- 심사관: 학과 교수 일괄 배정, 정보가 부족한 선형대수에 보완 자료 요청
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
from backend.models import Assignment, CourseEvaluation, Institution, Syllabus, TransferRequest, User
from scripts.seed_demo import seed

DEMO = Path(__file__).parent / "demo_data"
PASSWORD = "demo1234"


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


def _request(client: TestClient, token: str, source_id: int, major: str, files: list[str], submit: bool) -> int:
    r = client.post(
        "/student/requests",
        data={"source_institution_id": source_id, "major": major, "csrf_token": token},
        follow_redirects=False,
    )
    _ok(r.status_code, "create request")
    rid = int(r.headers["location"].rsplit("/", 1)[-1])
    uploads = [("files", (f"{name}.pdf", (DEMO / f"{name}.pdf").read_bytes(), "application/pdf")) for name in files]
    _ok(
        client.post(f"/student/requests/{rid}/syllabi", files=uploads, data={"csrf_token": token}).status_code, "upload"
    )
    if submit:
        _ok(client.post(f"/student/requests/{rid}/submit", data={"csrf_token": token}).status_code, "submit")
    return rid


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
        source_id = session.scalars(select(Institution.id).where(Institution.is_target.is_(False))).one()

    from backend.main import app

    with TestClient(app) as client:
        token = _login(client, "jiwon@student.example")
        courses = ["calculus", "linear_algebra_sparse", "data_structures", "general_physics", "korean_history"]
        rid = _request(client, token, source_id, "Computer Science and Engineering", courses, submit=True)
        _request(
            client, token, source_id, "Mathematics", ["linear_algebra_detailed", "general_chemistry"], submit=False
        )
        calc, sparse, ds = (_latest(rid, f"{n}.pdf") for n in ("calculus", "linear_algebra_sparse", "data_structures"))
        physics = _latest(rid, "general_physics.pdf")

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
    print(f"demo scenario ready: request #{rid}")


if __name__ == "__main__":
    run()
