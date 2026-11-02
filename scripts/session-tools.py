#!/usr/bin/env python3
"""Compact view of tool calls from `hermes sessions export` JSONL (stdin).

Usage:
  docker compose exec -T hermes hermes sessions export - --format jsonl \
    | python3 scripts/session-tools.py [--last N]
"""
import json
import sys

MAX_LEN = 160


def short(value) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = " ".join(text.split())
    return text if len(text) <= MAX_LEN else text[:MAX_LEN] + "…"


def walk(node, out: list) -> None:
    if isinstance(node, dict):
        role = node.get("role")
        if role == "user" and node.get("content"):
            out.append(f"USER    {short(node['content'])}")
        for call in node.get("tool_calls") or []:
            fn = call.get("function", call)
            out.append(f"CALL    {fn.get('name')}  {short(fn.get('arguments', ''))}")
        if role == "tool":
            out.append(f"  ->    {short(node.get('content', ''))}")
        if role == "assistant" and node.get("content") and not node.get("tool_calls"):
            out.append(f"ANSWER  {short(node['content'])}")
        for key, value in node.items():
            if key not in ("tool_calls", "content"):
                walk(value, out)
    elif isinstance(node, list):
        for item in node:
            walk(item, out)


def main() -> None:
    last = 40
    if "--last" in sys.argv:
        last = int(sys.argv[sys.argv.index("--last") + 1])
    lines: list = []
    for raw in sys.stdin:
        raw = raw.strip()
        if raw:
            try:
                walk(json.loads(raw), lines)
            except json.JSONDecodeError:
                continue
    print("\n".join(lines[-last:]) if lines else "Вызовов инструментов не найдено")


if __name__ == "__main__":
    main()
