"""
Agent Router Service

FastAPI server that routes tasks to appropriate AI CLI tools
(Codex, Copilot, Gemini, Cursor) using the shared rule-based classifier.

Start: uvicorn router:app --host 127.0.0.1 --port 8765
"""

from typing import Any, Dict, List, Optional

from classifier import (
    AGENT_CAPABILITIES,
    check_installed_agents,
    classify_prompt,
    select_agent,
)
from context_compressor import compress_agent_output
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Agent Router Service",
    description="Routes tasks to optimal AI CLI tools using rule-based classification",
    version="1.0.0",
)


# ============================================================================
# Request/Response models
# ============================================================================


class RouteRequest(BaseModel):
    """Request model for routing decisions."""

    prompt: str
    prefer_speed: bool = False
    prefer_cost: bool = False
    exclude_agents: Optional[List[str]] = None
    force_agent: Optional[str] = None
    only_available: bool = True
    debug: bool = False


class RouteResponse(BaseModel):
    """Response model with routing decision and analysis."""

    selected_agent: str
    confidence: float
    reasoning: str
    task_analysis: Dict[str, Any]
    alternative_agents: List[Dict[str, Any]]
    recommended_model: Optional[str] = None
    recommended_mode: Optional[str] = None
    specialized_task: Optional[str] = None
    available_agents: List[str] = []
    unavailable_agents: List[str] = []


class ClassifyRequest(BaseModel):
    """Request model for the /classify endpoint."""

    prompt: str
    debug: bool = False


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
# API Endpoints
# ============================================================================


@app.post("/route", response_model=RouteResponse)
async def route_task(request: RouteRequest) -> RouteResponse:
    """Route a task to the optimal AI CLI agent."""
    installed = check_installed_agents()
    available = [a for a, is_inst in installed.items() if is_inst]
    unavailable = [a for a, is_inst in installed.items() if not is_inst]

    exclude_agents = list(request.exclude_agents or [])
    if request.only_available:
        exclude_agents.extend(unavailable)
    exclude_agents = list(set(exclude_agents))

    if request.force_agent:
        if request.force_agent not in AGENT_CAPABILITIES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid agent: {request.force_agent}. Valid agents: {list(AGENT_CAPABILITIES.keys())}",
            )
        if request.only_available and request.force_agent in unavailable:
            raise HTTPException(
                status_code=400,
                detail=f"Agent '{request.force_agent}' is not installed. Install it or set only_available=false",
            )
        classification = classify_prompt(request.prompt, debug=request.debug)
        complexity = classification["complexity"]
        recommended_model = AGENT_CAPABILITIES[request.force_agent]["models"].get(
            complexity
        )
        return RouteResponse(
            selected_agent=request.force_agent,
            confidence=1.0,
            reasoning=f"Agent forced to {request.force_agent} by request",
            task_analysis=classification,
            alternative_agents=[],
            recommended_model=recommended_model,
            available_agents=available,
            unavailable_agents=unavailable,
        )

    classification = classify_prompt(request.prompt, debug=request.debug)

    result = select_agent(
        classification,
        prefer_speed=request.prefer_speed,
        prefer_cost=request.prefer_cost,
        exclude_agents=exclude_agents,
        available_only=False,  # Already filtered above
        prompt=request.prompt,
    )

    return RouteResponse(
        selected_agent=result["selected_agent"],
        confidence=result["confidence"],
        reasoning=result["reasoning"],
        task_analysis=result["task_analysis"],
        alternative_agents=result["alternative_agents"],
        recommended_model=result.get("recommended_model"),
        recommended_mode=result.get("recommended_mode"),
        specialized_task=result.get("specialized_task"),
        available_agents=available,
        unavailable_agents=unavailable,
    )


@app.post("/classify", response_model=ClassifyResponse)
async def classify_task(request: ClassifyRequest) -> ClassifyResponse:
    """Classify a prompt without making a routing decision."""
    classification = classify_prompt(request.prompt, debug=request.debug)

    return ClassifyResponse(
        task_type=classification["task_type"],
        task_type_confidence=classification["task_type_confidence"],
        complexity=classification["complexity"],
        complexity_score=classification["complexity_score"],
        all_scores=classification.get("all_scores", {}),
    )


@app.post("/compress", response_model=CompressResponse)
async def compress_content(request: CompressRequest) -> CompressResponse:
    """Compress agent output to minimize token usage."""
    if request.level not in ["minimal", "moderate", "aggressive"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid level: {request.level}. Valid levels: minimal, moderate, aggressive",
        )

    result = compress_agent_output(
        request.content, level=request.level, max_tokens=request.max_tokens
    )

    return CompressResponse(**result)


@app.get("/agents")
async def list_agents() -> Dict[str, Any]:
    """List all available agents and their capabilities."""
    return AGENT_CAPABILITIES


@app.get("/agents/installed")
async def list_installed_agents(refresh: bool = False) -> Dict[str, Any]:
    """Check which agents are installed on the system."""
    installed = check_installed_agents(force_refresh=refresh)
    available = [a for a, is_inst in installed.items() if is_inst]
    unavailable = [a for a, is_inst in installed.items() if not is_inst]

    return {
        "installed": installed,
        "available": available,
        "unavailable": unavailable,
        "install_instructions": {
            agent: "See https://github.com/sjarmak/agent-skills#installing-cli-tools"
            for agent in unavailable
        },
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "classifier": "rule_based_v2",
        "description": "Optimized keyword-based classifier for coding tasks",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765)
