#!/usr/bin/env python3
"""
stdio 冒烟测试：通过官方 MCP SDK client 驱动本 server 走完整传输层握手。

流程：initialize → tools/list（断言数量与名称）→ call_tool(list_jobs, {limit:1})

call_tool 不断言业务内容（依赖真实凭据），只断言传输层可正常返回。
无凭据时 list_jobs 返回 error dict 也视为传输层通过。

退出码 0 = 通过，1 = 失败。

用法：python scripts/smoke_stdio.py
"""
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

EXPECTED_TOOL_COUNT = 111

# 20 个代表性抽样 tool 名，覆盖全部域
EXPECTED_NAMES_SAMPLE = {
    # Objects core
    "list_addresses", "get_address", "create_address", "delete_address",
    "list_service_groups", "list_tags",
    # Security rules
    "list_security_rules", "move_security_rule",
    "list_decryption_rules", "list_app_override_rules",
    # Security profiles (readonly)
    "list_anti_spyware_profiles", "get_wildfire_anti_virus_profile",
    "list_url_filtering_categories",
    # Operations
    "list_jobs", "get_job", "list_config_versions",
    "get_running_config_version", "push_candidate_config",
    # IAM
    "list_service_accounts", "reset_service_account_secret",
}

SERVER_CMD = [sys.executable, "-m", "scm_mcp_server"]


def _load_dotenv() -> dict:
    """Load .env if present; merge into current environment."""
    env = dict(os.environ)
    dotenv = Path(__file__).parent.parent / ".env"
    if dotenv.exists():
        for line in dotenv.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env.setdefault(k.strip(), v.strip())
    return env


async def run() -> bool:
    env = _load_dotenv()
    params = StdioServerParameters(
        command=SERVER_CMD[0], args=SERVER_CMD[1:], env=env
    )
    print(f"Starting: {' '.join(SERVER_CMD)}")

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:

            # 1. initialize
            await session.initialize()
            print("✓  initialize handshake complete")

            # 2. tools/list
            result = await session.list_tools()
            actual_names = {t.name for t in result.tools}
            count = len(actual_names)
            print(f"✓  tools/list returned {count} tools")

            if count != EXPECTED_TOOL_COUNT:
                print(f"FAIL  expected {EXPECTED_TOOL_COUNT}, got {count}")
                missing = EXPECTED_NAMES_SAMPLE - actual_names
                if missing:
                    print(f"  missing from sample: {sorted(missing)}")
                return False

            missing_sample = EXPECTED_NAMES_SAMPLE - actual_names
            if missing_sample:
                print(f"FAIL  missing expected tool names: {sorted(missing_sample)}")
                return False
            print(f"✓  all {len(EXPECTED_NAMES_SAMPLE)} sampled names present")

            # 3. call_tool(list_jobs, {limit: 1})
            call_result = await session.call_tool("list_jobs", {"limit": 1})
            raw = call_result.content[0].text if call_result.content else "(empty)"
            try:
                parsed = json.loads(raw)
                if "error" in parsed:
                    print(f"✓  call_tool(list_jobs) → error (no credentials): {raw[:120]}")
                else:
                    print(f"✓  call_tool(list_jobs) → data: {raw[:120]}")
            except json.JSONDecodeError:
                print(f"✓  call_tool(list_jobs) → {raw[:120]}")

    return True


def main() -> None:
    ok = asyncio.run(run())
    if ok:
        print("\nSMOKE PASS — MCP stdio transport fully operational.")
        sys.exit(0)
    else:
        print("\nSMOKE FAIL")
        sys.exit(1)


if __name__ == "__main__":
    main()
