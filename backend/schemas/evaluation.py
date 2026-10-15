"""AI 과목 비교 출력 스키마. LLM 출력은 반드시 이 모델로 검증한다."""

from typing import Literal

from pydantic import BaseModel, Field

ConceptStatus = Literal["taught", "partial", "not_taught", "unclear"]


class ConceptJudgment(BaseModel):
    concept: str = Field(description="Target concept name exactly as given in the catalog")
    status: ConceptStatus = Field(
        description="taught: covered at comparable depth; partial: briefly or only some aspects; "
        "not_taught: clearly absent; unclear: the syllabus does not give enough detail to tell"
    )
    coverage: int = Field(ge=0, le=100, description="0-100 coverage of this concept at comparable depth")
    source_quotes: list[str] = Field(description="Verbatim quotes from the student's syllabus (each < 200 chars)")
    target_quotes: list[str] = Field(
        description="Verbatim quotes from the target reference syllabus (each < 200 chars)"
    )
    reason: str = Field(description="One short sentence in Korean")


class CandidateJudgment(BaseModel):
    course_code: str
    level: Literal["same", "lower", "higher"]
    level_note: str = Field(description="Korean sentence explaining a level difference, empty if same")
    concepts: list[ConceptJudgment]
    summary: str = Field(description="One or two Korean sentences for the student")


class EvaluationOutput(BaseModel):
    candidates: list[CandidateJudgment] = Field(description="Up to 3 plausible equivalents, best first; may be empty")
    no_match_reason: str = Field(description="Korean sentence when no candidate is plausible, else empty")
    elective_eligible: bool = Field(
        description="true if the prior course is a college-level academic course that could count as general "
        "elective credit even without an equivalent course"
    )
    missing_materials: list[str] = Field(
        description="Korean list of documents that would let a reviewer judge unclear concepts"
    )
