import secrets
import string

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Link

_ALPHABET = string.ascii_letters + string.digits
_CODE_LENGTH = 6
_MAX_CREATE_RETRIES = 5


def generate_unique_short_code(db: Session) -> str:
    """Return a random 6-char code not currently in the DB.

    Best-effort only: this check and the later INSERT aren't atomic, so
    create_link still guards against a concurrent collision.
    """
    while True:
        code = "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_LENGTH))
        exists = db.query(Link).filter(Link.short_code == code).first()
        if not exists:
            return code


def create_link(db: Session, original_url: str) -> Link:
    """Insert a new Link, retrying with a fresh short code if a concurrent
    insert claimed the same one (unique-constraint violation). Raises after
    _MAX_CREATE_RETRIES failed attempts.
    """
    for _ in range(_MAX_CREATE_RETRIES):
        short_code = generate_unique_short_code(db)
        link = Link(original_url=original_url, short_code=short_code, click_count=0)
        db.add(link)
        try:
            db.commit()
        except IntegrityError:
            # Another request inserted the same code between the uniqueness
            # check and this commit; roll back and try a fresh code.
            db.rollback()
            continue
        db.refresh(link)
        return link
    raise RuntimeError("Could not generate a unique short code")


def get_link_by_code(db: Session, short_code: str) -> Link | None:
    return db.query(Link).filter(Link.short_code == short_code).first()


def increment_click_count(db: Session, link: Link) -> Link:
    """Atomically increment click_count via one UPDATE statement (avoids a
    read-modify-write race between concurrent visits) and return the
    refreshed Link.
    """
    db.query(Link).filter(Link.id == link.id).update(
        {Link.click_count: Link.click_count + 1},
        synchronize_session=False,
    )
    db.commit()
    db.refresh(link)
    return link
