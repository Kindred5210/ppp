#!/usr/bin/env python3
"""
语法自检：对 scm_mcp_server/ 下全部 .py 文件跑 ast.parse。
全通退出码 0；任意文件语法错误退出码 1。

用法：python scripts/syntax_check.py
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent / "scm_mcp_server"

errors = []
checked = 0

for path in sorted(ROOT.rglob("*.py")):
    checked += 1
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        errors.append(f"  {path.relative_to(ROOT.parent)}  line {exc.lineno}: {exc.msg}")

print(f"Checked {checked} file(s) under scm_mcp_server/")
if errors:
    print(f"FAIL — {len(errors)} syntax error(s):")
    for e in errors:
        print(e)
    sys.exit(1)

print("PASS — all files parse cleanly.")
