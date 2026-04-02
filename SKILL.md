---
name: session-export
version: "3.0"
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
| `/session-export <id-or-slug>` | Direct: clipboard with default lang |
| `/session-export <id-or-slug> <path>` | Direct: save to file |

## Interactive Flow

**Step 1 -- Scope selection**

Before listing sessions, ask the user which sessions to show. Use AskUserQuestion:
- **Current project (Recommended)** -- only sessions from this working directory
- **All projects** -- sessions across the entire machine

For "Current project", pass `--project <cwd>` to the list script. For "All projects", omit `--project`.

If the user's request already implies a scope (e.g., "show all my sessions" or "show sessions for this project"), skip this question and use the implied scope.

**Step 2 -- List and select session**

```bash
python3 {SKILL_DIR}/scripts/list_sessions.py --json --limit 20 [--project <cwd>]
```

Parse the JSON output and present ALL sessions as a numbered list in your text response. Format as a compact table:

```
 #  Date        Project                   First Message
 1  04-02 21:34 playground/session-export  使用 /skill-creator 开发导出 Skill...
 2  04-02 21:32 playground/session-export  导出历史
 3  04-02 20:11 src/client                 /insights
 ...
```

Then ask the user to type a number to select. The user replies with just a number (e.g., `3`), and you map it to the corresponding session ID.

**Never** present sessions via raw Bash output -- it gets collapsed behind "ctrl+o to expand" in the terminal and is effectively invisible. Always parse `--json` first and format the list yourself.

**Step 3 -- Select destination and language**

Use AskUserQuestion with two questions in one call:

Question 1 -- Destination:
- **Clipboard (Recommended)** -- instant paste into docs, chats, or other LLMs
- **Current directory** -- saves alongside project files
- **Downloads** -- saves to `~/Downloads/`

Question 2 -- Template language (ONLY if user invoked in non-English; skip for English users):
- **Original language (Recommended)** -- labels match user's language (e.g., `### 用户` / `### 助手`)
- **English** -- labels in English (e.g., `### User` / `### Assistant`)

**Step 4 -- Export**

**Filename generation (for file destinations only):**

When saving to Current directory or Downloads, generate a descriptive filename from the session content -- NOT from the auto-generated slug (those are random words like `witty-leaping-lovelace`).

Rules for filename:
- Read the user's first message (available in `display` from the JSON listing or the exported Markdown)
- Derive a short English slug (3-5 words, kebab-case) that captures the session topic
- Examples: `skill-export-development.md`, `git-commit-analysis.md`, `bingo-adventure-design-review.md`
- If the first message is a slash command (like `/insights`), use the command name + project context
- Keep it under 50 chars (excluding `.md`)

Map destination to flags:

| Destination | Command |
|-------------|---------|
| Clipboard | `--clipboard` |
| Current directory | `--output {descriptive-slug}.md` |
| Downloads | `--output ~/Downloads/{descriptive-slug}.md` |

```bash
python3 {SKILL_DIR}/scripts/export_session.py <fullId> --lang <lang> [flags]
```

After export, report: filename, destination, line count, and character count.

Replace `{SKILL_DIR}` with the base directory path shown when this skill loads.

## Gotchas

1. **Session list goes in text, not AskUserQuestion.** AskUserQuestion is limited to 4 options, too few for session lists. Present the numbered list as formatted text and let the user type a number.

2. **Large exports.** If clipboard content > 100k chars, warn the user and suggest file output instead.

3. **Clipboard on Linux.** Requires `xclip` or `xsel`. If clipboard fails, the script falls back to stdout automatically.

4. **Tool markers use 4-space indent + brackets.** The `    [Tool: args]` notation renders as a code block in Markdown, avoiding conflicts with content that might contain blockquotes, headings, or HTML tags.

5. **Export has two sections.** The script outputs a Summary (numbered user messages with anchor links) followed by a full Transcript. No format flag needed.
