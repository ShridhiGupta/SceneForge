from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class EvaluationMethod(str, Enum):
    CLIP_SCORE = "clip_score"
    LLM_EVALUATION = "llm_evaluation"
    COMBINED = "combined"


class QualityThreshold(str, Enum):
    VERY_LOW = "very_low"      # 0.0 - 0.3
    LOW = "low"               # 0.3 - 0.5
    MEDIUM = "medium"         # 0.5 - 0.7
    HIGH = "high"             # 0.7 - 0.85
    VERY_HIGH = "very_high"   # 0.85 - 1.0


class CLIPScoreResult(BaseModel):
    """Result from CLIP-based image-text similarity evaluation"""
    
    clip_score: float = Field(..., ge=0.0, le=1.0, description="CLIP similarity score")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the score")
    processing_time_ms: Optional[float] = None
    model_used: str = "openai/clip-vit-base-patch32"


class LLMEvaluationResult(BaseModel):
    """Result from LLM-based image evaluation"""
    
    matches_prompt: bool = Field(..., description="Whether image matches the prompt")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="LLM quality assessment")
    reasoning: str = Field(..., description="LLM reasoning for the evaluation")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in evaluation")
    processing_time_ms: Optional[float] = None
    model_used: str = "gpt-4-vision-preview"


class CombinedQualityResult(BaseModel):
    """Combined quality evaluation result"""
    
    final_score: float = Field(..., ge=0.0, le=1.0, description="Final combined quality score")
    quality_threshold: QualityThreshold = Field(..., description="Quality category")
    clip_result: CLIPScoreResult
    llm_result: LLMEvaluationResult
    
    # Weight configuration
    clip_weight: float = Field(default=0.6, ge=0.0, le=1.0, description="Weight for CLIP score")
    llm_weight: float = Field(default=0.4, ge=0.0, le=1.0, description="Weight for LLM evaluation")
    
    # Metadata
    evaluation_time_ms: Optional[float] = None
    passes_threshold: bool = Field(..., description="Whether quality passes minimum threshold")
    threshold_used: float = Field(..., ge=0.0, le=1.0, description="Minimum quality threshold")


class QualityEvaluationRequest(BaseModel):
    """Request for quality evaluation"""
    
    image_path: str = Field(..., description="Path to generated image")
    prompt: str = Field(..., description="Original prompt used for generation")
    model_used: str = Field(..., description="AI model used for generation")
    
    # Optional context
    video_id: Optional[int] = None
    scene_id: Optional[int] = None
    task_id: Optional[str] = None
    
    # Evaluation configuration
    methods: List[EvaluationMethod] = Field(default=[EvaluationMethod.COMBINED])
    min_quality_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    clip_weight: float = Field(default=0.6, ge=0.0, le=1.0)
    llm_weight: float = Field(default=0.4, ge=0.0, le=1.0)


class QualityEvaluationResponse(BaseModel):
    """Response from quality evaluation"""
    
    request_id: str = Field(..., description="Unique request identifier")
    success: bool = Field(..., description="Whether evaluation succeeded")
    result: Optional[CombinedQualityResult] = None
    error: Optional[str] = None
    processing_time_ms: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class QualityMetrics(BaseModel):
    """Quality metrics over time"""
    
    period_start: datetime
    period_end: datetime
    total_evaluations: int
    average_score: float = Field(ge=0.0, le=1.0)
    score_distribution: Dict[str, int]  # Count by quality threshold
    method_performance: Dict[str, float]  # Average scores by method
    failure_rate: float = Field(ge=0.0, le=1.0)
    average_processing_time_ms: float


class QualityFailure(BaseModel):
    """Quality failure record for decision engine"""
    
    image_path: str
    prompt: str
    model_used: str
    quality_score: float
    evaluation_result: CombinedQualityResult
    failure_reason: str
    suggested_action: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
