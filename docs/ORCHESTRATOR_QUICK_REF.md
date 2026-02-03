# Orchestrator Pattern - Quick Reference

## Who Does What?

| Role | Responsibility | Number of Actions |
|------|----------------|-------------------|
| **User** | Invokes `/delegate <task>` | 1 (delegate once) |
| **Main Agent** (Claude Code) | Routes task, launches driver agent, waits | 1 (delegate once) |
| **Driver Agent** (orchestrator) | Evaluates, asks questions, loops back | 1-3 (iterates until satisfied) |
| **Sub-Agent CLI** (Gemini/Cursor/etc.) | Does the actual work | 1-3 (responds to driver) |

## Flow in 3 Steps

```
1. USER → MAIN AGENT
   "/delegate fix auth bug"

2. MAIN AGENT → DRIVER AGENT (cursor-driver)
   "Fix authentication bug"
   [launches Task tool, then WAITS]

3. DRIVER AGENT ↔ SUB-AGENT CLI (Cursor)
   Execute → Evaluate → Ask Questions → Execute → Evaluate → (repeat max 3x)
   [returns final result to Main Agent]
```

## The Orchestrator Pattern (Inside Driver Agents)

```
┌─────────────────────────────────────────┐
│ DRIVER AGENT receives task              │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ Execute sub-agent CLI (Cycle 1)         │
│ "Fix authentication bug"                │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│ EVALUATE Result:                        │
│ ✓ Completeness?                         │
│ ✓ Correctness?                          │
│ ✓ Clarity?                              │
│ ✓ Edge Cases?                           │
│ ✓ Testing?                              │
└──────────────┬──────────────────────────┘
               ↓
         ┌─────┴─────┐
         ↓           ↓
    Gaps Found?   No Gaps
         ↓           ↓
    ASK QUESTIONS   ACCEPT ✓
         ↓
┌─────────────────────────────────────────┐
│ Execute sub-agent CLI again (Cycle 2)   │
│ "How does this handle invalid creds?"   │
│ "What about rate limiting?"             │
└──────────────┬──────────────────────────┘
               ↓
         [Re-evaluate]
               ↓
         [Continue until satisfied or max 3 cycles]
```

## Key Insight

**The main agent delegates ONCE.**  
**The driver agent orchestrates MULTIPLE iterations.**

This means:
- You don't see the back-and-forth between driver and sub-agent
- You just get the final polished result
- The driver agent ensures quality through evaluation loops

## Example Conversation

**User**: `/delegate implement user login endpoint`

**Main Agent (Claude Code)**:
```
Delegating to gemini (model: gemini-3-pro)
Why gemini? Task type 'code_generation' with moderate complexity.

[Launches gemini-driver agent via Task tool]
[WAITS...]
```

**Driver Agent (gemini-driver)** - Internal Process (User doesn't see this):
```
Cycle 1:
  Execute: gemini "implement user login endpoint"
  Evaluate: Missing error handling, no validation
  
Cycle 2:
  Execute: gemini "Add error handling for invalid credentials and input validation"
  Evaluate: Good, but no rate limiting
  
Cycle 3:
  Execute: gemini "Add rate limiting to prevent brute force attacks"
  Evaluate: Complete! All criteria met.
```

**Main Agent (Claude Code)** - Returns to User:
```
## Gemini Results

### Implementation Complete
- POST /api/login endpoint created
- Email/password validation added
- Error handling for invalid credentials
- Rate limiting (5 attempts per minute)
- Unit tests included

### Orchestrator Notes
- Cycles used: 3
- Questions asked: Error handling, validation, rate limiting
- Remaining gaps: None
```

## When to Use `/delegate`

✓ **Use when**:
- You want to save Claude Code tokens
- Task can be done by another AI agent
- You want a fresh context for the work

✗ **Don't use when**:
- Task requires current conversation context
- It's a simple file read/grep
- Quick clarification question

## Benefits

| Without Orchestrator | With Orchestrator |
|---------------------|-------------------|
| Accept incomplete work | Evaluate for completeness |
| Miss edge cases | Actively check for gaps |
| Unclear decisions | Ask for justification |
| Manual follow-up needed | Automatic iteration |
| Single shot | Up to 3 refinement cycles |

## TL;DR

```
You delegate once →
  Main agent delegates once →
    Driver agent iterates 1-3 times →
      Sub-agent does work, answers questions →
    Driver agent returns polished result →
  Main agent presents to you
```

**The orchestrator pattern makes delegation smarter, not harder.**
