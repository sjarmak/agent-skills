# Agent Skills

A collection of Claude Code skills and sub-agents for delegating coding tasks to external AI CLI tools (Codex, GitHub Copilot, Gemini, and Cursor).

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/sjarmak/agent-skills.git ~/agent-skills
cd ~/agent-skills && ./install.sh

# 2. Start the router service
cd ~/agent-skills/router-service
source .venv/bin/activate
uvicorn router:app --host 127.0.0.1 --port 8765

# 3. In any Claude Code session, use /delegate
/delegate Fix the authentication bug in login.py
```

---

## Overview

This repository provides a **"driver" pattern** for Claude Code: instead of doing coding work directly, Claude delegates tasks to other AI assistants (Codex, Copilot, Gemini, or Cursor) and manages them like a Technical Program Manager—ensuring work stays on-spec, rejecting scope creep, and iterating until the goal is fully achieved.

The router uses a **fast, optimized rule-based classifier** (~1ms latency, no model loading required) to automatically select the best agent for each task.

Started from and inspired by: [skills-directory/skill-codex](https://github.com/skills-directory/skill-codex)

---

## The `/delegate` Command

The primary way to use agent-skills. In any Claude Code session:

```
/delegate Fix the authentication bug in login.py
/delegate Write a REST API endpoint for user registration
/delegate Explain how the caching system works
/delegate Refactor the payment module to use async/await
```

Claude will:
1. Call the router to classify your task (task type + complexity)
2. Pick the optimal agent (codex, cursor, gemini, copilot)
3. Delegate to the driver agent and return results

### Direct Agent Invocation

If you already know which agent to use, invoke a driver directly:

```
@"codex-driver (agent)" Create a REST API endpoint for user authentication
@"copilot-driver (agent)" Add a simple utility function
@"gemini-driver (agent)" Explain how the caching system works
@"cursor-driver (agent)" Refactor the payment module
```

---

## Installation

### 1. Install the Skills

```bash
git clone https://github.com/sjarmak/agent-skills.git ~/agent-skills
cd ~/agent-skills
./install.sh
```

This copies skills and agents to `~/.claude/` so they're available in all your Claude Code sessions.

### 2. Install AI CLI Tools (Prerequisites)

Install at least one of the CLI tools you want to use:

**OpenAI Codex CLI**
```bash
npm install -g @openai/codex
# Requires: OPENAI_API_KEY environment variable
```

**GitHub Copilot CLI**
```bash
npm install -g @githubnext/github-copilot-cli
gh auth login  # Authenticate with GitHub
```

**Google Gemini CLI**
```bash
npm install -g @anthropic-ai/gemini-cli
# Requires: GOOGLE_API_KEY environment variable
```

**Cursor AI CLI**
```bash
# Install Cursor from https://cursor.com
# The CLI is included with Cursor installation
cursor --version
```

### 3. Start the Router Service

```bash
cd ~/agent-skills/router-service
source .venv/bin/activate
uvicorn router:app --host 127.0.0.1 --port 8765
```

**Tip:** Add an alias to your shell config (`~/.zshrc` or `~/.bashrc`):
```bash
alias start-router='cd ~/agent-skills/router-service && source .venv/bin/activate && uvicorn router:app --host 127.0.0.1 --port 8765 &'
```

Then just run `start-router` before starting Claude Code.

---

## What's Included

### Skills (`.claude/skills/`)

Skills teach Claude Code how to use each CLI tool:

| Skill | Description |
|-------|-------------|
| `codex` | Command syntax, sandbox modes, and model selection for OpenAI Codex CLI |
| `copilot` | Flags, permissions, and model options for GitHub Copilot CLI |
| `gemini` | Headless execution, output formats, and session management for Google Gemini CLI |
| `cursor` | Mode selection, model options, and session management for Cursor AI CLI |
| `delegate` | The `/delegate` command for intelligent task routing |
| `model-router` | Rule-based classifier for selecting the best agent |

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

---

## How the Router Works

The router uses an optimized rule-based classifier to analyze your task in ~1ms:

### Task Type Classification

| Task Type | Trigger Keywords |
|-----------|-----------------|
| `code_debugging` | fix, bug, debug, error, broken, crash, exception, failing |
| `code_review` | review, audit, security, vulnerability, pull request, PR |
| `code_explanation` | explain, what does, how does, understand, describe |
| `code_generation` | write, create, implement, build, add, generate + function/class/api |
| `rewrite` | refactor, restructure, clean up, modernize, improve, optimize |
| `summarization` | summarize, summary, overview, tldr |
| `math` | calculate, compute, algorithm, complexity, big o |
| `open_qa` | questions without clear code context |

### Complexity Estimation

Complexity is determined by multiple signals:

| Signal | Effect |
|--------|--------|
| Prompt length | >150 words = complex, >75 = moderate, <30 = simple |
| Explicit keywords | "complex", "advanced", "production" increase; "simple", "basic" decrease |
| Multiple requirements | Bullet points, "and" conjunctions, numbered lists increase complexity |
| Technical depth | OAuth, JWT, database, microservice, etc. increase complexity |
| Multi-file scope | "entire codebase", "multiple files" increase complexity |

### Agent Selection

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

---

## Architecture

```
┌─────────────────┐
│   Claude Code   │
│                 │
└────────┬────────┘
         │ /delegate <task>
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

---

## API Reference

The router service exposes these endpoints:

```bash
# Route a task to the best agent
curl -s -X POST http://127.0.0.1:8765/route \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Fix the authentication bug"}' | jq

# Route with speed preference
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

---

## Why This Pattern?

- **Leverage multiple AI models**: Use the best tool for each job
- **Intelligent routing**: Rule-based classifier picks the optimal agent automatically
- **Quality control**: Driver agents ensure work meets spec exactly
- **Token efficiency**: Context compression minimizes tokens returned to Claude Code
- **Isolation**: External CLIs have their own context windows
- **Iteration**: Automatic retry on scope creep, redirection, or incomplete work
- **Transparency**: Clear audit trail of what each CLI produced
- **Fast startup**: No model loading—classifier runs in ~1ms
