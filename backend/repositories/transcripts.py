from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import StudentTranscript


def for_student(session: Session, student_id: int) -> StudentTranscript | None:
    return session.scalars(select(StudentTranscript).where(StudentTranscript.student_id == student_id)).first()


def add(session: Session, transcript: StudentTranscript) -> StudentTranscript:
    session.add(transcript)
    session.flush()
    return transcript
