"""SCM environment configuration."""

from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv

DEFAULT_BASE_URL = "https://api.strata.paloaltonetworks.com"
DEFAULT_AUTH_URL = "https://auth.apps.paloaltonetworks.com"
REQUIRED_ENV = ("SCM_CLIENT_ID", "SCM_CLIENT_SECRET", "SCM_TSG_ID")


@dataclass(frozen=True)
class Settings:
    base_url: str
    auth_url: str
    client_id: str
    client_secret: str
    tsg_id: str


def load() -> Settings:
    """Read SCM settings from the environment and fail fast on missing credentials."""
    load_dotenv()

    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )

    return Settings(
        base_url=os.environ.get("SCM_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        auth_url=os.environ.get("SCM_AUTH_URL", DEFAULT_AUTH_URL).rstrip("/"),
        client_id=os.environ["SCM_CLIENT_ID"],
        client_secret=os.environ["SCM_CLIENT_SECRET"],
        tsg_id=os.environ["SCM_TSG_ID"],
    )
