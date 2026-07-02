"""OAuth2 client_credentials token cache."""

from __future__ import annotations

import time
import threading

import httpx

from scm_mcp_server.config import load as load_config

TOKEN_TTL_SECONDS = 15 * 60
REFRESH_BEFORE_SECONDS = 60

_lock = threading.Lock()
_token: str | None = None
_expires_at: float = 0.0


def _fetch_token() -> str:
    """Fetch a fresh access token from SCM auth."""
    cfg = load_config()
    url = f"{cfg.auth_url}/auth/v1/oauth2/access_token"
    data = {
        "grant_type": "client_credentials",
        "client_id": cfg.client_id,
        "client_secret": cfg.client_secret,
        "scope": f"tsg_id:{cfg.tsg_id}",
    }
    response = httpx.post(url, data=data, timeout=10.0)
    if response.status_code != 200:
        raise RuntimeError(
            f"Token fetch failed ({response.status_code}): {response.text[:200]}"
        )
    body = response.json()
    token = body.get("access_token")
    if not token:
        raise RuntimeError("Token fetch failed: response did not include access_token")
    return token


def get_token() -> str:
    """Return a cached token, refreshing 60 seconds before the 15-minute TTL."""
    global _token, _expires_at

    with _lock:
        if _token is None or time.monotonic() >= _expires_at:
            _token = _fetch_token()
            _expires_at = (
                time.monotonic() + TOKEN_TTL_SECONDS - REFRESH_BEFORE_SECONDS
            )
        return _token


def bearer_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {get_token()}"}
