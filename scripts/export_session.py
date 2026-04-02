#!/usr/bin/env python3
"""Export a Claude Code session to Markdown."""

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

VERSION = "3.0"

LABELS = {
    "en": {
        "session": "Session",
        "date": "Date",
        "project": "Project",
        "session_id": "Session ID",
        "user": "User",
        "assistant": "Assistant",
        "summary": "Summary",
        "transcript": "Transcript",
    },
    "zh": {
        "session": "会话",
        "date": "日期",
        "project": "项目",
        "session_id": "会话 ID",
        "user": "用户",
        "assistant": "助手",
        "summary": "摘要",
        "transcript": "记录",
    },
}


def find_session_file(query: str, projects_dir: Path) -> Path | None:
    """Find session JSONL by ID prefix or slug."""
    if not projects_dir.is_dir():
        return None
    query_lower = query.lower()
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        for jsonl in project_dir.glob("*.jsonl"):
            if jsonl.stem.lower().startswith(query_lower):
                return jsonl
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        for jsonl in project_dir.glob("*.jsonl"):
            try:
                with open(jsonl) as f:
                    for i, line in enumerate(f):
                        if i >= 30:
                            break
                        try:
                            entry = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if entry.get("slug", "").lower() == query_lower:
                            return jsonl
            except (OSError, PermissionError):
                continue
    return None


def format_tool(name: str, inp: dict) -> str:
    """Compact one-line tool summary with 4-space indent."""
    if name == "Bash":
        cmd = inp.get("command", "")
        return f"    [Bash: {cmd[:120]}]" if len(cmd) <= 120 else f"    [Bash: {cmd[:117]}...]"
    if name == "Read":
        return f"    [Read: {inp.get('file_path', '')}]"
    if name in ("Write", "Edit"):
        return f"    [{name}: {inp.get('file_path', '')}]"
    if name == "Grep":
        p = inp.get("pattern", "")
        d = inp.get("path", "")
        return f"    [Grep: {p} in {d}]" if d else f"    [Grep: {p}]"
    if name == "Glob":
        return f"    [Glob: {inp.get('pattern', '')}]"
    if name == "Agent":
        desc = inp.get("description", "")
        stype = inp.get("subagent_type", "")
        return f"    [Agent: {desc} ({stype})]" if stype else f"    [Agent: {desc}]"
    if name == "Skill":
        return f"    [Skill: {inp.get('skill', '')}]"
    s = json.dumps(inp, ensure_ascii=False)
    return f"    [{name}: {s[:97]}...]" if len(s) > 100 else f"    [{name}: {s}]"


def truncate(text: str, maxlen: int = 80) -> str:
    text = text.replace("\n", " ").strip()
    return text if len(text) <= maxlen else text[:maxlen - 1] + "\u2026"


def format_time(ts) -> str:
    """Format timestamp to short HH:MM."""
    if isinstance(ts, str):
        # ISO format
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
            return dt.strftime("%H:%M")
        except ValueError:
            return ""
    elif isinstance(ts, (int, float)):
        dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).astimezone()
        return dt.strftime("%H:%M")
    return ""


def format_date(ts) -> str:
    """Format timestamp to YYYY-MM-DD HH:MM."""
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
            return dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return ts[:16].replace("T", " ")
    elif isinstance(ts, (int, float)):
        dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).astimezone()
        return dt.strftime("%Y-%m-%d %H:%M")
    return ""


def export_session(session_path: Path, lang: str = "en") -> str:
    """Parse session JSONL and produce Markdown with Summary + Transcript."""
    L = LABELS.get(lang, LABELS["en"])
    transcript_lines = []
    # Each turn: (user_text_truncated, user_time)
    turns = []
    metadata = {"slug": None, "session_id": None, "project": None, "date": None}
    current_role = None  # "user" or "assistant"
    turn_count = 0

    with open(session_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if not metadata["slug"] and entry.get("slug"):
                metadata["slug"] = entry["slug"]
            if not metadata["session_id"] and entry.get("sessionId"):
                metadata["session_id"] = entry["sessionId"]
            if not metadata["project"] and entry.get("cwd"):
                metadata["project"] = entry["cwd"]
            if not metadata["date"] and entry.get("timestamp"):
                metadata["date"] = format_date(entry["timestamp"])

            entry_type = entry.get("type", "")
            if entry_type in ("permission-mode", "system", "attachment",
                              "file-history-snapshot", "queue-operation"):
                continue
            if entry.get("isMeta"):
                continue

            message = entry.get("message")
            if not message:
                continue
            role, content = message.get("role", ""), message.get("content")
            if content is None:
                continue

            msg_time = format_time(entry.get("timestamp", ""))

            # --- User message ---
            if entry_type == "user" and role == "user":
                user_text = None
                if isinstance(content, str):
                    user_text = content
                elif isinstance(content, list):
                    if any(isinstance(b, dict) and b.get("type") == "tool_result"
                           for b in content):
                        continue
                    texts = [b.get("text", "") for b in content
                             if isinstance(b, dict) and b.get("type") == "text"]
                    if texts:
                        user_text = "\n".join(texts)

                if user_text:
                    turn_count += 1
                    turns.append((truncate(user_text), msg_time))

                    # Turn heading + separator
                    if turn_count > 1:
                        transcript_lines.append("---\n")
                    transcript_lines.append(f"### Turn {turn_count}\n")
                    transcript_lines.append(
                        f"_**{L['user']}** ({msg_time})_\n" if msg_time
                        else f"_**{L['user']}**_\n"
                    )
                    transcript_lines.append(user_text)
                    transcript_lines.append("")
                    current_role = "user"

            # --- Assistant message ---
            elif entry_type == "assistant" and role == "assistant":
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    bt = block.get("type", "")

                    if bt == "thinking":
                        continue

                    if bt == "text":
                        text = block.get("text", "").strip()
                        if not text:
                            continue
                        if current_role != "assistant":
                            transcript_lines.append(
                                f"\n_**{L['assistant']}** ({msg_time})_\n" if msg_time
                                else f"\n_**{L['assistant']}**_\n"
                            )
                            current_role = "assistant"
                        transcript_lines.append(text)
                        transcript_lines.append("")

                    elif bt == "tool_use":
                        if current_role != "assistant":
                            transcript_lines.append(
                                f"\n_**{L['assistant']}** ({msg_time})_\n" if msg_time
                                else f"\n_**{L['assistant']}**_\n"
                            )
                            current_role = "assistant"
                        transcript_lines.append(
                            format_tool(block.get("name", ""), block.get("input", {}))
                        )
                        transcript_lines.append("")

    # --- Assemble document ---
    title = metadata["slug"] or (metadata["session_id"] or session_path.stem)[:8]
    parts = []

    # Version header
    parts.append(f"<!-- session-export v{VERSION} -->\n")

    # Title + metadata
    parts.append(f"# {L['session']}: {title}\n")
    if metadata["date"]:
        parts.append(f"- **{L['date']}**: {metadata['date']}")
    if metadata["project"]:
        parts.append(f"- **{L['project']}**: {metadata['project']}")
    if metadata["session_id"]:
        parts.append(f"- **{L['session_id']}**: {metadata['session_id']}")
    parts.append("")

    # Summary / TOC
    parts.append(f"## {L['summary']}\n")
    for i, (text, time) in enumerate(turns, 1):
        time_tag = f" ({time})" if time else ""
        parts.append(f"{i}. [{text}](#turn-{i}){time_tag}")
    parts.append("")

    # Separator
    parts.append("---\n")

    # Transcript
    parts.append(f"## {L['transcript']}\n")
    parts.extend(transcript_lines)

    return "\n".join(parts)


def copy_to_clipboard(text: str) -> bool:
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        elif system == "Linux":
            try:
                subprocess.run(["xclip", "-selection", "clipboard"],
                               input=text.encode("utf-8"), check=True)
            except FileNotFoundError:
                subprocess.run(["xsel", "--clipboard", "--input"],
                               input=text.encode("utf-8"), check=True)
        else:
            return False
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def main():
    parser = argparse.ArgumentParser(description="Export a Claude Code session to Markdown")
    parser.add_argument("query", help="Session ID (prefix) or slug name")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    parser.add_argument("--clipboard", "-c", action="store_true",
                        help="Copy to system clipboard")
    parser.add_argument("--lang", "-l", choices=list(LABELS.keys()), default="en",
                        help="Template language: en (default), zh")
    args = parser.parse_args()

    projects_dir = Path.home() / ".claude" / "projects"
    session_path = find_session_file(args.query, projects_dir)

    if not session_path:
        print(f"No session found matching '{args.query}'", file=sys.stderr)
        sys.exit(1)

    markdown = export_session(session_path, lang=args.lang)
    line_count = markdown.count("\n")

    if args.clipboard:
        if copy_to_clipboard(markdown):
            print(f"Copied to clipboard ({line_count} lines, {len(markdown)} chars)",
                  file=sys.stderr)
        else:
            print("Failed to copy to clipboard, falling back to stdout", file=sys.stderr)
            print(markdown)
    elif args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown, encoding="utf-8")
        print(f"Exported to {out_path} ({line_count} lines)", file=sys.stderr)
    else:
        print(markdown)


if __name__ == "__main__":
    main()
