"""AI 분석 파이프라인: 문서 추출 → 구조화 → 학과 필터로 후보 선정 → Claude 개념별 비교 → 근거 검증 → 추천.

Celery 작업(backend/workers/tasks.py)이 호출한다. 웹 요청 안에서 직접 부르지 않는다.
같은 원본(content_hash)은 이미 추출한 결과를, 같은 비교 입력은 이미 낸 판정을 재사용해 LLM을 다시 부르지 않는다.
"""

import hashlib
import logging
from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from backend.ai import candidates as candidate_filter
from backend.ai import injection, matching
from backend.ai.extraction import build_chunks, extract_syllabus
from backend.ai.llm_client import LLMClient
from backend.ai.prompts_loader import load_prompt
from backend.documents import text as doc_text
from backend.documents.storage import ObjectStorage
from backend.errors import LLMError
from backend.i18n import N_
from backend.models import CourseEvaluation, EvidenceSpan, Syllabus, SyllabusChunk, TranscriptEntry
from backend.models.enums import EvaluationStatus, Recommendation, SyllabusStatus
from backend.repositories import catalog as catalog_repo
from backend.repositories import decisions as decision_repo
from backend.repositories import evaluations as evaluation_repo
from backend.repositories import requests as request_repo
from backend.repositories import syllabi as syllabus_repo
from backend.schemas.extraction import SyllabusExtraction
from backend.schemas.results import CandidateResult, EvaluationResult
from backend.schemas.transcript import TranscriptExtraction
from backend.schemas.transcription import PageTranscription
from backend.security.masking import mask_pii
from backend.services import scoring

logger = logging.getLogger(__name__)

AUTO_LINK_SCORE = 0.85
# 저장하는 글은 한국어 원문 그대로 두고 화면에서 번역한다 (backend/i18n.py N_, translate_stored)
DEFAULT_MISSING_MATERIALS = [N_("주차별 상세 강의 계획"), N_("교재 목차(다룬 장 표시)"), N_("시험지 또는 과제 샘플")]


def content_hash(*parts: bytes) -> str:
    """업로드 원본의 SHA-256. 보완 자료가 붙으면 이전 해시와 새 파일을 이어 다시 계산한다."""
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part)
    return digest.hexdigest()


# ---------- 문서 → 텍스트 ----------


@dataclass
class DocumentText:
    text: str
    quality: float  # 인식 품질 점수 0~1
    page_offsets: list[int]  # 원본 파일 페이지 위치표 (documents.text.join_pages)


def document_to_text(llm: LLMClient, data: bytes, filename: str) -> DocumentText:
    """텍스트·인식 품질 점수·페이지 위치표. 스캔 페이지는 Claude가 전사해 원래 페이지 자리에 넣는다."""
    doc = doc_text.extract(data, filename)
    if not doc.scanned_pages:
        text, offsets = doc_text.join_pages(doc.pages)
        return DocumentText(text, doc.quality, offsets)
    prompt = load_prompt("transcription").render()
    pages = list(doc.pages)
    legibility = []
    for number, page in zip(doc.scanned_index, doc.scanned_pages, strict=True):
        result = llm.parse(prompt, PageTranscription, images=[page], effort="low")
        pages[number] = result.output.text
        legibility.append(result.output.legibility)
    scanned_share = len(doc.scanned_pages) / max(len(doc.scanned_pages) + (1 if doc.text.strip() else 0), 1)
    quality = doc.quality + scanned_share * (sum(legibility) / len(legibility))
    text, offsets = doc_text.join_pages(pages)
    return DocumentText(text, round(min(quality, 1.0), 3), offsets)


def backfill_page_offsets(session: Session, storage: ObjectStorage) -> tuple[int, int]:
    """0007 이전에 올린 문서의 페이지 위치표를 채운다 (scripts/backfill_page_offsets.py). LLM은 부르지 않는다.

    텍스트 레이어만 있는 PDF를 다시 읽어 저장된 원문과 글자까지 같을 때만 채우고(보완 자료가 덧붙은 경우 포함),
    스캔 페이지가 있거나 원문이 달라진 문서는 건너뛴다. (채운 수, 건너뛴 수)를 돌려준다."""
    filled = skipped = 0
    for syllabus in syllabus_repo.without_page_offsets(session):
        assert syllabus.source_file_key is not None
        try:
            doc = doc_text.extract(storage.get(syllabus.source_file_key), syllabus.original_filename)
        except Exception:  # 지워졌거나 열 수 없는 파일은 건너뛴다
            skipped += 1
            continue
        text, offsets = doc_text.join_pages(doc.pages)
        if doc.scanned_pages or not (
            syllabus.raw_text == text or syllabus.raw_text.startswith(f"{text}\n\n[보완 자료: ")
        ):
            skipped += 1
            continue
        syllabus.page_offsets = offsets
        filled += 1
    session.commit()
    return filled, skipped


# ---------- 강의계획서 처리 ----------


def _reuse_extraction(session: Session, syllabus: Syllabus) -> bool:
    """같은 원본을 이미 추출했으면 텍스트·추출 결과·청크를 복사한다 (LLM 호출 없음)."""
    donor = syllabus_repo.analyzed_with_hash(session, syllabus.content_hash, exclude_id=syllabus.id)
    if donor is None:
        return False
    for attr in (
        "raw_text",
        "page_offsets",
        "quality_score",
        "injection_flags",
        "extracted_json",
        "extraction_model",
        "course_code",
        "course_title",
        "credits",
    ):
        setattr(syllabus, attr, getattr(donor, attr))
    syllabus_repo.replace_chunks(
        session,
        syllabus.id,
        [
            SyllabusChunk(
                syllabus_id=syllabus.id,
                week_no=c.week_no,
                concept=c.concept,
                text=c.text,
                char_start=c.char_start,
                char_end=c.char_end,
            )
            for c in syllabus_repo.chunks_of(session, donor.id)
        ],
    )
    return True


def _extract(session: Session, syllabus: Syllabus, llm: LLMClient, storage: ObjectStorage) -> None:
    if not syllabus.raw_text and syllabus.source_file_key:
        doc = document_to_text(llm, storage.get(syllabus.source_file_key), syllabus.original_filename)
        syllabus.raw_text = doc.text
        syllabus.quality_score = doc.quality
        syllabus.page_offsets = doc.page_offsets
    if len(syllabus.raw_text.strip()) < 40:
        raise LLMError("document has no readable text")

    flags = injection.detect(syllabus.raw_text)
    syllabus.injection_flags = [N_("{line}행: {text}").format(line=f.line_no, text=f.text) for f in flags]
    result = extract_syllabus(llm, injection.sanitize(syllabus.raw_text, flags))
    extraction = result.output
    syllabus.extracted_json = extraction.model_dump()
    syllabus.extraction_model = result.model
    syllabus.course_title = extraction.course_title[:255] or syllabus.original_filename[:255]
    syllabus.course_code = extraction.course_code[:50]
    syllabus.credits = extraction.credits
    syllabus_repo.replace_chunks(
        session,
        syllabus.id,
        [
            SyllabusChunk(
                syllabus_id=syllabus.id,
                week_no=d.week_no,
                concept=d.concept,
                text=d.text,
                char_start=d.char_start,
                char_end=d.char_end,
            )
            for d in build_chunks(syllabus.raw_text, extraction)
        ],
    )


def process_syllabus(session: Session, syllabus_id: int, *, llm: LLMClient, storage: ObjectStorage) -> None:
    syllabus = syllabus_repo.get(session, syllabus_id)
    if syllabus is None or syllabus.status == SyllabusStatus.DELETED:
        return
    syllabus.status = SyllabusStatus.PROCESSING
    session.commit()
    try:
        if syllabus.raw_text or not _reuse_extraction(session, syllabus):
            _extract(session, syllabus, llm, storage)
        syllabus.status = SyllabusStatus.READY
        syllabus.error_message = None
        session.commit()
    except LLMError as exc:
        session.rollback()
        syllabus.status = SyllabusStatus.FAILED
        syllabus.error_message = N_(
            "문서를 분석하지 못했어요. 글자를 읽을 수 있는 PDF나 이미지인지 확인한 뒤 다시 올려 주세요."
        )
        session.commit()
        logger.warning("syllabus processing failed", extra={"syllabus_id": syllabus_id, "error": type(exc).__name__})
        return

    if syllabus.transfer_request_id is not None:
        relink_transcript(session, syllabus.transfer_request_id)
        evaluate_syllabus(session, syllabus.id, llm=llm)


def add_supplement(
    session: Session, syllabus_id: int, file_key: str, *, llm: LLMClient, storage: ObjectStorage
) -> None:
    """보완 자료를 원문 뒤에 덧붙이고 다시 분석한다. 앞부분 위치가 그대로라 이전 분석의 근거 구절도 유효하다."""
    syllabus = syllabus_repo.get(session, syllabus_id)
    if syllabus is None:
        return
    filename = file_key.rsplit("/", 1)[-1]
    text = document_to_text(llm, storage.get(file_key), filename).text
    # 페이지 위치표는 원본 파일 것 그대로라 덧붙인 보완 자료 구절에는 페이지 링크가 없다
    syllabus.raw_text = f"{syllabus.raw_text}\n\n[보완 자료: {filename}]\n{text}"
    session.commit()
    process_syllabus(session, syllabus_id, llm=llm, storage=storage)


# ---------- 과목 비교 ----------


def _references(
    session: Session, target_institution_id: int, extraction: SyllabusExtraction
) -> list[matching.Reference]:
    """학과 필터로 고른 후보 과목과 각 과목의 기준 강의계획서·필수 개념."""
    courses = candidate_filter.select(catalog_repo.courses_of(session, target_institution_id), extraction.disciplines)
    concepts = syllabus_repo.reference_concepts(session, [c.id for c in courses])
    refs = []
    for course in courses:
        ref_syllabus = (
            syllabus_repo.get(session, course.reference_syllabus_id) if course.reference_syllabus_id else None
        )
        if ref_syllabus is None:
            continue
        refs.append(
            matching.Reference(
                course_id=course.id,
                code=course.code,
                title=course.title,
                credits=course.credits,
                level=course.level,
                syllabus_id=ref_syllabus.id,
                text=ref_syllabus.raw_text,
                # 학과가 과목 CSV로 정한 필수 개념이 먼저, 없으면 기준 강의계획서 청크의 개념
                concepts=list(course.concepts or []) or [c.concept for c in concepts.get(course.id, [])],
            )
        )
    return refs


def _input_hash(prompt_version: str, model: str, prompt: str) -> str:
    key = f"{prompt_version}\n{scoring.RULES_VERSION}\n{model}\n{prompt}"
    return hashlib.sha256(key.encode()).hexdigest()


def evaluate_syllabus(session: Session, syllabus_id: int, *, llm: LLMClient) -> CourseEvaluation | None:
    student = syllabus_repo.get(session, syllabus_id)
    if student is None or student.transfer_request_id is None or student.status != SyllabusStatus.READY:
        return None
    request = request_repo.get(session, student.transfer_request_id)
    extraction = SyllabusExtraction.from_stored(student.extracted_json)
    if request is None or extraction is None:
        return None

    refs = _references(session, request.target_institution_id, extraction)
    prompt, prompt_version = matching.build_prompt(
        request.target_institution.name, refs, student.credits, student.raw_text
    )
    input_hash = _input_hash(prompt_version, llm.model, prompt)

    before = evaluation_repo.latest_for_syllabus(session, student.id)
    evaluation = CourseEvaluation(
        transfer_request_id=request.id,
        syllabus_id=student.id,
        status=EvaluationStatus.RUNNING,
        input_hash=input_hash,
        prompt_version=prompt_version,
    )
    evaluation_repo.add(session, evaluation)
    # 심사 중 보완 자료로 다시 분석하면 담당 교수 배정을 새 결과로 이어 준다 (FR-22)
    if before is not None and decision_repo.for_evaluation(session, before.id) is None:
        evaluation_repo.carry_assignment(session, before.id, evaluation.id)
    session.commit()

    previous = evaluation_repo.find_by_input_hash(session, input_hash)
    if previous is not None and previous.id != evaluation.id:
        _copy_result(session, previous, evaluation)
        session.commit()
        return evaluation

    try:
        result = matching.compare(llm, prompt)
    except LLMError as exc:
        evaluation.status = EvaluationStatus.FAILED
        evaluation.error_message = N_("AI 분석에 실패했어요. 잠시 후 다시 분석을 요청해 주세요.")
        session.commit()
        logger.warning("evaluation failed", extra={"syllabus_id": syllabus_id, "error": type(exc).__name__})
        return evaluation

    output = result.output
    sparse = scoring.is_sparse(len(extraction.weekly_topics), len(extraction.learning_outcomes))
    refs_by_code = {r.code.lower(): r for r in refs}
    spans: list[matching.VerifiedSpan] = []
    scored: list[tuple[scoring.Score, CandidateResult]] = []
    for judgment in output.candidates[:3]:
        ref = refs_by_code.get(judgment.course_code.strip().lower())
        if ref is None:
            continue
        concepts, found = matching.concept_results(judgment, ref, student.raw_text, student.id)
        for c in concepts:
            c.coverage = scoring.apply_verification(c.status, c.coverage, c.verified)
        spans += found
        score = scoring.score_candidate(
            concepts, judgment.level, sparse_document=sparse, elective_eligible=output.elective_eligible
        )
        scored.append(
            (
                score,
                CandidateResult(
                    course_id=ref.course_id,
                    course_code=ref.code,
                    course_title=ref.title,
                    credits=ref.credits,
                    level=judgment.level,
                    level_note=judgment.level_note,
                    summary=judgment.summary,
                    coverage=score.coverage,
                    concepts=concepts,
                ),
            )
        )
    scored.sort(key=lambda pair: pair[0].adjusted, reverse=True)

    warnings = []
    if scored:
        best_score, best = scored[0]
        if best.level == "lower":
            warnings.append(
                best.level_note or N_("{code}보다 낮은 수준의 과목으로 판단돼요.").format(code=best.course_code)
            )
        if student.credits is not None and student.credits < best.credits:
            warnings.append(
                N_(
                    "전적 과목 {credits}학점이 {code}의 {target}학점보다 적어요. 학점 차이만큼 부분 인정될 수 있어요."
                ).format(credits=f"{student.credits:g}", code=best.course_code, target=f"{best.credits:g}")
            )
        # 커버리지가 낮으면 특정 과목으로 억지 매핑하지 않는다 (선택 인정·불인정만 추천).
        # 정보 부족이면 판단 대상 후보로 남겨 무엇을 보완할지 보여준다.
        keep = best_score.adjusted >= scoring.ELECTIVE_MIN or best_score.recommendation == Recommendation.INSUFFICIENT
        evaluation.candidate_course_id = best.course_id if keep else None
        evaluation.recommendation = best_score.recommendation
        evaluation.confidence = best_score.confidence
        evaluation.coverage = round(best_score.coverage, 3)
        evaluation.level_flag = best.level
        evaluation.summary = best.summary
        missing_concepts = best_score.missing_concepts
    else:
        if sparse:
            evaluation.recommendation = Recommendation.INSUFFICIENT
            evaluation.confidence = "low"
        else:
            evaluation.recommendation = Recommendation.ELECTIVE if output.elective_eligible else Recommendation.NONE
            evaluation.confidence = "medium"
        evaluation.summary = output.no_match_reason
        missing_concepts = []
    if student.injection_flags:
        warnings.append(N_("판정을 유도하는 의심 문구가 있어 해당 줄을 분석에서 제외했어요."))

    missing_materials = output.missing_materials or (
        DEFAULT_MISSING_MATERIALS if evaluation.recommendation == Recommendation.INSUFFICIENT else []
    )
    evaluation.coverage_json = EvaluationResult(
        candidates=[c for _, c in scored],
        missing_fields=extraction.missing_fields(),
        missing_concepts=missing_concepts,
        missing_materials=missing_materials,
        warnings=warnings,
        no_match_reason=output.no_match_reason,
        injection_flags=student.injection_flags or [],
    ).model_dump()
    evaluation.model = result.model
    evaluation.status = EvaluationStatus.DONE
    evaluation_repo.add_spans(
        session,
        [
            EvidenceSpan(
                course_evaluation_id=evaluation.id,
                side=s.side,
                syllabus_id=s.syllabus_id,
                char_start=s.start,
                char_end=s.end,
                concept=s.concept,
                verified=True,
            )
            for s in spans
        ],
    )
    session.commit()
    return evaluation


def _copy_result(session: Session, source: CourseEvaluation, target: CourseEvaluation) -> None:
    """같은 입력의 이전 결과를 그대로 재사용한다 (반복 실행 시 판정 동일, LLM 호출 없음)."""
    for attr in (
        "candidate_course_id",
        "recommendation",
        "confidence",
        "coverage",
        "level_flag",
        "coverage_json",
        "summary",
        "model",
    ):
        setattr(target, attr, getattr(source, attr))
    target.status = EvaluationStatus.DONE
    evaluation_repo.add_spans(
        session,
        [
            EvidenceSpan(
                course_evaluation_id=target.id,
                side=s.side,
                syllabus_id=s.syllabus_id if s.syllabus_id != source.syllabus_id else target.syllabus_id,
                char_start=s.char_start,
                char_end=s.char_end,
                concept=s.concept,
                verified=s.verified,
            )
            for s in evaluation_repo.spans_of(session, source.id)
        ],
    )


# ---------- 성적표 (FR-02) ----------


def _norm(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def link_score(entry: TranscriptEntry, syllabus: Syllabus) -> float:
    if entry.code and syllabus.course_code and _norm(entry.code) == _norm(syllabus.course_code):
        return 1.0
    a, b = _norm(entry.title), _norm(syllabus.course_title)
    if not a or not b:
        return 0.0
    return round(SequenceMatcher(None, a, b).ratio(), 3)


def relink_transcript(session: Session, request_id: int) -> None:
    """확인되지 않은 성적표 줄을 가장 비슷한 강의계획서에 연결한다. 불확실하면 학생 확인을 기다린다."""
    syllabi = [s for s in syllabus_repo.of_request(session, request_id) if s.status == SyllabusStatus.READY]
    for entry in request_repo.transcript_entries(session, request_id):
        if entry.link_confirmed or not syllabi:
            continue
        best = max(syllabi, key=lambda s: link_score(entry, s))
        score = link_score(entry, best)
        entry.syllabus_id = best.id if score >= 0.5 else None
        entry.link_score = score
        entry.link_confirmed = score >= AUTO_LINK_SCORE
    session.commit()


def process_transcript(session: Session, request_id: int, *, llm: LLMClient, storage: ObjectStorage) -> None:
    request = request_repo.get(session, request_id)
    if request is None or not request.transcript_file_key:
        return
    filename = request.transcript_file_key.rsplit("/", 1)[-1]
    text = document_to_text(llm, storage.get(request.transcript_file_key), filename).text
    masked = mask_pii(text)
    request.transcript_masked_name = masked.masked_name
    result = llm.parse(load_prompt("transcript").render(transcript=masked.text), TranscriptExtraction, effort="low")
    request_repo.replace_transcript_entries(
        session,
        request.id,
        [
            TranscriptEntry(
                transfer_request_id=request.id,
                title=line.title[:255],
                code=(line.code or None) and line.code[:50],
                credits=line.credits,
                grade=(line.grade or None) and line.grade[:10],
                term=(line.term or None) and line.term[:50],
            )
            for line in result.output.entries
        ],
    )
    session.commit()
    relink_transcript(session, request.id)
