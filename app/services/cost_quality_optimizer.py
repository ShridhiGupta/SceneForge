import math
from typing import Dict, List, Optional, Tuple
from app.schemas.cost_optimization import (
    ModelCostProfile, 
    UtilityParameters, 
    CostQualityRequest, 
    ModelRecommendation,
    CostQualityDecision,
    BudgetAnalysis,
    OptimizationResult,
    OptimizationStrategy,
    ModelTier
)
import logging

logger = logging.getLogger(__name__)


class CostQualityOptimizer:
    """
    Cost-quality optimization engine using utility functions
    U = alpha * quality - beta * cost
    """
    
    def __init__(self):
        self.model_profiles = self._initialize_model_profiles()
        self.default_utility_params = UtilityParameters()
        
    def _initialize_model_profiles(self) -> Dict[str, ModelCostProfile]:
        """Initialize model cost and quality profiles"""
        return {
            # Image Generation Models
            "stable-diffusion-v1-5": ModelCostProfile(
                name="stable-diffusion-v1-5",
                tier=ModelTier.BASIC,
                cost_per_call=0.01,
                expected_quality=0.65,
                speed_tier="fast",
                reliability=0.95,
                specializations=["basic_images", "speed"]
            ),
            
            "stable-diffusion-xl": ModelCostProfile(
                name="stable-diffusion-xl",
                tier=ModelTier.STANDARD,
                cost_per_call=0.02,
                expected_quality=0.78,
                speed_tier="medium",
                reliability=0.92,
                specializations=["quality_images", "detail"]
            ),
            
            "dall-e-3": ModelCostProfile(
                name="dall-e-3",
                tier=ModelTier.PREMIUM,
                cost_per_call=0.04,
                expected_quality=0.85,
                speed_tier="slow",
                reliability=0.98,
                specializations=["high_quality", "creative", "complex_prompts"]
            ),
            
            "midjourney": ModelCostProfile(
                name="midjourney",
                tier=ModelTier.ULTRA,
                cost_per_call=0.05,
                expected_quality=0.92,
                speed_tier="very_slow",
                reliability=0.90,
                specializations=["artistic", "high_quality", "style_transfer"]
            ),
            
            # Text Generation Models
            "gpt-3.5-turbo": ModelCostProfile(
                name="gpt-3.5-turbo",
                tier=ModelTier.BASIC,
                cost_per_call=0.002,
                expected_quality=0.70,
                speed_tier="fast",
                reliability=0.98,
                context_window=4096,
                specializations=["text_generation", "speed"]
            ),
            
            "gpt-4": ModelCostProfile(
                name="gpt-4",
                tier=ModelTier.STANDARD,
                cost_per_call=0.03,
                expected_quality=0.85,
                speed_tier="medium",
                reliability=0.99,
                context_window=8192,
                specializations=["reasoning", "complex_tasks"]
            ),
            
            "gpt-4-turbo": ModelCostProfile(
                name="gpt-4-turbo",
                tier=ModelTier.PREMIUM,
                cost_per_call=0.01,
                expected_quality=0.88,
                speed_tier="fast",
                reliability=0.99,
                context_window=128000,
                specializations=["reasoning", "large_context", "efficiency"]
            ),
            
            "claude-3-opus": ModelCostProfile(
                name="claude-3-opus",
                tier=ModelTier.ULTRA,
                cost_per_call=0.075,
                expected_quality=0.91,
                speed_tier="medium",
                reliability=0.97,
                context_window=200000,
                specializations=["analysis", "long_context", "high_quality"]
            )
        }
    
    def calculate_utility(self, model: ModelCostProfile, 
                         request: CostQualityRequest, 
                         params: UtilityParameters) -> float:
        """
        Calculate utility score: U = alpha * quality - beta * cost
        """
        # Adjust expected quality based on task requirements
        quality_adjustment = self._calculate_quality_adjustment(model, request)
        adjusted_quality = model.expected_quality * quality_adjustment
        
        # Normalize cost (higher cost = lower utility)
        normalized_cost = model.cost_per_call * params.cost_sensitivity
        
        # Calculate utility
        utility = params.alpha * adjusted_quality - params.beta * normalized_cost
        
        # Apply quality threshold penalty
        if adjusted_quality < params.quality_threshold:
            utility -= 0.5  # Significant penalty for below-threshold quality
        
        return utility
    
    def _calculate_quality_adjustment(self, model: ModelCostProfile, 
                                    request: CostQualityRequest) -> float:
        """Calculate quality adjustment based on task requirements"""
        adjustment = 1.0
        
        # Prompt complexity adjustment
        if request.prompt_complexity > 0.8:
            if model.tier == ModelTier.BASIC:
                adjustment *= 0.7  # Basic models struggle with complex prompts
            elif model.tier in [ModelTier.PREMIUM, ModelTier.ULTRA]:
                adjustment *= 1.2  # Premium models excel at complex prompts
        
        # Specialization bonus
        for specialization in model.specializations:
            if specialization in request.context.get("required_features", []):
                adjustment *= 1.1
        
        # Previous attempts penalty (avoid models that have failed)
        if request.previous_attempts > 0:
            if model.reliability < 0.9:
                adjustment *= 0.8  # Penalize unreliable models after failures
        
        return adjustment
    
    def optimize_model_selection(self, 
                               request: CostQualityRequest,
                               strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
                               utility_params: Optional[UtilityParameters] = None) -> CostQualityDecision:
        """
        Optimize model selection based on strategy and utility function
        """
        if utility_params is None:
            utility_params = self.default_utility_params
        
        utility_params.normalize_weights()
        
        # Filter available models
        available_models = [
            model for name, model in self.model_profiles.items()
            if name not in request.exclude_models
        ]
        
        # Calculate utility scores for all models
        model_scores = []
        for model in available_models:
            utility_score = self.calculate_utility(model, request, utility_params)
            
            model_scores.append({
                'model': model,
                'utility_score': utility_score,
                'expected_cost': model.cost_per_call,
                'expected_quality': model.expected_quality
            })
        
        # Sort by utility score (descending)
        model_scores.sort(key=lambda x: x['utility_score'], reverse=True)
        
        # Select best model based on strategy
        selected_model, reasoning = self._select_model_by_strategy(
            model_scores, request, strategy, utility_params
        )
        
        # Calculate alternatives
        alternatives = []
        for score_data in model_scores[1:4]:  # Top 3 alternatives
            alt_reasoning = self._generate_alternative_reasoning(
                selected_model, score_data['model'], request
            )
            
            alternatives.append(ModelRecommendation(
                model=score_data['model'],
                utility_score=score_data['utility_score'],
                expected_cost=score_data['expected_cost'],
                expected_quality=score_data['expected_quality'],
                confidence=0.8,
                reasoning=alt_reasoning
            ))
        
        # Calculate cost savings and quality tradeoff
        cost_savings = None
        quality_tradeoff = None
        
        if model_scores:
            most_expensive = max(model_scores, key=lambda x: x['expected_cost'])
            highest_quality = max(model_scores, key=lambda x: x['expected_quality'])
            
            if selected_model['expected_cost'] < most_expensive['expected_cost']:
                cost_savings = most_expensive['expected_cost'] - selected_model['expected_cost']
            
            if selected_model['expected_quality'] < highest_quality['expected_quality']:
                quality_tradeoff = highest_quality['expected_quality'] - selected_model['expected_quality']
        
        return CostQualityDecision(
            selected_model=selected_model['model'].name,
            strategy=strategy,
            utility_score=selected_model['utility_score'],
            expected_cost=selected_model['expected_cost'],
            expected_quality=selected_model['expected_quality'],
            budget_remaining=request.budget_constraint - selected_model['expected_cost'] if request.budget_constraint else None,
            cost_savings=cost_savings,
            quality_tradeoff=quality_tradeoff,
            reasoning=reasoning,
            alternatives=alternatives
        )
    
    def _select_model_by_strategy(self, 
                                model_scores: List[Dict],
                                request: CostQualityRequest,
                                strategy: OptimizationStrategy,
                                params: UtilityParameters) -> Tuple[Dict, str]:
        """Select best model based on strategy"""
        
        if strategy == OptimizationStrategy.MINIMIZE_COST:
            # Choose cheapest model that meets quality threshold
            viable_models = [
                score for score in model_scores
                if score['expected_quality'] >= params.quality_threshold
            ]
            
            if viable_models:
                selected = min(viable_models, key=lambda x: x['expected_cost'])
                reasoning = f"Selected cheapest model ({selected['model'].name}) that meets quality threshold ({params.quality_threshold})"
            else:
                selected = min(model_scores, key=lambda x: x['expected_cost'])
                reasoning = f"Selected cheapest model ({selected['model'].name}) - below quality threshold but budget constrained"
        
        elif strategy == OptimizationStrategy.MAXIMIZE_QUALITY:
            # Choose highest quality model within budget
            if request.budget_constraint:
                affordable_models = [
                    score for score in model_scores
                    if score['expected_cost'] <= request.budget_constraint
                ]
                
                if affordable_models:
                    selected = max(affordable_models, key=lambda x: x['expected_quality'])
                    reasoning = f"Selected highest quality model ({selected['model'].name}) within budget (${request.budget_constraint})"
                else:
                    selected = max(model_scores, key=lambda x: x['expected_quality'])
                    reasoning = f"Selected highest quality model ({selected['model'].name}) - exceeds budget but no affordable options"
            else:
                selected = max(model_scores, key=lambda x: x['expected_quality'])
                reasoning = f"Selected highest quality model ({selected['model'].name}) - no budget constraints"
        
        elif strategy == OptimizationStrategy.BUDGET_CONSTRAINED:
            # Optimize utility within budget
            if request.budget_constraint:
                affordable_models = [
                    score for score in model_scores
                    if score['expected_cost'] <= request.budget_constraint
                ]
                
                if affordable_models:
                    selected = max(affordable_models, key=lambda x: x['utility_score'])
                    reasoning = f"Selected best utility model ({selected['model'].name}) within budget (${request.budget_constraint})"
                else:
                    # Choose cheapest model if none affordable
                    selected = min(model_scores, key=lambda x: x['expected_cost'])
                    reasoning = f"Selected cheapest model ({selected['model'].name}) - no models within budget"
            else:
                selected = max(model_scores, key=lambda x: x['utility_score'])
                reasoning = f"Selected best utility model ({selected['model'].name}) - no budget constraints"
        
        elif strategy == OptimizationStrategy.QUALITY_THRESHOLD:
            # Choose cheapest model above quality threshold
            viable_models = [
                score for score in model_scores
                if score['expected_quality'] >= request.quality_requirement
            ]
            
            if viable_models:
                selected = min(viable_models, key=lambda x: x['expected_cost'])
                reasoning = f"Selected cheapest model ({selected['model'].name}) meeting quality requirement ({request.quality_requirement})"
            else:
                # Choose highest quality available if none meet threshold
                selected = max(model_scores, key=lambda x: x['expected_quality'])
                reasoning = f"Selected highest quality model ({selected['model'].name}) - none meet quality requirement ({request.quality_requirement})"
        
        else:  # BALANCED (default)
            # Choose model with highest utility score
            selected = max(model_scores, key=lambda x: x['utility_score'])
            reasoning = f"Selected model with highest utility score ({selected['model'].name}) - balanced cost-quality optimization"
        
        return selected, reasoning
    
    def _generate_alternative_reasoning(self, 
                                      selected: Dict, 
                                      alternative: Dict, 
                                      request: CostQualityRequest) -> str:
        """Generate reasoning for alternative models"""
        cost_diff = alternative['expected_cost'] - selected['expected_cost']
        quality_diff = alternative['expected_quality'] - selected['expected_quality']
        
        if cost_diff > 0 and quality_diff > 0:
            return f"Higher quality (+{quality_diff:.2f}) but more expensive (+${cost_diff:.3f})"
        elif cost_diff < 0 and quality_diff < 0:
            return f"Cheaper (-${abs(cost_diff):.3f}) but lower quality (-{abs(quality_diff):.2f})"
        elif cost_diff > 0:
            return f"Higher quality (+{quality_diff:.2f}) but more expensive (+${cost_diff:.3f})"
        elif cost_diff < 0:
            return f"Cheaper (-${abs(cost_diff):.3f}) but lower quality (-{abs(quality_diff):.2f})"
        else:
            return "Similar cost and quality to selected model"
    
    def analyze_budget(self, 
                      total_budget: float, 
                      spent_budget: float,
                      task_costs: List[float]) -> BudgetAnalysis:
        """Analyze budget and provide recommendations"""
        remaining_budget = total_budget - spent_budget
        budget_utilization = spent_budget / total_budget
        
        # Calculate cost optimization opportunities
        optimization_opportunities = []
        
        if budget_utilization > 0.9:
            optimization_opportunities.append("Budget nearly exhausted - consider upgrading to premium models for remaining tasks")
        elif budget_utilization > 0.7:
            optimization_opportunities.append("Moderate budget usage - can afford some premium models")
        elif budget_utilization < 0.3:
            optimization_opportunities.append("Low budget usage - consider using higher quality models")
        
        # Calculate recommended allocations
        avg_task_cost = sum(task_costs) / len(task_costs) if task_costs else 0
        remaining_tasks = int(remaining_budget / avg_task_cost) if avg_task_cost > 0 else 0
        
        recommended_allocations = {
            "basic_tasks": int(remaining_tasks * 0.4),
            "standard_tasks": int(remaining_tasks * 0.3),
            "premium_tasks": int(remaining_tasks * 0.2),
            "ultra_tasks": int(remaining_tasks * 0.1)
        }
        
        # Generate budget warnings
        warnings = []
        if budget_utilization > 0.95:
            warnings.append("Critical: Budget almost exhausted")
        elif remaining_budget < avg_task_cost:
            warnings.append("Warning: Insufficient budget for average task")
        
        return BudgetAnalysis(
            total_budget=total_budget,
            spent_budget=spent_budget,
            remaining_budget=remaining_budget,
            budget_utilization=budget_utilization,
            recommended_allocations=recommended_allocations,
            cost_optimization_opportunities=optimization_opportunities,
            budget_warnings=warnings
        )
    
    def should_upgrade_model(self, 
                           current_model: str, 
                           current_quality: float,
                           target_quality: float,
                           budget_remaining: float) -> bool:
        """
        Decide if should upgrade to a better model
        """
        current_profile = self.model_profiles.get(current_model)
        if not current_profile:
            return False
        
        # If current quality meets target, no upgrade needed
        if current_quality >= target_quality:
            return False
        
        # Find better models within budget
        better_models = [
            model for name, model in self.model_profiles.items()
            if (model.expected_quality > current_profile.expected_quality and
                model.cost_per_call <= budget_remaining and
                name != current_model)
        ]
        
        return len(better_models) > 0
    
    def suggest_downgrade(self, 
                         current_model: str,
                         current_quality: float,
                         budget_remaining: float) -> Optional[str]:
        """
        Suggest model downgrade to save costs
        """
        current_profile = self.model_profiles.get(current_model)
        if not current_profile:
            return None
        
        # Find cheaper models with acceptable quality
        cheaper_models = [
            name for name, model in self.model_profiles.items()
            if (model.cost_per_call < current_profile.cost_per_call and
                model.expected_quality >= 0.5 and  # Minimum acceptable quality
                name != current_model)
        ]
        
        if cheaper_models:
            # Select the best quality among cheaper options
            best_cheaper = max(
                cheaper_models,
                key=lambda name: self.model_profiles[name].expected_quality
            )
            return best_cheaper
        
        return None
    
    def get_cost_savings_estimate(self, 
                                  original_model: str,
                                  new_model: str,
                                  tasks_remaining: int) -> float:
        """Estimate cost savings from model switch"""
        original_profile = self.model_profiles.get(original_model)
        new_profile = self.model_profiles.get(new_model)
        
        if not original_profile or not new_profile:
            return 0.0
        
        cost_per_task = original_profile.cost_per_call - new_profile.cost_per_call
        return cost_per_task * tasks_remaining


# Global optimizer instance
cost_quality_optimizer = CostQualityOptimizer()
