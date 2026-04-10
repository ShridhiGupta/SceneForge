from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from enum import Enum


class ModelTier(str, Enum):
    """Model quality tiers"""
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    ULTRA = "ultra"


class OptimizationStrategy(str, Enum):
    """Cost optimization strategies"""
    MINIMIZE_COST = "minimize_cost"
    MAXIMIZE_QUALITY = "maximize_quality"
    BALANCED = "balanced"
    BUDGET_CONSTRAINED = "budget_constrained"
    QUALITY_THRESHOLD = "quality_threshold"


class ModelCostProfile(BaseModel):
    """Cost and quality profile for AI models"""
    name: str
    tier: ModelTier
    cost_per_call: float = Field(ge=0, description="Cost per API call in USD")
    expected_quality: float = Field(ge=0, le=1, description="Expected quality score (0-1)")
    speed_tier: str = Field(description="Relative speed: slow/medium/fast")
    reliability: float = Field(ge=0, le=1, description="Model reliability/success rate")
    context_window: Optional[int] = Field(description="Context window size")
    specializations: List[str] = Field(default_factory=list, description="Model specializations")
    
    class Config:
        use_enum_values = True


class UtilityParameters(BaseModel):
    """Parameters for utility function calculation"""
    alpha: float = Field(default=0.7, ge=0, le=1, description="Quality weight")
    beta: float = Field(default=0.3, ge=0, le=1, description="Cost weight")
    cost_sensitivity: float = Field(default=1.0, ge=0, description="Cost sensitivity factor")
    quality_threshold: float = Field(default=0.5, ge=0, le=1, description="Minimum acceptable quality")
    budget_limit: Optional[float] = Field(description="Budget constraint in USD")
    
    def normalize_weights(self):
        """Ensure alpha + beta = 1"""
        total = self.alpha + self.beta
        if total != 1:
            self.alpha = self.alpha / total
            self.beta = self.beta / total


class CostQualityRequest(BaseModel):
    """Request for cost-quality optimization"""
    task_type: str = Field(description="Type of task (image_generation, text_generation, etc.)")
    prompt_complexity: float = Field(ge=0, le=1, description="Complexity of prompt/task")
    quality_requirement: float = Field(ge=0, le=1, description="Required quality level")
    budget_constraint: Optional[float] = Field(description="Budget constraint for this task")
    previous_attempts: int = Field(default=0, description="Number of previous attempts")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    preferred_tier: Optional[ModelTier] = Field(description="Preferred model tier")
    exclude_models: List[str] = Field(default_factory=list, description="Models to exclude")


class ModelRecommendation(BaseModel):
    """Model recommendation with utility score"""
    model: ModelCostProfile
    utility_score: float
    expected_cost: float
    expected_quality: float
    confidence: float = Field(ge=0, le=1, description="Confidence in recommendation")
    reasoning: str
    alternative_options: List[ModelCostProfile] = Field(default_factory=list)


class CostQualityDecision(BaseModel):
    """Cost-quality optimization decision"""
    selected_model: str
    strategy: OptimizationStrategy
    utility_score: float
    expected_cost: float
    expected_quality: float
    budget_remaining: Optional[float] = None
    cost_savings: Optional[float] = None
    quality_tradeoff: Optional[float] = None
    reasoning: str
    alternatives: List[ModelRecommendation] = Field(default_factory=list)


class BudgetAnalysis(BaseModel):
    """Budget analysis and recommendations"""
    total_budget: float
    spent_budget: float
    remaining_budget: float
    budget_utilization: float
    recommended_allocations: Dict[str, float]
    cost_optimization_opportunities: List[str]
    budget_warnings: List[str]


class OptimizationResult(BaseModel):
    """Complete optimization result"""
    decision: CostQualityDecision
    budget_analysis: Optional[BudgetAnalysis]
    optimization_metrics: Dict[str, Any]
    recommendations: List[str]
    
    class Config:
        use_enum_values = True
