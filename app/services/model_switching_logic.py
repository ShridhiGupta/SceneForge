from typing import Dict, List, Optional, Tuple, Any
import logging
from app.services.cost_quality_optimizer import cost_quality_optimizer
from app.services.cost_aware_decision_engine import cost_aware_decision_engine
from app.schemas.cost_optimization import (
    ModelCostProfile, 
    CostQualityRequest, 
    OptimizationStrategy,
    UtilityParameters,
    ModelTier
)
from app.schemas.decision_engine import FailureContext, RecoveryAction

logger = logging.getLogger(__name__)


class ModelSwitchingLogic:
    """
    Intelligent model switching logic based on cost-quality optimization
    """
    
    def __init__(self):
        self.cost_optimizer = cost_quality_optimizer
        self.decision_engine = cost_aware_decision_engine
        
        # Switching thresholds
        self.quality_degradation_threshold = 0.1  # Switch if quality drops by 10%
        self.cost_increase_threshold = 0.5       # Switch if cost increases by 50%
        self.retry_threshold = 2                  # Switch after 2 retries
        
        # Model hierarchy for upgrades/downgrades
        self.model_hierarchy = {
            ModelTier.BASIC: ["stable-diffusion-v1-5", "gpt-3.5-turbo"],
            ModelTier.STANDARD: ["stable-diffusion-xl", "gpt-4"],
            ModelTier.PREMIUM: ["dall-e-3", "gpt-4-turbo"],
            ModelTier.ULTRA: ["midjourney", "claude-3-opus"]
        }
    
    async def should_switch_model(self, 
                                 current_model: str,
                                 current_quality: Optional[float],
                                 failure_context: FailureContext,
                                 budget_remaining: Optional[float] = None) -> Tuple[bool, Optional[str], str]:
        """
        Determine if should switch model and what to switch to
        Returns: (should_switch, new_model, reasoning)
        """
        
        # Get current model profile
        current_profile = self.cost_optimizer.model_profiles.get(current_model)
        if not current_profile:
            return False, None, f"Current model {current_model} not found in profiles"
        
        # Check retry threshold
        if failure_context.retry_count >= self.retry_threshold:
            return await self._switch_for_retries(current_model, current_quality, failure_context, budget_remaining)
        
        # Check quality issues
        if current_quality and current_quality < 0.5:
            return await self._switch_for_quality(current_model, current_quality, failure_context, budget_remaining)
        
        # Check cost issues
        if budget_remaining and current_profile.cost_per_call > budget_remaining:
            return await self._switch_for_cost(current_model, failure_context, budget_remaining)
        
        # Check failure type specific switching
        return await self._switch_for_failure_type(current_model, failure_context, budget_remaining)
    
    async def _switch_for_retries(self, 
                                current_model: str,
                                current_quality: Optional[float],
                                failure_context: FailureContext,
                                budget_remaining: Optional[float]) -> Tuple[bool, Optional[str], str]:
        """Switch model after multiple retries"""
        
        current_profile = self.cost_optimizer.model_profiles[current_model]
        
        # After multiple retries, upgrade to higher quality model
        upgrade_candidates = []
        
        for tier, models in self.model_hierarchy.items():
            if tier.value > current_profile.tier.value:
                for model_name in models:
                    model = self.cost_optimizer.model_profiles.get(model_name)
                    if model and (not budget_remaining or model.cost_per_call <= budget_remaining):
                        upgrade_candidates.append((model, model.expected_quality))
        
        if upgrade_candidates:
            # Select best quality upgrade
            best_upgrade = max(upgrade_candidates, key=lambda x: x[1])
            reasoning = f"Upgrading after {failure_context.retry_count} retries to improve success rate"
            return True, best_upgrade[0].name, reasoning
        
        return False, None, f"No suitable upgrade found after {failure_context.retry_count} retries"
    
    async def _switch_for_quality(self, 
                                current_model: str,
                                current_quality: float,
                                failure_context: FailureContext,
                                budget_remaining: Optional[float]) -> Tuple[bool, Optional[str], str]:
        """Switch model for quality improvement"""
        
        current_profile = self.cost_optimizer.model_profiles[current_model]
        
        # Find higher quality models
        quality_upgrades = []
        
        for model_name, model in self.cost_optimizer.model_profiles.items():
            if (model.expected_quality > current_profile.expected_quality and
                model_name != current_model and
                (not budget_remaining or model.cost_per_call <= budget_remaining)):
                quality_upgrades.append((model, model.expected_quality))
        
        if quality_upgrades:
            # Select best quality upgrade within budget
            best_upgrade = max(quality_upgrades, key=lambda x: x[1])
            improvement = best_upgrade[1] - current_quality
            reasoning = f"Upgrading for quality improvement: {improvement:.2f} points better"
            return True, best_upgrade[0].name, reasoning
        
        return False, None, f"No better quality model available within budget"
    
    async def _switch_for_cost(self, 
                             current_model: str,
                             failure_context: FailureContext,
                             budget_remaining: float) -> Tuple[bool, Optional[str], str]:
        """Switch model for cost optimization"""
        
        current_profile = self.cost_optimizer.model_profiles[current_model]
        
        # Find cheaper models with acceptable quality
        cost_downgrades = []
        
        for model_name, model in self.cost_optimizer.model_profiles.items():
            if (model.cost_per_call < current_profile.cost_per_call and
                model.expected_quality >= 0.5 and  # Minimum acceptable quality
                model_name != current_model and
                model.cost_per_call <= budget_remaining):
                cost_downgrades.append((model, model.cost_per_call))
        
        if cost_downgrades:
            # Select cheapest acceptable model
            best_downgrade = min(cost_downgrades, key=lambda x: x[1])
            savings = current_profile.cost_per_call - best_downgrade[1]
            reasoning = f"Downgrading for cost savings: ${savings:.3f} per call"
            return True, best_downgrade[0].name, reasoning
        
        return False, None, f"No cheaper model available within budget"
    
    async def _switch_for_failure_type(self, 
                                     current_model: str,
                                     failure_context: FailureContext,
                                     budget_remaining: Optional[float]) -> Tuple[bool, Optional[str], str]:
        """Switch model based on failure type"""
        
        error_logs = failure_context.error_logs.lower()
        
        # Timeout failures - switch to faster models
        if "timeout" in error_logs:
            return await self._switch_for_speed(current_model, budget_remaining)
        
        # Quality failures - switch to higher quality models
        if "quality" in error_logs or "low quality" in error_logs:
            return await self._switch_for_premium_quality(current_model, budget_remaining)
        
        # API errors - switch to more reliable models
        if "api error" in error_logs or "connection" in error_logs:
            return await self._switch_for_reliability(current_model, budget_remaining)
        
        # Resource errors - switch to lighter models
        if "memory" in error_logs or "resource" in error_logs:
            return await self._switch_for_efficiency(current_model, budget_remaining)
        
        return False, None, "No specific switching logic for this failure type"
    
    async def _switch_for_speed(self, 
                              current_model: str,
                              budget_remaining: Optional[float]) -> Tuple[bool, Optional[str], str]:
        """Switch to faster models for timeout issues"""
        
        current_profile = self.cost_optimizer.model_profiles[current_model]
        
        # Find faster models
        speed_upgrades = []
        
        for model_name, model in self.cost_optimizer.model_profiles.items():
            if (model.speed_tier == "fast" and current_profile.speed_tier != "fast" and
                model_name != current_model and
                (not budget_remaining or model.cost_per_call <= budget_remaining)):
                speed_upgrades.append((model, model.expected_quality))
        
        if speed_upgrades:
            # Select best quality among fast models
            best_fast = max(speed_upgrades, key=lambda x: x[1])
            reasoning = f"Switching to faster model ({best_fast[0].speed_tier}) to resolve timeout issues"
            return True, best_fast[0].name, reasoning
        
        return False, None, "No faster model available"
    
    async def _switch_for_premium_quality(self, 
                                        current_model: str,
                                        budget_remaining: Optional[float]) -> Tuple[bool, Optional[str], str]:
        """Switch to premium quality models"""
        
        # Find premium/ultra tier models
        premium_models = []
        
        for model_name, model in self.cost_optimizer.model_profiles.items():
            if (model.tier in [ModelTier.PREMIUM, ModelTier.ULTRA] and
                model_name != current_model and
                (not budget_remaining or model.cost_per_call <= budget_remaining)):
                premium_models.append((model, model.expected_quality))
        
        if premium_models:
            # Select highest quality premium model
            best_premium = max(premium_models, key=lambda x: x[1])
            reasoning = f"Switching to premium quality model for better results"
            return True, best_premium[0].name, reasoning
        
        return False, None, "No premium quality model available within budget"
    
    async def _switch_for_reliability(self, 
                                   current_model: str,
                                   budget_remaining: Optional[float]) -> Tuple[bool, Optional[str], str]:
        """Switch to more reliable models"""
        
        current_profile = self.cost_optimizer.model_profiles[current_model]
        
        # Find more reliable models
        reliable_upgrades = []
        
        for model_name, model in self.cost_optimizer.model_profiles.items():
            if (model.reliability > current_profile.reliability and
                model_name != current_model and
                (not budget_remaining or model.cost_per_call <= budget_remaining)):
                reliable_upgrades.append((model, model.reliability))
        
        if reliable_upgrades:
            # Select most reliable model
            most_reliable = max(reliable_upgrades, key=lambda x: x[1])
            reasoning = f"Switching to more reliable model ({most_reliable[1]:.1%} reliability)"
            return True, most_reliable[0].name, reasoning
        
        return False, None, "No more reliable model available"
    
    async def _switch_for_efficiency(self, 
                                  current_model: str,
                                  budget_remaining: Optional[float]) -> Tuple[bool, Optional[str], str]:
        """Switch to more efficient models for resource issues"""
        
        # Find lighter models (basic tier)
        efficient_models = []
        
        for model_name, model in self.cost_optimizer.model_profiles.items():
            if (model.tier == ModelTier.BASIC and
                model_name != current_model and
                (not budget_remaining or model.cost_per_call <= budget_remaining)):
                efficient_models.append((model, model.cost_per_call))
        
        if efficient_models:
            # Select cheapest efficient model
            most_efficient = min(efficient_models, key=lambda x: x[1])
            reasoning = f"Switching to efficient model for resource optimization"
            return True, most_efficient[0].name, reasoning
        
        return False, None, "No efficient model available"
    
    async def get_model_switching_path(self, 
                                     start_model: str,
                                     target_quality: float,
                                     budget_constraint: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Get recommended path for model switching to reach target quality
        """
        
        path = []
        current_model = start_model
        current_quality = self.cost_optimizer.model_profiles.get(start_model, {}).expected_quality
        
        while current_quality < target_quality:
            # Find next upgrade
            current_profile = self.cost_optimizer.model_profiles.get(current_model)
            if not current_profile:
                break
            
            # Find next tier model
            next_model = None
            next_quality = current_quality
            
            for model_name, model in self.cost_optimizer.model_profiles.items():
                if (model.expected_quality > current_quality and
                    model.expected_quality <= target_quality and
                    (not budget_constraint or model.cost_per_call <= budget_constraint)):
                    if model.expected_quality > next_quality:
                        next_model = model_name
                        next_quality = model.expected_quality
            
            if not next_model:
                break
            
            # Add to path
            path.append({
                "from_model": current_model,
                "to_model": next_model,
                "quality_improvement": next_quality - current_quality,
                "cost_increase": self.cost_optimizer.model_profiles[next_model].cost_per_call - current_profile.cost_per_call
            })
            
            current_model = next_model
            current_quality = next_quality
        
        return path
    
    async def evaluate_switching_decision(self, 
                                        from_model: str,
                                        to_model: str,
                                        context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a model switching decision
        """
        
        from_profile = self.cost_optimizer.model_profiles.get(from_model)
        to_profile = self.cost_optimizer.model_profiles.get(to_model)
        
        if not from_profile or not to_profile:
            return {"error": "Model not found in profiles"}
        
        # Calculate differences
        quality_diff = to_profile.expected_quality - from_profile.expected_quality
        cost_diff = to_profile.cost_per_call - from_profile.cost_per_call
        
        # Calculate utility scores
        utility_params = UtilityParameters()
        
        from_utility = self.cost_optimizer.calculate_utility(
            from_profile, 
            CostQualityRequest(
                task_type=context.get("task_type", "general"),
                prompt_complexity=context.get("prompt_complexity", 0.5),
                quality_requirement=context.get("quality_requirement", 0.5)
            ),
            utility_params
        )
        
        to_utility = self.cost_optimizer.calculate_utility(
            to_profile,
            CostQualityRequest(
                task_type=context.get("task_type", "general"),
                prompt_complexity=context.get("prompt_complexity", 0.5),
                quality_requirement=context.get("quality_requirement", 0.5)
            ),
            utility_params
        )
        
        utility_diff = to_utility - from_utility
        
        # Make recommendation
        recommendation = "switch" if utility_diff > 0 else "keep"
        
        reasoning = []
        if quality_diff > 0:
            reasoning.append(f"Quality improvement: +{quality_diff:.2f}")
        if cost_diff < 0:
            reasoning.append(f"Cost savings: ${abs(cost_diff):.3f}")
        elif cost_diff > 0:
            reasoning.append(f"Cost increase: ${cost_diff:.3f}")
        
        if utility_diff > 0:
            reasoning.append(f"Utility improvement: +{utility_diff:.2f}")
        else:
            reasoning.append(f"Utility decrease: {utility_diff:.2f}")
        
        return {
            "recommendation": recommendation,
            "quality_difference": quality_diff,
            "cost_difference": cost_diff,
            "utility_difference": utility_diff,
            "from_utility": from_utility,
            "to_utility": to_utility,
            "reasoning": " | ".join(reasoning)
        }
    
    def get_model_switching_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about model switching patterns
        """
        
        # This would typically be populated from actual usage data
        # For now, return template structure
        
        return {
            "total_switches": 0,
            "switches_by_reason": {
                "quality_improvement": 0,
                "cost_optimization": 0,
                "retry_exhaustion": 0,
                "timeout_resolution": 0,
                "reliability_improvement": 0
            },
            "most_common_switches": [],
            "average_quality_improvement": 0.0,
            "average_cost_change": 0.0,
            "switch_success_rate": 0.0
        }


# Global model switching logic instance
model_switching_logic = ModelSwitchingLogic()
