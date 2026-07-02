"""Small SCM REST client wrapper."""

from __future__ import annotations

from typing import Any

import httpx

from scm_mcp_server.auth import bearer_headers
from scm_mcp_server.config import load as load_config

TIMEOUT_SECONDS = 15.0


def request(
    method: str,
    full_path: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    """Send an SCM REST request and return (status, body), including non-2xx."""
    cfg = load_config()
    path = full_path if full_path.startswith("/") else f"/{full_path}"
    url = f"{cfg.base_url}{path}"

    try:
        response = httpx.request(
            method.upper(),
            url,
            headers=bearer_headers(),
            params=params,
            json=json,
            timeout=TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException:
        return 0, {"error": f"Request timeout after {TIMEOUT_SECONDS}s"}
    except httpx.ConnectError as exc:
        return 0, {"error": f"Cannot connect to {cfg.base_url}: {exc}"}
    except httpx.HTTPError as exc:
        return 0, {"error": f"HTTP error: {exc}"}

    try:
        body = response.json()
    except ValueError:
        body = {"raw": response.text}

    return response.status_code, body
