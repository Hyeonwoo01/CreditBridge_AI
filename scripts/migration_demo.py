"""마이그레이션 시험용 DB 만들기: 옛 스키마에 옛 데이터를 넣고 Alembic으로 올린다.

운영 DB가 실제로 거쳐 온 순서를 흉내 낸다. 0002까지 올린 빈 DB에 demo_data/migration/legacy_0002.sql을 넣고,
0009까지 올린 뒤 legacy_0009.sql(인정 학점이 있는 판정)을 넣고, 마지막으로 --to 리비전(기본 head)까지 올린다.
그래서 0003~0012의 데이터 백필(출신 대학·학과 채우기, 출신 대학 목록, closed 상태, 종료 요청의 이의 사유 지우기,
계정 성적표, 배분 원장, 학칙 정책, 증거 상태)이 빈 DB가 아니라 데이터가 있는 DB에서 실행되고, 0013 이후 칸·표 추가도
데이터가 있는 상태에서 지나간다. 기대 결과는 tests/integration/test_migrations.py에 있다.

실행 (대상 DB의 public 스키마를 모두 지우고 다시 만든다 — 그래서 주소를 꼭 직접 적게 했고,
앱 DB(DATABASE_URL)는 거절한다):
    uv run python -m scripts.migration_demo --database-url postgresql+psycopg://creditbridge:change-me@localhost:5432/cb_migration
    uv run python -m scripts.migration_demo --database-url ... --to 0006     # 중간 리비전에서 멈추고 들여다보기
DB가 없으면 만든다(접속 계정에 CREATEDB 권한 필요 — docker compose의 creditbridge 계정은 있음).
head까지 올린 DB는 앱으로 열어 볼 수 있다 (DATABASE_URL을 그 주소로, 계정은 legacy_0002.sql, 비밀번호 demo1234).
"""

import argparse
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url

from alembic import command

ROOT = Path(__file__).parent.parent
FIXTURES = Path(__file__).parent / "demo_data" / "migration"
# (이 리비전까지 올린 뒤, 이 파일을 넣는다) — 리비전 순서대로
STAGES: tuple[tuple[str, Path], ...] = (
    ("0002", FIXTURES / "legacy_0002.sql"),
    ("0009", FIXTURES / "legacy_0009.sql"),
)
SUMMARY_TABLES = (
    "users",
    "institution_sources",
    "transfer_requests",
    "student_transcripts",
    "transcript_entries",
    "decisions",
    "credit_allocations",
    "policy_rules",
    "appeals",
)


def alembic_config(database_url: str) -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.attributes["database_url"] = database_url  # alembic/env.py가 Settings보다 먼저 쓴다
    return cfg


def revision_order(cfg: Config) -> list[str]:
    """0001부터 head까지 리비전 id (갈래가 없다고 가정 — 지금 저장소는 한 줄)."""
    script = ScriptDirectory.from_config(cfg)
    return [rev.revision for rev in reversed(list(script.walk_revisions()))]


def check_target(cfg: Config, to: str) -> None:
    """없는 리비전이거나 첫 단계(0002)보다 앞이면 스키마를 지우기 전에 거절한다."""
    if to == "head":
        return
    order = revision_order(cfg)
    if to not in order:
        raise SystemExit(f"없는 리비전: {to}")
    if order.index(to) < order.index(STAGES[0][0]):
        raise SystemExit(f"{STAGES[0][0]}보다 앞 리비전에는 옛 데이터를 넣을 수 없어요: {to}")


def refuse_app_database(target: URL, app_database_url: str) -> None:
    """앱이 쓰는 DB를 실수로 지우지 않게 막는다 (같은 호스트·포트·DB 이름이면 거절)."""
    app = make_url(app_database_url)
    if (target.host, target.port or 5432, target.database) == (app.host, app.port or 5432, app.database):
        raise SystemExit(f"앱 DB({target.database})는 지우지 않아요. 시험용 DB 이름을 따로 주세요 (예: cb_migration).")


def ensure_database(database_url: str) -> None:
    """대상 DB가 없으면 만든다. 같은 서버의 postgres DB로 접속해 확인한다."""
    url = make_url(database_url)
    name = url.database
    if not name:
        raise SystemExit("주소에 DB 이름이 없어요.")
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": name}).first()
            if exists is None:
                # DB 이름은 바인드 변수로 못 넘긴다. 큰따옴표를 두 번 써서 식별자로만 쓴다
                quoted = '"' + name.replace('"', '""') + '"'
                conn.execute(text(f"CREATE DATABASE {quoted}"))
    finally:
        admin.dispose()


def reset_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))


def load_sql(engine: Engine, path: Path) -> None:
    # 매개변수 없이 실행하므로 psycopg가 여러 문장을 한 번에 보낸다. 한 트랜잭션이라 중간에 실패하면 모두 취소된다
    with engine.begin() as conn:
        conn.exec_driver_sql(path.read_text(encoding="utf-8"))


def build(database_url: str, to: str = "head") -> None:
    """빈 스키마에서 시작해 단계별 옛 데이터를 넣으며 to 리비전까지 올린다."""
    cfg = alembic_config(database_url)
    check_target(cfg, to)
    order = revision_order(cfg)
    stop = len(order) - 1 if to == "head" else order.index(to)
    engine = create_engine(database_url)
    try:
        reset_schema(engine)
        for revision, fixture in STAGES:
            if order.index(revision) > stop:
                break
            command.upgrade(cfg, revision)
            load_sql(engine, fixture)
        command.upgrade(cfg, to)
    finally:
        engine.dispose()


def summary(database_url: str) -> dict[str, int]:
    engine = create_engine(database_url)
    try:
        with engine.connect() as conn:
            existing = set(conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).scalars())
            return {
                # 표 이름은 위 고정 목록에서만 온다
                table: int(conn.execute(text(f'SELECT count(*) FROM "{table}"')).scalar_one())
                for table in SUMMARY_TABLES
                if table in existing
            }
    finally:
        engine.dispose()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="옛 데이터를 넣으며 마이그레이션을 올려 본다 (대상 DB 스키마를 지움)")
    parser.add_argument("--database-url", required=True, help="postgresql+psycopg://... (지워도 되는 DB)")
    parser.add_argument("--to", default="head", help="멈출 리비전 (기본 head)")
    args = parser.parse_args(argv)

    url = make_url(args.database_url)
    if not url.drivername.startswith("postgresql"):
        sys.exit("PostgreSQL 주소만 받아요.")
    from backend.config import get_settings

    refuse_app_database(url, get_settings().database_url)
    ensure_database(args.database_url)
    build(args.database_url, args.to)
    print(f"{url.database}: {args.to}까지 올림")
    for table, count in summary(args.database_url).items():
        print(f"  {table:<22}{count:>5}")


if __name__ == "__main__":
    main()
