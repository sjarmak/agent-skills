"""
Shared classifier module for the agent router.

Contains the canonical AGENT_CAPABILITIES, SPECIALIZED_TASKS,
classify_prompt(), detect_specialized_task(), select_agent(),
and check_installed_agents() used by both the FastAPI server
(router.py) and the standalone CLI (route_cli.py).
"""

import re
import subprocess
import time
from typing import Any, Dict, List, Optional


# ============================================================================
# Agent Capabilities
# ============================================================================

AGENT_CAPABILITIES = {
    "codex": {
        "strengths": ["misc_coding", "algorithms", "math", "utility_scripts"],
        "complexity_preference": "any",
        "description": "OpenAI Codex CLI - versatile for misc coding tasks with adjustable reasoning",
        "speed": "medium",
        "cost": "medium",
        "cli_command": "codex",
        "modes": {
            "default": None,
            "high_reasoning": "--reasoning high",
            "medium_reasoning": "--reasoning medium",
        },
        "models": {
            "simple": "gpt-5.2-codex",
            "moderate": "gpt-5.2-codex",
            "complex": "gpt-5.2-codex",
        },
        "reasoning_by_complexity": {
            "simple": "medium",
            "moderate": "medium",
            "complex": "high",
        },
    },
    "cursor": {
        "strengths": [
            "planning",
            "architecture",
            "refactoring",
            "code_debugging",
            "code_review",
            "rewrite",
        ],
        "complexity_preference": "moderate",
        "description": "Cursor AI - best for planning, architecture, debugging, and repo-aware refactoring",
        "speed": "medium",
        "cost": "medium",
        "cli_command": "agent",
        "modes": {"plan": "--mode plan", "agent": "--mode agent", "ask": "--mode ask"},
        "models": {
            "simple": "gpt-4o",
            "moderate": "claude-sonnet-4.5",
            "complex": "claude-opus-4.5",
        },
    },
    "gemini": {
        "strengths": [
            "code_generation",
            "research",
            "documentation",
            "open_qa",
            "summarization",
            "brainstorm",
            "code_explanation",
            "text_generation",
        ],
        "complexity_preference": "any",
        "description": "Gemini CLI - primary for code generation, research, documentation, and analysis",
        "speed": "fast",
        "cost": "low",
        "cli_command": "gemini",
        "modes": {"read": None, "edit": "--yolo"},
        "models": {
            "simple": "gemini-3-pro",
            "moderate": "gemini-3-pro",
            "complex": "gemini-3-pro",
        },
    },
    "copilot": {
        "strengths": [
            "complex_analysis",
            "deep_reasoning",
            "security_analysis",
            "architectural_review",
        ],
        "complexity_preference": "complex",
        "description": "GitHub Copilot CLI - Opus specialist for complex reasoning and deep analysis",
        "speed": "slow",
        "cost": "high",
        "cli_command": "copilot",
        "modes": {"default": None, "edit": "--allow-all-paths"},
        "models": {
            "simple": "claude-opus-4.5",
            "moderate": "claude-opus-4.5",
            "complex": "claude-opus-4.5",
        },
    },
}


# ============================================================================
# Specialized Task Routing
# ============================================================================

SPECIALIZED_TASKS = {
    "planning": {
        "keywords": [
            "plan the",
            "plan for",
            "create a plan",
            "implementation plan",
            "design the implementation",
            "how should we implement",
            "strategy for",
            "outline the approach",
            "roadmap for",
            "plan implementation",
        ],
        "single_match_keywords": ["plan the", "create a plan", "implementation plan"],
        "agent": "cursor",
        "mode": "plan",
        "model_tier": "complex",
        "reasoning": "Cursor's plan mode provides structured implementation planning",
    },
    "architecture": {
        "keywords": [
            "architect",
            "system design",
            "design the architecture",
            "database schema",
            "api design",
            "data model",
            "microservice",
            "infrastructure design",
            "scalability design",
            "system architecture",
        ],
        "single_match_keywords": [
            "system design",
            "database schema",
            "api design",
            "system architecture",
        ],
        "agent": "cursor",
        "mode": "plan",
        "model_tier": "complex",
        "reasoning": "Cursor excels at multi-file architectural analysis",
    },
    "code_review": {
        "keywords": [
            "review the",
            "review this",
            "code review",
            "audit the",
            "check for issues",
            "pr review",
            "review changes",
            "review my code",
            "review staged",
        ],
        "single_match_keywords": ["code review", "pr review", "review staged"],
        "agent": "cursor",
        "mode": "ask",
        "model_tier": "complex",
        "reasoning": "Cursor's ask mode for thorough code quality review",
    },
    "security_review": {
        "keywords": [
            "security review",
            "security audit",
            "check for vulnerabilities",
            "security analysis",
            "penetration test",
            "vulnerability scan",
            "security assessment",
            "threat model",
        ],
        "single_match_keywords": [
            "security review",
            "security audit",
            "vulnerability scan",
        ],
        "agent": "copilot",
        "mode": "default",
        "model_tier": "complex",
        "reasoning": "Copilot with Opus provides deep security analysis requiring maximum reasoning",
    },
    "refactoring": {
        "keywords": [
            "refactor the",
            "refactor this",
            "clean up the",
            "reorganize the",
            "consolidate the",
            "modernize the",
            "restructure the",
            "improve the code",
            "technical debt",
            "dead code",
        ],
        "single_match_keywords": ["refactor the", "refactor this", "technical debt"],
        "agent": "cursor",
        "mode": "agent",
        "model_tier": "complex",
        "reasoning": "Cursor's agent mode is repo-aware for safe multi-file refactoring",
    },
    "debugging_complex": {
        "keywords": [
            "race condition",
            "memory leak",
            "deadlock",
            "async bug",
            "concurrency issue",
            "intermittent failure",
            "timing issue",
            "hard to reproduce",
            "flaky test",
            "thread safety",
            "mutex",
            "semaphore",
            "lock contention",
        ],
        "single_match_keywords": [
            "race condition",
            "memory leak",
            "deadlock",
            "concurrency issue",
            "intermittent failure",
            "flaky test",
        ],
        "agent": "copilot",
        "mode": "default",
        "model_tier": "complex",
        "confidence_boost": 0.05,
        "reasoning": "Copilot with Opus for complex debugging requiring deep reasoning",
    },
    "debugging": {
        "keywords": [
            "debug the",
            "debug this",
            "fix the bug",
            "troubleshoot",
            "diagnose the",
            "find the issue",
            "why is.*failing",
            "why is.*broken",
        ],
        "single_match_keywords": ["debug the", "troubleshoot", "diagnose the"],
        "agent": "cursor",
        "mode": "agent",
        "model_tier": "complex",
        "reasoning": "Cursor's agent mode for systematic debugging with repo context",
    },
    "research": {
        "keywords": [
            "research how",
            "explore how",
            "find all",
            "understand how",
            "analyze how",
            "investigate the",
            "discover",
            "locate all",
            "search for",
            "examine the",
            "how is.*implemented",
            "where is.*used",
        ],
        "single_match_keywords": [
            "research how",
            "find all",
            "understand how",
            "analyze how",
        ],
        "agent": "gemini",
        "mode": "read",
        "model_tier": "complex",
        "reasoning": "Gemini excels at codebase analysis and pattern recognition",
    },
    "documentation": {
        "keywords": [
            "document the",
            "write docs",
            "update readme",
            "add jsdoc",
            "add comments",
            "explain the code",
            "document this",
            "write documentation",
        ],
        "single_match_keywords": ["write docs", "write documentation", "update readme"],
        "agent": "gemini",
        "mode": "edit",
        "model_tier": "complex",
        "reasoning": "Gemini produces clear, well-structured documentation",
    },
    "code_generation": {
        "keywords": [
            "implement the",
            "implement this",
            "write the code",
            "create the",
            "build the",
            "add a new",
            "generate the",
            "scaffold",
        ],
        "single_match_keywords": ["implement the", "write the code", "build the"],
        "agent": "gemini",
        "mode": "edit",
        "model_tier": "complex",
        "reasoning": "Gemini is the primary code generation engine with gemini-3-pro",
    },
    "complex_analysis": {
        "keywords": [
            "deep analysis",
            "comprehensive review",
            "thorough analysis",
            "in-depth review",
            "complex reasoning",
            "detailed analysis",
        ],
        "single_match_keywords": [
            "deep analysis",
            "comprehensive review",
            "thorough analysis",
        ],
        "agent": "copilot",
        "mode": "default",
        "model_tier": "complex",
        "reasoning": "Copilot with Opus for tasks requiring maximum reasoning depth",
    },
    "algorithms": {
        "keywords": [
            "algorithm for",
            "optimize the",
            "time complexity",
            "space complexity",
            "efficient implementation",
            "big o",
            "data structure for",
            "sorting algorithm",
            "search algorithm",
            "optimize performance",
        ],
        "single_match_keywords": ["time complexity", "space complexity", "big o"],
        "agent": "codex",
        "mode": "high_reasoning",
        "model_tier": "complex",
        "reasoning": "Codex with high reasoning for algorithmic thinking and optimization",
    },
    "misc_coding": {
        "keywords": [
            "utility",
            "helper function",
            "script for",
            "small task",
            "quick fix",
            "simple change",
            "minor update",
        ],
        "single_match_keywords": [],
        "agent": "codex",
        "mode": "default",
        "model_tier": "moderate",
        "reasoning": "Codex handles miscellaneous coding tasks efficiently",
    },
}


# ============================================================================
# Installed agents cache
# ============================================================================

_installed_agents_cache: Optional[Dict[str, bool]] = None
_cache_timestamp: float = 0


def check_installed_agents(force_refresh: bool = False) -> Dict[str, bool]:
    """
    Check which AI CLI agents are installed on the system.
    Caches results for 5 minutes to avoid repeated subprocess calls.
    """
    global _installed_agents_cache, _cache_timestamp

    if not force_refresh and _installed_agents_cache is not None:
        if time.time() - _cache_timestamp < 300:
            return _installed_agents_cache

    installed = {}

    for agent, caps in AGENT_CAPABILITIES.items():
        cli_cmd = caps["cli_command"].split()[0]
        try:
            result = subprocess.run(["which", cli_cmd], capture_output=True, timeout=5)
            installed[agent] = result.returncode == 0
        except Exception:
            installed[agent] = False

    _installed_agents_cache = installed
    _cache_timestamp = time.time()

    return installed


# ============================================================================
# Specialized task detection
# ============================================================================


def detect_specialized_task(prompt: str) -> Optional[Dict[str, Any]]:
    """Detect if prompt matches a specialized task pattern."""
    prompt_lower = prompt.lower()

    best_match = None
    best_confidence = 0.0

    for task_name, task_config in SPECIALIZED_TASKS.items():
        keywords = task_config["keywords"]
        single_match_keywords = task_config.get("single_match_keywords", [])

        # Strong single-keyword signals
        single_matches = [kw for kw in single_match_keywords if kw in prompt_lower]
        if single_matches:
            confidence = 0.85 + task_config.get("confidence_boost", 0)
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = {
                    "specialized_task": task_name,
                    "agent": task_config["agent"],
                    "mode": task_config["mode"],
                    "model_tier": task_config["model_tier"],
                    "reasoning": task_config["reasoning"],
                    "confidence": confidence,
                    "matched_keywords": single_matches,
                }
            continue

        # Multiple keyword matches
        matches = [kw for kw in keywords if kw in prompt_lower]
        if len(matches) >= 2:
            confidence = min(0.8 + (len(matches) * 0.05), 0.95)
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = {
                    "specialized_task": task_name,
                    "agent": task_config["agent"],
                    "mode": task_config["mode"],
                    "model_tier": task_config["model_tier"],
                    "reasoning": task_config["reasoning"],
                    "confidence": confidence,
                    "matched_keywords": matches,
                }
        elif len(matches) == 1:
            # Single keyword with supporting context
            supporting = any(
                ctx in prompt_lower
                for ctx in [
                    "codebase",
                    "project",
                    "repo",
                    "module",
                    "component",
                    "system",
                    "authentication",
                    "api",
                    "database",
                    "service",
                    "handler",
                ]
            )
            if supporting:
                confidence = 0.7
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = {
                        "specialized_task": task_name,
                        "agent": task_config["agent"],
                        "mode": task_config["mode"],
                        "model_tier": task_config["model_tier"],
                        "reasoning": task_config["reasoning"],
                        "confidence": confidence,
                        "matched_keywords": matches,
                    }

    return best_match


# ============================================================================
# Classification
# ============================================================================


def classify_prompt(prompt: str, debug: bool = False) -> Dict[str, Any]:
    """
    Classify a prompt using rule-based keyword matching.

    Detects task type (including research/exploration tasks) and estimates
    complexity from multiple signals. Returns task type, complexity, and
    confidence scores.
    """
    prompt_lower = prompt.lower()
    words = prompt_lower.split()
    word_count = len(words)

    task_type = None
    confidence = 0.5
    signals: List[str] = []

    # -1. RESEARCH / EXPLORATION - highest priority
    research_keywords = [
        "research",
        "explore",
        "investigate",
        "find all",
        "search for",
        "look for",
        "identify",
        "discover",
        "locate",
        "where is",
        "how is",
        "understand how",
        "learn about",
        "analyze",
        "find patterns",
        "scan",
        "survey",
        "examine all",
        "across",
        "throughout",
        "in the codebase",
        "in the repo",
        "search the",
        "look through",
        "examine",
        "study",
        "inspect",
    ]

    exploration_patterns = [
        r"how does .* work",
        r"where .* implemented",
        r"find .* usage",
        r"search .* for",
        r"look .* across",
        r"identify all .*",
        r"list all .*",
        r"show .* across",
        r"find all .* in",
    ]

    research_matches = sum(1 for kw in research_keywords if kw in prompt_lower)
    pattern_matches = sum(
        1 for pattern in exploration_patterns if re.search(pattern, prompt_lower)
    )

    if research_matches >= 2 or pattern_matches >= 1:
        task_type = "research"
        confidence = min(
            0.8 + (research_matches * 0.03) + (pattern_matches * 0.05), 0.95
        )
        signals.append(f"research_keywords:{research_matches},patterns:{pattern_matches}")
    elif research_matches == 1:
        code_context = any(
            kw in prompt_lower
            for kw in [
                "codebase",
                "repo",
                "files",
                "modules",
                "code",
                "implementation",
                "across",
                "throughout",
                "all",
                "entire",
                "whole",
                "project",
            ]
        )
        if code_context:
            task_type = "research"
            confidence = 0.75
            signals.append("research_keywords:1,code_context")

    # 0. CODE REVIEW
    if not task_type:
        review_keywords = [
            "review",
            "audit",
            "check for",
            "look for issues",
            "security review",
            "code review",
            "pr review",
            "pull request",
            "vulnerability",
            "best practices",
            "code quality",
        ]
        review_matches = sum(1 for kw in review_keywords if kw in prompt_lower)
        if review_matches > 0:
            task_type = "code_review"
            confidence = min(0.7 + (review_matches * 0.05), 0.95)
            signals.append(f"review_keywords:{review_matches}")

    # 1. CODE DEBUGGING
    if not task_type:
        debug_keywords = [
            "fix",
            "bug",
            "debug",
            "error",
            "broken",
            "failing",
            "crash",
            "exception",
            "traceback",
            "doesn't work",
            "not working",
            "wrong output",
            "unexpected",
            "fault",
            "defect",
        ]
        debug_matches = sum(1 for kw in debug_keywords if kw in prompt_lower)
        if debug_matches > 0:
            task_type = "code_debugging"
            confidence = min(0.7 + (debug_matches * 0.05), 0.95)
            signals.append(f"debug_keywords:{debug_matches}")

    # 2. CODE EXPLANATION
    if not task_type:
        explain_keywords = [
            "explain",
            "what does",
            "how does",
            "understand",
            "walk through",
            "describe",
            "what is",
            "tell me about",
            "how is",
            "why does",
            "meaning of",
            "purpose of",
        ]
        code_context = any(
            kw in prompt_lower
            for kw in [
                "code",
                "function",
                "class",
                "module",
                "method",
                "variable",
                "algorithm",
                "pattern",
                "regex",
                "database",
                "connection",
                "api",
                "endpoint",
                "server",
                "client",
                "request",
                "response",
                "query",
                "cache",
                "pool",
                "thread",
                "process",
                "async",
                ".py",
                ".js",
                ".ts",
                ".go",
                ".rs",
                ".java",
                ".cpp",
                "this file",
                "this code",
                "the code",
                "this script",
            ]
        )
        explain_matches = sum(1 for kw in explain_keywords if kw in prompt_lower)
        if explain_matches > 0 and (code_context or "?" in prompt):
            task_type = "code_explanation"
            confidence = min(0.7 + (explain_matches * 0.05), 0.95)
            signals.append(f"explain_keywords:{explain_matches}")

    # 3. REFACTORING / REWRITE
    if not task_type:
        refactor_keywords = [
            "refactor",
            "restructure",
            "reorganize",
            "clean up",
            "improve",
            "optimize",
            "simplify",
            "modernize",
            "convert to",
            "migrate",
            "upgrade",
            "rewrite",
        ]
        refactor_matches = sum(1 for kw in refactor_keywords if kw in prompt_lower)
        if refactor_matches > 0:
            task_type = "rewrite"
            confidence = min(0.7 + (refactor_matches * 0.05), 0.95)
            signals.append(f"refactor_keywords:{refactor_matches}")

    # 4. CODE GENERATION
    if not task_type:
        gen_keywords = [
            "write",
            "create",
            "implement",
            "build",
            "add",
            "generate",
            "make",
            "develop",
            "set up",
            "scaffold",
            "bootstrap",
        ]
        gen_context = [
            "function",
            "class",
            "api",
            "endpoint",
            "module",
            "script",
            "component",
            "service",
            "handler",
            "test",
            "interface",
            "method",
            "route",
            "middleware",
            "hook",
            "util",
        ]
        gen_matches = sum(1 for kw in gen_keywords if kw in prompt_lower)
        context_matches = sum(1 for kw in gen_context if kw in prompt_lower)
        if gen_matches > 0 and context_matches > 0:
            task_type = "code_generation"
            confidence = min(
                0.7 + (gen_matches * 0.03) + (context_matches * 0.03), 0.95
            )
            signals.append(f"gen_keywords:{gen_matches},context:{context_matches}")
        elif gen_matches >= 2:
            task_type = "code_generation"
            confidence = 0.7
            signals.append(f"gen_keywords:{gen_matches}")

    # 5. SUMMARIZATION
    if not task_type:
        summary_keywords = [
            "summarize",
            "summary",
            "overview",
            "tldr",
            "brief",
            "recap",
            "key points",
            "main points",
            "gist",
        ]
        if any(kw in prompt_lower for kw in summary_keywords):
            task_type = "summarization"
            confidence = 0.8
            signals.append("summary_keywords")

    # 6. MATH / ALGORITHMIC
    if not task_type:
        math_keywords = [
            "calculate",
            "compute",
            "algorithm",
            "complexity",
            "big o",
            "formula",
            "equation",
            "fibonacci",
            "sort",
            "search",
            "optimize",
            "efficient",
        ]
        if any(kw in prompt_lower for kw in math_keywords):
            task_type = "math"
            confidence = 0.75
            signals.append("math_keywords")

    # 7. OPEN QA
    if not task_type:
        if "?" in prompt or any(
            prompt_lower.startswith(q)
            for q in ["what", "why", "how", "when", "where", "which", "can"]
        ):
            task_type = "open_qa"
            confidence = 0.6
            signals.append("question_pattern")

    # 8. DEFAULT
    if not task_type:
        task_type = "code_generation"
        confidence = 0.5
        signals.append("default")

    if debug:
        print(f"[DEBUG] Task type: {task_type}, confidence: {confidence}")
        print(f"[DEBUG] Signals: {signals}")

    # =========================================================================
    # Complexity Estimation (multi-signal)
    # =========================================================================

    complexity_score = 0.0
    complexity_signals: List[str] = []

    # Signal 1: Prompt length
    if word_count > 150:
        complexity_score += 0.3
        complexity_signals.append("very_long")
    elif word_count > 75:
        complexity_score += 0.2
        complexity_signals.append("long")
    elif word_count > 30:
        complexity_score += 0.1
        complexity_signals.append("medium")
    else:
        complexity_signals.append("short")

    # Signal 2: Explicit complexity indicators
    high_complexity = [
        "complex",
        "advanced",
        "sophisticated",
        "comprehensive",
        "full",
        "complete",
        "production",
        "enterprise",
        "scalable",
        "distributed",
        "concurrent",
        "async",
        "parallel",
    ]
    low_complexity = [
        "simple",
        "basic",
        "quick",
        "small",
        "tiny",
        "minimal",
        "just",
        "only",
        "single",
        "one",
    ]

    high_matches = sum(1 for kw in high_complexity if kw in prompt_lower)
    low_matches = sum(1 for kw in low_complexity if kw in prompt_lower)

    if high_matches > 0:
        complexity_score += 0.15 * high_matches
        complexity_signals.append(f"high_kw:{high_matches}")
    if low_matches > 0:
        complexity_score -= 0.1 * low_matches
        complexity_signals.append(f"low_kw:{low_matches}")

    # Signal 3: Multiple requirements (bullet points, numbered lists, "and")
    and_count = prompt_lower.count(" and ")
    bullet_count = prompt.count("- ") + prompt.count("* ") + prompt.count("\u2022 ")
    numbered = len(
        [
            w
            for w in words
            if w.rstrip(".):") in ["1", "2", "3", "4", "5", "first", "second", "third"]
        ]
    )

    multi_req = and_count + bullet_count + numbered
    if multi_req > 3:
        complexity_score += 0.25
        complexity_signals.append(f"multi_req:{multi_req}")
    elif multi_req > 1:
        complexity_score += 0.15
        complexity_signals.append(f"multi_req:{multi_req}")

    # Signal 4: Technical depth indicators
    tech_depth = [
        "authentication",
        "authorization",
        "oauth",
        "jwt",
        "encryption",
        "database",
        "caching",
        "queue",
        "websocket",
        "graphql",
        "grpc",
        "kubernetes",
        "docker",
        "terraform",
        "cicd",
        "pipeline",
        "microservice",
        "architecture",
        "design pattern",
        "solid",
        "transaction",
        "rollback",
        "migration",
        "schema",
    ]
    depth_matches = sum(1 for kw in tech_depth if kw in prompt_lower)
    if depth_matches > 2:
        complexity_score += 0.2
        complexity_signals.append(f"tech_depth:{depth_matches}")
    elif depth_matches > 0:
        complexity_score += 0.1
        complexity_signals.append(f"tech_depth:{depth_matches}")

    # Signal 5: File/scope indicators
    multi_file = [
        "multiple files",
        "several files",
        "across",
        "entire",
        "whole codebase",
        "all files",
        "project-wide",
        "repo",
    ]
    if any(kw in prompt_lower for kw in multi_file):
        complexity_score += 0.15
        complexity_signals.append("multi_file")

    # Signal 6: Research scope boost
    if task_type == "research":
        research_scope = [
            "entire",
            "whole",
            "all",
            "every",
            "across",
            "throughout",
            "complete",
            "comprehensive",
            "full",
            "codebase",
            "repo",
        ]
        scope_matches = sum(1 for kw in research_scope if kw in prompt_lower)
        if scope_matches >= 2:
            complexity_score += 0.20
            complexity_signals.append(f"research_scope:{scope_matches}")
        elif scope_matches == 1:
            complexity_score += 0.10
            complexity_signals.append(f"research_scope:{scope_matches}")

    # Normalize and categorize
    complexity_score = max(0.1, min(0.95, complexity_score + 0.3))

    if complexity_score < 0.35:
        complexity = "simple"
    elif complexity_score < 0.65:
        complexity = "moderate"
    else:
        complexity = "complex"

    if debug:
        print(f"[DEBUG] Complexity: {complexity} ({complexity_score})")
        print(f"[DEBUG] Complexity signals: {complexity_signals}")

    return {
        "task_type": task_type,
        "task_type_confidence": round(confidence, 2),
        "complexity": complexity,
        "complexity_score": round(complexity_score, 2),
        "all_scores": {
            "classifier": "rule_based_v2",
            "task_signals": signals,
            "complexity_signals": complexity_signals,
        },
    }


# ============================================================================
# Agent Selection
# ============================================================================


def select_agent(
    classification: Dict[str, Any],
    prefer_speed: bool = False,
    prefer_cost: bool = False,
    exclude_agents: Optional[List[str]] = None,
    available_only: bool = True,
    prompt: str = "",
) -> Dict[str, Any]:
    """
    Select the best agent based on classification and specialized task detection.

    Returns a dict with: selected_agent, confidence, reasoning, recommended_model,
    recommended_mode, alternative_agents, task_analysis, and optionally
    specialized_task.
    """
    exclude_agents = list(exclude_agents or [])

    if available_only:
        installed = check_installed_agents()
        exclude_agents.extend([a for a, inst in installed.items() if not inst])

    exclude_agents = list(set(exclude_agents))

    # Check specialized tasks first (planning, architecture, review, etc.)
    specialized = detect_specialized_task(prompt) if prompt else None

    if specialized and specialized["agent"] not in exclude_agents:
        agent = specialized["agent"]
        caps = AGENT_CAPABILITIES[agent]
        model_tier = specialized["model_tier"]

        if prefer_cost and model_tier == "complex":
            model_tier = "moderate"
        if prefer_speed and model_tier != "simple":
            model_tier = "moderate" if model_tier == "complex" else "simple"

        recommended_model = caps["models"].get(model_tier, caps["models"]["moderate"])
        recommended_mode = caps["modes"].get(specialized["mode"])

        if agent == "codex" and "reasoning_by_complexity" in caps:
            reasoning_level = caps["reasoning_by_complexity"].get(model_tier, "medium")
            if reasoning_level == "high":
                recommended_mode = caps["modes"].get("high_reasoning")
            else:
                recommended_mode = caps["modes"].get("medium_reasoning")

        return {
            "selected_agent": agent,
            "confidence": specialized["confidence"],
            "reasoning": specialized["reasoning"],
            "recommended_model": recommended_model,
            "recommended_mode": recommended_mode,
            "specialized_task": specialized["specialized_task"],
            "alternative_agents": [],
            "task_analysis": classification,
        }

    # Fall back to general classification-based selection
    task_type = classification["task_type"]
    complexity = classification["complexity"]

    agent_scores: Dict[str, float] = {}

    for agent, caps in AGENT_CAPABILITIES.items():
        if agent in exclude_agents:
            continue

        score = 0.0

        # Direct strength match
        if task_type in caps["strengths"]:
            score += 0.5

        # Task-specific routing bonuses
        if agent == "gemini" and task_type == "code_generation":
            score += 0.3
        elif agent == "cursor" and task_type in [
            "planning",
            "architecture",
            "rewrite",
            "code_debugging",
        ]:
            score += 0.3
        elif agent == "copilot" and complexity == "complex":
            score += 0.2
        elif agent == "codex" and task_type not in [
            "planning",
            "architecture",
            "research",
        ]:
            score += 0.1

        # Complexity preference matching
        if caps["complexity_preference"] == "any":
            score += 0.15
        elif caps["complexity_preference"] == complexity:
            score += 0.25
        elif caps["complexity_preference"] == "complex" and complexity == "moderate":
            score += 0.1

        # Speed/cost preferences
        if prefer_speed and caps["speed"] == "fast":
            score += 0.2
        if prefer_cost and caps["cost"] == "low":
            score += 0.2

        agent_scores[agent] = score

    if not agent_scores:
        return {
            "selected_agent": "gemini",
            "confidence": 0.5,
            "reasoning": "Default fallback - all agents excluded or unavailable",
            "recommended_model": None,
            "recommended_mode": None,
            "alternative_agents": [],
            "task_analysis": classification,
        }

    sorted_agents = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)
    best_agent, best_score = sorted_agents[0]

    best_score = min(1.0, max(0.0, best_score))

    caps = AGENT_CAPABILITIES[best_agent]
    reasoning = f"Task type '{task_type}' with {complexity} complexity."
    if task_type in caps["strengths"]:
        reasoning += f" {best_agent.capitalize()} excels at {task_type}."

    alternatives = [
        {
            "agent": a,
            "score": round(s, 2),
            "description": AGENT_CAPABILITIES[a]["description"],
        }
        for a, s in sorted_agents[1:3]
    ]

    recommended_model = caps["models"].get(complexity)

    # Determine recommended mode based on task type
    recommended_mode = None
    if best_agent == "cursor":
        if task_type in ["planning", "architecture"]:
            recommended_mode = caps["modes"].get("plan")
        elif task_type in ["code_review", "code_explanation"]:
            recommended_mode = caps["modes"].get("ask")
        else:
            recommended_mode = caps["modes"].get("agent")
    elif best_agent == "gemini":
        if task_type in ["code_generation", "documentation", "rewrite"]:
            recommended_mode = caps["modes"].get("edit")
        # Read mode (None) is default for research
    elif best_agent == "codex":
        if "reasoning_by_complexity" in caps:
            reasoning_level = caps["reasoning_by_complexity"].get(complexity, "medium")
            if reasoning_level == "high":
                recommended_mode = caps["modes"].get("high_reasoning")
            else:
                recommended_mode = caps["modes"].get("medium_reasoning")
    elif best_agent == "copilot":
        if task_type in ["code_generation", "refactoring", "rewrite"]:
            recommended_mode = caps["modes"].get("edit")

    return {
        "selected_agent": best_agent,
        "confidence": round(best_score, 2),
        "reasoning": reasoning,
        "recommended_model": recommended_model,
        "recommended_mode": recommended_mode,
        "alternative_agents": alternatives,
        "task_analysis": classification,
    }
