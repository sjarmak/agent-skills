# Agent Skills

A collection of Claude Code skills and sub-agents for delegating coding tasks to external AI CLI tools (Codex, GitHub Copilot, and Gemini).

## Overview

This repository provides a **"driver" pattern** for Claude Code: instead of doing coding work directly, Claude delegates tasks to other AI assistants (Codex, Copilot, or Gemini) and manages them like a Technical Program Manager—ensuring work stays on-spec, rejecting scope creep, and iterating until the goal is fully achieved.

Started from and inspired by: [skills-directory/skill-codex](https://github.com/skills-directory/skill-codex)

## What's Included

### Skills (`.claude/skills/`)

Skills teach Claude Code how to use each CLI tool:

| Skill | Description |
|-------|-------------|
| `skill-codex.md` | Command syntax, sandbox modes, and model selection for OpenAI Codex CLI |
| `skill-copilot-cli.md` | Flags, permissions, and model options for GitHub Copilot CLI |
| `skill-gemini-cli.md` | Headless execution, output formats, and session management for Google Gemini CLI |

### Sub-Agents (`.claude/agents/`)

Sub-agents are specialized Claude instances that use the skills to drive each CLI:

| Agent | Description |
|-------|-------------|
| `codex-driver.md` | Drives Codex CLI to complete coding tasks |
| `copilot-driver.md` | Drives GitHub Copilot CLI to complete coding tasks |
| `gemini-driver.md` | Drives Gemini CLI to complete coding tasks |

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

## Why This Pattern?

- **Leverage multiple AI models**: Use the best tool for each job
- **Quality control**: Driver agents ensure work meets spec exactly
- **Isolation**: External CLIs have their own context windows
- **Iteration**: Automatic retry on scope creep, redirection, or incomplete work
- **Transparency**: Clear audit trail of what each CLI produced
