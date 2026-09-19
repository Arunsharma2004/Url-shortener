import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import crud
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


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "ftp://example.com/file",
        "data:text/html,<script>alert(1)</script>",
    ],
)
def test_shorten_rejects_non_http_scheme(client, url):
    resp = client.post("/shorten", json={"original_url": url})

    assert resp.status_code == 422


def test_shorten_accepts_plain_http_url(client):
    resp = client.post("/shorten", json={"original_url": "http://example.com"})

    assert resp.status_code == 201


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "http://127.0.0.1:8000/",
        "http://localhost/x",
        "http://LOCALHOST/x",
        "https://sub.localhost/x",
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://172.16.0.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "http://[fe80::1]/",
        "http://0.0.0.0/",
        "http://2130706433/",  # decimal-encoded 127.0.0.1
        "http://trusted.com@evil.com/",  # userinfo trick
        "http://user:pass@10.0.0.5/",
    ],
)
def test_shorten_rejects_internal_or_userinfo_urls(client, url):
    resp = client.post("/shorten", json={"original_url": url})

    assert resp.status_code == 422


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/some/long/path",
        "http://8.8.8.8/",  # public IP literal
        "https://example.com/a@b",  # @ in path, not userinfo
    ],
)
def test_shorten_accepts_public_urls(client, url):
    resp = client.post("/shorten", json={"original_url": url})

    assert resp.status_code == 201


def test_create_link_retries_on_short_code_collision(client, monkeypatch):
    taken = make_short_code(client)
    codes = iter([taken, "fresh1"])
    monkeypatch.setattr(
        crud, "generate_unique_short_code", lambda db: next(codes)
    )

    resp = client.post("/shorten", json={"original_url": ORIGINAL_URL})

    assert resp.status_code == 201
    assert resp.json()["short_code"] == "fresh1"


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


# --- POST /shorten: request-body validation edge cases ---


def test_shorten_missing_original_url_field_returns_422(client):
    """Body with no `original_url` key -> 422 (distinct from a malformed value)."""
    resp = client.post("/shorten", json={})
    assert resp.status_code == 422


def test_shorten_empty_original_url_returns_422(client):
    resp = client.post("/shorten", json={"original_url": ""})
    assert resp.status_code == 422


def test_shorten_original_url_wrong_type_returns_422(client):
    resp = client.post("/shorten", json={"original_url": 12345})
    assert resp.status_code == 422


def test_shorten_url_exceeding_max_length_returns_422(client):
    long_url = "https://example.com/" + "a" * 2048
    resp = client.post("/shorten", json={"original_url": long_url})
    assert resp.status_code == 422


# --- short-code generation ---


def test_generated_short_code_is_six_url_safe_chars(client):
    code = make_short_code(client)
    assert len(code) == 6
    assert all(c.isalnum() and c.isascii() for c in code)


def test_same_url_shortened_twice_gets_distinct_codes(client):
    """No dedup by design: each POST creates a new row with a fresh code."""
    first = make_short_code(client)
    second = make_short_code(client)
    assert first != second


# --- click_count lifecycle ---


def test_new_link_starts_with_zero_clicks(client):
    code = make_short_code(client)
    resp = client.get(f"/stats/{code}")
    assert resp.status_code == 200
    assert resp.json()["click_count"] == 0


def test_click_count_accumulates_across_visits(client):
    code = make_short_code(client)
    for _ in range(3):
        client.get(f"/{code}", follow_redirects=False)
    assert client.get(f"/stats/{code}").json()["click_count"] == 3


def test_stats_endpoint_does_not_increment_click_count(client):
    code = make_short_code(client)
    for _ in range(3):
        client.get(f"/stats/{code}")
    assert client.get(f"/stats/{code}").json()["click_count"] == 0


# --- data-model fidelity: stored exactly as provided ---


def test_original_url_round_trips_exactly(client):
    messy = "https://example.com/p?a=1&b=2#frag-section"
    code = make_short_code(client, url=messy)
    assert client.get(f"/stats/{code}").json()["original_url"] == messy
    redirect = client.get(f"/{code}", follow_redirects=False)
    assert redirect.headers["location"] == messy


# --- redirect lookup edge cases ---


def test_redirect_short_code_lookup_is_case_sensitive(client):
    code = make_short_code(client)
    swapped = code.swapcase()
    if swapped == code:  # vanishingly unlikely all-digit code
        return
    assert client.get(f"/{swapped}", follow_redirects=False).status_code == 404


def test_head_request_does_not_increment_click_count(client):
    """CLAUDE.md lists HEAD-inflates-count as a known limitation; on the
    installed FastAPI/Starlette the GET route does not serve HEAD, so it
    returns 405 and the count is untouched. Pins current behavior."""
    code = make_short_code(client)
    resp = client.head(f"/{code}")
    assert resp.status_code == 405
    assert client.get(f"/stats/{code}").json()["click_count"] == 0


# --- 404 error bodies ---


def test_stats_404_detail_message(client):
    resp = client.get("/stats/nope")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Short code not found"


def test_redirect_404_detail_message(client):
    resp = client.get("/nope", follow_redirects=False)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Short code not found"


# --- create_link retry exhaustion (known limitation: opaque 500, should be 503) ---


def test_create_link_raises_after_exhausting_retries(client, monkeypatch):
    taken = make_short_code(client)
    monkeypatch.setattr(crud, "generate_unique_short_code", lambda db: taken)
    # Every retry collides on the unique constraint; crud.create_link gives up
    # with a bare RuntimeError, which surfaces to the client as an opaque 500.
    with pytest.raises(RuntimeError, match="unique short code"):
        client.post("/shorten", json={"original_url": ORIGINAL_URL})


# --- rate limiting on POST /shorten (5/minute) ---


def test_shorten_rate_limited_after_five_requests(client):
    main.limiter.reset()
    main.limiter.enabled = True
    try:
        statuses = [
            client.post(
                "/shorten", json={"original_url": f"https://example.com/{i}"}
            ).status_code
            for i in range(7)
        ]
    finally:
        main.limiter.enabled = False
        main.limiter.reset()
    assert statuses[:5] == [201] * 5
    assert statuses[5:] == [429, 429]


# --- short_url is built from the client-supplied Host header (known limitation) ---


def test_short_url_reflects_spoofed_host_header(client):
    resp = client.post(
        "/shorten",
        json={"original_url": ORIGINAL_URL},
        headers={"host": "attacker.example"},
    )
    assert resp.status_code == 201
    assert resp.json()["short_url"].startswith("http://attacker.example/")
