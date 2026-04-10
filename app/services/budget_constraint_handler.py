from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import logging
from app.schemas.cost_optimization import (
    BudgetAnalysis, 
    ModelCostProfile, 
    CostQualityRequest,
    OptimizationStrategy
)
from app.services.cost_quality_optimizer import cost_quality_optimizer

logger = logging.getLogger(__name__)


@dataclass
class BudgetAllocation:
    """Budget allocation for different model tiers"""
    tier: str
    allocation_percentage: float
    allocated_amount: float
    spent_amount: float
    remaining_amount: float


@dataclass
class BudgetAlert:
    """Budget alert for monitoring"""
    alert_type: str
    severity: str
    message: str
    budget_utilization: float
    recommended_action: str


class BudgetConstraintHandler:
    """
    Handles budget constraints and optimization for cost-aware AI system
    """
    
    def __init__(self):
        self.cost_optimizer = cost_quality_optimizer
        self.budget_history: List[Dict[str, Any]] = []
        
        # Default budget allocations by tier
        self.default_allocations = {
            "basic": 0.4,      # 40% for basic models
            "standard": 0.3,    # 30% for standard models
            "premium": 0.2,    # 20% for premium models
            "ultra": 0.1       # 10% for ultra models
        }
        
        # Budget alert thresholds
        self.alert_thresholds = {
            "warning": 0.7,    # 70% utilization
            "critical": 0.9,   # 90% utilization
            "exhausted": 0.95  # 95% utilization
        }
    
    def create_budget_plan(self, 
                          total_budget: float,
                          task_count: int,
                          quality_requirements: Dict[str, float],
                          historical_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a comprehensive budget plan
        """
        
        # Adjust allocations based on quality requirements
        allocations = self._calculate_allocations(total_budget, quality_requirements)
        
        # Estimate costs per tier
        estimated_costs = self._estimate_costs_by_tier(task_count, allocations)
        
        # Generate budget recommendations
        recommendations = self._generate_budget_recommendations(
            allocations, estimated_costs, total_budget
        )
        
        # Create budget alerts
        alerts = self._generate_budget_alerts(allocations, total_budget)
        
        return {
            "total_budget": total_budget,
            "task_count": task_count,
            "allocations": allocations,
            "estimated_costs": estimated_costs,
            "recommendations": recommendations,
            "alerts": alerts,
            "created_at": datetime.utcnow().isoformat()
        }
    
    def _calculate_allocations(self, 
                             total_budget: float,
                             quality_requirements: Dict[str, float]) -> List[BudgetAllocation]:
        """Calculate budget allocations based on quality requirements"""
        
        allocations = []
        
        # Adjust default allocations based on quality requirements
        adjusted_allocations = self.default_allocations.copy()
        
        # If high quality requirements are present, shift budget to premium/ultra
        avg_quality = sum(quality_requirements.values()) / len(quality_requirements) if quality_requirements else 0.5
        
        if avg_quality > 0.8:
            # Shift budget towards higher tiers
            adjusted_allocations["basic"] = 0.2
            adjusted_allocations["standard"] = 0.3
            adjusted_allocations["premium"] = 0.3
            adjusted_allocations["ultra"] = 0.2
        elif avg_quality > 0.6:
            # Moderate quality requirements
            adjusted_allocations["basic"] = 0.3
            adjusted_allocations["standard"] = 0.4
            adjusted_allocations["premium"] = 0.2
            adjusted_allocations["ultra"] = 0.1
        elif avg_quality < 0.4:
            # Low quality requirements - focus on basic models
            adjusted_allocations["basic"] = 0.6
            adjusted_allocations["standard"] = 0.3
            adjusted_allocations["premium"] = 0.1
            adjusted_allocations["ultra"] = 0.0
        
        # Create allocation objects
        for tier, percentage in adjusted_allocations.items():
            allocated_amount = total_budget * percentage
            allocations.append(BudgetAllocation(
                tier=tier,
                allocation_percentage=percentage,
                allocated_amount=allocated_amount,
                spent_amount=0.0,
                remaining_amount=allocated_amount
            ))
        
        return allocations
    
    def _estimate_costs_by_tier(self, 
                               task_count: int,
                               allocations: List[BudgetAllocation]) -> Dict[str, Dict[str, Any]]:
        """Estimate costs by tier based on allocations"""
        
        tier_costs = {}
        
        for allocation in allocations:
            # Get average cost per model in tier
            tier_models = [
                model for model in self.cost_optimizer.model_profiles.values()
                if model.tier.value == allocation.tier
            ]
            
            if tier_models:
                avg_cost_per_call = sum(model.cost_per_call for model in tier_models) / len(tier_models)
                
                # Estimate how many tasks can be handled
                tasks_possible = allocation.allocated_amount / avg_cost_per_call
                
                # Calculate cost per task
                cost_per_task = avg_cost_per_call
                
                tier_costs[allocation.tier] = {
                    "average_cost_per_call": avg_cost_per_call,
                    "tasks_possible": tasks_possible,
                    "cost_per_task": cost_per_task,
                    "total_estimated_cost": min(allocation.allocated_amount, tasks_possible * cost_per_task)
                }
        
        return tier_costs
    
    def _generate_budget_recommendations(self, 
                                        allocations: List[BudgetAllocation],
                                        estimated_costs: Dict[str, Dict[str, Any]],
                                        total_budget: float) -> List[str]:
        """Generate budget optimization recommendations"""
        
        recommendations = []
        
        # Check for underutilized allocations
        for allocation in allocations:
            if allocation.tier in estimated_costs:
                tier_info = estimated_costs[allocation.tier]
                utilization = tier_info["total_estimated_cost"] / allocation.allocated_amount
                
                if utilization < 0.5:
                    recommendations.append(
                        f"Consider reducing {allocation.tier} tier allocation from {allocation.allocation_percentage:.1%} "
                        f"to {allocation.allocation_percentage * 0.5:.1%} - underutilized at {utilization:.1%}"
                    )
                elif utilization > 0.9:
                    recommendations.append(
                        f"Consider increasing {allocation.tier} tier allocation from {allocation.allocation_percentage:.1%} "
                        f"to {min(1.0, allocation.allocation_percentage * 1.2):.1%} - highly utilized at {utilization:.1%}"
                    )
        
        # Check total cost efficiency
        total_estimated_cost = sum(tier["total_estimated_cost"] for tier in estimated_costs.values())
        
        if total_estimated_cost < total_budget * 0.8:
            recommendations.append(
                f"Budget is underutilized ({total_estimated_cost/total_budget:.1%}). "
                f"Consider increasing quality requirements or reducing total budget."
            )
        elif total_estimated_cost > total_budget:
            recommendations.append(
                f"Estimated costs (${total_estimated_cost:.2f}) exceed budget (${total_budget:.2f}). "
                f"Consider reducing quality requirements or increasing budget."
            )
        
        # Add tier-specific recommendations
        if "basic" in estimated_costs and "premium" in estimated_costs:
            basic_cost = estimated_costs["basic"]["average_cost_per_call"]
            premium_cost = estimated_costs["premium"]["average_cost_per_call"]
            
            if premium_cost > basic_cost * 5:
                recommendations.append(
                    f"Premium models are {premium_cost/basic_cost:.1f}x more expensive than basic models. "
                    f"Ensure quality requirements justify the cost difference."
                )
        
        return recommendations
    
    def _generate_budget_alerts(self, 
                               allocations: List[BudgetAllocation],
                               total_budget: float) -> List[BudgetAlert]:
        """Generate budget alerts based on current utilization"""
        
        alerts = []
        
        for allocation in allocations:
            utilization = allocation.spent_amount / allocation.allocated_amount if allocation.allocated_amount > 0 else 0
            
            if utilization >= self.alert_thresholds["exhausted"]:
                alerts.append(BudgetAlert(
                    alert_type="budget_exhausted",
                    severity="critical",
                    message=f"{allocation.tier.capitalize()} tier budget nearly exhausted ({utilization:.1%})",
                    budget_utilization=utilization,
                    recommended_action="Immediately reduce usage or reallocate budget"
                ))
            elif utilization >= self.alert_thresholds["critical"]:
                alerts.append(BudgetAlert(
                    alert_type="budget_critical",
                    severity="high",
                    message=f"{allocation.tier.capitalize()} tier budget critically low ({utilization:.1%})",
                    budget_utilization=utilization,
                    recommended_action="Monitor closely and consider budget reallocation"
                ))
            elif utilization >= self.alert_thresholds["warning"]:
                alerts.append(BudgetAlert(
                    alert_type="budget_warning",
                    severity="medium",
                    message=f"{allocation.tier.capitalize()} tier budget usage high ({utilization:.1%})",
                    budget_utilization=utilization,
                    recommended_action="Plan for budget optimization"
                ))
        
        return alerts
    
    def check_budget_constraint(self, 
                              requested_cost: float,
                              budget_remaining: float,
                              model_tier: str,
                              task_importance: str = "medium") -> Tuple[bool, Optional[str]]:
        """
        Check if a request fits within budget constraints
        
        Returns: (allowed, alternative_model)
        """
        
        if requested_cost <= budget_remaining:
            return True, None
        
        # Budget exceeded - find alternatives
        alternatives = self._find_budget_alternatives(
            requested_cost, budget_remaining, model_tier, task_importance
        )
        
        if alternatives:
            best_alternative = alternatives[0]
            return False, best_alternative["model"]
        
        return False, None
    
    def _find_budget_alternatives(self, 
                                 requested_cost: float,
                                 budget_remaining: float,
                                 current_tier: str,
                                 task_importance: str) -> List[Dict[str, Any]]:
        """Find alternative models within budget"""
        
        alternatives = []
        
        # Get models in lower tiers
        tier_hierarchy = {"basic": 0, "standard": 1, "premium": 2, "ultra": 3}
        current_tier_level = tier_hierarchy.get(current_tier, 2)
        
        for model_name, model in self.cost_optimizer.model_profiles.items():
            model_tier_level = tier_hierarchy.get(model.tier.value, 2)
            
            # Only consider lower tiers or same tier with lower cost
            if (model_tier_level < current_tier_level or 
                (model_tier_level == current_tier_level and model.cost_per_call < requested_cost)):
                
                if model.cost_per_call <= budget_remaining:
                    savings = requested_cost - model.cost_per_call
                    quality_diff = model.expected_quality - self.cost_optimizer.model_profiles.get(
                        list(self.cost_optimizer.model_profiles.values())[0], 
                        ModelCostProfile(name="default", tier="basic", cost_per_call=0, expected_quality=0.5, speed_tier="medium", reliability=0.9)
                    ).expected_quality
                    
                    alternatives.append({
                        "model": model_name,
                        "cost": model.cost_per_call,
                        "savings": savings,
                        "quality_impact": quality_diff,
                        "tier": model.tier.value,
                        "recommendation_strength": self._calculate_recommendation_strength(
                            savings, quality_diff, task_importance
                        )
                    })
        
        # Sort by recommendation strength
        alternatives.sort(key=lambda x: x["recommendation_strength"], reverse=True)
        
        return alternatives
    
    def _calculate_recommendation_strength(self, 
                                          savings: float,
                                          quality_impact: float,
                                          task_importance: str) -> float:
        """Calculate strength of recommendation for alternative model"""
        
        strength = 0.0
        
        # Savings impact (higher savings = stronger recommendation)
        strength += min(1.0, savings * 20)  # Normalize savings impact
        
        # Quality impact (lower negative impact = stronger recommendation)
        if quality_impact < 0:
            strength += max(0, 1.0 + quality_impact)  # Reduce strength for quality loss
        
        # Task importance adjustment
        importance_multiplier = {
            "low": 1.2,      # More willing to switch for low importance tasks
            "medium": 1.0,   # Normal
            "high": 0.8,     # Less willing to switch for high importance tasks
            "critical": 0.6  # Very reluctant to switch for critical tasks
        }
        
        strength *= importance_multiplier.get(task_importance, 1.0)
        
        return strength
    
    def optimize_spending(self, 
                         current_spending: Dict[str, float],
                         remaining_budget: float,
                         upcoming_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Optimize spending for remaining tasks
        """
        
        # Analyze current spending patterns
        spending_analysis = self._analyze_spending_patterns(current_spending)
        
        # Generate optimization strategy
        optimization_strategy = self._generate_optimization_strategy(
            spending_analysis, remaining_budget, upcoming_tasks
        )
        
        # Calculate potential savings
        potential_savings = self._calculate_potential_savings(
            optimization_strategy, upcoming_tasks
        )
        
        return {
            "spending_analysis": spending_analysis,
            "optimization_strategy": optimization_strategy,
            "potential_savings": potential_savings,
            "recommended_actions": self._generate_optimization_actions(optimization_strategy)
        }
    
    def _analyze_spending_patterns(self, current_spending: Dict[str, float]) -> Dict[str, Any]:
        """Analyze current spending patterns"""
        
        total_spent = sum(current_spending.values())
        
        # Calculate spending by tier
        tier_spending = {}
        for model_name, cost in current_spending.items():
            model = self.cost_optimizer.model_profiles.get(model_name)
            if model:
                tier = model.tier.value
                tier_spending[tier] = tier_spending.get(tier, 0) + cost
        
        # Calculate spending percentages
        spending_percentages = {}
        for tier, cost in tier_spending.items():
            spending_percentages[tier] = cost / total_spent if total_spent > 0 else 0
        
        return {
            "total_spent": total_spent,
            "tier_spending": tier_spending,
            "spending_percentages": spending_percentages,
            "average_cost_per_task": total_spent / len(current_spending) if current_spending else 0
        }
    
    def _generate_optimization_strategy(self, 
                                       spending_analysis: Dict[str, Any],
                                       remaining_budget: float,
                                       upcoming_tasks: List[Dict[str, Any]]) -> str:
        """Generate optimization strategy based on spending and remaining budget"""
        
        total_spent = spending_analysis["total_spent"]
        avg_cost_per_task = spending_analysis["average_cost_per_task"]
        
        # Estimate tasks remaining with current budget
        tasks_remaining_estimate = remaining_budget / avg_cost_per_task if avg_cost_per_task > 0 else 0
        
        # Determine strategy
        if remaining_budget < total_spent * 0.2:
            return "aggressive_cost_cutting"
        elif remaining_budget < total_spent * 0.5:
            return "moderate_optimization"
        elif remaining_budget > total_spent:
            return "quality_investment"
        else:
            return "balanced_approach"
    
    def _calculate_potential_savings(self, 
                                   strategy: str,
                                   upcoming_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate potential savings based on optimization strategy"""
        
        savings = {
            "strategy": strategy,
            "estimated_savings": 0.0,
            "quality_impact": 0.0,
            "recommendations": []
        }
        
        if strategy == "aggressive_cost_cutting":
            # Switch all tasks to basic models
            basic_model_cost = 0.01  # Approximate cost for basic models
            current_avg_cost = 0.03  # Approximate current average cost
            
            savings["estimated_savings"] = (current_avg_cost - basic_model_cost) * len(upcoming_tasks)
            savings["quality_impact"] = -0.2  # Estimated quality reduction
            savings["recommendations"].append("Switch all upcoming tasks to basic-tier models")
            
        elif strategy == "moderate_optimization":
            # Switch 50% to basic models
            savings["estimated_savings"] = 0.01 * len(upcoming_tasks) * 0.5
            savings["quality_impact"] = -0.1
            savings["recommendations"].append("Switch 50% of tasks to basic-tier models")
            
        elif strategy == "quality_investment":
            # Upgrade to premium models for critical tasks
            critical_tasks = [task for task in upcoming_tasks if task.get("importance") == "high"]
            savings["estimated_savings"] = -0.02 * len(critical_tasks)  # Negative = additional cost
            savings["quality_impact"] = 0.15
            savings["recommendations"].append(f"Upgrade {len(critical_tasks)} critical tasks to premium models")
        
        return savings
    
    def _generate_optimization_actions(self, strategy: str) -> List[str]:
        """Generate specific optimization actions"""
        
        actions = []
        
        if strategy == "aggressive_cost_cutting":
            actions.extend([
                "Disable ultra-tier models",
                "Limit premium-tier usage to critical tasks only",
                "Increase quality threshold for basic models",
                "Implement batch processing for cost efficiency"
            ])
        
        elif strategy == "moderate_optimization":
            actions.extend([
                "Balance basic and standard tier usage",
                "Use premium tier only for high-quality requirements",
                "Monitor spending in real-time",
                "Implement cost alerts at 70% budget utilization"
            ])
        
        elif strategy == "quality_investment":
            actions.extend([
                "Allocate more budget to premium and ultra tiers",
                "Reduce basic tier allocation",
                "Invest in higher quality for important tasks",
                "Track quality improvements vs cost increases"
            ])
        
        else:  # balanced_approach
            actions.extend([
                "Maintain current tier distribution",
                "Optimize within each tier for better value",
                "Monitor cost-quality tradeoffs",
                "Adjust allocations based on performance"
            ])
        
        return actions
    
    def track_budget_utilization(self, 
                              model_usage: Dict[str, int],
                              costs: Dict[str, float]) -> Dict[str, Any]:
        """Track and analyze budget utilization"""
        
        # Calculate total usage and cost
        total_usage = sum(model_usage.values())
        total_cost = sum(costs.values())
        
        # Calculate utilization by tier
        tier_utilization = {}
        for model_name, usage in model_usage.items():
            model = self.cost_optimizer.model_profiles.get(model_name)
            if model:
                tier = model.tier.value
                tier_utilization[tier] = tier_utilization.get(tier, 0) + usage
        
        # Calculate cost efficiency
        cost_per_usage = total_cost / total_usage if total_usage > 0 else 0
        
        return {
            "total_usage": total_usage,
            "total_cost": total_cost,
            "cost_per_usage": cost_per_usage,
            "tier_utilization": tier_utilization,
            "efficiency_rating": self._calculate_efficiency_rating(cost_per_usage),
            "tracked_at": datetime.utcnow().isoformat()
        }
    
    def _calculate_efficiency_rating(self, cost_per_usage: float) -> str:
        """Calculate efficiency rating based on cost per usage"""
        
        if cost_per_usage <= 0.01:
            return "excellent"
        elif cost_per_usage <= 0.02:
            return "good"
        elif cost_per_usage <= 0.03:
            return "fair"
        elif cost_per_usage <= 0.05:
            return "poor"
        else:
            return "critical"


# Global budget constraint handler instance
budget_constraint_handler = BudgetConstraintHandler()
