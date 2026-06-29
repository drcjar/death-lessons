"""Time-limited signed download links for purchased artifacts.

A buyer's /account page mints a short-lived signed token; /download
verifies it (and re-checks entitlement) before streaming the file. The
token is signed with SECRET_KEY, so no link can be forged or outlive its
TTL.
"""
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .config import get_settings

settings = get_settings()
_serializer = URLSafeTimedSerializer(settings.secret_key, salt="download")


def make_download_token(user_id: int, product: str) -> str:
    return _serializer.dumps({"uid": user_id, "product": product})


def verify_download_token(token: str) -> tuple[int, str] | None:
    try:
        data = _serializer.loads(token, max_age=settings.download_ttl_seconds)
    except (BadSignature, SignatureExpired):
        return None
    return data.get("uid"), data.get("product")
