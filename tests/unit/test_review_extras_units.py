from datetime import timedelta
from typing import Any, ClassVar

import pytest

from backend.config import Settings
from backend.db.base import utcnow
from backend.models import Notification, PrivacyRequest, User
from backend.services import csv_import, equivalencies, notifications
from backend.services.privacy import is_overdue
from backend.web.templating import highlight


def test_highlight_escapes_and_anchors_overlapping_spans() -> None:
    html = str(highlight("<a> calculus and limits", [(4, 12), (8, 16), (99, 120)], "src"))
    assert html.startswith("&lt;a&gt; ")
    assert 'id="src-4-12"' in html and 'id="src-8-16"' in html
    assert html.count("<mark>") == 1 and "src-99-120" not in html  # 겹치면 하나로, 범위 밖은 무시


def test_privacy_overdue_only_until_completed() -> None:
    now = utcnow()
    late = PrivacyRequest(status="reviewed", due_at=now - timedelta(days=1))
    done = PrivacyRequest(status="completed", due_at=now - timedelta(days=1))
    assert is_overdue(late, now) and not is_overdue(done, now)


def test_equivalency_course_key_matches_decision_key() -> None:
    assert equivalencies.course_key("MATH 101 ") == "math101"
    assert csv_import._decode("과목".encode("cp949")) == "과목"


class FakeSMTP:
    sent: ClassVar[list[Any]] = []

    def __init__(self, host: str, port: int, timeout: int) -> None:
        self.host = host

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def starttls(self) -> None:
        pass

    def login(self, user: str, password: str) -> None:
        pass

    def send_message(self, msg: Any) -> None:
        FakeSMTP.sent.append(msg)


def test_email_delivery_is_skipped_without_smtp_and_sends_with_it(monkeypatch: pytest.MonkeyPatch) -> None:
    user = User(id=1, email="prof@msu.example", name="x", role="professor", password_hash="")
    note = Notification(
        id=7, user_id=1, kind="assignment.created", message="새 심사가 배정됐어요: MATH 101", link="/professor"
    )

    class FakeSession:
        committed = False

        def commit(self) -> None:
            FakeSession.committed = True

    monkeypatch.setattr(notifications.notification_repo, "pending_email", lambda session, since: [(note, user)])
    monkeypatch.setattr(notifications.smtplib, "SMTP", FakeSMTP)
    assert notifications.deliver_pending(FakeSession(), Settings(smtp_host="")) == 0  # type: ignore[arg-type]
    assert (
        notifications.deliver_pending(FakeSession(), Settings(smtp_host="smtp.test", app_base_url="https://cb.test"))
        == 1
    )  # type: ignore[arg-type]
    msg = FakeSMTP.sent[-1]
    assert msg["To"] == "prof@msu.example" and "https://cb.test/professor" in msg.get_content()
    assert note.emailed_at is not None and FakeSession.committed
