"""coverage_json에 저장하고 화면에 그리는 분석 결과 구조."""

from pydantic import BaseModel


class EvidenceView(BaseModel):
    side: str
    text: str
    char_start: int
    char_end: int


class ConceptResult(BaseModel):
    concept: str
    status: str
    coverage: float  # 0~1, 근거 검증 반영 후
    reason: str
    verified: bool
    source_evidence: list[EvidenceView]
    target_evidence: list[EvidenceView]


class CandidateResult(BaseModel):
    course_id: int
    course_code: str
    course_title: str
    credits: float
    level: str
    level_note: str
    summary: str
    coverage: float  # 개념 평균 0~1
    concepts: list[ConceptResult]


class EvaluationResult(BaseModel):
    candidates: list[CandidateResult]
    missing_fields: list[str]
    missing_concepts: list[str]
    missing_materials: list[str]
    warnings: list[str]
    no_match_reason: str
    injection_flags: list[str]
