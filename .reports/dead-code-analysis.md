# Dead Code Analysis Report

Generated: 2026-02-02

## SAFE TO REMOVE

| # | File | Item | Reason |
|---|------|------|--------|
| 1 | `hello.py` | Entire file | Untracked throwaway `print('Hello, World!')` |
| 2 | `router-service/router.py:29-45` | `TASK_LABELS` | Defined but never referenced |
| 3 | `router-service/router.py:47` | `COMPLEXITY_LABELS` | Defined but never referenced |
| 4 | `router-service/router.py:147-150` | `get_available_agents()` | Defined but never called |
| 5 | `README.md` | `model-router` skill reference | Skill directory doesn't exist |
| 6 | 5 deleted files | Various planning/patch docs | Deleted from working tree, not committed |

## CAUTION

| # | File | Item | Reason |
|---|------|------|--------|
| 7 | `router.py` vs `route_cli.py` | Duplicated & diverged logic | AGENT_CAPABILITIES, classify_prompt, select_agent all duplicated with different implementations |
| 8 | `requirements.txt` | `requests` dep | Only used by test_router.py, not production code |
| 9 | `docs/DELEGATE_USER_GUIDE.md` | Untracked doc | Not linked from README |
| 10 | `docs/ORCHESTRATOR_QUICK_REF.md` | Untracked doc | Not linked from README |
| 11 | `settings.local.json` | Stale permissions | `mcp__acp__*`, `Bash(git remote add:*)`, `Bash(git reset:*)` potentially unused |
| 12 | `router-service/start.sh` | Convenience script | Not referenced from any documentation |

## DANGER (structural)

| # | Issue | Detail |
|---|-------|--------|
| 13 | `router.py` vs `route_cli.py` divergence | CLI version has research routing, specialized task detection, different agent capabilities. Server version is stale. API consumers get worse routing than CLI users. |
