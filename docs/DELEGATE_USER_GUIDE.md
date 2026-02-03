# Delegate Orchestrator Pattern - User Guide

## Overview

The delegate skill has been enhanced with an **orchestrator pattern** that ensures sub-agents (Gemini, Cursor, Codex, Copilot) produce high-quality, complete work through guided iteration.

## Architecture Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ USER: /delegate "Fix authentication bug"                        │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ MAIN AGENT (Claude Code)                                        │
│ - Invokes delegate skill                                        │
│ - Runs router to select best sub-agent                          │
│ - Launches driver agent (e.g., cursor-driver)                   │
│ - WAITS for final results                                       │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ DRIVER AGENT (cursor-driver) ← THE ORCHESTRATOR                 │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Cycle 1: Initial Execution                                │  │
│  │  - Execute Cursor CLI with task                           │  │
│  │  - Receive results                                        │  │
│  │  - EVALUATE: Completeness? Correctness? Clarity?          │  │
│  │  - Gaps found: Missing error handling                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                             ↓                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Cycle 2: Follow-Up Questions                              │  │
│  │  - ASK: "How does this handle invalid credentials?"       │  │
│  │  - ASK: "What about rate limiting?"                       │  │
│  │  - Execute Cursor CLI again with questions                │  │
│  │  - Receive updated results                                │  │
│  │  - EVALUATE: Still gaps? Or satisfied?                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                             ↓                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Cycle 3: Final Refinement (if needed)                     │  │
│  │  - Final clarifications                                   │  │
│  │  - Execute Cursor CLI one last time                       │  │
│  │  - Accept best available result                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                             ↓                                    │
│  RETURN: Comprehensive results + evaluation notes               │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ MAIN AGENT: Presents final results to user                      │
└─────────────────────────────────────────────────────────────────┘
```

**Key Point**: You (the main agent) delegate ONCE. The driver agent does all the iteration with the sub-agent internally, then returns the final polished result.

## What Changed?

### Before: Passive Relay
Driver agents would simply pass your request to the sub-agent and return whatever came back, even if incomplete or unclear.

### After: Active Orchestrator
Driver agents now:
1. **Evaluate** every sub-agent response critically
2. **Ask follow-up questions** to clarify gaps
3. **Loop back** to the sub-agent with refined prompts
4. **Iterate up to 3 cycles** to ensure quality
5. **Document** the evaluation process

## How It Works

### The 3-Cycle Loop

Each driver agent follows this pattern:

```
Cycle 1: Initial Execution
├─ Execute sub-agent with your request
├─ Evaluate response for completeness, correctness, clarity
├─ If gaps found → proceed to Cycle 2
└─ If complete → accept and report

Cycle 2: Clarification Round
├─ Ask specific follow-up questions about gaps
├─ Execute sub-agent with clarifications
├─ Evaluate updated response
├─ If still incomplete → proceed to Cycle 3
└─ If complete → accept and report

Cycle 3: Final Refinement
├─ Request final refinements
├─ Execute sub-agent with specific asks
├─ Evaluate final response
└─ Accept best available result (document any remaining gaps)
```

### Quality Checklist

Each response is evaluated against:

- ✓ **Completeness**: All aspects of the request addressed?
- ✓ **Correctness**: Technically sound implementation?
- ✓ **Clarity**: Decisions explained and justified?
- ✓ **Edge Cases**: Error handling and edge cases covered?
- ✓ **Testing**: Tests included or verification mentioned?

## Example Scenarios

### Scenario 1: Incomplete Implementation

**Your Request**: "Implement a user authentication endpoint"

**Cycle 1**: Sub-agent implements basic endpoint
- **Gap Found**: No error handling for invalid credentials
- **Action**: Loop back with questions

**Cycle 2**: Sub-agent adds error handling
- **Gap Found**: No rate limiting mentioned
- **Action**: Loop back requesting rate limiting

**Cycle 3**: Sub-agent adds rate limiting
- **Result**: Complete implementation accepted

### Scenario 2: Unclear Decisions

**Your Request**: "Optimize database query performance"

**Cycle 1**: Sub-agent adds an index
- **Gap Found**: Why this index? What's the performance impact?
- **Action**: Loop back asking for justification

**Cycle 2**: Sub-agent explains index choice with metrics
- **Result**: Clear, justified solution accepted

### Scenario 3: Immediate Success

**Your Request**: "Write unit tests for the login function"

**Cycle 1**: Sub-agent provides comprehensive tests with edge cases
- **Evaluation**: All criteria met
- **Result**: Accepted immediately (no further cycles needed)

## Benefits

### For You
- **Higher Quality**: No more accepting incomplete work
- **Better Understanding**: Gaps are identified and filled
- **Time Savings**: Fewer back-and-forth manual iterations

### For the Sub-Agents
- **Guided Improvement**: Learn what's missing through specific questions
- **Focused Work**: Clear direction on what to fix or add
- **Quality Bar**: Consistent expectations across all agents

## What You'll See

When using `/delegate`, you'll notice:

1. **Evaluation Reports**: Driver agents will share their assessment
2. **Follow-Up Questions**: Questions posed to the sub-agent before accepting
3. **Cycle Tracking**: Clear indication of which cycle (1, 2, or 3)
4. **Final Documentation**: Summary of what was checked and any remaining concerns

## Best Practices

### Write Clear Initial Requests
The better your initial request, the fewer cycles needed:
- ✓ Specify requirements clearly
- ✓ Mention edge cases you care about
- ✓ Request tests if needed
- ✓ Note any constraints

### Trust the Process
The orchestrator will:
- Find gaps you might have missed
- Ask questions you didn't think to ask
- Ensure consistent quality

### Review Final Reports
Driver agents document their evaluation:
- What was checked
- What questions were asked
- Any remaining concerns

## Cycle Limit (Max 3)

Why a maximum of 3 cycles?

1. **Prevents Infinite Loops**: Stops endless back-and-forth
2. **Forces Clarity**: Sub-agents learn to be thorough upfront
3. **Practical Balance**: Most issues resolved in 2-3 iterations

If 3 cycles aren't enough, the driver agent will:
- Accept the best available result
- Document remaining gaps
- You can decide whether to iterate manually

## Agent-Specific Patterns

### Gemini (Code Generation)
- Emphasizes completeness and error handling
- Questions implementation choices
- Verifies test coverage

### Cursor (Planning/Architecture)
- Challenges architectural decisions
- Questions rollback strategies
- Ensures migration plans are complete

### Codex (Algorithms)
- Requests complexity analysis
- Questions algorithm choice
- Verifies edge case handling

### Copilot (Deep Analysis)
- Pushes for root cause explanations
- Questions security implications
- Challenges assumptions

## Tips

1. **Be Patient**: The orchestrator may take 2-3 cycles, but the result will be better
2. **Read Evaluations**: Learn what good code looks like from the quality checks
3. **Iterate Yourself**: If 3 cycles aren't enough, use the feedback to refine your request
4. **Trust the Process**: The orchestrator is designed to catch what humans miss

## Summary

The delegate orchestrator pattern transforms driver agents from passive relays into active quality gates, ensuring every delegated task meets high standards through structured evaluation and guided iteration.

**Result**: Better code, fewer bugs, less rework.
