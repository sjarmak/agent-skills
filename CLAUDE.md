# Claude Code Project Instructions

This project provides intelligent routing and delegation of coding tasks to external AI CLI tools.

## Available Agents

You have access to these driver agents for delegating coding work:

| Agent | Use For |
|-------|---------|
| `codex-driver` | Complex code generation, debugging, math/algorithms |
| `cursor-driver` | Repo-aware edits, refactoring, code review |
| `gemini-driver` | Explanation, analysis, summarization, Q&A |
| `copilot-driver` | Simple/fast code generation, quick fixes |

## Automatic Task Routing

**Before delegating any coding task**, use the router service to determine the optimal agent.

### Step 1: Route the Task

```bash
curl -s -X POST http://127.0.0.1:8765/route \
  -H "Content-Type: application/json" \
  -d '{"prompt": "<user's task description>"}'
```

The response tells you which agent to use:
```json
{
  "selected_agent": "codex",
  "reasoning": "Task type 'code_debugging' with moderate complexity...",
  "recommended_flags": {"sandbox": "workspace-write", "reasoning": "medium"}
}
```

### Step 2: Delegate to the Selected Agent

Based on `selected_agent`, invoke the corresponding driver:

- `"codex"` → `@"codex-driver (agent)" <task>`
- `"cursor"` → `@"cursor-driver (agent)" <task>`
- `"gemini"` → `@"gemini-driver (agent)" <task>`
- `"copilot"` → `@"copilot-driver (agent)" <task>`

### Step 3: Compress Output (Optional)

If the agent returns verbose output, compress it before showing the user:

```bash
curl -s -X POST http://127.0.0.1:8765/compress \
  -H "Content-Type: application/json" \
  -d '{"content": "<agent output>", "level": "moderate"}'
```

## When to Route

Use routing for these types of requests:
- "Fix this bug..."
- "Write a function that..."
- "Explain how this code works..."
- "Refactor this to..."
- "Review this code for..."
- Any coding task the user wants delegated

## When NOT to Route

Skip routing for:
- Simple questions you can answer directly
- File reading/exploration (use your own tools)
- Non-coding tasks
- When the user specifically requests a particular agent

## Router Service

The router must be running at `http://127.0.0.1:8765`. Check with:
```bash
curl -s http://127.0.0.1:8765/health
```

If the router is down, default to `gemini-driver` (most versatile).

## Quick Reference

| Task Type | Typical Agent |
|-----------|---------------|
| Fix bug, debug error | codex (complex) or copilot (simple) |
| Write new code | copilot (simple) or cursor (moderate) or codex (complex) |
| Explain code | gemini or cursor |
| Review/audit code | cursor |
| Refactor code | cursor |
| Summarize changes | gemini |
| Algorithm/math | codex |

## Example Workflow

User: "Fix the authentication bug in the login handler"

1. Route the task:
   ```bash
   curl -s -X POST http://127.0.0.1:8765/route \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Fix the authentication bug in the login handler"}'
   ```

2. Response: `{"selected_agent": "codex", ...}`

3. Delegate:
   ```
   @"codex-driver (agent)" Fix the authentication bug in the login handler
   ```

4. Return the result to the user (compress if needed)
