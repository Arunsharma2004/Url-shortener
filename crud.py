import secrets
import string

from sqlalchemy.orm import Session

from models import Link

_ALPHABET = string.ascii_letters + string.digits
_CODE_LENGTH = 6


def generate_unique_short_code(db: Session) -> str:
    while True:
        code = "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_LENGTH))
        exists = db.query(Link).filter(Link.short_code == code).first()
        if not exists:
            return code


def create_link(db: Session, original_url: str) -> Link:
    short_code = generate_unique_short_code(db)
    link = Link(original_url=original_url, short_code=short_code, click_count=0)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def get_link_by_code(db: Session, short_code: str) -> Link | None:
    return db.query(Link).filter(Link.short_code == short_code).first()


def increment_click_count(db: Session, link: Link) -> Link:
    db.query(Link).filter(Link.id == link.id).update(
        {Link.click_count: Link.click_count + 1},
        synchronize_session=False,
    )
    db.commit()
    db.refresh(link)
    return link
