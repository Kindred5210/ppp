#!/usr/bin/env python3
"""
路由完整性验证：断言路由表 key 集合 == tool descriptor name 集合，无遗漏、无多余。

检查规则：
  readonly._LIST_TOOLS ∪ readonly._GET_BY_ID_TOOLS
  ∪ write._CREATE_TOOLS ∪ write._UPDATE_TOOLS ∪ write._DELETE_TOOLS
  ∪ special._MOVE_TOOLS ∪ {push/load/delete_candidate/reset 四个单例}
  == {t.name for t in list_tool_descriptors()}

退出码 0 = 通过，1 = 有差异。

用法：python scripts/route_integrity.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scm_mcp_server.tools import readonly, write, special, list_tool_descriptors

_SPECIAL_SINGLETONS = {
    "push_candidate_config",
    "load_config_version",
    "delete_candidate_config",
    "reset_service_account_secret",
}

route_keys = (
    set(readonly._LIST_TOOLS)
    | set(readonly._GET_BY_ID_TOOLS)
    | set(write._CREATE_TOOLS)
    | set(write._UPDATE_TOOLS)
    | set(write._DELETE_TOOLS)
    | set(special._MOVE_TOOLS)
    | _SPECIAL_SINGLETONS
)

descriptor_names = {t.name for t in list_tool_descriptors()}

missing_routes  = sorted(descriptor_names - route_keys)   # 有 descriptor 但无路由
missing_descriptors = sorted(route_keys - descriptor_names)  # 有路由但无 descriptor

print(f"Route table keys : {len(route_keys)}")
print(f"Descriptor names : {len(descriptor_names)}")

ok = True
if missing_routes:
    print(f"\nFAIL — {len(missing_routes)} tool(s) have descriptor but no route entry:")
    for t in missing_routes:
        print(f"  {t}")
    ok = False

if missing_descriptors:
    print(f"\nFAIL — {len(missing_descriptors)} route key(s) have no descriptor:")
    for t in missing_descriptors:
        print(f"  {t}")
    ok = False

if ok:
    print(f"PASS — {len(route_keys)} route keys == {len(descriptor_names)} descriptor names.")
    sys.exit(0)
else:
    sys.exit(1)
