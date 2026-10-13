"""강의계획서 구조화 추출 스키마 (FR-03). 원문에 없는 값은 비워둔다 (FR-04)."""

from pydantic import BaseModel, Field


class WeeklyTopic(BaseModel):
    week: int | None = Field(description="Week number as written in the syllabus, or null if not numbered")
    label: str = Field(description="Original label such as 'Week 3' or 'Weeks 3-4'")
    topic: str = Field(description="Topic text copied from the syllabus")


class SyllabusExtraction(BaseModel):
    course_title: str = Field(description="Course title, empty string if not stated")
    course_code: str = Field(description="Course code, empty string if not stated")
    credits: float | None = Field(description="Credit hours/units, null if not stated")
    contact_hours: str | None = Field(description="Weekly contact hours as written, null if not stated")
    learning_outcomes: list[str] = Field(description="Learning outcomes/objectives copied from the syllabus")
    weekly_topics: list[WeeklyTopic] = Field(description="Week-by-week schedule in order")
    textbooks: list[str] = Field(description="Required or recommended textbooks")
    prerequisites: list[str] = Field(description="Prerequisite or corequisite courses")
    assessment: list[str] = Field(description="Grading components with weights as written")

    def missing_fields(self) -> list[str]:
        """기재 없음으로 표시할 필드 (FR-04)."""
        checks = {
            "learning_outcomes": bool(self.learning_outcomes),
            "weekly_topics": bool(self.weekly_topics),
            "textbooks": bool(self.textbooks),
            "prerequisites": bool(self.prerequisites),
            "assessment": bool(self.assessment),
            "credits": self.credits is not None,
        }
        return [name for name, present in checks.items() if not present]
