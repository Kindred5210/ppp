"""
连通性自检：获取 token + GET /config/operations/v1/jobs。
退出码 0 = 成功，1 = 失败。

用法：python -m scm_mcp_server.check
"""
import sys

# ref: openapi-specs/scm/config/sase/operations/config-operations-march.yaml
_JOBS_PATH = "/config/operations/v1/jobs"


def main() -> None:
    try:
        from scm_mcp_server.config import load as load_config
        load_config()
    except RuntimeError as exc:
        print(f"[check] FAIL config: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        from scm_mcp_server.auth import get_token
        token = get_token()
        print(f"[check] OK   token obtained (first 8 chars: {token[:8]}...)")
    except Exception as exc:
        print(f"[check] FAIL token: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        from scm_mcp_server.rest_client import request
        status, body = request("GET", _JOBS_PATH, params={"limit": 1})
        if status == 0:
            print(f"[check] FAIL jobs: {body.get('error')}", file=sys.stderr)
            sys.exit(1)
        if status >= 400:
            print(f"[check] FAIL jobs: HTTP {status} — {body}", file=sys.stderr)
            sys.exit(1)
        print(f"[check] OK   GET {_JOBS_PATH} → HTTP {status}")
    except Exception as exc:
        print(f"[check] FAIL jobs: {exc}", file=sys.stderr)
        sys.exit(1)

    print("[check] All checks passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
