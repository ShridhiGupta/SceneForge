from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
from app.services.cost_quality_optimizer import cost_quality_optimizer
from app.services.cost_aware_decision_engine import cost_aware_decision_engine
from app.services.model_switching_logic import model_switching_logic
from app.services.budget_constraint_handler import budget_constraint_handler
from app.schemas.cost_optimization import (
    CostQualityRequest, 
    OptimizationStrategy, 
    UtilityParameters,
    OptimizationResult,
    ModelTier
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cost-optimization", tags=["cost-optimization"])


@router.post("/optimize-model")
async def optimize_model_selection(
    task_type: str,
    prompt_complexity: float = Query(ge=0, le=1, description="Complexity of prompt/task"),
    quality_requirement: float = Query(ge=0, le=1, description="Required quality level"),
    budget_constraint: Optional[float] = Query(description="Budget constraint for this task"),
    previous_attempts: int = Query(default=0, description="Number of previous attempts"),
    strategy: OptimizationStrategy = Query(default=OptimizationStrategy.BALANCED),
    preferred_tier: Optional[ModelTier] = Query(description="Preferred model tier"),
    exclude_models: List[str] = Query(default=[], description="Models to exclude")
):
    """
    Optimize model selection using utility function
    U = alpha * quality - beta * cost
    """
    try:
        # Create cost-quality request
        request = CostQualityRequest(
            task_type=task_type,
            prompt_complexity=prompt_complexity,
            quality_requirement=quality_requirement,
            budget_constraint=budget_constraint,
            previous_attempts=previous_attempts,
            preferred_tier=preferred_tier,
            exclude_models=exclude_models
        )
        
        # Get optimization decision
        decision = cost_quality_optimizer.optimize_model_selection(
            request, strategy
        )
        
        return {
            "success": True,
            "decision": decision.dict(),
            "request": request.dict()
        }
        
    except Exception as e:
        logger.error(f"Model optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/utility-calculation")
async def calculate_utility_scores(
    task_type: str,
    prompt_complexity: float = Query(ge=0, le=1),
    quality_requirement: float = Query(ge=0, le=1),
    alpha: float = Query(default=0.7, ge=0, le=1, description="Quality weight"),
    beta: float = Query(default=0.3, ge=0, le=1, description="Cost weight"),
    budget_constraint: Optional[float] = Query(None)
):
    """
    Calculate utility scores for all available models
    """
    try:
        # Create request
        request = CostQualityRequest(
            task_type=task_type,
            prompt_complexity=prompt_complexity,
            quality_requirement=quality_requirement,
            budget_constraint=budget_constraint
        )
        
        # Create utility parameters
        utility_params = UtilityParameters(alpha=alpha, beta=beta)
        utility_params.normalize_weights()
        
        # Calculate scores for all models
        model_scores = []
        
        for model_name, model in cost_quality_optimizer.model_profiles.items():
            if model_name not in request.exclude_models:
                utility_score = cost_quality_optimizer.calculate_utility(
                    model, request, utility_params
                )
                
                model_scores.append({
                    "model": model_name,
                    "tier": model.tier.value,
                    "cost_per_call": model.cost_per_call,
                    "expected_quality": model.expected_quality,
                    "utility_score": utility_score,
                    "speed_tier": model.speed_tier,
                    "reliability": model.reliability
                })
        
        # Sort by utility score
        model_scores.sort(key=lambda x: x["utility_score"], reverse=True)
        
        return {
            "success": True,
            "utility_parameters": utility_params.dict(),
            "model_scores": model_scores,
            "best_model": model_scores[0] if model_scores else None,
            "request": request.dict()
        }
        
    except Exception as e:
        logger.error(f"Utility calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/model-switching-decision")
async def get_model_switching_decision(
    current_model: str,
    current_quality: Optional[float] = Query(None, ge=0, le=1),
    failure_type: str = Query(description="Type of failure"),
    retry_count: int = Query(default=0, description="Number of retries"),
    budget_remaining: Optional[float] = Query(None),
    prompt_complexity: float = Query(ge=0, le=1),
    quality_requirement: float = Query(ge=0, le=1)
):
    """
    Get model switching decision based on current context
    """
    try:
        from app.schemas.decision_engine import FailureContext, PipelineStage
        
        # Create failure context
        failure_context = FailureContext(
            task_name="model_switching_analysis",
            stage=PipelineStage.IMAGE,
            error_logs=failure_type,
            retry_count=retry_count,
            model_used=current_model,
            prompt_used="sample_prompt"
        )
        
        # Get switching decision
        should_switch, new_model, reasoning = await model_switching_logic.should_switch_model(
            current_model, current_quality, failure_context, budget_remaining
        )
        
        return {
            "success": True,
            "should_switch": should_switch,
            "current_model": current_model,
            "recommended_model": new_model,
            "reasoning": reasoning,
            "context": {
                "current_quality": current_quality,
                "failure_type": failure_type,
                "retry_count": retry_count,
                "budget_remaining": budget_remaining
            }
        }
        
    except Exception as e:
        logger.error(f"Model switching decision failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/budget-plan")
async def create_budget_plan(
    total_budget: float,
    task_count: int,
    quality_requirements: Dict[str, float] = {},
    historical_data: Optional[Dict[str, Any]] = None
):
    """
    Create comprehensive budget plan
    """
    try:
        plan = budget_constraint_handler.create_budget_plan(
            total_budget, task_count, quality_requirements, historical_data
        )
        
        return {
            "success": True,
            "plan": plan
        }
        
    except Exception as e:
        logger.error(f"Budget plan creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/budget-constraint-check")
async def check_budget_constraint(
    requested_cost: float,
    budget_remaining: float,
    model_tier: str,
    task_importance: str = "medium"
):
    """
    Check if request fits within budget constraints
    """
    try:
        allowed, alternative_model = budget_constraint_handler.check_budget_constraint(
            requested_cost, budget_remaining, model_tier, task_importance
        )
        
        return {
            "success": True,
            "allowed": allowed,
            "requested_cost": requested_cost,
            "budget_remaining": budget_remaining,
            "alternative_model": alternative_model,
            "task_importance": task_importance
        }
        
    except Exception as e:
        logger.error(f"Budget constraint check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cost-aware-decision")
async def get_cost_aware_decision(
    task_name: str,
    stage: str,
    error_logs: str,
    prompt_used: str,
    model_used: str,
    retry_count: int = 0,
    cost_so_far: float = 0.0,
    budget_constraint: Optional[float] = None,
    alpha: float = 0.7,
    beta: float = 0.3
):
    """
    Get cost-aware decision from decision engine
    """
    try:
        from app.schemas.decision_engine import FailureContext, PipelineStage
        
        # Create failure context
        failure_context = FailureContext(
            task_name=task_name,
            stage=PipelineStage(stage),
            error_logs=error_logs,
            prompt_used=prompt_used,
            model_used=model_used,
            retry_count=retry_count,
            cost_so_far=cost_so_far
        )
        
        # Create utility parameters
        utility_params = UtilityParameters(alpha=alpha, beta=beta)
        
        # Get cost-aware decision
        decision = await cost_aware_decision_engine.analyze_failure_with_cost_optimization(
            failure_context, budget_constraint, utility_params
        )
        
        # Get cost optimization suggestions
        suggestions = await cost_aware_decision_engine.suggest_cost_optimization(
            failure_context, cost_so_far, budget_constraint or 0
        )
        
        return {
            "success": True,
            "decision": decision.dict(),
            "suggestions": suggestions,
            "utility_parameters": utility_params.dict()
        }
        
    except Exception as e:
        logger.error(f"Cost-aware decision failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-profiles")
async def get_model_profiles():
    """
    Get all available model profiles
    """
    try:
        profiles = {}
        
        for name, model in cost_quality_optimizer.model_profiles.items():
            profiles[name] = {
                "name": model.name,
                "tier": model.tier.value,
                "cost_per_call": model.cost_per_call,
                "expected_quality": model.expected_quality,
                "speed_tier": model.speed_tier,
                "reliability": model.reliability,
                "context_window": model.context_window,
                "specializations": model.specializations
            }
        
        return {
            "success": True,
            "profiles": profiles,
            "total_models": len(profiles)
        }
        
    except Exception as e:
        logger.error(f"Failed to get model profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/switching-path")
async def get_model_switching_path(
    start_model: str,
    target_quality: float = Query(ge=0, le=1),
    budget_constraint: Optional[float] = None
):
    """
    Get recommended path for model switching to reach target quality
    """
    try:
        path = await model_switching_logic.get_model_switching_path(
            start_model, target_quality, budget_constraint
        )
        
        return {
            "success": True,
            "start_model": start_model,
            "target_quality": target_quality,
            "budget_constraint": budget_constraint,
            "switching_path": path,
            "total_steps": len(path)
        }
        
    except Exception as e:
        logger.error(f"Failed to get switching path: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluate-switching")
async def evaluate_switching_decision(
    from_model: str,
    to_model: str,
    task_type: str = "general",
    prompt_complexity: float = 0.5,
    quality_requirement: float = 0.5
):
    """
    Evaluate a model switching decision
    """
    try:
        context = {
            "task_type": task_type,
            "prompt_complexity": prompt_complexity,
            "quality_requirement": quality_requirement
        }
        
        evaluation = await model_switching_logic.evaluate_switching_decision(
            from_model, to_model, context
        )
        
        return {
            "success": True,
            "evaluation": evaluation
        }
        
    except Exception as e:
        logger.error(f"Switching evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize-spending")
async def optimize_spending(
    current_spending: Dict[str, float],
    remaining_budget: float,
    upcoming_tasks: List[Dict[str, Any]]
):
    """
    Optimize spending for remaining tasks
    """
    try:
        optimization = budget_constraint_handler.optimize_spending(
            current_spending, remaining_budget, upcoming_tasks
        )
        
        return {
            "success": True,
            "optimization": optimization
        }
        
    except Exception as e:
        logger.error(f"Spending optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/track-utilization")
async def track_budget_utilization(
    model_usage: Dict[str, int],
    costs: Dict[str, float]
):
    """
    Track and analyze budget utilization
    """
    try:
        utilization = budget_constraint_handler.track_budget_utilization(
            model_usage, costs
        )
        
        return {
            "success": True,
            "utilization": utilization
        }
        
    except Exception as e:
        logger.error(f"Budget utilization tracking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optimization-strategies")
async def get_optimization_strategies():
    """
    Get available optimization strategies
    """
    try:
        strategies = {}
        
        for strategy in OptimizationStrategy:
            strategies[strategy.value] = {
                "name": strategy.value,
                "description": self._get_strategy_description(strategy),
                "use_case": self._get_strategy_use_case(strategy)
            }
        
        return {
            "success": True,
            "strategies": strategies
        }
        
    except Exception as e:
        logger.error(f"Failed to get optimization strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_strategy_description(strategy: OptimizationStrategy) -> str:
    """Get description for optimization strategy"""
    descriptions = {
        OptimizationStrategy.MINIMIZE_COST: "Prioritize cost reduction over quality",
        OptimizationStrategy.MAXIMIZE_QUALITY: "Prioritize quality over cost",
        OptimizationStrategy.BALANCED: "Balance cost and quality equally",
        OptimizationStrategy.BUDGET_CONSTRAINED: "Optimize within strict budget limits",
        OptimizationStrategy.QUALITY_THRESHOLD: "Meet minimum quality threshold at lowest cost"
    }
    return descriptions.get(strategy, "Unknown strategy")


def _get_strategy_use_case(strategy: OptimizationStrategy) -> str:
    """Get use case for optimization strategy"""
    use_cases = {
        OptimizationStrategy.MINIMIZE_COST: "Large scale processing with budget constraints",
        OptimizationStrategy.MAXIMIZE_QUALITY: "Critical tasks where quality is paramount",
        OptimizationStrategy.BALANCED: "General purpose tasks requiring good balance",
        OptimizationStrategy.BUDGET_CONSTRAINED: "Limited budget scenarios",
        OptimizationStrategy.QUALITY_THRESHOLD: "Tasks with minimum quality requirements"
    }
    return use_cases.get(strategy, "General use")


@router.get("/health")
async def health_check():
    """
    Health check for cost optimization system
    """
    try:
        return {
            "status": "healthy",
            "optimizer_available": True,
            "model_profiles_count": len(cost_quality_optimizer.model_profiles),
            "decision_engine_available": True,
            "budget_handler_available": True
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
