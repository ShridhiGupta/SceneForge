from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum


class PipelineStage(str, Enum):
    SCENE = "scene"
    IMAGE = "image"
    CLIP = "clip"
    RENDER = "render"


class FailureType(str, Enum):
    TIMEOUT = "timeout"
    API_ERROR = "api_error"
    LOW_QUALITY = "low_quality"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    UNKNOWN = "unknown"


class RecoveryAction(str, Enum):
    RETRY = "retry"
    MODIFY_PROMPT = "modify_prompt"
    SWITCH_MODEL = "switch_model"
    ADJUST_PARAMETERS = "adjust_parameters"
    SKIP_TASK = "skip_task"
    ESCALATE_RESOURCES = "escalate_resources"


class FailureContext(BaseModel):
    task_name: str
    stage: PipelineStage
    error_logs: str
    retry_count: int = Field(ge=0)
    output_quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    cost_so_far: float = Field(ge=0.0)
    model_used: str
    prompt_used: str
    additional_context: Optional[Dict[str, Any]] = None


class LLMDecision(BaseModel):
    failure_type: FailureType
    reason: str = Field(..., description="Why the failure occurred")
    action: RecoveryAction
    new_prompt: Optional[str] = None
    new_model: Optional[str] = None
    parameter_changes: Optional[Dict[str, Any]] = None
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in this decision")


class DecisionRequest(BaseModel):
    context: FailureContext


class DecisionResponse(BaseModel):
    decision: LLMDecision
    processing_time_ms: Optional[float] = None
