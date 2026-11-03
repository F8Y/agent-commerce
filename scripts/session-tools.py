#!/usr/bin/env python3
"""Compact view of tool calls from `hermes sessions export` JSONL (stdin).

By default shows only the most recent session. Usage:
  docker compose exec -T hermes hermes sessions export - --format jsonl \
    | python3 scripts/session-tools.py [--last N] [--all]
"""
import json
import sys

MAX_LEN = 160
TIME_HINTS = ("updated", "last_active", "ended", "started", "created", "timestamp")


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


def session_time(session: dict) -> str:
    """Latest top-level timestamp-like value as a sortable string ('' if none)."""
    stamps = [str(v) for k, v in session.items()
              if isinstance(v, (str, int, float)) and any(h in k.lower() for h in TIME_HINTS)]
    return max(stamps) if stamps else ""


def main() -> None:
    args = sys.argv[1:]
    last = int(args[args.index("--last") + 1]) if "--last" in args else 40
    sessions = []
    for raw in sys.stdin:
        raw = raw.strip()
        if raw:
            try:
                sessions.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    if not sessions:
        print("Сессий не найдено")
        return

    if "--all" not in args:
        # Hermes exports newest first; prefer an explicit timestamp when present.
        timed = [s for s in sessions if isinstance(s, dict) and session_time(s)]
        sessions = [max(timed, key=session_time)] if timed else sessions[:1]

    lines: list = []
    for i, session in enumerate(sessions):
        if len(sessions) > 1:
            sid = session.get("id") or session.get("session_id") if isinstance(session, dict) else None
            lines.append(f"===== session {i + 1}" + (f" ({sid})" if sid else ""))
        walk(session, lines)
    print("\n".join(lines[-last:]) if lines else "Вызовов инструментов не найдено")


if __name__ == "__main__":
    main()
