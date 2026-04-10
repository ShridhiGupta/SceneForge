from typing import Dict, Any, Optional, List
import logging
from app.services.decision_engine import DecisionEngine
from app.services.cost_quality_optimizer import cost_quality_optimizer, CostQualityOptimizer
from app.schemas.cost_optimization import (
    CostQualityRequest, 
    OptimizationStrategy, 
    UtilityParameters,
    ModelTier
)
from app.schemas.decision_engine import FailureContext, LLMDecision, RecoveryAction
import asyncio

logger = logging.getLogger(__name__)


class CostAwareDecisionEngine(DecisionEngine):
    """
    Decision engine with cost-quality optimization
    Integrates utility function-based model selection with decision making
    """
    
    def __init__(self):
        super().__init__()
        self.cost_optimizer = cost_quality_optimizer
        self.cost_aware_strategies = {
            "low_quality": OptimizationStrategy.QUALITY_THRESHOLD,
            "timeout": OptimizationStrategy.MINIMIZE_COST,
            "api_error": OptimizationStrategy.BALANCED,
            "resource_exhausted": OptimizationStrategy.BUDGET_CONSTRAINED,
            "budget_exceeded": OptimizationStrategy.MINIMIZE_COST
        }
    
    async def analyze_failure_with_cost_optimization(self, 
                                                   failure_context: FailureContext,
                                                   budget_constraint: Optional[float] = None,
                                                   utility_params: Optional[UtilityParameters] = None) -> LLMDecision:
        """
        Analyze failure with cost-quality optimization
        """
        # Get base decision
        base_decision = await self.analyze_failure(failure_context)
        
        # Optimize model selection if decision involves model change
        if base_decision.action in [RecoveryAction.SWITCH_MODEL, RecoveryAction.MODIFY_PROMPT]:
            cost_optimized_decision = await self._optimize_decision_cost(
                base_decision, failure_context, budget_constraint, utility_params
            )
            return cost_optimized_decision
        
        return base_decision
    
    async def _optimize_decision_cost(self, 
                                    base_decision: LLMDecision,
                                    failure_context: FailureContext,
                                    budget_constraint: Optional[float],
                                    utility_params: Optional[UtilityParameters]) -> LLMDecision:
        """Optimize decision with cost-quality considerations"""
        
        # Create cost-quality request
        request = self._create_cost_quality_request(failure_context, budget_constraint)
        
        # Determine optimization strategy
        strategy = self._determine_optimization_strategy(failure_context, budget_constraint)
        
        # Get cost-optimized decision
        optimization_decision = self.cost_optimizer.optimize_model_selection(
            request, strategy, utility_params
        )
        
        # Update base decision with cost-optimized model
        if base_decision.action == RecoveryAction.SWITCH_MODEL:
            base_decision.new_model = optimization_decision.selected_model
            base_decision.reasoning += f" [Cost-optimized: {optimization_decision.reasoning}]"
        
        # Add cost information to reasoning
        cost_info = f"Expected cost: ${optimization_decision.expected_cost:.3f}"
        if optimization_decision.cost_savings:
            cost_info += f", Savings: ${optimization_decision.cost_savings:.3f}"
        
        base_decision.reasoning += f" [{cost_info}]"
        
        logger.info(f"Cost-optimized decision: {base_decision.action} with model {optimization_decision.selected_model}")
        
        return base_decision
    
    def _create_cost_quality_request(self, 
                                   failure_context: FailureContext,
                                   budget_constraint: Optional[float]) -> CostQualityRequest:
        """Create cost-quality optimization request from failure context"""
        
        # Determine task type from stage
        task_type = self._map_stage_to_task_type(failure_context.stage.value)
        
        # Calculate prompt complexity
        prompt_complexity = self._calculate_prompt_complexity(failure_context.prompt_used)
        
        # Determine quality requirement based on failure type
        quality_requirement = self._determine_quality_requirement(failure_context)
        
        # Extract context
        context = {
            "failure_type": failure_context.error_logs,
            "retry_count": failure_context.retry_count,
            "previous_model": failure_context.model_used,
            "cost_sensitivity": self._calculate_cost_sensitivity(failure_context)
        }
        
        return CostQualityRequest(
            task_type=task_type,
            prompt_complexity=prompt_complexity,
            quality_requirement=quality_requirement,
            budget_constraint=budget_constraint,
            previous_attempts=failure_context.retry_count,
            context=context,
            exclude_models=self._get_models_to_exclude(failure_context)
        )
    
    def _map_stage_to_task_type(self, stage: str) -> str:
        """Map pipeline stage to task type"""
        stage_mapping = {
            "image": "image_generation",
            "text": "text_generation",
            "scene": "scene_processing",
            "clip": "clip_generation",
            "render": "video_rendering"
        }
        return stage_mapping.get(stage, "general")
    
    def _calculate_prompt_complexity(self, prompt: str) -> float:
        """Calculate prompt complexity (0-1)"""
        if not prompt:
            return 0.0
        
        complexity = 0.0
        
        # Length-based complexity
        if len(prompt) > 500:
            complexity += 0.3
        elif len(prompt) > 200:
            complexity += 0.2
        elif len(prompt) > 100:
            complexity += 0.1
        
        # Content-based complexity
        complex_keywords = [
            "detailed", "intricate", "complex", "multiple", "various",
            "high quality", "photorealistic", "4k", "8k", "ultra",
            "professional", "cinematic", "artistic", "creative"
        ]
        
        keyword_count = sum(1 for keyword in complex_keywords if keyword.lower() in prompt.lower())
        complexity += min(0.4, keyword_count * 0.1)
        
        # Structure complexity
        if "," in prompt and "." in prompt:
            complexity += 0.2  # Multiple sentences
        if any(char in prompt for char in [":", ";", "-"]):
            complexity += 0.1  # Structured content
        
        return min(1.0, complexity)
    
    def _determine_quality_requirement(self, failure_context: FailureContext) -> float:
        """Determine quality requirement based on failure context"""
        base_requirement = 0.5
        
        # Increase requirement based on failure type
        if "quality" in failure_context.error_logs.lower():
            base_requirement = 0.8  # High quality needed for quality failures
        
        # Increase based on retry count (more retries = higher quality needed)
        if failure_context.retry_count >= 2:
            base_requirement += 0.1
        
        # Increase based on cost sensitivity (if cost is not a concern)
        cost_sensitivity = self._calculate_cost_sensitivity(failure_context)
        if cost_sensitivity < 0.5:
            base_requirement += 0.1
        
        return min(1.0, base_requirement)
    
    def _calculate_cost_sensitivity(self, failure_context: FailureContext) -> float:
        """Calculate cost sensitivity (0-1, lower = less sensitive)"""
        sensitivity = 0.5  # Default
        
        # Reduce sensitivity if budget is high
        if failure_context.cost_so_far > 10.0:  # High spending so far
            sensitivity = 0.3  # Less cost sensitive
        
        # Increase sensitivity if many retries (cost accumulating)
        if failure_context.retry_count >= 3:
            sensitivity = 0.7  # More cost sensitive
        
        # Adjust based on failure type
        if "timeout" in failure_context.error_logs.lower():
            sensitivity = 0.8  # Very cost sensitive for timeouts
        
        return sensitivity
    
    def _get_models_to_exclude(self, failure_context: FailureContext) -> List[str]:
        """Get models to exclude based on failure context"""
        exclude_models = []
        
        # Exclude current model if it failed
        if failure_context.model_used:
            exclude_models.append(failure_context.model_used)
        
        # Exclude models that have failed recently (would need RAG memory for this)
        # For now, just exclude the current model
        
        return exclude_models
    
    def _determine_optimization_strategy(self, 
                                       failure_context: FailureContext,
                                       budget_constraint: Optional[float]) -> OptimizationStrategy:
        """Determine optimization strategy based on context"""
        
        # Budget constrained strategy
        if budget_constraint and budget_constraint < 0.1:
            return OptimizationStrategy.MINIMIZE_COST
        
        # Quality threshold strategy for quality failures
        if "quality" in failure_context.error_logs.lower():
            return OptimizationStrategy.QUALITY_THRESHOLD
        
        # Budget constrained for high spending
        if failure_context.cost_so_far > 5.0:
            return OptimizationStrategy.BUDGET_CONSTRAINED
        
        # Maximize quality for critical failures
        if failure_context.retry_count >= 2:
            return OptimizationStrategy.MAXIMIZE_QUALITY
        
        # Default to balanced
        return OptimizationStrategy.BALANCED
    
    async def should_switch_model_for_cost(self, 
                                         current_model: str,
                                         current_quality: float,
                                         target_quality: float,
                                         budget_remaining: float) -> bool:
        """
        Decide if should switch models for cost optimization
        """
        return self.cost_optimizer.should_upgrade_model(
            current_model, current_quality, target_quality, budget_remaining
        )
    
    async def suggest_cost_optimization(self, 
                                      failure_context: FailureContext,
                                      current_cost: float,
                                      budget_remaining: float) -> Dict[str, Any]:
        """
        Suggest cost optimization strategies
        """
        suggestions = []
        
        # Analyze current spending
        if current_cost > 0.05:  # High cost task
            cheaper_alternatives = self.cost_optimizer.suggest_downgrade(
                failure_context.model_used, 0.7, budget_remaining
            )
            
            if cheaper_alternatives:
                savings = self.cost_optimizer.get_cost_savings_estimate(
                    failure_context.model_used, cheaper_alternatives, 1
                )
                suggestions.append({
                    "type": "downgrade_model",
                    "current_model": failure_context.model_used,
                    "suggested_model": cheaper_alternatives,
                    "estimated_savings": savings,
                    "reasoning": f"Switch to {cheaper_alternatives} for ${savings:.3f} savings"
                })
        
        # Budget optimization suggestions
        if budget_remaining < 0.1:
            suggestions.append({
                "type": "budget_constraint",
                "message": "Low budget remaining - consider cost-effective models",
                "recommended_strategy": "minimize_cost"
            })
        
        # Quality optimization suggestions
        if failure_context.retry_count >= 2:
            suggestions.append({
                "type": "quality_investment",
                "message": "Multiple retries - consider investing in higher quality model",
                "recommended_strategy": "maximize_quality"
            })
        
        return {
            "suggestions": suggestions,
            "current_cost": current_cost,
            "budget_remaining": budget_remaining,
            "optimization_potential": len(suggestions) > 0
        }
    
    def get_utility_parameters_for_context(self, 
                                          failure_context: FailureContext) -> UtilityParameters:
        """Get utility parameters tailored to specific context"""
        
        # Default parameters
        alpha = 0.7  # Quality weight
        beta = 0.3   # Cost weight
        
        # Adjust weights based on context
        if failure_context.retry_count >= 3:
            # More retries = prioritize quality over cost
            alpha = 0.8
            beta = 0.2
        elif failure_context.cost_so_far > 5.0:
            # High cost = prioritize cost over quality
            alpha = 0.5
            beta = 0.5
        elif "timeout" in failure_context.error_logs.lower():
            # Timeout = prioritize cost (faster models)
            alpha = 0.4
            beta = 0.6
        
        # Set quality threshold
        quality_threshold = 0.5
        if "quality" in failure_context.error_logs.lower():
            quality_threshold = 0.7
        
        # Set cost sensitivity
        cost_sensitivity = 1.0
        if budget_remaining := failure_context.additional_context.get("budget_remaining"):
            if budget_remaining < 0.1:
                cost_sensitivity = 2.0  # More sensitive to cost
        
        return UtilityParameters(
            alpha=alpha,
            beta=beta,
            cost_sensitivity=cost_sensitivity,
            quality_threshold=quality_threshold,
            budget_limit=failure_context.additional_context.get("budget_remaining")
        )


# Global cost-aware decision engine instance
cost_aware_decision_engine = CostAwareDecisionEngine()
