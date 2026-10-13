"""테스트 공통 설정. 통합 테스트는 실제 MariaDB(TEST_DATABASE_URL)에 마이그레이션을 적용해 실행한다."""

import os
import re
from collections.abc import Iterator
from pathlib import Path

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "mysql+pymysql://creditbridge:change-me@localhost:3306/creditbridge_test?charset=utf8mb4"
)
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["CLAUDE_MODEL"] = "fake-claude"
os.environ["SESSION_SECRET"] = "test-secret"
os.environ["APP_ENV"] = "test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.fakes import FakeLLM, FakeStorage

DEMO = Path(__file__).parent.parent / "scripts" / "demo_data"


@pytest.fixture(scope="session")
def migrated() -> None:
    from alembic.config import Config

    from alembic import command
    from app.db.session import engine

    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for (table,) in conn.execute(text("SHOW TABLES")).all():
            conn.execute(text(f"DROP TABLE `{table}`"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    cfg.attributes["database_url"] = os.environ["DATABASE_URL"]
    command.upgrade(cfg, "head")


@pytest.fixture
def db(migrated: None) -> Iterator[Session]:
    from app.db.session import SessionLocal, engine

    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for (table,) in conn.execute(text("SHOW TABLES")).all():
            if table != "alembic_version":
                conn.execute(text(f"TRUNCATE TABLE `{table}`"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    # 앱이 다른 연결에서 커밋한 결과를 바로 읽을 수 있게 테스트 세션은 READ COMMITTED로
    with SessionLocal(bind=engine.execution_options(isolation_level="READ COMMITTED")) as session:
        yield session


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def fake_storage() -> FakeStorage:
    return FakeStorage()


@pytest.fixture
def seeded(db: Session) -> Session:
    from scripts.seed_demo import seed

    seed(db)
    return db


@pytest.fixture
def client(
    seeded: Session,
    fake_llm: FakeLLM,
    fake_storage: FakeStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    from app.main import app
    from app.web.routes import student as student_routes
    from app.workers import tasks

    monkeypatch.setattr(tasks, "get_llm", lambda: fake_llm)
    monkeypatch.setattr(tasks, "get_storage", lambda: fake_storage)
    monkeypatch.setattr(student_routes, "get_storage", lambda: fake_storage)
    with TestClient(app) as c:
        yield c


def csrf_of(client: TestClient, path: str = "/login") -> str:
    html = client.get(path).text
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert m, f"no csrf token on {path}"
    return m.group(1)


def login(client: TestClient, email: str, password: str = "demo1234") -> str:
    client.cookies.clear()
    token = csrf_of(client)
    r = client.post("/login", data={"email": email, "password": password, "csrf_token": token}, follow_redirects=False)
    assert r.status_code == 303, r.text
    # 로그인하면 세션이 새로 만들어지므로 토큰도 새로 받는다
    return csrf_of(client, r.headers["location"])


def demo_text(name: str) -> str:
    return (DEMO / name).read_text(encoding="utf-8")


def demo_pdf(name: str, extra: str = "") -> bytes:
    """demo_data의 .txt 강의계획서를 업로드용 PDF로 (업로드는 PDF·JPG·PNG만 받는다)."""
    from scripts.make_demo_pdfs import text_to_pdf

    return text_to_pdf(demo_text(name) + extra)
