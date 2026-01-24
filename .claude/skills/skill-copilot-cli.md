---
name: copilot
description: Translates task requirements into GitHub Copilot CLI commands. Used by copilot-driver agent to execute coding tasks via Copilot.
---

# GitHub Copilot CLI Skill Guide

## Baseline Rules

Always apply these for programmatic (non-interactive) execution:
- `-p "<prompt>"` — required for single-command execution
- `--allow-all-paths` — required when creating or editing files

## Command Templates

### New Task (read-only)
```bash
copilot -p "<prompt>"
```

### New Task (with file edits)
```bash
copilot -p "<prompt>" --allow-all-paths
```

### New Task (with URL access)
```bash
copilot -p "<prompt>" --allow-all-paths --allow-all-urls
```

### Resume Session
```bash
copilot --continue
```
Note: Session inherits its original model and permissions. Use `-p "<prompt>"` with `--continue` if providing a new prompt.

## Permission Modes

| Task Type | Flags | Notes |
| --- | --- | --- |
| Analysis, review, Q&A | (none) | Read-only by default |
| Create or edit files | `--allow-all-paths` | Standard for most coding tasks |
| Access specific URL | `--allow-url <domain>` | e.g., `--allow-url github.com` |
| Access any URL | `--allow-all-urls` | Confirm with user first |

## Model Selection

When the calling agent specifies requirements, translate to flags:

| Requirement | Flag | Notes |
| --- | --- | --- |
| Default / balanced | `--model claude-sonnet-4.5` | Standard coding tasks (1x cost) |
| Fast / cheap | `--model claude-haiku-4.5` | Quick, straightforward tasks (0.33x cost) |
| Complex / high-quality | `--model claude-opus-4.5` | Multi-step problems, nuanced reasoning (3x cost) |
| OpenAI | `--model gpt-5.2-codex` | OpenAI's code model (1x cost) |
| Google | `--model gemini-3-pro` | Google's model (1x cost) |

If not specified, use default: `claude-sonnet-4.5`.

## File References

Reference files in prompts using `@` syntax:
```bash
copilot -p "Explain @src/config/settings.ts"
```

## Interpreting Results

### Success indicators
- Copilot reports files created/modified
- Output describes completed actions matching the request
- No error messages or stack traces

### Failure indicators
- Non-zero exit code
- Error messages in output
- "I cannot" or "I'm unable to" language
- Partial completion ("I've started but...")

### Scope creep indicators
- Mentions of "I also..." or "While I was at it..."
- Changes to files not mentioned in the original request
- Added features, tests, or documentation not requested

### Redirection indicators
- Output describes different work than requested
- "Instead of X, I did Y..."
- Solving a different problem than specified

## After Completion

Report to user: "You can resume this Copilot session by saying 'copilot continue'."

## Error Handling

- If command exits non-zero: stop and report the error
- If output contains warnings: summarize and ask how to proceed
- Before `--allow-all-urls`: confirm with user unless pre-authorized

## Reference

### Built-in Sub-Agents

Copilot automatically delegates to internal sub-agents (not configurable via flags):

| Sub-agent | Used for |
| --- | --- |
| `explore` | Fast codebase exploration and Q&A |
| `task` | Executing commands (tests, builds, installs) |
| `general-purpose` | Complex multi-step tasks |
| `code-review` | Reviewing code changes |

### Interactive Mode Commands

For interactive sessions (not programmatic), these slash commands are available:

| Command | Function |
| --- | --- |
| `/model` | Select AI model |
| `/agent` | Select custom agent |
| `/delegate [prompt]` | Hand off to GitHub Copilot coding agent |
| `/context` | View token usage |
| `/compact` | Compress conversation history |
