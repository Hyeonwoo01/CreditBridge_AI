"""카탈로그 출처·검증·게시 (리뷰 v3 P1-2)."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import CatalogImport, Course
from tests.conftest import login

CSV = (
    "code,title,credits,department,level,concepts\n"
    "MATH 1151,Calculus I (2027),4,Mathematics,,Limits;Derivatives;Integrals\n"
    "MATH 9001,Topology,3,Mathematics,,Open sets;Continuity\n"
)


def upload(client: TestClient, token: str, body: str = CSV, year: str = "2027") -> int:
    r = client.post(
        "/admin/data/courses",
        files={"file": ("catalog.csv", body.encode(), "text/csv")},
        data={"csrf_token": token, "source": "2027 학사 편람", "catalog_year": year},
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text
    page = client.get("/admin/data").text
    return int(page.split('data-catalog-draft="', 1)[1].split('"', 1)[0])


def test_draft_shows_diff_and_publish_records_provenance(client: TestClient, seeded: Session) -> None:
    token = login(client, "admin@msu.example")
    draft_id = upload(client, token)
    draft = seeded.get(CatalogImport, draft_id)
    assert draft is not None and draft.status == "draft" and len(draft.file_hash) == 64
    assert draft.changes["added"] == ["MATH 9001"]
    assert draft.changes["changed"]["MATH 1151"]["title"][1] == "Calculus I (2027)"
    page = client.get("/admin/data").text
    assert "Calculus I (2027)" in page and "2027 학사 편람" in page
    # 게시 전에는 카탈로그에 없다 (AI 후보에 쓰이지 않음)
    assert seeded.scalars(select(Course).where(Course.code == "MATH 9001")).first() is None

    client.post(f"/admin/data/imports/{draft_id}/publish", data={"csrf_token": token})
    seeded.expire_all()
    topo = seeded.scalars(select(Course).where(Course.code == "MATH 9001")).one()
    calc = seeded.scalars(select(Course).where(Course.code == "MATH 1151")).one()
    assert topo.catalog_import_id == draft_id and calc.catalog_import_id == draft_id
    assert calc.title == "Calculus I (2027)"
    draft = seeded.get(CatalogImport, draft_id)
    assert draft is not None and draft.status == "published" and draft.reviewed_by is not None
    page = client.get("/admin/data").text
    assert "출처 2027 학사 편람 · 2027학년도" in page and "data-catalog-draft" not in page
    again = client.post(f"/admin/data/imports/{draft_id}/publish", data={"csrf_token": token})
    assert "이미 게시했거나 버린" in again.text  # 이미 게시한 대기본은 다시 게시할 수 없다


def test_discard_and_new_upload_replaces_draft(client: TestClient, seeded: Session) -> None:
    token = login(client, "admin@msu.example")
    first = upload(client, token)
    second = upload(client, token)
    seeded.expire_all()
    assert seeded.get(CatalogImport, first).status == "discarded"  # type: ignore[union-attr]
    client.post(f"/admin/data/imports/{second}/discard", data={"csrf_token": token})
    seeded.expire_all()
    assert seeded.get(CatalogImport, second).status == "discarded"  # type: ignore[union-attr]
    assert seeded.scalars(select(Course).where(Course.code == "MATH 9001")).first() is None
    r = client.post(
        "/admin/data/courses",
        files={"file": ("catalog.csv", CSV.encode(), "text/csv")},
        data={"csrf_token": token, "catalog_year": "27"},
    )
    assert "네 자리 연도" in r.text
    evaluator = login(client, "rachel@msu.example")  # 다른 역할은 게시할 수 없다
    assert client.post(f"/admin/data/imports/{second}/publish", data={"csrf_token": evaluator}).status_code == 403
