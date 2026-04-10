from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class PipelineStatus(str, Enum):
    INITIALIZING = "initializing"
    PROCESSING_SCENES = "processing_scenes"
    GENERATING_IMAGES = "generating_images"
    EVALUATING_QUALITY = "evaluating_quality"
    MAKING_DECISIONS = "making_decisions"
    OPTIMIZING_COST = "optimizing_cost"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"


class QualityLevel(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class DecisionAction(str, Enum):
    RETRY = "retry"
    MODIFY_PROMPT = "modify_prompt"
    SWITCH_MODEL = "switch_model"
    ADJUST_PARAMETERS = "adjust_parameters"
    SKIP_TASK = "skip_task"
    ESCALATE_RESOURCES = "escalate_resources"
    CONTINUE = "continue"


class Scene(BaseModel):
    """Individual scene data"""
    id: int
    scene_number: int
    description: str
    duration: float
    prompt: Optional[str] = None
    image_path: Optional[str] = None
    quality_score: Optional[float] = None
    retry_count: int = 0
    cost: float = 0.0
    model_used: Optional[str] = None
    status: AgentStatus = AgentStatus.IDLE


class GenerationResult(BaseModel):
    """Result from image generation"""
    success: bool
    image_path: Optional[str] = None
    model_used: Optional[str] = None
    cost: float = 0.0
    error_message: Optional[str] = None
    generation_time_ms: Optional[float] = None


class QualityResult(BaseModel):
    """Result from quality evaluation"""
    success: bool
    quality_score: float = Field(ge=0.0, le=1.0)
    quality_level: QualityLevel
    passes_threshold: bool
    clip_score: Optional[float] = None
    llm_score: Optional[float] = None
    evaluation_time_ms: Optional[float] = None
    reasoning: Optional[str] = None


class DecisionResult(BaseModel):
    """Result from decision agent"""
    action: DecisionAction
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    new_prompt: Optional[str] = None
    new_model: Optional[str] = None
    parameter_changes: Optional[Dict[str, Any]] = None
    estimated_cost_impact: float = 0.0


class CostOptimization(BaseModel):
    """Cost optimization recommendations"""
    total_cost: float
    budget_limit: Optional[float] = None
    cost_per_scene: float
    optimization_suggestions: List[str]
    recommended_model: Optional[str] = None
    potential_savings: float = 0.0


class PipelineState(BaseModel):
    """Complete pipeline state shared between agents"""
    
    # Core pipeline data
    video_id: int
    title: str
    script: str
    total_budget: Optional[float] = None
    
    # Scene management
    scenes: List[Scene] = Field(default_factory=list)
    current_scene_index: int = 0
    completed_scenes: int = 0
    
    # Generation tracking
    generation_results: List[GenerationResult] = Field(default_factory=list)
    quality_results: List[QualityResult] = Field(default_factory=list)
    decision_results: List[DecisionResult] = Field(default_factory=list)
    
    # Cost tracking
    total_cost: float = 0.0
    cost_breakdown: Dict[str, float] = Field(default_factory=dict)
    cost_optimization: Optional[CostOptimization] = None
    
    # Pipeline status
    status: PipelineStatus = PipelineStatus.INITIALIZING
    current_agent: Optional[str] = None
    agent_statuses: Dict[str, AgentStatus] = Field(default_factory=dict)
    
    # Retry and error handling
    retry_count: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None
    error_history: List[str] = Field(default_factory=list)
    
    # Configuration
    quality_threshold: float = 0.5
    preferred_model: str = "stable-diffusion-xl"
    enable_cost_optimization: bool = True
    
    # Metadata
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    execution_time_ms: Optional[float] = None
    
    # Agent communication
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    shared_context: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        arbitrary_types_allowed = True


class AgentMessage(BaseModel):
    """Message between agents"""
    sender: str
    recipient: str
    message_type: Literal["request", "response", "notification", "error"]
    content: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    priority: int = Field(default=1, ge=1, le=5)  # 1=low, 5=high


class AgentConfig(BaseModel):
    """Configuration for individual agents"""
    name: str
    enabled: bool = True
    max_retries: int = 3
    timeout_seconds: int = 300
    retry_delay_seconds: int = 60
    custom_config: Dict[str, Any] = Field(default_factory=dict)


class WorkflowConfig(BaseModel):
    """Configuration for the entire workflow"""
    agents: Dict[str, AgentConfig] = Field(default_factory=dict)
    global_settings: Dict[str, Any] = Field(default_factory=dict)
    retry_policy: Dict[str, Any] = Field(default_factory=dict)
    cost_limits: Dict[str, float] = Field(default_factory=dict)
