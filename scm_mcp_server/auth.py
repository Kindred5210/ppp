"""
OAuth2 client_credentials token 获取与内存缓存。

- token 有效期按 SCM 响应的 expires_in（秒）计算，提前 60 s 刷新。
- 若 SCM 未返回 expires_in，默认按 15 分钟（900 s）计算。
- threading.Lock 保证并发安全（MCP server 在单线程事件循环中运行，但防御性保留）。
"""
import time
import threading
import httpx

from scm_mcp_server.config import load as load_config

_DEFAULT_TTL = 900  # seconds
_REFRESH_BEFORE = 60  # seconds

_lock = threading.Lock()
_token: str | None = None
_expires_at: float = 0.0


def _fetch_token() -> tuple[str, float]:
    """调用 /auth/v1/oauth2/access_token，返回 (access_token, expires_at)。"""
    cfg = load_config()
    url = cfg["auth_url"] + "/auth/v1/oauth2/access_token"
    data = {
        "grant_type": "client_credentials",
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "scope": f"tsg_id:{cfg['tsg_id']}",
    }
    resp = httpx.post(url, data=data, timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Token fetch failed ({resp.status_code}): {resp.text[:200]}"
        )
    body = resp.json()
    ttl = int(body.get("expires_in", _DEFAULT_TTL))
    expires_at = time.monotonic() + ttl - _REFRESH_BEFORE
    return body["access_token"], expires_at


def get_token() -> str:
    """返回有效 token，必要时自动刷新。"""
    global _token, _expires_at
    with _lock:
        if _token is None or time.monotonic() >= _expires_at:
            _token, _expires_at = _fetch_token()
        return _token


def bearer_headers() -> dict[str, str]:
    """返回含 Authorization Bearer 的 headers 字典。"""
    return {"Authorization": f"Bearer {get_token()}"}
