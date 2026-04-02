#!/usr/bin/env python3
"""Export a Claude Code session to Markdown."""

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

FORMATS = ("clean", "full", "conversation")

# Template labels by language
LABELS = {
    "en": {
        "session": "Session",
        "date": "Date",
        "project": "Project",
        "session_id": "Session ID",
        "user": "User",
        "assistant": "Assistant",
        "tool": "Tool",
    },
    "zh": {
        "session": "会话",
        "date": "日期",
        "project": "项目",
        "session_id": "会话 ID",
        "user": "用户",
        "assistant": "助手",
        "tool": "工具",
    },
}


def find_session_file(query: str, projects_dir: Path) -> Path | None:
    """Find session JSONL by ID prefix or slug."""
    if not projects_dir.is_dir():
        return None

    query_lower = query.lower()

    # Try ID prefix match first (fast: just check filenames)
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        for jsonl in project_dir.glob("*.jsonl"):
            if jsonl.stem.lower().startswith(query_lower):
                return jsonl

    # Fallback: slug match (scan first 30 lines of each file)
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


def format_tool_compact(name: str, inp: dict) -> str:
    """One-line tool summary for clean format."""
    if name == "Bash":
        cmd = inp.get("command", "")
        cmd_display = cmd if len(cmd) < 120 else cmd[:117] + "..."
        return f"**Bash**: `{cmd_display}`"
    if name == "Read":
        return f"**Read**: `{inp.get('file_path', '')}`"
    if name in ("Write", "Edit"):
        return f"**{name}**: `{inp.get('file_path', '')}`"
    if name == "Grep":
        parts = [f"`{inp.get('pattern', '')}`"]
        if inp.get("path"):
            parts.append(f"in `{inp['path']}`")
        return f"**Grep**: {' '.join(parts)}"
    if name == "Glob":
        return f"**Glob**: `{inp.get('pattern', '')}`"
    if name == "Agent":
        desc = inp.get("description", "")
        stype = inp.get("subagent_type", "")
        suffix = f" ({stype})" if stype else ""
        return f"**Agent**: {desc}{suffix}"
    if name == "Skill":
        return f"**Skill**: `{inp.get('skill', '')}`"
    # Generic
    summary = json.dumps(inp, ensure_ascii=False)
    if len(summary) > 100:
        summary = summary[:97] + "..."
    return f"**{name}**: {summary}"


def format_tool_full(name: str, inp: dict) -> str:
    """Detailed tool rendering for full format."""
    if name == "Bash":
        cmd = inp.get("command", "")
        return f"`{cmd}`" if len(cmd) < 200 else f"`{cmd[:200]}...`"
    if name == "Read":
        return f"`{inp.get('file_path', '')}`"
    if name in ("Write", "Edit"):
        return f"`{inp.get('file_path', '')}`"
    if name == "Grep":
        parts = [f"pattern: `{inp.get('pattern', '')}`"]
        if inp.get("path"):
            parts.append(f"path: `{inp['path']}`")
        return ", ".join(parts)
    if name == "Glob":
        return f"pattern: `{inp.get('pattern', '')}`"
    if name == "Agent":
        parts = []
        if inp.get("description"):
            parts.append(inp["description"])
        if inp.get("subagent_type"):
            parts.append(f"({inp['subagent_type']})")
        return " ".join(parts) if parts else str(inp)[:500]
    if name == "Skill":
        return f"`{inp.get('skill', '')}`"
    s = json.dumps(inp, ensure_ascii=False, indent=2)
    if len(s) > 500:
        s = s[:500] + "\n..."
    return f"```json\n{s}\n```"


def export_session(session_path: Path, fmt: str = "clean", lang: str = "en") -> str:
    """Parse session JSONL and produce Markdown.

    fmt: "clean" (default), "full", or "conversation"
    lang: "en" (default) or "zh"
    """
    L = LABELS.get(lang, LABELS["en"])
    lines_out = []
    metadata = {"slug": None, "session_id": None, "project": None, "date": None}
    current_speaker = None

    with open(session_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Extract metadata from early entries
            if not metadata["slug"] and entry.get("slug"):
                metadata["slug"] = entry["slug"]
            if not metadata["session_id"] and entry.get("sessionId"):
                metadata["session_id"] = entry["sessionId"]
            if not metadata["project"] and entry.get("cwd"):
                metadata["project"] = entry["cwd"]
            if not metadata["date"] and entry.get("timestamp"):
                ts = entry["timestamp"]
                if isinstance(ts, str):
                    metadata["date"] = ts[:16].replace("T", " ")
                elif isinstance(ts, (int, float)):
                    dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).astimezone()
                    metadata["date"] = dt.strftime("%Y-%m-%d %H:%M")

            entry_type = entry.get("type", "")

            if entry_type in ("permission-mode", "system", "attachment",
                              "file-history-snapshot", "queue-operation"):
                continue

            if entry.get("isMeta"):
                continue

            message = entry.get("message")
            if not message:
                continue

            role = message.get("role", "")
            content = message.get("content")
            if content is None:
                continue

            # --- User message ---
            if entry_type == "user" and role == "user":
                if isinstance(content, str):
                    if current_speaker != "user":
                        lines_out.append(f"\n## {L['user']}\n")
                        current_speaker = "user"
                    lines_out.append(content)
                    lines_out.append("")
                elif isinstance(content, list):
                    has_tool_result = any(
                        isinstance(b, dict) and b.get("type") == "tool_result"
                        for b in content
                    )
                    if has_tool_result:
                        continue
                    texts = [
                        b.get("text", "")
                        for b in content
                        if isinstance(b, dict) and b.get("type") == "text"
                    ]
                    if texts:
                        if current_speaker != "user":
                            lines_out.append(f"\n## {L['user']}\n")
                            current_speaker = "user"
                        lines_out.append("\n".join(texts))
                        lines_out.append("")

            # --- Assistant message ---
            elif entry_type == "assistant" and role == "assistant":
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    block_type = block.get("type", "")

                    if block_type == "thinking":
                        continue

                    if block_type == "text":
                        text = block.get("text", "").strip()
                        if not text:
                            continue
                        if current_speaker != "assistant":
                            lines_out.append(f"\n## {L['assistant']}\n")
                            current_speaker = "assistant"
                        lines_out.append(text)
                        lines_out.append("")

                    elif block_type == "tool_use":
                        if fmt == "conversation":
                            continue
                        if current_speaker != "assistant":
                            lines_out.append(f"\n## {L['assistant']}\n")
                            current_speaker = "assistant"
                        tool_name = block.get("name", "unknown")
                        tool_input = block.get("input", {})

                        if fmt == "clean":
                            compact = format_tool_compact(tool_name, tool_input)
                            lines_out.append(f"> {compact}")
                            lines_out.append("")
                        elif fmt == "full":
                            formatted = format_tool_full(tool_name, tool_input)
                            lines_out.append("<details>")
                            lines_out.append(f"<summary>{L['tool']}: {tool_name}</summary>\n")
                            lines_out.append(formatted)
                            lines_out.append("\n</details>\n")

    # Build header
    title = metadata["slug"] or (metadata["session_id"] or session_path.stem)[:8]
    header_lines = [f"# {L['session']}: {title}\n"]
    if metadata["date"]:
        header_lines.append(f"- **{L['date']}**: {metadata['date']}")
    if metadata["project"]:
        header_lines.append(f"- **{L['project']}**: {metadata['project']}")
    if metadata["session_id"]:
        header_lines.append(f"- **{L['session_id']}**: {metadata['session_id']}")
    header_lines.append("")
    header_lines.append("---")
    header_lines.append("")

    return "\n".join(header_lines + lines_out)


def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard. Returns True on success."""
    system = platform.system()
    try:
        if system == "Darwin":
            proc = subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        elif system == "Linux":
            # Try xclip first, then xsel
            try:
                proc = subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=text.encode("utf-8"), check=True,
                )
            except FileNotFoundError:
                proc = subprocess.run(
                    ["xsel", "--clipboard", "--input"],
                    input=text.encode("utf-8"), check=True,
                )
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
    parser.add_argument("--format", "-f", choices=FORMATS, default="clean",
                        help="Export format: clean (default), full, conversation")
    parser.add_argument("--lang", "-l", choices=list(LABELS.keys()), default="en",
                        help="Template language: en (default), zh")
    # Legacy flag
    parser.add_argument("--no-tools", action="store_true",
                        help="Alias for --format conversation")
    args = parser.parse_args()

    if args.no_tools:
        args.format = "conversation"

    projects_dir = Path.home() / ".claude" / "projects"
    session_path = find_session_file(args.query, projects_dir)

    if not session_path:
        print(f"No session found matching '{args.query}'", file=sys.stderr)
        print(f"Searched in: {projects_dir}", file=sys.stderr)
        sys.exit(1)

    markdown = export_session(session_path, fmt=args.format, lang=args.lang)
    line_count = markdown.count("\n")

    if args.clipboard:
        if copy_to_clipboard(markdown):
            print(f"Copied to clipboard ({line_count} lines, {len(markdown)} chars)",
                  file=sys.stderr)
        else:
            print("Failed to copy to clipboard, printing to stdout instead",
                  file=sys.stderr)
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
