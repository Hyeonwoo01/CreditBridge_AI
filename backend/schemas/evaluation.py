"""AI 과목 비교 출력 스키마. LLM 출력은 반드시 이 모델로 검증한다.

설명 글은 두 벌: 학생용 한국어(reason 등)와 교직원용 영어(reason_en 등). 화면 언어에 맞춰 고른다."""

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
    reason: str = Field(description="One short sentence in Korean, for the student")
    reason_en: str = Field(description="The same sentence in English, for faculty reviewers")


class ReviewItemFinding(BaseModel):
    """교수 체크리스트 항목이 학생 강의계획서에 적혀 있는지 (리뷰 v3 P1-1 미리 채우기). 판정이 아니라 찾은 위치만."""

    key: str = Field(description="Review item key exactly as given in the candidate's review_items")
    stated: bool = Field(description="true only if the student's syllabus explicitly states this information")
    quote: str = Field(description="One verbatim quote from the student's syllabus (< 200 chars), empty if not stated")


class CandidateJudgment(BaseModel):
    course_code: str
    level: Literal["same", "lower", "higher"]
    level_note: str = Field(description="Korean sentence explaining a level difference, empty if same")
    level_note_en: str = Field(description="The same note in English, empty if same")
    concepts: list[ConceptJudgment]
    summary: str = Field(description="One or two Korean sentences for the student")
    summary_en: str = Field(description="The same summary in English, for faculty reviewers")
    review_items: list[ReviewItemFinding] = Field(
        default_factory=list, description="One entry per review item listed for this candidate"
    )


class EvaluationOutput(BaseModel):
    candidates: list[CandidateJudgment] = Field(description="Up to 3 plausible equivalents, best first; may be empty")
    no_match_reason: str = Field(description="Korean sentence when no candidate is plausible, else empty")
    no_match_reason_en: str = Field(description="The same sentence in English, else empty")
    elective_eligible: bool = Field(
        description="true if the prior course is a college-level academic course that could count as general "
        "elective credit even without an equivalent course"
    )
    missing_materials: list[str] = Field(
        description="Korean list of documents that would let a reviewer judge unclear concepts"
    )
    missing_materials_en: list[str] = Field(
        description="The same list in English, in the same order and with the same number of items"
    )
