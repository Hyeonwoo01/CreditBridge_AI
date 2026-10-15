"""강의계획서 구조화 추출(FR-03)과 주차·개념 단위 청크 분할."""

from dataclasses import dataclass

from backend.ai.evidence import locate
from backend.ai.llm_client import LLMClient, LLMResult
from backend.ai.prompts_loader import load_prompt
from backend.schemas.extraction import SyllabusExtraction


@dataclass(frozen=True)
class ChunkDraft:
    week_no: int | None
    concept: str
    text: str
    char_start: int | None
    char_end: int | None


def extract_syllabus(llm: LLMClient, text: str) -> LLMResult[SyllabusExtraction]:
    prompt = load_prompt("extraction").render(syllabus=text)
    return llm.parse(prompt, SyllabusExtraction, effort="low")


def build_chunks(raw_text: str, extraction: SyllabusExtraction) -> list[ChunkDraft]:
    """주차 주제와 학습 목표를 청크로 만든다. 원문에서 찾은 경우 위치를 함께 저장한다."""
    drafts: list[ChunkDraft] = []
    seen: set[str] = set()
    items: list[tuple[int | None, str]] = [(w.week, w.topic) for w in extraction.weekly_topics]
    items += [(None, o) for o in extraction.learning_outcomes]
    for week, text in items:
        key = text.strip().lower()
        if len(key) < 3 or key in seen:
            continue
        seen.add(key)
        span = locate(raw_text, text)
        drafts.append(
            ChunkDraft(
                week_no=week,
                concept=text.strip()[:255],
                text=text.strip(),
                char_start=span.start if span else None,
                char_end=span.end if span else None,
            )
        )
    if not drafts and raw_text.strip():
        # 구조가 없는 문서: 원문 앞부분을 하나의 청크로
        body = raw_text.strip()[:2000]
        drafts.append(ChunkDraft(week_no=None, concept=body[:255], text=body, char_start=None, char_end=None))
    return drafts
