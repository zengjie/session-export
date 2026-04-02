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
/session-export                    # Interactive: pick session, format, destination
/session-export <id>               # Quick export to clipboard (clean format)
/session-export <slug>             # Export by slug name
/session-export <id> output.md     # Export to file
```

### Formats

| Format | Description |
|--------|-------------|
| `clean` (default) | Conversation + one-line tool summaries |
| `full` | Conversation + collapsible tool detail blocks |
| `conversation` | Text only, no tool information |

### Destinations

| Destination | Description |
|-------------|-------------|
| Clipboard (default) | Copies Markdown to system clipboard |
| Current directory | Saves `{slug}.md` in working directory |
| Downloads | Saves to `~/Downloads/{slug}.md` |

## Standalone

```bash
python3 scripts/list_sessions.py --limit 20
python3 scripts/list_sessions.py --json --limit 4
python3 scripts/export_session.py <id-or-slug> --format clean --clipboard
python3 scripts/export_session.py <id-or-slug> --format full --output session.md
```
