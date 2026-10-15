from pydantic import BaseModel, Field


class PageTranscription(BaseModel):
    text: str = Field(description="All text on the page in reading order, line breaks preserved")
    legibility: float = Field(ge=0, le=1, description="0-1 how legible the page was")
