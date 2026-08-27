# URL Shortener

A small URL shortener backend built with FastAPI. Give it a long URL, it
generates a short code, and visiting the short link redirects to the
original URL. It also tracks a running click count per link.

- **Storage:** SQLite (`url_shortener.db`, created automatically on first run)
- **Rate limiting:** `POST /shorten` is limited to 5 requests/minute per IP
- **Frontend:** a single static `index.html` page

## Requirements

- Python 3.11+

## Setup

From the project root:

```bash
# 1. Create a virtual environment
python -m venv venv

# 2. Activate it
#    Windows (PowerShell)
venv\Scripts\Activate.ps1
#    Windows (cmd)
venv\Scripts\activate.bat
#    macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Running locally

```bash
uvicorn main:app --reload
```

The API is now available at `http://127.0.0.1:8000`.

- Interactive API docs (Swagger UI): `http://127.0.0.1:8000/docs`
- The database file `url_shortener.db` and its `links` table are created
  automatically on startup.

## API endpoints

### `POST /shorten`

Create a short code for a long URL.

Request body:

```json
{ "original_url": "https://example.com/some/long/path" }
```

Response `201 Created`:

```json
{
  "short_code": "Ab3xYz",
  "short_url": "http://127.0.0.1:8000/Ab3xYz"
}
```

- `422 Unprocessable Entity` if `original_url` is missing or not a valid
  absolute URL.
- `429 Too Many Requests` if you exceed 5 requests/minute from one IP.

### `GET /{short_code}`

Redirect to the original URL and increment that link's `click_count`.

- `307 Temporary Redirect` with the original URL in the `Location` header.
- `404 Not Found` if the short code doesn't exist.

Not rate limited (it only updates an existing row and popular links may
legitimately get heavy shared-IP traffic).

### `GET /stats/{short_code}`

Return stats for a short code.

Response `200 OK`:

```json
{
  "original_url": "https://example.com/some/long/path",
  "click_count": 1
}
```

- `404 Not Found` if the short code doesn't exist.

## Using the frontend

`index.html` is a standalone page that talks to the API at
`http://127.0.0.1:8000` (see `API_BASE` near the top of the `<script>`
block — change it if you run the backend elsewhere).

1. Start the backend with `uvicorn main:app --reload`.
2. Open `index.html` in your browser. Opening the file directly
   (`file://...`) works; the backend enables permissive CORS so the page
   can call it from any origin. You can also serve it statically, e.g.:

   ```bash
   python -m http.server 5500
   # then visit http://127.0.0.1:5500/index.html
   ```

3. Paste a long URL, click **Shorten**, and copy the resulting short link
   with the **Copy** button. Invalid URLs and other errors are shown
   inline.

## Running the tests

```bash
pytest
```

`test_main.py` covers the shorten / redirect / stats flows using an
isolated in-memory database, so it never touches `url_shortener.db`.

## Project layout

| File | Purpose |
| --- | --- |
| `main.py` | FastAPI app, routes, rate limiting, CORS |
| `schemas.py` | Pydantic request/response models and URL validation |
| `crud.py` | Database operations, short-code generation |
| `models.py` | SQLAlchemy `Link` model |
| `database.py` | Engine, session, `get_db` dependency |
| `index.html` | Static frontend |
| `test_main.py` | pytest suite |
