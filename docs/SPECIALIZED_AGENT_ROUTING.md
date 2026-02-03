# Specialized Agent Routing Strategy

## The Opportunity

Currently, specialized agents (planner, architect, code-reviewer, refactor-cleaner) run natively in Claude Code, consuming Claude Code tokens. However, the external CLI agents (Cursor, Copilot, Gemini, Codex) have their own subscriptions and specialized capabilities that can handle these tasks while:

1. **Preserving Claude Code tokens** for coordination
2. **Leveraging subscription diversity** (spread load across services)
3. **Using specialized modes** (Cursor plan mode, Gemini research, etc.)
4. **Getting alternative perspectives** from different AI architectures

## Current vs. Proposed Architecture

### Current (Native Agents)

```
User Request → Claude Code → Native Agent (planner/architect/etc.) → Result
                             ↓
                        Consumes Claude Code Opus tokens
```

### Proposed (CLI-Based Specialized Agents)

```
User Request → Claude Code → Route CLI → Specialized CLI Agent → Result
                             ↓              ↓
                        Minimal tokens    Uses external subscription
```

## Task-to-Agent Mapping

### Planning Tasks

| Current | Proposed | Model | Rationale |
|---------|----------|-------|-----------|
| `planner` (native Opus) | **Cursor** `--mode plan` | --model auto (recommended) | Cursor has dedicated plan mode for architecture planning |

**Cursor Plan Mode:**
```bash
agent -p "Plan the implementation of user authentication" --mode plan --model auto --output-format text
```

### Architecture Tasks

| Current | Proposed | Model | Rationale |
|---------|----------|-------|-----------|
| `architect` (native Opus) | **Cursor** `--mode plan` | --model auto (recommended) | Context-heavy, multi-file decisions |
| Alternative | **Gemini** | gemini-3-pro | Different perspective on system design |

**Cursor for Architecture:**
```bash
agent -p "Design the database schema for the new feature" --mode plan --model auto --output-format text
```

### Code Review Tasks

| Current | Proposed | Model | Rationale |
|---------|----------|-------|-----------|
| `code-reviewer` (native Opus) | **Copilot** | claude-opus-4.5 | Included in GitHub subscription |
| Alternative | **Cursor** `--mode ask` | --model auto (recommended) | Read-only review mode |

**Copilot for Review:**
```bash
copilot -p "Review the staged changes for security issues and code quality" --model claude-opus-4.5 --allow-all-paths
```

**Cursor for Review:**
```bash
agent -p "Review the staged changes for security issues and code quality" --mode ask --model auto --output-format text
```

### Refactoring Tasks

| Current | Proposed | Model | Rationale |
|---------|----------|-------|-----------|
| `refactor-cleaner` (native Opus) | **Cursor** `--mode agent` | --model auto (recommended) | Cursor is repo-aware for multi-file refactoring |

**Cursor for Refactoring:**
```bash
agent -p "Refactor the authentication module to use async/await" --mode agent --model auto --output-format text
```

### Research/Exploration Tasks

| Current | Proposed | Model | Rationale |
|---------|----------|-------|-----------|
| `Explore` (native) | **Gemini** | gemini-3-pro | Gemini excels at codebase analysis |

**Gemini for Research:**
```bash
gemini -p "Research how error handling is implemented across the codebase" -m gemini-2.5-pro --include-directories src
```

### Bug Fixing Tasks

| Current | Proposed | Model | Rationale |
|---------|----------|-------|-----------|
| varies | **Codex** | gpt-5.2-codex | High reasoning for deep debugging |
| Simple bugs | **Copilot** | gpt-5-mini | Fast for obvious fixes |

**Codex for Complex Bugs:**
```bash
codex -p "Debug the race condition in the WebSocket handler" --sandbox workspace-write --reasoning high
```

### Code Generation Tasks

| Complexity | Proposed | Model | Rationale |
|------------|----------|-------|-----------|
| Simple | **Copilot** | gpt-5-mini | Fast, cheap, sufficient quality |
| Moderate | **Cursor** | --model auto (recommended) | Auto-selects appropriate model for task |
| Complex | **Codex** | gpt-5.1-codex-max | Maximum reasoning for algorithms |

## Subscription Optimization Strategy

### Priority Order (Cost-Efficiency)

1. **Gemini** (Free tier / low cost)
   - Use for: Research, exploration, code explanation, documentation
   - Model: gemini-2.5-flash (free) or gemini-3-pro (paid)

2. **Copilot** (GitHub subscription - often included)
   - Use for: Simple code gen, quick fixes, code review
   - Model: gpt-5-mini (fast) or claude-opus-4.5 (quality)

3. **Cursor** (Cursor subscription)
   - Use for: Planning, architecture, refactoring, complex edits
   - Model: --model auto (recommended, auto-selects optimal model)

4. **Codex** (OpenAI subscription)
   - Use for: Complex algorithms, math, deep debugging
   - Model: gpt-5.2-codex (default) or gpt-5.1-codex-max (complex)

5. **Claude Code** (Anthropic subscription - reserve for coordination)
   - Use for: Task routing, integration, final review, conversation context
   - Model: Opus for complex, Sonnet for routine

## Implementation: Enhanced Router

### Updated CLI Router with Specialized Task Detection

```python
# Specialized task mapping
SPECIALIZED_TASKS = {
    "planning": {
        "keywords": ["plan", "design", "architecture", "how should we", "implementation strategy"],
        "agent": "cursor",
        "mode": "plan",
        "model": "auto"
    },
    "architecture": {
        "keywords": ["architect", "system design", "scalability", "database schema", "API design"],
        "agent": "cursor",
        "mode": "plan",
        "model": "auto"
    },
    "code_review": {
        "keywords": ["review", "audit", "check for issues", "security review", "code quality"],
        "agent": "copilot",
        "mode": "review",
        "model": "claude-opus-4.5"
    },
    "refactoring": {
        "keywords": ["refactor", "clean up", "reorganize", "consolidate", "modernize"],
        "agent": "cursor",
        "mode": "agent",
        "model": "auto"
    },
    "research": {
        "keywords": ["research", "explore", "find all", "understand how", "analyze"],
        "agent": "gemini",
        "mode": "read",
        "model": "gemini-3-pro"
    },
    "debugging": {
        "keywords": ["fix", "bug", "debug", "error", "broken", "crash"],
        "agent": "codex",  # Complex bugs
        "fallback": "copilot",  # Simple bugs
        "model": "gpt-5.2-codex"
    },
    "code_generation": {
        "simple": {"agent": "copilot", "model": "gpt-5-mini"},
        "moderate": {"agent": "cursor", "model": "auto"},
        "complex": {"agent": "codex", "model": "gpt-5.1-codex-max"}
    }
}
```

### Updated Delegate Skill Flow

```
1. User Request
   ↓
2. CLI Router classifies task
   - Task type (planning/architecture/review/refactor/research/debug/codegen)
   - Complexity (simple/moderate/complex)
   ↓
3. Select optimal agent + model based on:
   - Task type mapping
   - Complexity level
   - Available agents (installed CLIs)
   - Subscription optimization (prefer free/cheap first)
   ↓
4. Execute via driver agent
   - cursor-driver for planning/architecture/refactoring
   - copilot-driver for review/simple tasks
   - gemini-driver for research/exploration
   - codex-driver for complex algorithms/debugging
   ↓
5. Return compressed results to Claude Code
```

## Example Scenarios

### Scenario 1: "Plan a user authentication system"

**Current:** Claude Code runs native `planner` agent (Opus tokens consumed)

**Proposed:**
```bash
# Router classifies: planning task, complex
# Routes to: Cursor plan mode with auto model selection
agent -p "Plan a user authentication system with OAuth, JWT, and MFA" \
  --mode plan --model auto --output-format text
```
**Benefit:** Cursor's plan mode + auto model selection, Claude Code tokens preserved

### Scenario 2: "Review the authentication changes for security issues"

**Current:** Claude Code runs native `code-reviewer` agent (Opus tokens consumed)

**Proposed:**
```bash
# Router classifies: code_review task, security focus
# Routes to: Copilot with Opus
copilot -p "Review staged changes for security vulnerabilities, injection risks, and authentication bypasses" \
  --model claude-opus-4.5 --allow-all-paths
```
**Benefit:** Uses GitHub subscription, Opus quality review

### Scenario 3: "Research how caching is implemented across the codebase"

**Current:** Claude Code runs `Explore` agent (Claude tokens consumed)

**Proposed:**
```bash
# Router classifies: research task, moderate complexity
# Routes to: Gemini
gemini -p "Analyze how caching is implemented across the codebase. Find all cache-related patterns, libraries, and identify potential optimizations." \
  -m gemini-2.5-pro --include-directories src,lib
```
**Benefit:** Gemini's research strength, different AI perspective, cheaper

### Scenario 4: "Fix the race condition in the WebSocket handler"

**Current:** Varies, often Claude Code directly

**Proposed:**
```bash
# Router classifies: debugging task, complex (race condition)
# Routes to: Codex with high reasoning
codex -p "Debug and fix the race condition in the WebSocket handler. Analyze timing issues, identify the root cause, and implement a thread-safe solution." \
  --sandbox workspace-write --reasoning high
```
**Benefit:** Codex's strong debugging + reasoning capabilities

## Token/Cost Comparison

### Before (Native Agents)

| Task | Agent | Model | Token Source |
|------|-------|-------|--------------|
| Planning | planner | Opus | Claude Code subscription |
| Architecture | architect | Opus | Claude Code subscription |
| Code Review | code-reviewer | Opus | Claude Code subscription |
| Refactoring | refactor-cleaner | Opus | Claude Code subscription |
| Research | Explore | Sonnet/Opus | Claude Code subscription |

**Total:** All tasks consume Claude Code tokens

### After (CLI Routing)

| Task | Agent | Model | Token Source |
|------|-------|-------|--------------|
| Planning | Cursor | claude-opus-4.5 | Cursor subscription |
| Architecture | Cursor | claude-opus-4.5 | Cursor subscription |
| Code Review | Copilot | claude-opus-4.5 | GitHub subscription |
| Refactoring | Cursor | claude-opus-4.5 | Cursor subscription |
| Research | Gemini | gemini-3-pro | Google subscription |
| Bug Fixing | Codex | gpt-5.2-codex | OpenAI subscription |
| Simple Code | Copilot | gpt-5-mini | GitHub subscription |

**Result:** Claude Code tokens reserved for coordination only

## Implementation Steps

### Phase 1: Update Router CLI

1. Add specialized task detection to `route_cli.py`
2. Include agent mode recommendations (plan/agent/ask)
3. Add model tier recommendations based on task complexity

### Phase 2: Create Specialized Driver Agents

1. Update `cursor-driver` with plan mode awareness
2. Add review mode to `copilot-driver`
3. Update model selection in all drivers

### Phase 3: Update Delegate Skill

1. Parse router's specialized task recommendations
2. Pass mode and model to appropriate driver
3. Add explanation of why this routing was chosen

### Phase 4: Deprecate Native Specialized Agents (Optional)

1. Keep native agents as fallback
2. Route primarily through CLI agents
3. Monitor quality and iterate

## Configuration Options

### User Preferences

```json
{
  "routing_preferences": {
    "prefer_subscription": "gemini",  // Use Gemini when possible
    "quality_vs_cost": "balanced",     // "quality" | "balanced" | "cost"
    "allow_opus": true,                // Allow Opus-tier models
    "fallback_to_native": true         // Use native agents if CLI unavailable
  }
}
```

### Per-Task Overrides

```bash
/delegate --prefer cursor "Plan the authentication system"
/delegate --prefer gemini --cheap "Research the caching implementation"
/delegate --quality "Review security of the payment module"
```

## Success Metrics

1. **Token Efficiency:** % reduction in Claude Code token usage
2. **Subscription Utilization:** Balanced usage across subscriptions
3. **Task Quality:** Success rate and user satisfaction
4. **Response Time:** Average time per task type
5. **Cost per Task:** Average cost across different task types

## Next Steps

1. [ ] Implement enhanced task detection in `route_cli.py`
2. [ ] Update driver agents with mode/model awareness
3. [ ] Update delegate skill to pass routing metadata
4. [ ] Create configuration system for user preferences
5. [ ] Test with real-world tasks
6. [ ] Monitor and iterate on routing decisions
