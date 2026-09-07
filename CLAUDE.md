# CLAUDE.md

## Overview
A URL shortener backend built with FastAPI. Takes a long URL, generates
a short code, and redirects visitors from the short URL to the original
long URL. Tracks a simple click count per link.

## Data Model
Link:
- id: unique identifier, auto-assigned by the database
- original_url: the full, original URL, stored exactly as provided
- short_code: a short, unique string used to build the shortened link
- click_count: integer, starts at 0, increments each time the short
  link is visited

## Storage
SQLite database.

## API Design
- POST /shorten - accepts a long URL, returns a short code/URL
- GET /{short_code} - redirects to the original URL, increments
  click_count
- GET /stats/{short_code} - returns click_count and original_url for
  a given short code

## Future Enhancements (not built yet)
Per-click tracking (a separate Click table recording each individual
visit with a timestamp, rather than just a running count) would enable
richer stats - e.g. clicks per week, time-of-day patterns. Deliberately
deferred to keep the initial build well-scoped; click_count alone
satisfies today's requirements.

Rate limiting on `GET /{short_code}` (the redirect route) was considered
alongside the `/shorten` limiter but intentionally left unprotected.
Unlike `/shorten`, it only increments `click_count` on an existing row
rather than creating new rows, so it doesn't carry the same unbounded
database growth risk. A per-IP limit there could also incorrectly block
legitimate shared-IP traffic (offices, schools) on a link that's
genuinely popular.

## Known Limitations
Items surfaced in review and consciously left unaddressed for now:

- **No SQLite busy timeout.** The engine is created without a
  `busy_timeout` (or `timeout` connect arg), so concurrent writers under
  heavy load can hit "database is locked" errors instead of waiting for
  the lock. Acceptable at current scale; revisit if write contention
  shows up. This is made worse by the redirect route: `GET /{short_code}`
  performs a SQLite write (the `click_count` UPDATE) on *every* visit, so
  a single popular link under heavy but entirely legitimate traffic can
  produce enough write contention to surface "database is locked". A
  busy timeout, WAL mode, or batching/deferring the count update would
  all help.
- **Duplicated 404 lookup.** The "look up by `short_code`, raise 404 if
  missing" block is repeated in `get_stats` and `redirect_to_original`
  in `main.py`. Small enough (a few lines) that extracting a shared
  helper or dependency wasn't judged worthwhile yet.
- **307 redirect is deliberate but unconventional.** The redirect route
  returns 307 rather than the more typical 301/302 so that clients and
  intermediaries don't cache the redirect, which keeps `click_count`
  accurate. This trade-off should be called out in a code comment on the
  route.
- **No `max_length` on `original_url`.** Neither the `ShortenRequest`
  schema nor the `Link.original_url` column caps length, so a very large
  string could be submitted and stored. A sane upper bound (e.g. a few
  thousand characters) would prevent abuse.
- **URL validator does not resolve hostnames.** `ShortenRequest`'s
  validator rejects non-http(s) schemes, URLs carrying userinfo
  (`trusted.com@evil.com`), and URLs whose host is an IP literal in a
  loopback / private / link-local / reserved range (incl. the
  169.254.169.254 cloud-metadata endpoint) or the name `localhost`. It
  does **not** resolve DNS, so a public hostname whose A/AAAA record
  points at an internal address (DNS rebinding) is not caught. Doing so
  would mean network I/O inside request validation; deferred.
- **Rate limiter storage is in-memory and per-process.** `slowapi` is
  configured with the default in-memory backend keyed on
  `get_remote_address`. Behind a reverse proxy or load balancer every
  request appears to originate from the proxy's IP, so the `5/minute`
  limit on `/shorten` collapses into a single shared bucket for all
  clients; with multiple app processes each also keeps its own separate
  counter. A shared store (e.g. Redis) plus honoring a trusted
  `X-Forwarded-For` would be needed for the limit to mean anything in a
  real deployment.
- **Retry exhaustion raises a bare `RuntimeError`.** When
  `crud.create_link` fails `_MAX_CREATE_RETRIES` times it raises
  `RuntimeError`, which surfaces to the client as an opaque 500. It
  should raise a 503 (retryable) via `HTTPException`. Separately,
  `generate_unique_short_code` loops `while True` with no attempt cap, so
  if the code space were ever near-exhausted it would spin instead of
  giving up; it should bound its attempts and let the caller translate
  that into a 503 as well.
- **`click_count` increments on `HEAD` requests.** FastAPI serves `HEAD`
  for the `GET /{short_code}` route, and the handler increments the count
  before returning. Link-preview/unfurl bots (Slack, Discord, iMessage,
  etc.) issue `HEAD` (and sometimes `GET`) requests, inflating the count
  with non-human traffic — which undercuts the redirect-accuracy goal the
  307 status was chosen to protect. Skipping the increment for `HEAD`,
  and/or filtering known bot user-agents, would help.
- **`short_url` is built from the request `Host` header.** `shorten_url`
  constructs the returned short link from `request.base_url`, which is
  derived from the client-supplied `Host` header. An attacker can send a
  spoofed `Host` and get back a short URL on a domain they chose (useful
  for phishing, since the stored redirect is still legitimate). Building
  the URL from a configured base URL / allowed-hosts list would fix this.
- **Tests do touch `url_shortener.db` at import time.** The README claims
  the suite "never touches `url_shortener.db`". That's true for the
  request flows (they use an in-memory DB via a dependency override), but
  `test_main.py` imports `main`, and `main.py` runs
  `Base.metadata.create_all(bind=engine)` at module import against the
  real SQLite file — so importing the app (in tests or anywhere) creates
  `url_shortener.db` and its `links` table as a side effect. Moving
  `create_all` into a startup hook (or guarding it) would make the claim
  accurate.

## Linting

`ruff` is configured via `pyproject.toml`, which ignores rule `B008`
("do not perform function call `Depends` in argument defaults").
FastAPI's dependency injection relies on calling `Depends()` in argument
defaults - that's the framework's standard, correct pattern, not a bug,
so this rule is disabled project-wide rather than suppressed line by
line.