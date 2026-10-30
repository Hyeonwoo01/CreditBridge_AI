"""공개 데모용 예시 AI (Settings.demo_mode). Claude API를 부르지 않는다. 테스트 대역(tests/fakes.py)도 이것을 쓴다."""

import json
import re
from typing import cast

from pydantic import BaseModel

from backend.ai.llm_client import Effort, LLMClient, LLMResult
from backend.errors import LLMError
from backend.schemas.evaluation import CandidateJudgment, ConceptJudgment, EvaluationOutput
from backend.schemas.extraction import SyllabusExtraction, WeeklyTopic
from backend.schemas.transcript import TranscriptExtraction, TranscriptLine
from backend.schemas.transcription import PageTranscription

STOP = {
    "the",
    "and",
    "of",
    "a",
    "an",
    "to",
    "in",
    "for",
    "with",
    "on",
    "as",
    "by",
    "its",
    "their",
    "using",
    "use",
    "week",
    "including",
    "introduction",
    "basic",
    "applied",
    "problems",
    "functions",
    "function",
    "theory",
}
UNVERIFIABLE_QUOTE = "Students will master quantum chromodynamics in week 3."


def tokens(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z][a-z'\-]+", text.lower()):
        w = w.strip("'-")
        if w.endswith("s") and len(w) > 4:
            w = w[:-1]
        if w not in STOP and len(w) > 2:
            out.add(w)
    return out


def _block(prompt: str, tag: str) -> str:
    """마지막 <tag>…</tag> 블록. 지시문 속 태그 언급이 아니라 실제 데이터 블록을 읽는다."""
    start = prompt.rfind(f"<{tag}")
    end = prompt.rfind(f"</{tag}>")
    if start < 0 or end < start:
        return ""
    body = prompt[prompt.index(">", start) + 1 : end]
    return body.strip("\n")


def _section(lines: list[str], header: str) -> list[str]:
    out: list[str] = []
    capture = False
    for line in lines:
        if re.match(r"^[A-Z][A-Za-z ]+$", line.strip()) and len(line.strip()) < 30:
            capture = line.strip().lower().startswith(header)
            continue
        if capture and line.strip():
            out.append(line.strip())
    return out


class DemoLLM(LLMClient):
    """Claude를 부르지 않고 프롬프트 종류에 맞는 그럴듯한 구조화 출력을 만든다 (공개 데모·테스트용).

    추출은 강의계획서 글의 "Week N:" 줄·과목 코드·학점을 읽고, 개념 비교는 기준 개념과 학생 강의계획서 줄의
    낱말이 얼마나 겹치는지로 다룸/부분/없음을 정한다. 실제 판단이 아니므로 데모 화면에서만 쓴다.
    첫 개념에는 원문에 없는 구절을 하나 섞어, 근거 검증(backend/ai/evidence.py)이 걸러내는 모습을 보여 준다."""

    MODEL = "demo-ai"
    REASON = "예시 AI 판단: 학생 강의계획서 구절과 기준 개념의 낱말이 겹치는 정도로 정했어요."
    REASON_EN = "Example AI judgment: based on word overlap between the student syllabus and the reference concept."
    SUMMARY = "예시 AI 요약이에요. 실제 서비스에서는 AI(Claude 또는 GPT)가 개념별 근거를 읽고 요약해요."
    SUMMARY_EN = (
        "Example AI summary. In the real service, the AI (Claude or GPT) reads the evidence for each concept "
        "and sums it up."
    )

    def __init__(self) -> None:  # Claude 클라이언트를 만들지 않는다
        self._model = self.MODEL
        self._fallback = False

    def parse[T: BaseModel](
        self,
        prompt: str,
        output_model: type[T],
        *,
        images: list[bytes] | None = None,
        effort: Effort = "medium",
        max_tokens: int = 16000,
    ) -> LLMResult[T]:
        out: BaseModel
        if output_model is SyllabusExtraction:
            out = self._extract(_block(prompt, "syllabus"))
        elif output_model is EvaluationOutput:
            out = self._evaluate(prompt)
        elif output_model is TranscriptExtraction:
            out = self._transcript(_block(prompt, "transcript"))
        elif output_model is PageTranscription:
            out = PageTranscription(text="Week 1: Limits and continuity\nWeek 2: Derivatives", legibility=0.9)
        else:
            raise LLMError(f"demo AI has no output for {output_model.__name__}")
        return LLMResult(output=cast(T, out), model=self.model)

    @classmethod
    def _extract(cls, text: str) -> SyllabusExtraction:
        lines = [line.rstrip() for line in text.splitlines()]
        code_line = next((ln for ln in lines[:6] if re.search(r"\b[A-Z]{2,7}\s?\d{3,4}\b", ln)), "")
        code = re.search(r"\b[A-Z]{2,7}\s?\d{3,4}\b", code_line)
        credits = re.search(r"(\d+(?:\.\d)?)\s*(?:\(|credits?\b)|Credits:\s*(\d+(?:\.\d)?)", text)
        weeks = []
        for ln in lines:
            m = re.match(r"^Week (\d+):\s*(.+)$", ln.strip())
            if m:
                weeks.append(WeeklyTopic(week=int(m.group(1)), label=f"Week {m.group(1)}", topic=m.group(2)))
        outcomes = [re.sub(r"^\d+\.\s*", "", ln) for ln in _section(lines, "learning outcome")]
        return SyllabusExtraction(
            course_title=code_line[code.end() :].strip() if code else "",
            course_code=code.group(0) if code else "",
            credits=float(credits.group(1) or credits.group(2)) if credits else None,
            contact_hours=None,
            learning_outcomes=outcomes,
            weekly_topics=weeks,
            textbooks=_section(lines, "textbook")[:1],
            prerequisites=_section(lines, "prerequisite")[:1],
            assessment=_section(lines, "assessment") or _section(lines, "grading"),
            disciplines=cls._disciplines(code.group(0) if code else ""),
        )

    @staticmethod
    def _disciplines(code: str) -> list[str]:
        prefix = code.split(" ")[0] if code else ""
        return {
            "MATH": ["Mathematics"],
            "CSE": ["Computer Science"],
            "PHY": ["Physics"],
            "CHEM": ["Chemistry"],
            "HIS": ["History"],
            "BUS": ["Business"],
        }.get(prefix, [])

    def _evaluate(self, prompt: str) -> EvaluationOutput:
        student = _block(prompt, "student_syllabus")
        student_lines = [ln.strip() for ln in student.splitlines() if len(ln.strip()) > 8]
        week_lines = [ln for ln in student_lines if ln.startswith("Week ")]
        thin = len(week_lines) < 4
        candidates = []
        for raw in re.findall(r"<candidate>\n(.*?)\n</candidate>", _block(prompt, "catalog_candidates"), re.S):
            header = json.loads(raw.split("\n", 1)[0])
            reference = _block(raw, "reference_syllabus")
            ref_lines = [ln for ln in reference.splitlines() if ln.startswith("Week ")]
            concepts = []
            for i, name in enumerate(header["concepts"]):
                ref_line = ref_lines[i] if i < len(ref_lines) else ""
                ref_sentence = ref_line.split(": ", 1)[-1]
                want = tokens(name) | tokens(ref_sentence)
                best, best_score = "", 0.0
                for ln in student_lines:
                    score = len(want & tokens(ln)) / max(len(want), 1)
                    if score > best_score:
                        best, best_score = ln, score
                if thin:
                    status, coverage = "unclear", 0
                elif best_score >= 0.34:
                    status, coverage = "taught", 90
                elif best_score >= 0.18:
                    status, coverage = "partial", 50
                else:
                    status, coverage = "not_taught", 0
                quotes = [best] if status in ("taught", "partial") else []
                if i == 0 and quotes:
                    quotes.append(UNVERIFIABLE_QUOTE)  # 원문에 없는 구절 — 근거 검증에서 걸러진다
                concepts.append(
                    ConceptJudgment(
                        concept=name,
                        status=status,
                        coverage=coverage,
                        source_quotes=quotes,
                        target_quotes=[ref_sentence] if ref_sentence else [],
                        reason=self.REASON,
                        reason_en=self.REASON_EN,
                    )
                )
            avg = sum(c.coverage for c in concepts) / max(len(concepts), 1)
            title_overlap = len(tokens(header.get("title", "")) & tokens(student))
            if avg >= 15 or thin:
                level = "lower" if header["course_code"] == "MATH 1050" else "same"
                candidates.append(
                    (
                        (avg, title_overlap),
                        CandidateJudgment(
                            course_code=header["course_code"],
                            level=level,
                            level_note="",
                            level_note_en="",
                            concepts=concepts,
                            summary=self.SUMMARY,
                            summary_en=self.SUMMARY_EN,
                        ),
                    )
                )
        candidates.sort(key=lambda p: p[0], reverse=True)
        chosen = [c for _, c in candidates[:3]]
        if thin:
            chosen = chosen[:1]
        return EvaluationOutput(
            candidates=chosen,
            no_match_reason="" if chosen else "대응 과목이 없어요.",
            no_match_reason_en="" if chosen else "No equivalent course.",
            elective_eligible=True,
            missing_materials=["주차별 상세 강의 계획", "고유값 단원 강의 노트"] if thin else [],
            missing_materials_en=["Detailed weekly course plan", "Lecture notes for the eigenvalue unit"]
            if thin
            else [],
        )

    @staticmethod
    def _transcript(text: str) -> TranscriptExtraction:
        entries = []
        for ln in text.splitlines():
            parts = [p.strip() for p in ln.split("|")]
            if len(parts) == 4 and re.match(r"^\d", parts[2]):
                entries.append(
                    TranscriptLine(
                        code=parts[0] or None, title=parts[1], credits=float(parts[2]), grade=parts[3], term=None
                    )
                )
        return TranscriptExtraction(entries=entries)
