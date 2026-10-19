"""공개 데모 모드 부품: 예시 AI, 로컬 파일 저장 (Settings.demo_mode)."""

from pathlib import Path

import pytest

from backend.ai.demo_llm import DemoLLM
from backend.documents.storage import DiskStorage
from backend.schemas.evaluation import EvaluationOutput
from backend.schemas.extraction import SyllabusExtraction


def test_disk_storage_round_trip_and_rejects_keys_outside_root(tmp_path: Path) -> None:
    storage = DiskStorage(str(tmp_path / "files"))
    key = storage.new_key("syllabi", "plan 1.pdf")
    storage.put(key, b"%PDF", "application/pdf")
    assert storage.get(key) == b"%PDF"
    storage.delete(key)
    storage.delete(key)  # 없어도 오류가 아니다
    with pytest.raises(ValueError):
        storage.put("../escape.txt", b"x", "text/plain")


def test_demo_llm_answers_without_claude_and_labels_itself() -> None:
    llm = DemoLLM()
    assert llm.model == "demo-ai"
    syllabus = "MATH 101 Calculus I\nCredits: 3\nWeek 1: Limits\nWeek 2: Derivatives\n"
    extracted = llm.parse(f"<syllabus>\n{syllabus}</syllabus>", SyllabusExtraction).output
    assert extracted.course_code == "MATH 101" and extracted.credits == 3 and len(extracted.weekly_topics) == 2
    assert extracted.disciplines == ["Mathematics"]
    empty = llm.parse("<student_syllabus>\nshort\n</student_syllabus>", EvaluationOutput).output
    assert empty.candidates == [] and "예시" not in empty.no_match_reason  # 후보가 없으면 대응 과목 없음
    assert "예시 AI" in DemoLLM.REASON and "Example AI" in DemoLLM.REASON_EN
