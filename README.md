# Agent Skills

A collection of Claude Code skills and sub-agents for delegating coding tasks to external AI CLI tools (Codex, GitHub Copilot, Gemini, and Cursor).

## Overview

This repository provides a **"driver" pattern** for Claude Code: instead of doing coding work directly, Claude delegates tasks to other AI assistants (Codex, Copilot, Gemini, or Cursor) and manages them like a Technical Program Manager—ensuring work stays on-spec, rejecting scope creep, and iterating until the goal is fully achieved.

**New:** Includes intelligent routing via an optimized rule-based classifier to automatically select the best agent for each task.

Started from and inspired by: [skills-directory/skill-codex](https://github.com/skills-directory/skill-codex)

## What's Included

### Skills (`.claude/skills/`)

Skills teach Claude Code how to use each CLI tool:

| Skill | Description |
|-------|-------------|
| `codex` | Command syntax, sandbox modes, and model selection for OpenAI Codex CLI |
| `copilot` | Flags, permissions, and model options for GitHub Copilot CLI |
| `gemini` | Headless execution, output formats, and session management for Google Gemini CLI |
| `cursor` | Mode selection, model options, and session management for Cursor AI CLI |
| `model-router` | **Intelligent routing** using NVIDIA's prompt classifier to select the best agent |

### Sub-Agents (`.claude/agents/`)

Sub-agents are specialized Claude instances that use the skills to drive each CLI:

| Agent | Description |
|-------|-------------|
| `codex-driver` | Drives Codex CLI to complete coding tasks |
| `copilot-driver` | Drives GitHub Copilot CLI to complete coding tasks |
| `gemini-driver` | Drives Gemini CLI to complete coding tasks |
| `cursor-driver` | Drives Cursor AI CLI to complete coding tasks |

Each driver agent:
- Owns the goal and doesn't let it drift
- Rejects scope creep (unrequested additions)
- Catches redirection (wrong work being done)
- Iterates until the exact deliverable is achieved
- Verifies results before reporting completion

## Usage

### Prerequisites

Install the CLI tools you want to use:

- **OpenAI Codex**: [github.com/openai/codex](https://github.com/openai/codex)
- **GitHub Copilot CLI**: [github.com/github/copilot-cli](https://github.com/github/copilot-cli)
- **Google Gemini CLI**: [github.com/google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli)
- **Cursor CLI**: [cursor.com](https://cursor.com)

### Activating in Claude Code

Copy the `.claude` directory to your project or add it to your global Claude Code configuration:

```bash
cp -r .claude ~/.claude
```

### Delegating Tasks

In Claude Code, invoke a driver agent:

```
@"codex-driver (agent)" Create a REST API endpoint for user authentication
```

```
@"copilot-driver (agent)" Refactor the database module to use connection pooling
```

```
@"gemini-driver (agent)" Review src/auth.py for security vulnerabilities
```

The driver agent will:
1. Translate your request into the appropriate CLI command
2. Execute it using the corresponding skill
3. Evaluate the results for correctness
4. Iterate if needed (scope creep, redirection, or incomplete work)
5. Report back when the goal is fully achieved

## Architecture

```
┌─────────────────┐
│   Claude Code   │
│                 │
└────────┬────────┘
         │ delegates to
         ▼
┌─────────────────┐     uses      ┌─────────────────┐
│  Driver Agent   │──────────────▶│     Skill       │
│  (TPM role)     │               │  (CLI syntax)   │
└────────┬────────┘               └─────────────────┘
         │ executes
         ▼
┌─────────────────┐
│   External CLI  │
│ (Codex/Copilot/ │
│    Gemini)      │
└─────────────────┘
```

## Model Router (Intelligent Agent Selection)

The `model-router` skill uses an optimized rule-based classifier to automatically select the best agent for each coding task. Fast (~1ms), no model loading required.

### Setup

```bash
cd router-service
pip install -r requirements.txt
uvicorn router:app --host 127.0.0.1 --port 8765
```

### How It Works

1. **Classifies the task** using keyword patterns optimized for coding:
   - Task types: `code_debugging`, `code_generation`, `code_explanation`, `code_review`, `rewrite`, `summarization`, `math`, `open_qa`
   - Complexity: `simple`, `moderate`, `complex` (based on prompt length, technical depth, multi-requirements)

2. **Selects the optimal agent** based on task type and complexity:

   | Task Type | Simple | Moderate | Complex |
   |-----------|--------|----------|---------|
   | code_debugging | copilot | codex | codex |
   | code_generation | copilot | cursor | codex |
   | code_explanation | gemini | cursor | cursor |
   | code_review | cursor | cursor | cursor |
   | rewrite/refactor | cursor | cursor | cursor |
   | summarization | gemini | gemini | gemini |
   | math | codex | codex | codex |
   | open_qa | gemini | gemini | gemini |

3. **Compresses agent output** to minimize tokens returned to Claude Code (3 levels: minimal, moderate, aggressive)

### API Endpoints

```bash
# Route a task
curl -s -X POST http://127.0.0.1:8765/route \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Fix the authentication bug"}' | jq

# Response:
# {
#   "selected_agent": "codex",
#   "confidence": 0.80,
#   "task_analysis": {
#     "task_type": "code_debugging",
#     "complexity": "moderate",
#     "all_scores": {"task_signals": ["debug_keywords:2"], ...}
#   },
#   "recommended_flags": {"sandbox": "workspace-write", "reasoning": "medium"}
# }

# With preferences
curl -s -X POST http://127.0.0.1:8765/route \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write tests", "prefer_speed": true}' | jq

# Compress agent output
curl -s -X POST http://127.0.0.1:8765/compress \
  -H "Content-Type: application/json" \
  -d '{"content": "<verbose output>", "level": "moderate"}' | jq

# Health check
curl -s http://127.0.0.1:8765/health | jq
```

### Workflow Integration

**Option 1: Manual routing via skill**
```
# In Claude Code, use the model-router skill:
1. Call router service to classify task
2. Use the returned agent recommendation
3. Delegate to the appropriate driver agent
```

**Option 2: Direct driver invocation** (if you know which agent to use)
```
@"codex-driver (agent)" Fix the complex authentication bug
@"copilot-driver (agent)" Add a simple utility function
@"gemini-driver (agent)" Explain how the caching system works
@"cursor-driver (agent)" Refactor the payment module
```

### Architecture

```
┌─────────────────┐
│   Claude Code   │
│                 │
└────────┬────────┘
         │ task
         ▼
┌─────────────────┐
│  Router Service │  ← rule-based classifier (~1ms)
│  (model-router) │
└────────┬────────┘
         │ {agent, flags, reasoning}
         ▼
┌─────────────────┐     uses      ┌─────────────────┐
│  Driver Agent   │──────────────▶│     Skill       │
│  (TPM role)     │               │  (CLI syntax)   │
└────────┬────────┘               └─────────────────┘
         │ executes
         ▼
┌─────────────────┐
│   External CLI  │
│ (Codex/Copilot/ │
│  Gemini/Cursor) │
└────────┬────────┘
         │ output
         ▼
┌─────────────────┐
│   Compressor    │  ← minimize tokens (optional)
└────────┬────────┘
         │ compressed result
         ▼
┌─────────────────┐
│   Claude Code   │
└─────────────────┘
```

## Why This Pattern?

- **Leverage multiple AI models**: Use the best tool for each job
- **Intelligent routing**: NVIDIA classifier picks the optimal agent automatically
- **Quality control**: Driver agents ensure work meets spec exactly
- **Token efficiency**: Context compression minimizes tokens returned to Claude Code
- **Isolation**: External CLIs have their own context windows
- **Iteration**: Automatic retry on scope creep, redirection, or incomplete work
- **Transparency**: Clear audit trail of what each CLI produced
