"""후보 과목 검색: 학생 강의계획서 청크와 대상 과목 기준 강의계획서 청크의 벡터 거리 (FR-05)."""

from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.repositories import syllabi as syllabus_repo

# 이 유사도 이상이면 대상 개념이 다뤄졌을 가능성이 있다고 본다 (bge-m3 코사인)
CONCEPT_HIT_SIMILARITY = 0.55
NEIGHBORS_PER_CHUNK = 12


@dataclass
class CandidateCourse:
    course_id: int
    score: float
    hit_concepts: set[str] = field(default_factory=set)


def find_candidates(
    session: Session, chunk_embeddings: list[list[float]], target_institution_id: int, limit: int = 5
) -> list[CandidateCourse]:
    if not chunk_embeddings:
        return []
    best_per_chunk: dict[int, list[float]] = defaultdict(list)
    concepts_hit: dict[int, set[str]] = defaultdict(set)
    for embedding in chunk_embeddings:
        best: dict[int, float] = {}
        for hit in syllabus_repo.nearest_target_chunks(session, embedding, target_institution_id, NEIGHBORS_PER_CHUNK):
            similarity = 1.0 - hit.distance
            best[hit.course_id] = max(best.get(hit.course_id, 0.0), similarity)
            if similarity >= CONCEPT_HIT_SIMILARITY:
                concepts_hit[hit.course_id].add(hit.concept)
        for course_id, similarity in best.items():
            best_per_chunk[course_id].append(similarity)

    concept_counts = {
        cid: len(chunks) for cid, chunks in syllabus_repo.reference_concepts(session, list(best_per_chunk)).items()
    }
    candidates = []
    for course_id, sims in best_per_chunk.items():
        total = max(concept_counts.get(course_id, 1), 1)
        concept_share = len(concepts_hit[course_id]) / total
        mean_similarity = sum(sims) / len(chunk_embeddings)
        candidates.append(
            CandidateCourse(
                course_id=course_id,
                score=0.6 * concept_share + 0.4 * mean_similarity,
                hit_concepts=concepts_hit[course_id],
            )
        )
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:limit]
