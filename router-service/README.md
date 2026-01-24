# Agent Router Service

Routes coding tasks to optimal AI CLI tools (Codex, Cursor, Gemini, Copilot) using NVIDIA's prompt-task-and-complexity-classifier model hosted locally.

## Setup

### 1. Install Dependencies

```bash
cd router-service
pip install -r requirements.txt
```

**Note**: First run will download the NVIDIA model (~500MB). This happens once.

### 2. Start the Service

```bash
uvicorn router:app --host 127.0.0.1 --port 8765
```

Or run directly:
```bash
python router.py
```

### 3. Verify It's Running

```bash
curl http://127.0.0.1:8765/health
```

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
- `context` (optional): Additional context
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
  "task_analysis": {...},
  "alternative_agents": [...],
  "recommended_flags": {"sandbox": "workspace-write", "reasoning": "high"}
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
Health check.

## Agent Capabilities

| Agent | Best For | Speed | Cost |
|-------|----------|-------|------|
| codex | Complex code gen, debugging, math | Slow | High |
| cursor | Repo-aware edits, refactoring | Medium | Medium |
| gemini | Analysis, explanation, QA | Fast | Low |
| copilot | Simple code tasks, quick fixes | Fast | Low |

## Task Types Recognized

The NVIDIA classifier recognizes:
- brainstorm, chat, classify, closed_qa
- **code_generation**, **code_explanation**, **code_debugging**, **code_review**
- extraction, math, open_qa, rewrite, summarization, other

## Integration with Claude Code

Use the `model-router` skill in Claude Code:

```
Use the model-router skill to route this task: "Implement user authentication"
```

Or invoke directly via the Task tool with the appropriate driver agent.

## Architecture

```
User Request
    ↓
Router Service (this)
    ├── NVIDIA Classifier (task type + complexity)
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
