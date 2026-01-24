---
name: delegate
description: Intelligently routes and delegates coding tasks to the best AI agent (Codex, Cursor, Gemini, Copilot). Use /delegate <task> to automatically pick the optimal agent based on task type and complexity.
user-invocable: true
---

# Delegate Skill

Routes coding tasks to the optimal AI CLI agent and delegates execution.

## Usage

```
/delegate <task description>
```

## Examples

```
/delegate Fix the authentication bug in login.py
/delegate Write a REST API endpoint for user registration
/delegate Explain how the caching system works
/delegate Refactor the payment module to use async/await
```

## How It Works

When invoked, this skill:

1. **Routes the task** by calling the router service
2. **Selects the best agent** based on task type and complexity
3. **Delegates to the driver** and returns results

## Execution Steps

### Step 1: Check Router Service

```bash
curl -s http://127.0.0.1:8765/health
```

If the router is not running, inform the user:
> "The router service is not running. Start it with: `cd ~/agent-skills/router-service && uvicorn router:app --host 127.0.0.1 --port 8765`"

### Step 2: Route the Task

```bash
curl -s -X POST http://127.0.0.1:8765/route \
  -H "Content-Type: application/json" \
  -d '{"prompt": "<task from user>"}'
```

### Step 3: Parse Response

The router returns:
```json
{
  "selected_agent": "codex|cursor|gemini|copilot",
  "confidence": 0.80,
  "reasoning": "Task type 'X' with Y complexity...",
  "task_analysis": {
    "task_type": "code_debugging|code_generation|...",
    "complexity": "simple|moderate|complex"
  },
  "recommended_flags": {...}
}
```

### Step 4: Inform User and Delegate

Tell the user which agent was selected and why:
> "Routing to **{agent}**: {reasoning}"

Then delegate using the Task tool with the appropriate driver:
- `selected_agent: "codex"` → use `codex-driver` agent
- `selected_agent: "cursor"` → use `cursor-driver` agent
- `selected_agent: "gemini"` → use `gemini-driver` agent
- `selected_agent: "copilot"` → use `copilot-driver` agent

### Step 5: Return Results

Return the agent's output to the user. If output is very long, consider using the compress endpoint:

```bash
curl -s -X POST http://127.0.0.1:8765/compress \
  -H "Content-Type: application/json" \
  -d '{"content": "<output>", "level": "moderate"}'
```

## Agent Capabilities Reference

| Agent | Best For |
|-------|----------|
| codex | Complex code gen, debugging, math, algorithms |
| cursor | Repo-aware edits, refactoring, code review |
| gemini | Explanation, analysis, summarization, Q&A |
| copilot | Simple/fast code generation, quick fixes |

## Router Service Setup

The router service must be running. Install globally:

```bash
# One-time setup
git clone https://github.com/sjarmak/agent-skills.git ~/agent-skills
cd ~/agent-skills/router-service
pip install -r requirements.txt

# Start the router (add to shell startup for convenience)
uvicorn router:app --host 127.0.0.1 --port 8765 &
```

## Fallback Behavior

If router is unavailable:
- Default to `gemini-driver` for explanation/analysis tasks
- Default to `cursor-driver` for code modification tasks
- Inform user that routing is unavailable
