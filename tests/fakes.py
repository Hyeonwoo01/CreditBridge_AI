"""테스트용 대역: Claude, S3. 외부 API는 테스트에서 호출하지 않는다 (실제 호출은 tests/eval)."""

import json
import re
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from backend.ai.llm_client import LLMResult
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
FABRICATED_QUOTE = "Students will master quantum chromodynamics in week 3."


def tokens(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z][a-z'\-]+", text.lower()):
        w = w.strip("'-")
        if w.endswith("s") and len(w) > 4:
            w = w[:-1]
        if w not in STOP and len(w) > 2:
            out.add(w)
    return out


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    @staticmethod
    def new_key(kind: str, filename: str) -> str:
        return f"{kind}/{uuid4()}/{filename}"

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = data

    def get(self, key: str) -> bytes:
        return self.objects[key]

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)


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


class FakeLLM:
    """프롬프트 종류에 맞는 그럴듯한 구조화 출력을 만든다. 보낸 프롬프트는 calls에 남는다."""

    model = "fake-claude"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.fail_with: Exception | None = None

    def parse(self, prompt: str, output_model: type[BaseModel], **kwargs: Any) -> LLMResult[Any]:
        self.calls.append((output_model.__name__, prompt))
        if self.fail_with:
            raise self.fail_with
        if output_model is SyllabusExtraction:
            out: BaseModel = self._extract(_block(prompt, "syllabus"))
        elif output_model is EvaluationOutput:
            out = self._evaluate(prompt)
        elif output_model is TranscriptExtraction:
            out = self._transcript(_block(prompt, "transcript"))
        elif output_model is PageTranscription:
            out = PageTranscription(text="Week 1: Limits and continuity\nWeek 2: Derivatives", legibility=0.9)
        else:
            raise AssertionError(f"unexpected output model {output_model}")
        return LLMResult(output=out, model=self.model)

    def prompts(self, kind: str) -> list[str]:
        return [p for k, p in self.calls if k == kind]

    @staticmethod
    def _extract(text: str) -> SyllabusExtraction:
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
            disciplines=FakeLLM._disciplines(code.group(0) if code else ""),
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

    @staticmethod
    def _evaluate(prompt: str) -> EvaluationOutput:
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
                    quotes.append(FABRICATED_QUOTE)  # 원문에 없는 구절 — 검증에서 걸러져야 한다
                concepts.append(
                    ConceptJudgment(
                        concept=name,
                        status=status,
                        coverage=coverage,
                        source_quotes=quotes,
                        target_quotes=[ref_sentence] if ref_sentence else [],
                        reason="테스트 판단",
                        reason_en="Test judgment",
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
                            summary="요약",
                            summary_en="Summary",
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
