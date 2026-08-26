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