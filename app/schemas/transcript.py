from pydantic import BaseModel, Field


class TranscriptLine(BaseModel):
    title: str
    code: str | None = Field(description="Course code if printed, else null")
    credits: float | None
    grade: str | None
    term: str | None


class TranscriptExtraction(BaseModel):
    entries: list[TranscriptLine]
