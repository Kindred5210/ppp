"""
轻量 REST 客户端：注入 Bearer header，不抛非 2xx，直接返回 (status, body)。
"""
import httpx

from scm_mcp_server.auth import bearer_headers
from scm_mcp_server.config import load as load_config

_TIMEOUT = 15.0  # seconds


def request(
    method: str,
    full_path: str,
    *,
    params: dict | None = None,
    json: dict | None = None,
    base: str | None = None,
) -> tuple[int, dict]:
    """
    发起 HTTP 请求。

    full_path 以 / 开头，会拼接到 base_url 后。
    base 若传入则覆盖 config 中的 base_url（用于 IAM 等使用不同域名的 API）。
    返回 (status_code, response_body_dict)。
    网络错误转为 (0, {"error": "..."})。
    """
    cfg = load_config()
    effective_base = (base or cfg["base_url"]).rstrip("/")
    url = effective_base + full_path
    try:
        resp = httpx.request(
            method.upper(),
            url,
            headers=bearer_headers(),
            params=params,
            json=json,
            timeout=_TIMEOUT,
        )
    except httpx.TimeoutException:
        return 0, {"error": f"Request timeout after {_TIMEOUT}s: {method} {full_path}"}
    except httpx.ConnectError as exc:
        return 0, {"error": f"Cannot connect to {effective_base}: {exc}"}
    except httpx.HTTPError as exc:
        return 0, {"error": f"HTTP error: {exc}"}

    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text}

    return resp.status_code, body
