# session-export

[English](README.md) | 中文

一个 Claude Code 技能，用于将会话导出为可读的 Markdown 文件。

## 安装

```bash
git clone https://github.com/zengjie/session-export.git ~/.claude/skills/session-export
```

或从本地目录创建符号链接：

```bash
ln -s /path/to/this/repo ~/.claude/skills/session-export
```

## 环境要求

- Python 3.8+（仅使用标准库，无需安装额外依赖）
- Claude Code CLI
- `pbcopy` (macOS) 或 `xclip`/`xsel` (Linux) 用于剪贴板支持

## 使用方法

在 Claude Code 中：

```
/session-export                    # 交互模式：选择会话、格式和导出位置
/session-export <id>               # 快速导出到剪贴板（clean 格式）
/session-export <slug>             # 通过 slug 名称导出
/session-export <id> output.md     # 导出到文件
```

### 导出格式

| 格式 | 说明 |
|------|------|
| `clean`（默认） | 对话内容 + 单行工具摘要 |
| `full` | 对话内容 + 可折叠的工具详情块 |
| `conversation` | 仅文本，不包含工具信息 |

### 导出位置

| 位置 | 说明 |
|------|------|
| 剪贴板（默认） | 将 Markdown 复制到系统剪贴板 |
| 当前目录 | 保存为 `{描述性文件名}.md` |
| Downloads | 保存到 `~/Downloads/{描述性文件名}.md` |

### 模板语言

导出文件的结构标签支持中英文切换：

| `--lang en` | `--lang zh` |
|---|---|
| `## User` | `## 用户` |
| `## Assistant` | `## 助手` |
| `**Date**` | `**日期**` |

交互模式下，如果你用中文调用技能，会自动询问模板语言偏好。

## 独立使用（无需 Claude Code）

```bash
python3 scripts/list_sessions.py --limit 20
python3 scripts/list_sessions.py --json --limit 4
python3 scripts/export_session.py <id-or-slug> --format clean --clipboard
python3 scripts/export_session.py <id-or-slug> --format clean --lang zh --output session.md
```
