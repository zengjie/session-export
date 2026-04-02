---
name: session-export
version: "2.1"
description: "Export Claude Code sessions to readable Markdown. Use when: 'export session', 'session to markdown', 'list sessions', 'show my sessions', 'session history', 'save conversation', 'export conversation', 'copy session'. Always use this skill when the user mentions exporting, saving, or sharing a Claude Code session, even if they don't say 'markdown' explicitly."
user-invocable: true
argument-hint: "[<session-id-or-slug>] [output-path]"
allowed-tools: Read, Bash, Write, AskUserQuestion
---

# /session-export

## Language Rule

Respond in the language the user used to invoke this skill. If the user wrote in Chinese, all your messages, AskUserQuestion labels, and descriptions should be in Chinese. If in English, use English. Match the user's language throughout.

## Argument Dispatch

| Invocation | Behavior |
|------------|----------|
| `/session-export` | Interactive flow (Steps 1-4 below) |
| `/session-export <id-or-slug>` | Direct: clipboard with clean format |
| `/session-export <id-or-slug> <path>` | Direct: save to file with clean format |

## Interactive Flow

**Step 0 -- Scope selection**

Before listing sessions, ask the user which sessions to show. Use AskUserQuestion:
- **Current project (Recommended)** -- only sessions from this working directory
- **All projects** -- sessions across the entire machine

For "Current project", pass `--project <cwd>` to the list script. For "All projects", omit `--project`.

If the user's request already implies a scope (e.g., "show all my sessions" or "show sessions for this project"), skip this question and use the implied scope.

**Step 1 -- List and select session**

```bash
python3 {SKILL_DIR}/scripts/list_sessions.py --json --limit 20 [--project <cwd>]
```

Parse the JSON output and present sessions via AskUserQuestion in pages of 4. Never show raw Bash output to the user -- it gets collapsed behind "ctrl+o to expand" in the terminal and is effectively invisible.

**Page 1:** Show the 4 most recent sessions. For each option:
- `label`: date + first ~25 chars of display
- `description`: project name
- `preview`: full session card showing date, project, display text, and ID

**Pagination:** If the user selects "Other", show the next 4 sessions (items 5-8) via another AskUserQuestion. Keep paginating until:
- The user selects a session, OR
- There are no more sessions to show, OR
- The user types a specific ID/slug in "Other"

When presenting a page beyond the first, include a note like "Showing sessions 5-8 of 20. Select 'Other' for more or type an ID/slug." in the description of the last option or as text before the question.

**Step 2 -- Select format**

Use AskUserQuestion with preview showing sample output for each format:
- **Clean (Recommended)** -- conversation + one-line tool summaries like `> **Bash**: \`cmd\``
- **Full** -- conversation + collapsible `<details>` tool blocks
- **Conversation** -- text only, no tool details

**Step 3 -- Select destination**

Use AskUserQuestion:
- **Clipboard (Recommended)** -- instant paste into docs, chats, or other LLMs
- **Current directory** -- saves `{slug-or-id}.md` alongside project files
- **Downloads** -- saves to `~/Downloads/{slug-or-id}.md`

**Step 4 -- Template language (conditional)**

This controls the language of structural labels in the exported Markdown (e.g., `## User` vs `## 用户`, `**Date**` vs `**日期**`). Conversation content is never translated.

ONLY ask this if the user invoked the skill in a non-English language. Skip entirely for English users (default to `--lang en`).

Use AskUserQuestion:
- **Original language (Recommended)** -- template labels match user's language (e.g., `## 用户` / `## 助手`)
- **English** -- template labels in English (e.g., `## User` / `## Assistant`)

Map selection to `--lang` flag: `zh` for Chinese labels, `en` for English.

Supported `--lang` values: `en`, `zh`. Default: `en`.

**Step 5 -- Export**

**Filename generation (for file destinations only):**

When saving to Current directory or Downloads, generate a descriptive filename from the session content -- NOT from the auto-generated slug (those are random words like `witty-leaping-lovelace`).

Rules for filename:
- Read the user's first message (available in `display` from the JSON listing or the exported Markdown)
- Derive a short English slug (3-5 words, kebab-case) that captures the session topic
- Examples: `skill-export-development.md`, `git-commit-analysis.md`, `bingo-adventure-design-review.md`, `auth-middleware-bugfix.md`
- If the first message is a slash command (like `/insights`), use the command name + project context
- Keep it under 50 chars (excluding `.md`)

Map destination to flags:

| Destination | Command |
|-------------|---------|
| Clipboard | `--clipboard` |
| Current directory | `--output {descriptive-slug}.md` |
| Downloads | `--output ~/Downloads/{descriptive-slug}.md` |

```bash
python3 {SKILL_DIR}/scripts/export_session.py <fullId> --format <fmt> --lang <lang> [flags]
```

After export, report: filename, destination, line count, and character count.

Replace `{SKILL_DIR}` with the base directory path shown when this skill loads.

## Gotchas

1. **Combine AskUserQuestion calls.** Steps 2+3 (format + destination) can be asked in a single AskUserQuestion call (two questions). Step 4 (language) is conditional and separate. Minimize round-trips.

2. **AskUserQuestion max 4 options.** Show the 4 most recent sessions. "Other" is automatic.

3. **Large exports.** If clipboard content > 100k chars, warn the user and suggest file output instead.

4. **Clipboard on Linux.** Requires `xclip` or `xsel`. If clipboard fails, the script falls back to stdout automatically.

5. **Translation scope.** When translating to English, only translate human-written text (user messages, assistant prose). Leave code, file paths, tool names, and commands unchanged.
