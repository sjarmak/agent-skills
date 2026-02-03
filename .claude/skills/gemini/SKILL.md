---
name: gemini
description: Translates task requirements into Gemini CLI commands. Used by gemini-driver agent to execute coding tasks via Google Gemini.
---

# Gemini CLI Skill Guide

## PATH Setup (CRITICAL)

Subagents run with a minimal PATH. Always include mise/node paths:

```bash
export PATH="$HOME/.local/share/mise/installs/node/24.13.0/bin:$HOME/.local/bin:$PATH" && gemini <args>
```

## Baseline Rules

Always apply these for programmatic (headless) execution:
- `-p "<prompt>"` — required for headless mode
- `--yolo` — required when creating or editing files (auto-approves actions)
- `--output-format json` — recommended for programmatic processing

## Command Templates

### New Task (read-only)
```bash
export PATH="$HOME/.local/share/mise/installs/node/24.13.0/bin:$HOME/.local/bin:$PATH" && NODE_OPTIONS="--no-warnings" gemini -p "<prompt>"
```

### New Task (with file edits)
```bash
export PATH="$HOME/.local/share/mise/installs/node/24.13.0/bin:$HOME/.local/bin:$PATH" && NODE_OPTIONS="--no-warnings" gemini -p "<prompt>" --yolo
```

### New Task (with additional directories)
```bash
export PATH="$HOME/.local/share/mise/installs/node/24.13.0/bin:$HOME/.local/bin:$PATH" && NODE_OPTIONS="--no-warnings" gemini -p "<prompt>" --yolo --include-directories src,lib
```

### Pipe file content
```bash
export PATH="$HOME/.local/share/mise/installs/node/24.13.0/bin:$HOME/.local/bin:$PATH" && cat <file> | NODE_OPTIONS="--no-warnings" gemini -p "<prompt describing what to do with the content>"
```

### Resume Session
```bash
export PATH="$HOME/.local/share/mise/installs/node/24.13.0/bin:$HOME/.local/bin:$PATH" && NODE_OPTIONS="--no-warnings" gemini --resume latest -p "<prompt>"
```
Note: Use `--resume latest` for most recent session, or `--resume <id>` for a specific session. Use `--list-sessions` to see available sessions.

### JSON output for parsing
```bash
export PATH="$HOME/.local/share/mise/installs/node/24.13.0/bin:$HOME/.local/bin:$PATH" && NODE_OPTIONS="--no-warnings" gemini -p "<prompt>" --output-format json | jq -r '.response'
```

## Approval Modes

| Task Type | Flags | Notes |
| --- | --- | --- |
| Analysis, review, Q&A | (none) | Read-only by default |
| Create or edit files | `--yolo` | Auto-approves all actions |
| Controlled edits | `--approval-mode auto_edit` | Auto-approve edits only |

## Model Selection

When the calling agent specifies requirements, translate to flags:

| Requirement | Flag | Notes |
| --- | --- | --- |
| Default / high-quality | `-m gemini-2.5-pro` | Best for complex reasoning |
| Fast / cheap | `-m gemini-2.5-flash` | Quick, straightforward tasks |

If not specified, use default model (no flag needed).

## Output Formats

| Format | Flag | Use Case |
| --- | --- | --- |
| Text (default) | (none) | Human-readable output |
| JSON | `--output-format json` | Programmatic processing, includes stats |
| Streaming JSON | `--output-format stream-json` | Real-time monitoring, live UI |

### JSON Response Structure
```json
{
  "response": "The AI-generated content",
  "stats": { "models": {...}, "tools": {...}, "files": {...} },
  "error": { "type": "...", "message": "..." }  // only if error occurred
}
```

## File References

Pipe file content to Gemini:
```bash
export PATH="$HOME/.local/share/mise/installs/node/24.13.0/bin:$HOME/.local/bin:$PATH" && cat src/config.ts | gemini -p "Explain this configuration"
```

Or use `--include-directories` to give Gemini access:
```bash
export PATH="$HOME/.local/share/mise/installs/node/24.13.0/bin:$HOME/.local/bin:$PATH" && gemini -p "Analyze the authentication module" --include-directories src/auth
```

## Interpreting Results

### Success indicators
- JSON output has `response` field with content
- No `error` field in JSON output
- `stats.files.totalLinesAdded` > 0 for edit tasks

### Failure indicators
- Non-zero exit code
- JSON output contains `error` field
- `error.type` indicates failure category (ApiError, AuthError, etc.)

### Scope creep indicators
- Mentions of "I also..." or "While I was at it..."
- `stats.files` shows changes to unexpected files
- Response describes work beyond the original request

### Redirection indicators
- Output describes different work than requested
- "Instead of X, I did Y..."
- Solving a different problem than specified

## After Completion

Report to user: "You can resume this Gemini session by saying 'gemini resume'."

### Session Management
- `--list-sessions` — Show all recorded sessions
- `--resume latest` — Resume most recent session
- `--resume <id>` — Resume specific session by ID
- `--delete-session <id>` — Remove a session

## Error Handling

- If command exits non-zero: stop and report the error
- If JSON contains `error` field: report `error.type` and `error.message`
- If output contains warnings: summarize and ask how to proceed
- Before `--yolo`: confirm with user unless pre-authorized

## Reference

### Useful Patterns

```bash
# Set PATH for all commands
export PATH="$HOME/.local/share/mise/installs/node/24.13.0/bin:$HOME/.local/bin:$PATH"

# Code review
cat src/auth.py | gemini -p "Review for security issues"

# Generate commit message
git diff --cached | gemini -p "Write a concise commit message"

# Batch analysis
for file in src/*.py; do
    cat "$file" | gemini -p "Find bugs" --output-format json | jq -r '.response'
done
```

### Debug Mode

Add `--debug` or `-d` for verbose output when troubleshooting.
