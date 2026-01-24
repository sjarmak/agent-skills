"""
NVIDIA Prompt Classifier Router Service

Routes tasks to appropriate AI CLI tools (Codex, Copilot, Gemini, Cursor)
based on task type and complexity analysis using NVIDIA's classifier.

Start: uvicorn router:app --host 127.0.0.1 --port 8765
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoConfig, AutoModel
from huggingface_hub import PyTorchModelHubMixin
import os
import json

from context_compressor import compress_agent_output

# Model configuration
MODEL_ID = "nvidia/prompt-task-and-complexity-classifier"

app = FastAPI(
    title="Agent Router Service",
    description="Routes tasks to optimal AI CLI tools using NVIDIA's classifier",
    version="1.0.0"
)


# ============================================================================
# NVIDIA Custom Model Components (from model card)
# ============================================================================

class MeanPooling(nn.Module):
    """Mean pooling layer for BERT-style models."""
    def __init__(self):
        super(MeanPooling, self).__init__()

    def forward(self, last_hidden_state, attention_mask):
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
        sum_embeddings = torch.sum(last_hidden_state * input_mask_expanded, 1)
        sum_mask = input_mask_expanded.sum(1)
        sum_mask = torch.clamp(sum_mask, min=1e-9)
        mean_embeddings = sum_embeddings / sum_mask
        return mean_embeddings


class MulticlassHead(nn.Module):
    """Classification head for multi-class output."""
    def __init__(self, input_dim, num_classes):
        super(MulticlassHead, self).__init__()
        self.fc = nn.Linear(input_dim, num_classes)

    def forward(self, x):
        return self.fc(x)


class CustomModel(nn.Module, PyTorchModelHubMixin):
    """NVIDIA's custom prompt classifier model."""
    def __init__(self, target_sizes, task_type_map, weights_map, divisor_map, base_model="nvidia/NV-Embed-v2"):
        super(CustomModel, self).__init__()
        self.base_model = AutoModel.from_pretrained(base_model, trust_remote_code=True)
        self.mean_pooling = MeanPooling()
        hidden_size = self.base_model.config.hidden_size

        self.heads = nn.ModuleDict()
        for target, num_classes in target_sizes.items():
            self.heads[target] = MulticlassHead(hidden_size, num_classes)

        self.task_type_map = task_type_map
        self.weights_map = weights_map
        self.divisor_map = divisor_map
        self.target_sizes = target_sizes

    def forward(self, encoded_input, debug=False):
        outputs = self.base_model(**encoded_input)
        last_hidden_state = outputs.last_hidden_state
        pooled_output = self.mean_pooling(last_hidden_state, encoded_input["attention_mask"])
        results = {}

        if debug:
            print(f"[DEBUG] Pooled output shape: {pooled_output.shape}")

        for target, head in self.heads.items():
            logits = head(pooled_output)

            if debug:
                print(f"[DEBUG] {target} logits shape: {logits.shape}, values: {logits}")

            if target == "task_type":
                probs = torch.softmax(logits, dim=-1)
                top2 = torch.topk(probs, k=2, dim=-1)

                if debug:
                    print(f"[DEBUG] task_type probs: {probs}")
                    print(f"[DEBUG] task_type top2 indices: {top2.indices}, values: {top2.values}")

                results["task_type_1"] = [self.task_type_map.get(str(i.item()), "Unknown") for i in top2.indices[:, 0]]
                results["task_type_2"] = [self.task_type_map.get(str(i.item()), "Unknown") for i in top2.indices[:, 1]]
                results["task_type_prob"] = [round(p.item(), 4) for p in top2.values[:, 0]]
            else:
                preds = torch.argmax(logits, dim=-1)

                if debug:
                    print(f"[DEBUG] {target} preds: {preds}, divisor: {self.divisor_map.get(target, 1)}")

                results[target] = [round(p.item() / self.divisor_map.get(target, 1), 4) for p in preds]

        if debug:
            print(f"[DEBUG] Final results: {results}")

        return results


# ============================================================================
# Global model instance
# ============================================================================

_tokenizer = None
_model = None
_model_config = None


def get_model():
    """
    Get the classifier model.

    Uses optimized rule-based classification by default.
    Set USE_NVIDIA_MODEL=1 env var to try the NVIDIA model instead.
    """
    global _tokenizer, _model, _model_config

    if _tokenizer is None:
        use_nvidia = os.environ.get("USE_NVIDIA_MODEL", "0") == "1"

        if use_nvidia:
            print("Loading NVIDIA prompt classifier model...")
            print("(This may take a minute on first run)")
            try:
                _model_config = AutoConfig.from_pretrained(MODEL_ID, trust_remote_code=True)
                _tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
                _model = CustomModel(
                    target_sizes=_model_config.target_sizes,
                    task_type_map=_model_config.task_type_map,
                    weights_map=_model_config.weights_map,
                    divisor_map=_model_config.divisor_map,
                ).from_pretrained(MODEL_ID)
                _model.eval()
                print("NVIDIA model loaded successfully.")
            except Exception as e:
                print(f"Warning: Could not load NVIDIA model: {e}")
                print("Falling back to rule-based classification.")
                _tokenizer = "fallback"
                _model = "fallback"
        else:
            print("Using optimized rule-based classifier (fast, no model loading)")
            _tokenizer = "fallback"
            _model = "fallback"

    return _tokenizer, _model


# ============================================================================
# Task type mapping (NVIDIA labels -> our internal labels)
# ============================================================================

NVIDIA_TO_INTERNAL = {
    "Code Generation": "code_generation",
    "Text Generation": "text_generation",
    "Open QA": "open_qa",
    "Closed QA": "closed_qa",
    "Summarization": "summarization",
    "Chatbot": "chat",
    "Classification": "classify",
    "Rewrite": "rewrite",
    "Brainstorming": "brainstorm",
    "Extraction": "extraction",
    "Other": "other",
}

# Our internal task labels
TASK_LABELS = [
    "brainstorm",
    "chat",
    "classify",
    "closed_qa",
    "code_generation",
    "code_explanation",
    "code_debugging",
    "code_review",
    "extraction",
    "math",
    "open_qa",
    "rewrite",
    "summarization",
    "text_generation",
    "other"
]

# Complexity levels
COMPLEXITY_LABELS = ["simple", "moderate", "complex"]

# Agent capabilities mapping
AGENT_CAPABILITIES = {
    "codex": {
        "strengths": ["code_generation", "code_debugging", "math"],
        "complexity_preference": "complex",
        "description": "OpenAI Codex CLI - best for complex code generation with high reasoning",
        "speed": "slow",
        "cost": "high"
    },
    "cursor": {
        "strengths": ["code_generation", "code_explanation", "code_review", "rewrite"],
        "complexity_preference": "moderate",
        "description": "Cursor AI - best for repo-aware edits and refactoring",
        "speed": "medium",
        "cost": "medium"
    },
    "gemini": {
        "strengths": ["open_qa", "summarization", "brainstorm", "extraction", "code_explanation", "text_generation"],
        "complexity_preference": "any",
        "description": "Gemini CLI - best for analysis, explanation, and general reasoning",
        "speed": "fast",
        "cost": "low"
    },
    "copilot": {
        "strengths": ["code_generation", "code_debugging", "closed_qa"],
        "complexity_preference": "simple",
        "description": "GitHub Copilot CLI - fast for straightforward code tasks",
        "speed": "fast",
        "cost": "low"
    }
}


# ============================================================================
# Request/Response models
# ============================================================================

class RouteRequest(BaseModel):
    """Request model for routing decisions."""
    prompt: str
    context: Optional[str] = None
    prefer_speed: bool = False
    prefer_cost: bool = False
    exclude_agents: Optional[List[str]] = None
    force_agent: Optional[str] = None
    debug: bool = False  # Enable debug output


class RouteResponse(BaseModel):
    """Response model with routing decision and analysis."""
    selected_agent: str
    confidence: float
    reasoning: str
    task_analysis: Dict[str, Any]
    alternative_agents: List[Dict[str, Any]]
    recommended_flags: Dict[str, str]


class ClassifyResponse(BaseModel):
    """Response model for classification only."""
    task_type: str
    task_type_confidence: float
    complexity: str
    complexity_score: float
    all_scores: Dict[str, Any]


class CompressRequest(BaseModel):
    """Request model for context compression."""
    content: str
    level: str = "moderate"
    max_tokens: int = 2000


class CompressResponse(BaseModel):
    """Response model for compressed content."""
    compressed: str
    code_blocks: List[str]
    file_paths: List[str]
    errors: List[str]
    original_length: int
    compressed_length: int
    compression_ratio: float


# ============================================================================
# Classification functions
# ============================================================================

def _default_classification() -> Dict[str, Any]:
    """Return default classification when model fails."""
    return {
        "task_type": "code_generation",
        "task_type_confidence": 0.5,
        "complexity": "moderate",
        "complexity_score": 0.5,
        "all_scores": {}
    }


def _rule_based_classify(prompt: str) -> Dict[str, Any]:
    """
    Enhanced rule-based classification optimized for coding tasks.

    Uses weighted keyword matching with priority ordering and
    multi-signal complexity estimation.
    """
    prompt_lower = prompt.lower()
    words = prompt_lower.split()
    word_count = len(words)

    # =========================================================================
    # Task Type Detection (priority ordered - first match wins)
    # =========================================================================

    task_type = None
    confidence = 0.5
    signals = []

    # 0. CODE REVIEW - check first because "issues" overlaps with debugging
    review_keywords = ["review", "audit", "check for", "look for issues",
                      "security review", "code review", "pr review", "pull request",
                      "vulnerability", "best practices", "code quality"]
    review_matches = sum(1 for kw in review_keywords if kw in prompt_lower)
    if review_matches > 0:
        task_type = "code_review"
        confidence = min(0.7 + (review_matches * 0.05), 0.95)
        signals.append(f"review_keywords:{review_matches}")

    # 1. CODE DEBUGGING - for "fix" type tasks (but not if already matched review)
    if not task_type:
        debug_keywords = ["fix", "bug", "debug", "error", "broken", "failing",
                          "crash", "exception", "traceback", "doesn't work", "not working",
                          "wrong output", "unexpected", "fault", "defect"]
        debug_matches = sum(1 for kw in debug_keywords if kw in prompt_lower)
        if debug_matches > 0:
            task_type = "code_debugging"
            confidence = min(0.7 + (debug_matches * 0.05), 0.95)
            signals.append(f"debug_keywords:{debug_matches}")

    # 2. CODE EXPLANATION
    if not task_type:
        explain_keywords = ["explain", "what does", "how does", "understand",
                           "walk through", "describe", "what is", "tell me about",
                           "how is", "why does", "meaning of", "purpose of"]
        code_context = any(kw in prompt_lower for kw in
                          ["code", "function", "class", "module", "method", "variable",
                           "algorithm", "pattern", "regex", "database", "connection",
                           "api", "endpoint", "server", "client", "request", "response",
                           "query", "cache", "pool", "thread", "process", "async",
                           ".py", ".js", ".ts", ".go", ".rs", ".java", ".cpp",
                           "this file", "this code", "the code", "this script"])
        explain_matches = sum(1 for kw in explain_keywords if kw in prompt_lower)
        if explain_matches > 0 and (code_context or "?" in prompt):
            task_type = "code_explanation"
            confidence = min(0.7 + (explain_matches * 0.05), 0.95)
            signals.append(f"explain_keywords:{explain_matches}")

    # 4. REFACTORING / REWRITE
    if not task_type:
        refactor_keywords = ["refactor", "restructure", "reorganize", "clean up",
                            "improve", "optimize", "simplify", "modernize",
                            "convert to", "migrate", "upgrade", "rewrite"]
        refactor_matches = sum(1 for kw in refactor_keywords if kw in prompt_lower)
        if refactor_matches > 0:
            task_type = "rewrite"
            confidence = min(0.7 + (refactor_matches * 0.05), 0.95)
            signals.append(f"refactor_keywords:{refactor_matches}")

    # 5. CODE GENERATION
    if not task_type:
        gen_keywords = ["write", "create", "implement", "build", "add", "generate",
                       "make", "develop", "set up", "scaffold", "bootstrap"]
        gen_context = ["function", "class", "api", "endpoint", "module", "script",
                      "component", "service", "handler", "test", "interface",
                      "method", "route", "middleware", "hook", "util"]
        gen_matches = sum(1 for kw in gen_keywords if kw in prompt_lower)
        context_matches = sum(1 for kw in gen_context if kw in prompt_lower)
        if gen_matches > 0 and context_matches > 0:
            task_type = "code_generation"
            confidence = min(0.7 + (gen_matches * 0.03) + (context_matches * 0.03), 0.95)
            signals.append(f"gen_keywords:{gen_matches},context:{context_matches}")
        elif gen_matches >= 2:
            task_type = "code_generation"
            confidence = 0.7
            signals.append(f"gen_keywords:{gen_matches}")

    # 6. SUMMARIZATION
    if not task_type:
        summary_keywords = ["summarize", "summary", "overview", "tldr", "brief",
                          "recap", "key points", "main points", "gist"]
        if any(kw in prompt_lower for kw in summary_keywords):
            task_type = "summarization"
            confidence = 0.8
            signals.append("summary_keywords")

    # 7. MATH / ALGORITHMIC
    if not task_type:
        math_keywords = ["calculate", "compute", "algorithm", "complexity",
                        "big o", "formula", "equation", "fibonacci", "sort",
                        "search", "optimize", "efficient"]
        if any(kw in prompt_lower for kw in math_keywords):
            task_type = "math"
            confidence = 0.75
            signals.append("math_keywords")

    # 8. OPEN QA - questions without clear code context
    if not task_type:
        if "?" in prompt or any(prompt_lower.startswith(q) for q in
                                ["what", "why", "how", "when", "where", "which", "can"]):
            task_type = "open_qa"
            confidence = 0.6
            signals.append("question_pattern")

    # 9. DEFAULT - assume code generation for coding assistant context
    if not task_type:
        task_type = "code_generation"
        confidence = 0.5
        signals.append("default")

    # =========================================================================
    # Complexity Estimation (multi-signal)
    # =========================================================================

    complexity_score = 0.0
    complexity_signals = []

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
    high_complexity = ["complex", "advanced", "sophisticated", "comprehensive",
                      "full", "complete", "production", "enterprise", "scalable",
                      "distributed", "concurrent", "async", "parallel"]
    low_complexity = ["simple", "basic", "quick", "small", "tiny", "minimal",
                     "just", "only", "single", "one"]

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
    bullet_count = prompt.count("- ") + prompt.count("* ") + prompt.count("• ")
    numbered = len([w for w in words if w.rstrip(".):") in
                   ["1", "2", "3", "4", "5", "first", "second", "third"]])

    multi_req = and_count + bullet_count + numbered
    if multi_req > 3:
        complexity_score += 0.25
        complexity_signals.append(f"multi_req:{multi_req}")
    elif multi_req > 1:
        complexity_score += 0.15
        complexity_signals.append(f"multi_req:{multi_req}")

    # Signal 4: Technical depth indicators
    tech_depth = ["authentication", "authorization", "oauth", "jwt", "encryption",
                 "database", "caching", "queue", "websocket", "graphql", "grpc",
                 "kubernetes", "docker", "terraform", "cicd", "pipeline",
                 "microservice", "architecture", "design pattern", "solid",
                 "transaction", "rollback", "migration", "schema"]
    depth_matches = sum(1 for kw in tech_depth if kw in prompt_lower)
    if depth_matches > 2:
        complexity_score += 0.2
        complexity_signals.append(f"tech_depth:{depth_matches}")
    elif depth_matches > 0:
        complexity_score += 0.1
        complexity_signals.append(f"tech_depth:{depth_matches}")

    # Signal 5: File/scope indicators
    multi_file = ["multiple files", "several files", "across", "entire",
                 "whole codebase", "all files", "project-wide", "repo"]
    if any(kw in prompt_lower for kw in multi_file):
        complexity_score += 0.15
        complexity_signals.append("multi_file")

    # Normalize and categorize
    complexity_score = max(0.1, min(0.95, complexity_score + 0.3))  # base + signals

    if complexity_score < 0.35:
        complexity = "simple"
    elif complexity_score < 0.65:
        complexity = "moderate"
    else:
        complexity = "complex"

    return {
        "task_type": task_type,
        "task_type_confidence": round(confidence, 2),
        "complexity": complexity,
        "complexity_score": round(complexity_score, 2),
        "all_scores": {
            "classifier": "rule_based_v2",
            "task_signals": signals,
            "complexity_signals": complexity_signals
        }
    }


def _detect_coding_task(prompt: str) -> Optional[tuple[str, float]]:
    """
    Detect specific coding task types from keywords.
    Returns (task_type, confidence) or None if not a clear coding task.
    """
    prompt_lower = prompt.lower()

    # Code debugging - highest priority
    if any(kw in prompt_lower for kw in ["fix", "bug", "error", "debug", "issue", "broken", "failing", "crash"]):
        return ("code_debugging", 0.85)

    # Code explanation
    if any(kw in prompt_lower for kw in ["explain", "what does", "how does", "understand", "walk through", "describe how"]):
        if any(kw in prompt_lower for kw in ["code", "function", "class", "module", "file", ".py", ".js", ".ts"]):
            return ("code_explanation", 0.85)

    # Code review
    if any(kw in prompt_lower for kw in ["review", "audit", "check for", "security", "vulnerability", "pr ", "pull request"]):
        return ("code_review", 0.85)

    # Refactoring
    if any(kw in prompt_lower for kw in ["refactor", "restructure", "reorganize", "clean up", "improve the code"]):
        return ("rewrite", 0.85)

    # Code generation - explicit signals
    if any(kw in prompt_lower for kw in ["write", "create", "implement", "build", "add", "generate"]):
        if any(kw in prompt_lower for kw in ["function", "class", "api", "endpoint", "module", "script", "code", "program"]):
            return ("code_generation", 0.85)

    # Test writing
    if any(kw in prompt_lower for kw in ["test", "unit test", "integration test", "write tests"]):
        return ("code_generation", 0.80)

    return None


def classify_prompt(prompt: str, debug: bool = False) -> Dict[str, Any]:
    """
    Classify a prompt using the NVIDIA model with coding-aware overrides.

    Returns task type, complexity, and confidence scores.
    """
    try:
        tokenizer, model = get_model()

        # Use fallback if model didn't load
        if tokenizer == "fallback" or model == "fallback":
            return _rule_based_classify(prompt)

        # First, check for clear coding task patterns
        coding_override = _detect_coding_task(prompt)
        if debug and coding_override:
            print(f"[DEBUG] Coding task detected: {coding_override}")

        # Tokenize with required prefix
        encoded = tokenizer(
            [f"Prompt: {prompt}"],
            return_tensors="pt",
            add_special_tokens=True,
            max_length=512,
            padding="max_length",
            truncation=True,
        )

        if debug:
            print(f"[DEBUG] Input prompt: {prompt}")
            print(f"[DEBUG] Encoded input_ids shape: {encoded['input_ids'].shape}")

        with torch.no_grad():
            result = model(encoded, debug=debug)

        # Extract primary task type from NVIDIA model
        primary_task = result.get("task_type_1", ["Other"])[0]
        nvidia_task_type = NVIDIA_TO_INTERNAL.get(primary_task, "other")
        task_confidence = result.get("task_type_prob", [0.5])[0]

        # Use coding override if detected, otherwise use NVIDIA classification
        if coding_override:
            task_type, task_confidence = coding_override
            if debug:
                print(f"[DEBUG] Using coding override: {task_type} (NVIDIA said: {nvidia_task_type})")
        else:
            task_type = nvidia_task_type

        # Calculate complexity score from individual dimensions
        # Weights: 0.35*Creativity + 0.25*Reasoning + 0.15*Constraints + 0.15*DomainKnowledge + 0.05*ContextualKnowledge
        creativity = result.get("creativity_scope", [0])[0] if result.get("creativity_scope") else 0
        reasoning = result.get("reasoning", [0])[0] if result.get("reasoning") else 0
        constraints = result.get("constraint_ct", [0])[0] if result.get("constraint_ct") else 0
        domain_knowledge = result.get("domain_knowledge", [0])[0] if result.get("domain_knowledge") else 0
        contextual = result.get("contextual_knowledge", [0])[0] if result.get("contextual_knowledge") else 0

        # Ensure all values are numeric
        def safe_float(v):
            try:
                return float(v) if not isinstance(v, (list, tuple)) else float(v[0]) if v else 0.0
            except:
                return 0.0

        complexity_score = (
            0.35 * safe_float(creativity) +
            0.25 * safe_float(reasoning) +
            0.15 * safe_float(constraints) +
            0.15 * safe_float(domain_knowledge) +
            0.05 * safe_float(contextual)
        )

        # Map complexity score to level
        if complexity_score < 0.3:
            complexity = "simple"
        elif complexity_score < 0.6:
            complexity = "moderate"
        else:
            complexity = "complex"

        return {
            "task_type": task_type,
            "task_type_confidence": task_confidence,
            "complexity": complexity,
            "complexity_score": round(complexity_score, 4),
            "all_scores": {
                "primary_task": primary_task,
                "secondary_task": result.get("task_type_2", ["Unknown"])[0],
                "creativity": safe_float(creativity),
                "reasoning": safe_float(reasoning),
                "domain_knowledge": safe_float(domain_knowledge),
                "constraints": safe_float(constraints),
            }
        }

    except Exception as e:
        print(f"Error in classify_prompt: {e}")
        import traceback
        traceback.print_exc()
        return _rule_based_classify(prompt)


# ============================================================================
# Agent selection
# ============================================================================

def select_agent(
    classification: Dict[str, Any],
    prefer_speed: bool = False,
    prefer_cost: bool = False,
    exclude_agents: Optional[List[str]] = None
) -> tuple[str, float, str, List[Dict[str, Any]]]:
    """
    Select the best agent based on classification results.

    Returns: (selected_agent, confidence, reasoning, alternatives)
    """
    exclude_agents = exclude_agents or []
    task_type = classification["task_type"]
    complexity = classification["complexity"]

    agent_scores = {}

    for agent, caps in AGENT_CAPABILITIES.items():
        if agent in exclude_agents:
            continue

        score = 0.0

        # Task type match (primary factor)
        if task_type in caps["strengths"]:
            score += 0.5

        # Complexity match
        if caps["complexity_preference"] == "any":
            score += 0.2
        elif caps["complexity_preference"] == complexity:
            score += 0.3
        elif (caps["complexity_preference"] == "complex" and complexity == "moderate"):
            score += 0.15
        elif (caps["complexity_preference"] == "moderate" and complexity in ["simple", "complex"]):
            score += 0.1

        # Speed preference
        if prefer_speed:
            if caps["speed"] == "fast":
                score += 0.2
            elif caps["speed"] == "medium":
                score += 0.1

        # Cost preference
        if prefer_cost:
            if caps["cost"] == "low":
                score += 0.2
            elif caps["cost"] == "medium":
                score += 0.1

        agent_scores[agent] = score

    if not agent_scores:
        return "gemini", 0.5, "Default fallback - all agents excluded", []

    sorted_agents = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)
    best_agent, best_score = sorted_agents[0]

    # Generate reasoning
    caps = AGENT_CAPABILITIES[best_agent]
    reasoning_parts = [f"Task type '{task_type}' with {complexity} complexity."]

    if task_type in caps["strengths"]:
        reasoning_parts.append(f"{best_agent.capitalize()} excels at {task_type}.")

    if prefer_speed:
        reasoning_parts.append(f"Speed preferred; {best_agent} is {caps['speed']}.")

    if prefer_cost:
        reasoning_parts.append(f"Cost preferred; {best_agent} cost is {caps['cost']}.")

    reasoning = " ".join(reasoning_parts)

    alternatives = [
        {
            "agent": agent,
            "score": score,
            "description": AGENT_CAPABILITIES[agent]["description"]
        }
        for agent, score in sorted_agents[1:3]
    ]

    return best_agent, best_score, reasoning, alternatives


def get_recommended_flags(agent: str, classification: Dict[str, Any]) -> Dict[str, str]:
    """Get recommended CLI flags based on agent and task analysis."""
    task_type = classification["task_type"]
    complexity = classification["complexity"]

    flags = {}

    if agent == "codex":
        flags["sandbox"] = "workspace-write" if task_type in ["code_generation", "code_debugging"] else "read-only"
        if complexity == "complex":
            flags["reasoning"] = "high"
        elif complexity == "simple":
            flags["reasoning"] = "low"
        else:
            flags["reasoning"] = "medium"

    elif agent == "cursor":
        if task_type in ["code_generation", "code_debugging", "rewrite"]:
            flags["mode"] = "agent"
        elif task_type in ["code_explanation", "code_review"]:
            flags["mode"] = "ask"
        else:
            flags["mode"] = "agent"

    elif agent == "gemini":
        if task_type in ["code_generation", "code_debugging", "rewrite"]:
            flags["approval"] = "--yolo"
        else:
            flags["approval"] = "(none - read-only)"
        if complexity == "complex":
            flags["model"] = "gemini-2.5-pro"
        else:
            flags["model"] = "gemini-2.5-flash"

    elif agent == "copilot":
        if task_type in ["code_generation", "code_debugging", "rewrite"]:
            flags["permissions"] = "--allow-all-paths"
        else:
            flags["permissions"] = "(none - read-only)"

    return flags


# ============================================================================
# API Endpoints
# ============================================================================

@app.post("/route", response_model=RouteResponse)
async def route_task(request: RouteRequest) -> RouteResponse:
    """Route a task to the optimal AI CLI agent."""
    if request.force_agent:
        if request.force_agent not in AGENT_CAPABILITIES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid agent: {request.force_agent}. Valid agents: {list(AGENT_CAPABILITIES.keys())}"
            )
        classification = classify_prompt(request.prompt, debug=request.debug)
        return RouteResponse(
            selected_agent=request.force_agent,
            confidence=1.0,
            reasoning=f"Agent forced to {request.force_agent} by request",
            task_analysis=classification,
            alternative_agents=[],
            recommended_flags=get_recommended_flags(request.force_agent, classification)
        )

    classification = classify_prompt(request.prompt, debug=request.debug)

    selected_agent, confidence, reasoning, alternatives = select_agent(
        classification,
        prefer_speed=request.prefer_speed,
        prefer_cost=request.prefer_cost,
        exclude_agents=request.exclude_agents
    )

    flags = get_recommended_flags(selected_agent, classification)

    return RouteResponse(
        selected_agent=selected_agent,
        confidence=confidence,
        reasoning=reasoning,
        task_analysis=classification,
        alternative_agents=alternatives,
        recommended_flags=flags
    )


@app.post("/classify", response_model=ClassifyResponse)
async def classify_task(request: RouteRequest) -> ClassifyResponse:
    """Classify a prompt without making a routing decision."""
    classification = classify_prompt(request.prompt)

    return ClassifyResponse(
        task_type=classification["task_type"],
        task_type_confidence=classification["task_type_confidence"],
        complexity=classification["complexity"],
        complexity_score=classification["complexity_score"],
        all_scores=classification.get("all_scores", {})
    )


@app.post("/compress", response_model=CompressResponse)
async def compress_content(request: CompressRequest) -> CompressResponse:
    """Compress agent output to minimize token usage."""
    if request.level not in ["minimal", "moderate", "aggressive"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid level: {request.level}. Valid levels: minimal, moderate, aggressive"
        )

    result = compress_agent_output(
        request.content,
        level=request.level,
        max_tokens=request.max_tokens
    )

    return CompressResponse(**result)


@app.get("/agents")
async def list_agents() -> Dict[str, Any]:
    """List all available agents and their capabilities."""
    return AGENT_CAPABILITIES


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    tokenizer, model = get_model()
    if model == "fallback":
        return {
            "status": "healthy",
            "classifier": "rule_based_v2",
            "description": "Optimized keyword-based classifier for coding tasks"
        }
    else:
        return {
            "status": "healthy",
            "classifier": "nvidia",
            "model": MODEL_ID
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)
