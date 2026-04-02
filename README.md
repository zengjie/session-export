# session-export

English | [中文](README.zh-CN.md)

A Claude Code skill that exports conversation sessions to readable Markdown.

## Install

```bash
git clone https://github.com/zengjie/session-export.git ~/.claude/skills/session-export
```

Or symlink from a local checkout:

```bash
ln -s /path/to/this/repo ~/.claude/skills/session-export
```

## Requirements

- Python 3.8+ (stdlib only, no external dependencies)
- Claude Code CLI
- `pbcopy` (macOS) or `xclip`/`xsel` (Linux) for clipboard support

## Usage

Just ask Claude in natural language -- no need to memorize slash commands:

> "Export my last session to markdown"
> "Save this conversation to a file"
> "Show me my recent sessions"

Or use the slash command directly:

```
/session-export                    # Interactive: pick session and destination
/session-export <id>               # Quick export to clipboard
/session-export <slug>             # Export by slug name
/session-export <id> output.md     # Export to file
```

## Export Format

Each export contains two sections:

- **Summary** -- numbered list of user messages with anchor links for quick navigation
- **Transcript** -- full conversation with tool calls shown as `[Tool: args]`

## Standalone

```bash
python3 scripts/list_sessions.py --limit 20
python3 scripts/list_sessions.py --json --limit 4
python3 scripts/export_session.py <id-or-slug> --clipboard
python3 scripts/export_session.py <id-or-slug> --lang zh --output session.md
```
