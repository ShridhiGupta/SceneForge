from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class RecoveryAction(str, Enum):
    RETRY = "retry"
    MODIFY_PROMPT = "modify_prompt"
    SWITCH_MODEL = "switch_model"
    ADJUST_PARAMETERS = "adjust_parameters"
    SKIP_TASK = "skip_task"
    ESCALATE_RESOURCES = "escalate_resources"


class FailureType(str, Enum):
    TIMEOUT = "timeout"
    API_ERROR = "api_error"
    LOW_QUALITY = "low_quality"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    UNKNOWN = "unknown"


class PipelineStage(str, Enum):
    SCENE = "scene"
    IMAGE = "image"
    CLIP = "clip"
    RENDER = "render"


class FailureMemory(BaseModel):
    """Schema for storing failure experiences in memory"""
    
    # Core failure information
    failure_type: FailureType
    stage: PipelineStage
    error_logs: str
    prompt_used: str
    model_used: str
    
    # Decision and outcome
    action_taken: RecoveryAction
    new_prompt: Optional[str] = None
    new_model: Optional[str] = None
    parameter_changes: Optional[Dict[str, Any]] = None
    
    # Results
    success: bool = Field(..., description="Whether the recovery action succeeded")
    final_quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    total_cost: float = Field(ge=0.0)
    retry_count: int = Field(ge=0)
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    task_id: Optional[str] = None
    video_id: Optional[int] = None
    scene_id: Optional[int] = None
    
    # Embedding metadata
    embedding_id: Optional[str] = None
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class MemoryQuery(BaseModel):
    """Query for searching failure memory"""
    
    # Current failure context
    failure_type: FailureType
    stage: PipelineStage
    error_logs: str
    prompt_used: str
    model_used: str
    
    # Query parameters
    top_k: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0)
    require_success: bool = Field(default=True, description="Only return successful recoveries")


class MemoryResult(BaseModel):
    """Result from memory search"""
    
    memory: FailureMemory
    similarity_score: float = Field(ge=0.0, le=1.0)
    relevance_explanation: str


class MemorySearchResponse(BaseModel):
    """Response for memory search"""
    
    query: MemoryQuery
    results: List[MemoryResult]
    total_found: int
    search_time_ms: Optional[float] = None


class MemoryStats(BaseModel):
    """Statistics about the memory system"""
    
    total_memories: int
    memories_by_stage: Dict[str, int]
    memories_by_failure_type: Dict[str, int]
    success_rate_by_action: Dict[str, float]
    average_similarity_score: float
    last_updated: datetime
