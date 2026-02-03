# Agent Router Service

Routes coding tasks to optimal AI CLI tools (Codex, Cursor, Gemini, Copilot) using a fast, optimized rule-based classifier.

## Quick Start

```bash
# Install dependencies (one-time)
cd router-service
pip install -r requirements.txt

# Start the service
uvicorn router:app --host 127.0.0.1 --port 8765

# Verify it's running
curl http://127.0.0.1:8765/health
```

The service starts immediately—no model download required.

## How It Works

The router uses an optimized rule-based classifier that:
- Classifies task type using keyword patterns (debugging, generation, explanation, etc.)
- Estimates complexity from multiple signals (prompt length, technical depth, requirements count)
- Selects the best agent based on task/complexity match
- Returns in ~1ms with no startup overhead

## API Endpoints

### POST /route

Routes a task to the best agent.

```bash
curl -s -X POST http://127.0.0.1:8765/route \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Fix the authentication bug in login.py"}' | jq
```

**Request body:**
- `prompt` (required): The task description
- `prefer_speed` (optional): Prefer faster agents
- `prefer_cost` (optional): Prefer cheaper agents
- `exclude_agents` (optional): List of agents to exclude
- `force_agent` (optional): Force a specific agent

**Response:**
```json
{
  "selected_agent": "codex",
  "confidence": 0.85,
  "reasoning": "Task type 'code_debugging' with complex complexity. Codex excels at code_debugging.",
  "task_analysis": {
    "task_type": "code_debugging",
    "complexity": "moderate",
    "all_scores": {"classifier": "rule_based_v2", "task_signals": ["debug_keywords:2"]}
  },
  "alternative_agents": [...],
  "recommended_model": "claude-opus-4.5",
  "recommended_mode": "--mode agent",
  "specialized_task": null
}
```

### POST /classify

Classify a task without routing decision.

```bash
curl -s -X POST http://127.0.0.1:8765/classify \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain how the auth module works"}' | jq
```

### POST /compress

Compress agent output to reduce token usage.

```bash
curl -s -X POST http://127.0.0.1:8765/compress \
  -H "Content-Type: application/json" \
  -d '{"content": "<long agent output>", "level": "moderate", "max_tokens": 2000}' | jq
```

**Compression levels:**
- `minimal`: Light whitespace cleanup
- `moderate`: Remove verbose explanations, keep code and key info
- `aggressive`: Only code blocks, errors, and action summaries

### GET /agents

List available agents and capabilities.

### GET /health

Health check—also shows which classifier is active.

## Agent Capabilities

| Agent | Best For | Speed | Cost |
|-------|----------|-------|------|
| codex | Complex code gen, debugging, math | Slow | High |
| cursor | Repo-aware edits, refactoring | Medium | Medium |
| gemini | Analysis, explanation, QA | Fast | Low |
| copilot | Simple code tasks, quick fixes | Fast | Low |

## Task Types

The classifier recognizes these task types:

**Code-specific:**
- `code_generation` - Write, create, implement code
- `code_explanation` - Explain how code works
- `code_debugging` - Fix bugs, errors, crashes
- `code_review` - Review, audit, security check

**General:**
- `rewrite` - Refactor, restructure, improve
- `summarization` - Summarize, overview, tldr
- `math` - Calculate, algorithm, complexity
- `open_qa` - General questions

## Architecture

```
User Request
    ↓
Router Service (this)
    ├── Rule-Based Classifier (task type + complexity)
    └── Agent Selection (match capabilities)
    ↓
Routing Decision
    ├── Selected Agent
    ├── Recommended Flags
    └── Alternatives
    ↓
Driver Agent (cursor-driver, codex-driver, etc.)
    ↓
AI CLI Execution
    ↓
Context Compression (optional)
    ↓
Result to Claude Code
```

## Integration with Claude Code

The `/delegate` command in Claude Code uses this service automatically:

```
/delegate Fix the authentication bug in login.py
```

Or use the `model-router` skill directly for more control.

## Development

Run tests (requires `pytest`, install with `pip install pytest`):
```bash
python -m pytest test_router.py -v
```

Run with debug output:
```bash
curl -s -X POST http://127.0.0.1:8765/route \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Fix bug", "debug": true}'
```
