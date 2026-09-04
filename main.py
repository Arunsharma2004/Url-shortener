from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

import crud
from database import Base, engine, get_db
from schemas import ShortenRequest, ShortenResponse, StatsResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(title="URL Shortener")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/shorten", response_model=ShortenResponse, status_code=201)
@limiter.limit("5/minute")
def shorten_url(
    payload: ShortenRequest, request: Request, db: Session = Depends(get_db)
):
    link = crud.create_link(db, payload.original_url)
    short_url = str(request.base_url) + link.short_code
    return ShortenResponse(short_code=link.short_code, short_url=short_url)


@app.get("/stats/{short_code}", response_model=StatsResponse)
def get_stats(short_code: str, db: Session = Depends(get_db)):
    link = crud.get_link_by_code(db, short_code)
    if link is None:
        raise HTTPException(status_code=404, detail="Short code not found")
    return StatsResponse(original_url=link.original_url, click_count=link.click_count)


@app.get("/{short_code}")
def redirect_to_original(short_code: str, db: Session = Depends(get_db)):
    """Redirect to the stored URL and increment its click_count.

    Uses 307 rather than 301/302 so browsers and proxies don't cache the
    redirect, which would let click_count silently undercount.
    """
    link = crud.get_link_by_code(db, short_code)
    if link is None:
        raise HTTPException(status_code=404, detail="Short code not found")
    crud.increment_click_count(db, link)
    return RedirectResponse(url=link.original_url, status_code=307)
