"""Signed public URLs so Replicate can fetch large uploaded videos."""

import hashlib
import hmac
import time
from urllib.parse import urlencode

from app.core.config import settings


def _signing_secret() -> str:
    token = settings.REPLICATE_API_TOKEN
    if not token:
        raise RuntimeError("REPLICATE_API_TOKEN is required for media signing")
    return token


def build_replicate_media_url(file_id: str, ttl_seconds: int | None = None) -> str:
    ttl = ttl_seconds or settings.REPLICATE_MEDIA_TTL_SECONDS
    expires = int(time.time()) + ttl
    payload = f"{file_id}:{expires}"
    sig = hmac.new(
        _signing_secret().encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    query = urlencode({"expires": expires, "sig": sig})
    base = settings.public_api_base_url.rstrip("/")
    prefix = settings.route_prefix("/files")
    return f"{base}{prefix}/{file_id}/replicate-media?{query}"


def verify_replicate_media_signature(file_id: str, expires: int, sig: str) -> bool:
    if expires < int(time.time()):
        return False
    payload = f"{file_id}:{expires}"
    expected = hmac.new(
        _signing_secret().encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, sig)
