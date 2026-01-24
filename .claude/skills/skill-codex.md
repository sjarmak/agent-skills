---
name: codex
description: Translates task requirements into Codex CLI commands. Used by codex-driver agent to execute coding tasks via OpenAI Codex.
---

# Codex Skill Guide

## Baseline Rules

Always apply these to every `codex exec` command:
- `--skip-git-repo-check` — required for all commands
- `2>/dev/null` — suppresses thinking tokens (omit only if debugging)
- `--full-auto` — required when using `workspace-write` or `danger-full-access` sandbox

## Command Templates

### New Task
```bash
codex exec --skip-git-repo-check --sandbox <MODE> [options] "<prompt>" 2>/dev/null
```

### Resume Session
```bash
echo "<prompt>" | codex exec --skip-git-repo-check resume --last 2>/dev/null
```
Note: When resuming, do not include model/sandbox flags — the session inherits its original settings. Flags must go between `exec` and `resume`.

## Sandbox Modes

| Task Type | Mode | Notes |
| --- | --- | --- |
| Analysis, review, Q&A | `--sandbox read-only` | No file modifications allowed |
| Create or edit files | `--sandbox workspace-write --full-auto` | Standard for most coding tasks |
| Network access needed | `--sandbox danger-full-access --full-auto` | Confirm with user first |

## Model Selection

When the calling agent specifies requirements, translate to flags:

| Requirement | Flag | Notes |
| --- | --- | --- |
| Default | `-m gpt-5.2-codex` | Optimized for code tasks |
| General-purpose | `-m gpt-5.2` | Non-code or mixed tasks |

| Complexity | Flag | Notes |
| --- | --- | --- |
| Complex / multi-step | `--config model_reasoning_effort="xhigh"` | Architectural decisions, large refactors |
| Standard (default) | `--config model_reasoning_effort="high"` | Most coding tasks |
| Simple | `--config model_reasoning_effort="medium"` | Straightforward edits |
| Trivial | `--config model_reasoning_effort="low"` | Quick fixes, formatting |

If not specified, use defaults: `gpt-5.2-codex` with `high` reasoning.

## Interpreting Results

### Success indicators
- Codex reports files created/modified
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

Report to user: "You can resume this Codex session by saying 'codex resume'."

## Error Handling

- If command exits non-zero: stop and report the error
- If output contains warnings: summarize and ask how to proceed
- Before `danger-full-access`: confirm with user unless pre-authorized
