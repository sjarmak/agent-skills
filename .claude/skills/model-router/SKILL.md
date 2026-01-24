---
name: model-router
description: Routes tasks to optimal AI CLI agents (Codex, Cursor, Gemini, Copilot) using an optimized rule-based classifier. Analyzes task type and complexity to select the best tool.
---

# Model Router Skill Guide

Routes coding tasks to the optimal AI CLI agent based on task type and complexity analysis.

## Prerequisites

Start the router service before using:
```bash
cd router-service && uvicorn router:app --host 127.0.0.1 --port 8765
```

## Baseline Rules

- Call the router service to classify tasks before delegating
- Use the routing decision to select the appropriate driver agent
- Apply recommended flags from the routing response
- Optionally compress subagent output to minimize token usage

## Command Templates

### Route a Task
```bash
curl -s -X POST http://127.0.0.1:8765/route \
  -H "Content-Type: application/json" \
  -d '{"prompt": "<task description>"}'
```

### Route with Speed Preference
```bash
curl -s -X POST http://127.0.0.1:8765/route \
  -H "Content-Type: application/json" \
  -d '{"prompt": "<task>", "prefer_speed": true}'
```

### Route with Cost Preference
```bash
curl -s -X POST http://127.0.0.1:8765/route \
  -H "Content-Type: application/json" \
  -d '{"prompt": "<task>", "prefer_cost": true}'
```

### Compress Agent Output
```bash
curl -s -X POST http://127.0.0.1:8765/compress \
  -H "Content-Type: application/json" \
  -d '{"content": "<agent output>", "level": "moderate", "max_tokens": 2000}'
```

### Check Service Health
```bash
curl -s http://127.0.0.1:8765/health
```

## Routing Response Structure

```json
{
  "selected_agent": "codex",
  "confidence": 0.80,
  "reasoning": "Task type 'code_debugging' with moderate complexity. Codex excels at code_debugging.",
  "task_analysis": {
    "task_type": "code_debugging",
    "task_type_confidence": 0.80,
    "complexity": "moderate",
    "complexity_score": 0.45,
    "all_scores": {
      "classifier": "rule_based_v2",
      "task_signals": ["debug_keywords:2"],
      "complexity_signals": ["short", "tech_depth:1"]
    }
  },
  "alternative_agents": [
    {"agent": "copilot", "score": 0.50},
    {"agent": "cursor", "score": 0.30}
  ],
  "recommended_flags": {
    "sandbox": "workspace-write",
    "reasoning": "medium"
  }
}
```

## Task Type Classification

| Task Type | Trigger Keywords |
|-----------|-----------------|
| code_debugging | fix, bug, debug, error, broken, crash, exception, failing |
| code_review | review, audit, security, vulnerability, pull request, PR |
| code_explanation | explain, what does, how does, understand, describe |
| code_generation | write, create, implement, build, add, generate + (function, class, api, etc.) |
| rewrite | refactor, restructure, clean up, modernize, improve, optimize |
| summarization | summarize, summary, overview, tldr |
| math | calculate, compute, algorithm, complexity, big o |
| open_qa | questions without clear code context |

## Complexity Estimation

Complexity is determined by multiple signals:

| Signal | Effect |
|--------|--------|
| Prompt length | >150 words = complex, >75 = moderate, <30 = simple |
| Explicit keywords | "complex", "advanced", "production" increase; "simple", "basic" decrease |
| Multiple requirements | Bullet points, "and" conjunctions, numbered lists increase complexity |
| Technical depth | OAuth, JWT, database, microservice, etc. increase complexity |
| Multi-file scope | "entire codebase", "multiple files" increase complexity |

## Agent Selection Logic

| Task Type | Simple → | Moderate → | Complex → |
|-----------|----------|------------|-----------|
| code_debugging | copilot | codex | codex |
| code_generation | copilot | cursor | codex |
| code_explanation | gemini | cursor | cursor |
| code_review | cursor | cursor | cursor |
| rewrite | cursor | cursor | cursor |
| summarization | gemini | gemini | gemini |
| math | codex | codex | codex |
| open_qa | gemini | gemini | gemini |

## Compression Levels

| Level | Use Case | Preserves |
|-------|----------|-----------|
| minimal | Full context needed | Everything, just whitespace cleanup |
| moderate | Standard use | Code, errors, file paths, key outcomes |
| aggressive | Token-constrained | Only code blocks, errors, and action summaries |

## Workflow Pattern

1. **Receive task** from user
2. **Route task** via `/route` endpoint
3. **Read routing decision** - agent, flags, reasoning
4. **Delegate to driver** using the selected agent's driver
5. **Capture output** from the driver
6. **Compress output** (optional) via `/compress` endpoint
7. **Return result** to user/Claude Code

## Error Handling

- If router service is down: Default to gemini (most versatile)
- If routing confidence < 0.5: Consider using alternative agent or asking user
- If compression fails: Return raw output with truncation warning
