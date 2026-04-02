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

用自然语言对 Claude 说就行，无需记忆斜杠命令：

> "帮我导出上一个会话"
> "把这个对话保存成 Markdown"
> "看看我最近的会话记录"

也可以直接使用斜杠命令：

```
/session-export                    # 交互模式：选择会话和导出位置
/session-export <id>               # 快速导出到剪贴板
/session-export <slug>             # 通过 slug 名称导出
/session-export <id> output.md     # 导出到文件
```

## 导出格式

每份导出包含两个部分：

- **摘要** -- 用户消息编号列表，带锚点链接可快速跳转到对应位置
- **记录** -- 完整对话记录，工具调用以 `[Tool: args]` 格式展示

### 模板语言

导出文件的结构标签支持中英文切换（`--lang zh` / `--lang en`）：

| `--lang en` | `--lang zh` |
|---|---|
| `### User` | `### 用户` |
| `### Assistant` | `### 助手` |
| `## Summary` | `## 摘要` |

## 独立使用（无需 Claude Code）

```bash
python3 scripts/list_sessions.py --limit 20
python3 scripts/list_sessions.py --json --limit 4
python3 scripts/export_session.py <id-or-slug> --clipboard
python3 scripts/export_session.py <id-or-slug> --lang zh --output session.md
```
