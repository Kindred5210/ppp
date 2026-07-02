"""
验证 config.load() 对缺失必填变量的行为。
"""
import os
import pytest
from unittest.mock import patch


def test_missing_all_required_raises():
    with patch.dict(os.environ, {}, clear=True):
        from scm_mcp_server import config
        with pytest.raises(RuntimeError) as exc_info:
            config.load()
    msg = str(exc_info.value)
    assert "SCM_CLIENT_ID" in msg or "SCM_CLIENT_SECRET" in msg or "SCM_TSG_ID" in msg


def test_missing_one_required_raises():
    env = {"SCM_CLIENT_ID": "id", "SCM_CLIENT_SECRET": "secret"}
    with patch.dict(os.environ, env, clear=True):
        from scm_mcp_server import config
        with pytest.raises(RuntimeError) as exc_info:
            config.load()
    assert "SCM_TSG_ID" in str(exc_info.value)


def test_all_required_present_returns_dict():
    env = {
        "SCM_CLIENT_ID": "id",
        "SCM_CLIENT_SECRET": "secret",
        "SCM_TSG_ID": "tsg123",
    }
    with patch.dict(os.environ, env, clear=True):
        from scm_mcp_server import config
        cfg = config.load()
    assert cfg["client_id"] == "id"
    assert cfg["client_secret"] == "secret"
    assert cfg["tsg_id"] == "tsg123"
    assert cfg["base_url"] == "https://api.strata.paloaltonetworks.com"


def test_custom_base_url():
    env = {
        "SCM_CLIENT_ID": "id",
        "SCM_CLIENT_SECRET": "secret",
        "SCM_TSG_ID": "tsg123",
        "SCM_BASE_URL": "https://custom.example.com/",
    }
    with patch.dict(os.environ, env, clear=True):
        from scm_mcp_server import config
        cfg = config.load()
    assert cfg["base_url"] == "https://custom.example.com"  # trailing slash stripped
