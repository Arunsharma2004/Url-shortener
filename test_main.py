import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from database import Base, get_db

ORIGINAL_URL = "https://example.com/some/really/long/path?x=1"


@pytest.fixture
def client():
    """A TestClient backed by a fresh in-memory database, with rate limiting off."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override_get_db
    main.limiter.enabled = False

    with TestClient(main.app) as test_client:
        yield test_client

    main.app.dependency_overrides.clear()
    main.limiter.enabled = True
    Base.metadata.drop_all(bind=engine)


def make_short_code(client, url=ORIGINAL_URL):
    resp = client.post("/shorten", json={"original_url": url})
    assert resp.status_code == 201
    return resp.json()["short_code"]


def test_shorten_valid_url_returns_201_with_code_and_url(client):
    resp = client.post("/shorten", json={"original_url": ORIGINAL_URL})

    assert resp.status_code == 201
    body = resp.json()
    assert body["short_code"]
    assert body["short_url"].endswith(body["short_code"])


def test_shorten_invalid_url_returns_422(client):
    resp = client.post("/shorten", json={"original_url": "not-a-valid-url"})

    assert resp.status_code == 422


def test_redirect_returns_307_to_original_url(client):
    short_code = make_short_code(client)

    resp = client.get(f"/{short_code}", follow_redirects=False)

    assert resp.status_code == 307
    assert resp.headers["location"] == ORIGINAL_URL


def test_redirect_unknown_code_returns_404(client):
    resp = client.get("/doesnotexist", follow_redirects=False)

    assert resp.status_code == 404


def test_stats_reflects_click_count_after_one_visit(client):
    short_code = make_short_code(client)

    client.get(f"/{short_code}", follow_redirects=False)

    resp = client.get(f"/stats/{short_code}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["original_url"] == ORIGINAL_URL
    assert body["click_count"] == 1


def test_stats_unknown_code_returns_404(client):
    resp = client.get("/stats/doesnotexist")

    assert resp.status_code == 404
