---
name: delegate
description: Intelligently routes and delegates coding tasks to the best AI agent (Codex, Cursor, Gemini, Copilot). Use /delegate <task> to automatically pick the optimal agent based on task type and complexity.
user-invocable: true
---

# Delegate Skill

Routes coding tasks to the optimal AI CLI agent and delegates execution.

**No server required** - uses standalone CLI router.

---
## ⚠️ CRITICAL INSTRUCTION ⚠️

**When this skill is invoked, you MUST delegate to the selected agent.**

- Do NOT handle the task yourself
- Do NOT second-guess the router's recommendation
- Do NOT rationalize why "context" or "codebase familiarity" means you should do it

The user is invoking `/delegate` specifically to SAVE THEIR CLAUDE TOKENS by offloading work to other AI agents. If you handle it yourself, you are wasting their subscription and ignoring their explicit request.

**Follow the router's recommendation. Delegate immediately. No exceptions.**

---

## Why Delegate?

Delegation provides three key benefits:

1. **Token Preservation**: Each delegated task runs in a fresh context, preserving Claude Code's tokens for coordination and integration work.

2. **Alternative Perspectives**: Different AI agents have different training and specializations. Delegation provides diverse approaches.

3. **Specialized Expertise**: Each agent excels at different task types:
   - **Copilot**: Opus specialist - complex reasoning, security analysis, deep reviews
   - **Cursor**: Planning, architecture, refactoring, debugging, code review
   - **Gemini**: Primary code generation, research, documentation, analysis
   - **Codex**: Miscellaneous coding, algorithms, utility scripts

## CRITICAL: MANDATORY DELEGATION RULE

**When the user invokes `/delegate`, you MUST delegate to the selected agent. No exceptions.**

❌ **NEVER do this:**
> "The router selected Gemini for this task. However, since this is about our codebase, I'll handle this directly..."

✅ **ALWAYS do this:**
> "Delegating to Gemini..." [then immediately use Task tool with gemini-driver]

**The entire purpose of `/delegate` is to offload work to other agents to:**
- Save the user's Claude subscription tokens
- Get more value from their AI tool subscriptions
- Use fresh context windows for each task

**If Claude handles it directly, the user gains NOTHING from the delegation system.**

When the router recommends an agent, that decision is final. Do not second-guess it. Do not rationalize handling it yourself. DELEGATE.

## When Claude Code Should Handle Directly (WITHOUT /delegate)

These are cases where the user did NOT invoke `/delegate`:
- Task is simple file reading or grepping
- Task requires immediate context from the current conversation
- Task is a quick clarification question

**But if the user says `/delegate`, ALWAYS delegate. Period.**

## Usage

```
/delegate <task description>
```

## Examples

```
/delegate Research how error handling is implemented across the codebase
/delegate Fix the authentication bug in login.py
/delegate Write a REST API endpoint for user registration
/delegate Explain the caching system architecture
/delegate Refactor the payment module to use async/await
```

## Execution Steps

### Step 1: Route the Task (No Server Required)

Run the CLI router directly:

```bash
python3 ~/agent-skills/router-service/route_cli.py "<task from user>"
```

Or with options:
```bash
python3 ~/agent-skills/router-service/route_cli.py "<task>" --prefer-speed
python3 ~/agent-skills/router-service/route_cli.py "<task>" --prefer-cost
python3 ~/agent-skills/router-service/route_cli.py "<task>" --compact
```

### Step 2: Parse Response

The CLI returns JSON:
```json
{
  "selected_agent": "gemini",
  "confidence": 0.85,
  "reasoning": "Task type 'research' with moderate complexity. Gemini excels at research.",
  "recommended_model": "gemini-3-flash",
  "alternative_agents": [...],
  "task_analysis": {
    "task_type": "research|code_generation|code_debugging|...",
    "complexity": "simple|moderate|complex"
  }
}
```

Key fields:
- `selected_agent`: The best **installed** agent for this task
- `recommended_model`: Optimal model for the task complexity
- `reasoning`: Why this agent was selected

### Step 3: Inform User and IMMEDIATELY Delegate

**MANDATORY: You must delegate. Do not handle the task yourself.**

Tell the user which agent was selected, then IMMEDIATELY invoke the Task tool:

**Template:**
> "Delegating to **{agent}** (model: {recommended_model})
>
> **Why {agent}?** {reasoning}"

**Then IMMEDIATELY use the Task tool** (in the same response):
- `selected_agent: "codex"` → use `subagent_type: "codex-driver"`
- `selected_agent: "cursor"` → use `subagent_type: "cursor-driver"`
- `selected_agent: "gemini"` → use `subagent_type: "gemini-driver"`
- `selected_agent: "copilot"` → use `subagent_type: "copilot-driver"`

**⚠️ DO NOT:**
- Say "however, I'll handle this directly"
- Say "since this is about our codebase, I can do it"
- Say "to maintain context, I'll do this myself"
- Make ANY excuse to not delegate

**The user explicitly asked for delegation. Respect their request.**

### Step 4: Wait for Orchestrator to Complete

**The driver agent (e.g., gemini-driver) is the orchestrator.**

Once you launch the driver agent, it will:
1. Execute the sub-agent CLI (Gemini/Cursor/Codex/Copilot)
2. **Evaluate the results** using the orchestrator pattern
3. **Ask follow-up questions** if gaps are found
4. **Loop back to the sub-agent** with clarifications (max 3 cycles)
5. **Return final results** to you when satisfied

**You just delegate once and wait.** The driver agent handles all the iteration internally.

### Step 5: Return Compressed Results

For long outputs (>500 chars), summarize key findings:

```
## {Agent} Results

### Key Findings
- {Finding 1}
- {Finding 2}

### Code Changes (if applicable)
- {file1}: {what changed}

### Errors/Issues (if any)
- {error 1}

### Orchestrator Notes
- Cycles used: {1-3}
- Questions asked: {summary}
- Remaining gaps: {if any}
```

## Agent Capabilities & Models

| Agent | Role | Best For | Model |
|-------|------|----------|-------|
| **copilot** | Opus Specialist | Complex reasoning, security analysis, deep reviews | claude-opus-4.5 (all tiers) |
| **cursor** | Structural Work | Planning, architecture, refactoring, debugging, code review | --model auto (auto-selects optimal model) |
| **gemini** | Code Gen Engine | Code generation (post-planning), research, documentation | gemini-3-pro (all tiers) |
| **codex** | Misc Coding | Algorithms, utility scripts, miscellaneous tasks | gpt-5.2-codex (med/high reasoning) |

## Task Type Routing Guide

| Task Type | Recommended Agent | Why |
|-----------|------------------|-----|
| **planning** / **architecture** | Cursor | Plan mode for structured implementation planning |
| **code_review** | Cursor | Ask mode for thorough code quality review |
| **security_review** | Copilot | Opus reasoning for deep security analysis |
| **refactoring** | Cursor | Agent mode is repo-aware for multi-file changes |
| **debugging** | Cursor | Agent mode for systematic debugging |
| **debugging_complex** | Copilot | Opus for race conditions, memory leaks, concurrency |
| **code_generation** | Gemini | Primary code gen engine with gemini-3-pro |
| **research** / **exploration** | Gemini | Excels at codebase analysis and patterns |
| **documentation** | Gemini | Produces clear, well-structured docs |
| **algorithms** | Codex | High reasoning for algorithmic optimization |
| **misc_coding** | Codex | Versatile for utility scripts and small tasks |
| **complex_analysis** | Copilot | Opus specialist for maximum reasoning depth |

## CLI Options

```bash
# Basic routing
python3 ~/agent-skills/router-service/route_cli.py "your task"

# Prefer speed
python3 ~/agent-skills/router-service/route_cli.py "your task" --prefer-speed

# Prefer cost
python3 ~/agent-skills/router-service/route_cli.py "your task" --prefer-cost

# Exclude specific agents
python3 ~/agent-skills/router-service/route_cli.py "your task" --exclude codex cursor

# Classification only (no agent selection)
python3 ~/agent-skills/router-service/route_cli.py "your task" --classify-only

# Compact JSON output (single line)
python3 ~/agent-skills/router-service/route_cli.py "your task" --compact
```

## Installation

```bash
# One-time setup
git clone https://github.com/sjarmak/agent-skills.git ~/agent-skills

# No server needed - CLI works standalone
# Just ensure Python 3 is available
```

## Fallback Behavior

If the CLI is unavailable or fails:
- Default to `gemini-driver` for research/explanation/analysis tasks
- Default to `cursor-driver` for code modification tasks
- Inform user that routing is unavailable

If no agents are installed:
- Inform user which CLIs need to be installed
- Provide installation instructions

## Optional: Server Mode

If you prefer the server (for high-volume routing or API access):

```bash
cd ~/agent-skills/router-service
source .venv/bin/activate
pip install -r requirements.txt
uvicorn router:app --host 127.0.0.1 --port 8765 &
```

Then use curl instead of the CLI:
```bash
curl -s -X POST http://127.0.0.1:8765/route \
  -H "Content-Type: application/json" \
  -d '{"prompt": "<task>"}'
```
