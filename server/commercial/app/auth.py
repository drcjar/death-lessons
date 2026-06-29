"""Passwordless magic-link auth + signed session cookies.

- Login: issue a single-use, 15-minute token, email a link.
- Verify: exchange the token for a signed session cookie.
- Session: itsdangerous-signed cookie holding the user id; no server state.
"""
from __future__ import annotations
import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from .config import get_settings
from .models import LoginToken, User

settings = get_settings()
SESSION_COOKIE = "dl_session"
SESSION_MAX_AGE = 30 * 24 * 3600  # 30 days
TOKEN_TTL = timedelta(minutes=15)

_serializer = URLSafeTimedSerializer(settings.secret_key, salt="session")


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def get_or_create_user(db: Session, email: str) -> User:
    email = email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def issue_login_token(db: Session, email: str) -> str:
    """Create a magic-link token; return the raw token (only stored hashed)."""
    email = email.strip().lower()
    raw = secrets.token_urlsafe(32)
    db.add(LoginToken(email=email, token_hash=_hash(raw),
                      expires_at=datetime.utcnow() + TOKEN_TTL))
    db.commit()
    return raw


def consume_login_token(db: Session, raw: str) -> User | None:
    """Validate + burn a token, returning the (created-on-demand) user."""
    rec = (db.query(LoginToken)
           .filter(LoginToken.token_hash == _hash(raw), LoginToken.used == False)  # noqa: E712
           .order_by(LoginToken.id.desc())
           .first())
    if rec is None or rec.expires_at < datetime.utcnow():
        return None
    rec.used = True
    db.commit()
    return get_or_create_user(db, rec.email)


def make_session_cookie(user: User) -> str:
    return _serializer.dumps({"uid": user.id})


def current_user(request: Request, db: Session) -> User | None:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return None
    try:
        data = _serializer.loads(raw, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    return db.get(User, data.get("uid"))
