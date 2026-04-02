#!/usr/bin/env python3
"""List recent Claude Code sessions grouped by project."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def load_history(history_path: Path) -> dict:
    """Parse history.jsonl, deduplicate by sessionId."""
    sessions = {}
    with open(history_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            sid = entry.get("sessionId")
            if not sid:
                continue
            if sid not in sessions:
                sessions[sid] = {
                    "sessionId": sid,
                    "display": entry.get("display", ""),
                    "firstTimestamp": entry.get("timestamp", 0),
                    "lastTimestamp": entry.get("timestamp", 0),
                    "project": entry.get("project", ""),
                }
            else:
                ts = entry.get("timestamp", 0)
                if ts > sessions[sid]["lastTimestamp"]:
                    sessions[sid]["lastTimestamp"] = ts
    return sessions


def shorten_project(project: str) -> str:
    """Show last 2 path components for readability."""
    parts = Path(project).parts
    if len(parts) <= 2:
        return project
    return str(Path(*parts[-2:]))


def format_timestamp(ts_ms: int) -> str:
    """Convert epoch milliseconds to YYYY-MM-DD HH:MM."""
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).astimezone()
    return dt.strftime("%Y-%m-%d %H:%M")


def truncate(text: str, maxlen: int = 60) -> str:
    """Truncate text, replacing newlines with spaces."""
    text = text.replace("\n", " ").strip()
    if len(text) <= maxlen:
        return text
    return text[:maxlen - 1] + "\u2026"


def main():
    parser = argparse.ArgumentParser(description="List recent Claude Code sessions")
    parser.add_argument("--limit", type=int, default=20, help="Number of sessions to show")
    parser.add_argument("--all", action="store_true", help="Show all sessions (no limit)")
    parser.add_argument("--json", action="store_true", help="Output as JSON array for programmatic use")
    args = parser.parse_args()

    history_path = Path.home() / ".claude" / "history.jsonl"
    if not history_path.exists():
        print(f"No history file found at {history_path}", file=sys.stderr)
        sys.exit(1)

    sessions = load_history(history_path)
    if not sessions:
        print("No sessions found.", file=sys.stderr)
        sys.exit(1)

    sorted_sessions = sorted(sessions.values(), key=lambda s: s["lastTimestamp"], reverse=True)
    if not args.all:
        sorted_sessions = sorted_sessions[:args.limit]

    if args.json:
        out = []
        for s in sorted_sessions:
            out.append({
                "id": s["sessionId"][:8],
                "fullId": s["sessionId"],
                "date": format_timestamp(s["lastTimestamp"]),
                "project": shorten_project(s["project"]) if s["project"] else "(unknown)",
                "fullProject": s["project"] or "",
                "display": truncate(s["display"]),
            })
        json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return

    # Group by project
    by_project = {}
    for s in sorted_sessions:
        proj = s["project"] or "(unknown)"
        by_project.setdefault(proj, []).append(s)

    # Output
    for project, sess_list in by_project.items():
        print(f"\n  {shorten_project(project)}")
        print(f"  {'─' * 78}")
        for s in sess_list:
            date = format_timestamp(s["lastTimestamp"])
            sid = s["sessionId"][:8]
            display = truncate(s["display"])
            print(f"  {date}  {sid}  {display}")

    print()


if __name__ == "__main__":
    main()
