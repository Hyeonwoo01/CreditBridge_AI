"""골든셋 AI 품질 평가 (테스트 명세서 6장). 실제 Claude API와 bge-m3를 호출하므로 비용이 든다.

실행: ANTHROPIC_API_KEY=... CLAUDE_MODEL=... uv run pytest tests/eval -m eval -s
지표: 오인정률(정답이 직접 인정이 아닌데 직접 인정 추천) ≤ 3%, 근거 환각 0건, 판정 일치도 ≥ 85%, 반복 실행 동일성.
"""

import json
import os
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Course, CourseEvaluation, EvidenceSpan, Institution, Syllabus, TransferRequest, User
from tests.conftest import DEMO

pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY가 없어 실제 API 평가를 건너뜀"
    ),
]

GOLDEN = json.loads((Path(__file__).parent / "golden.json").read_text(encoding="utf-8"))["cases"]


@pytest.fixture
def real_seeded(db: Session) -> Session:
    from app.ai.embedding import get_embedder
    from scripts.seed_demo import seed

    seed(db, get_embedder())
    return db


def test_golden_set(real_seeded: Session) -> None:
    from app.ai.embedding import get_embedder
    from app.ai.llm_client import LLMClient
    from app.config import Settings
    from app.services import analysis

    os.environ["CLAUDE_MODEL"] = os.environ.get("EVAL_CLAUDE_MODEL", os.environ["CLAUDE_MODEL"])
    llm = LLMClient(Settings())
    db = real_seeded
    student = db.scalars(select(User).where(User.role == "student")).first()
    src = db.scalars(select(Institution).where(Institution.is_target.is_(False))).one()
    tgt = db.scalars(select(Institution).where(Institution.is_target.is_(True))).one()
    assert student is not None
    request = TransferRequest(student_id=student.id, source_institution_id=src.id, target_institution_id=tgt.id)
    db.add(request)
    db.commit()

    agree = misgrant = negatives = hallucinated = 0
    rows = []
    for case in GOLDEN:
        syllabus = Syllabus(
            institution_id=src.id,
            transfer_request_id=request.id,
            owner_id=student.id,
            raw_text=(DEMO / case["file"]).read_text(encoding="utf-8"),
            original_filename=case["file"],
            status="uploaded",
        )
        db.add(syllabus)
        db.commit()
        analysis.process_syllabus(db, syllabus.id, llm=llm, embedder=get_embedder(), storage=None)  # type: ignore[arg-type]
        ev = db.scalars(select(CourseEvaluation).where(CourseEvaluation.syllabus_id == syllabus.id)).one()
        course = db.get(Course, ev.candidate_course_id) if ev.candidate_course_id else None
        predicted = ev.recommendation
        if case["label"] != "direct":
            negatives += 1
            misgrant += predicted == "direct"
        agree += predicted == case["label"] and (case["target"] is None or (course and course.code == case["target"]))
        for span in db.scalars(select(EvidenceSpan).where(EvidenceSpan.course_evaluation_id == ev.id)):
            source = db.get(Syllabus, span.syllabus_id)
            hallucinated += not (source and 0 <= span.char_start < span.char_end <= len(source.raw_text))
        rows.append((case["file"], case["label"], predicted, course.code if course else None, ev.probability))

    for r in rows:
        print(r)
    agreement = agree / len(GOLDEN)
    misgrant_rate = misgrant / max(negatives, 1)
    print(f"agreement={agreement:.0%} misgrant={misgrant_rate:.0%} hallucinated_spans={hallucinated}")
    assert hallucinated == 0
    assert misgrant_rate <= 0.03
    assert agreement >= 0.85
