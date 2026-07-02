"""
读取 SCM 连接配置，缺必填项时 raise RuntimeError。
"""
import os

_REQUIRED = ("SCM_CLIENT_ID", "SCM_CLIENT_SECRET", "SCM_TSG_ID")
_DEFAULT_BASE_URL = "https://api.strata.paloaltonetworks.com"
_DEFAULT_AUTH_URL = "https://auth.apps.paloaltonetworks.com"


def _get(key: str, default: str | None = None) -> str:
    value = os.environ.get(key, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


def load() -> dict:
    missing = [k for k in _REQUIRED if not os.environ.get(k)]
    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )

    return {
        "client_id": os.environ["SCM_CLIENT_ID"],
        "client_secret": os.environ["SCM_CLIENT_SECRET"],
        "tsg_id": os.environ["SCM_TSG_ID"],
        "base_url": os.environ.get("SCM_BASE_URL", _DEFAULT_BASE_URL).rstrip("/"),
        "auth_url": os.environ.get("SCM_AUTH_URL", _DEFAULT_AUTH_URL).rstrip("/"),
    }
