import time
from typing import Dict, Any, Optional, List, Tuple
import logging
from app.agents.base_agent import BaseAgent
from app.agents.state_schema import (
    PipelineState, 
    Scene, 
    CostOptimization, 
    AgentStatus, 
    PipelineStatus
)

logger = logging.getLogger(__name__)


class CostOptimizationAgent(BaseAgent):
    """
    Cost Optimization Agent: Optimizes costs while maintaining quality
    Responsibilities:
    - Monitor and track generation costs
    - Suggest cost-saving strategies
    - Optimize model selection for budget constraints
    - Provide real-time cost analysis
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("cost_optimization_agent", config)
        
        # Model cost configurations
        self.model_costs = {
            "stable-diffusion-xl": {
                "cost_per_generation": 0.02,
                "quality_score": 0.8,
                "speed": "medium"
            },
            "dall-e-3": {
                "cost_per_generation": 0.04,
                "quality_score": 0.9,
                "speed": "slow"
            },
            "stable-diffusion-v1-5": {
                "cost_per_generation": 0.01,
                "quality_score": 0.7,
                "speed": "fast"
            },
            "midjourney": {
                "cost_per_generation": 0.05,
                "quality_score": 0.95,
                "speed": "very_slow"
            }
        }
        
        # Optimization strategies
        self.optimization_strategies = [
            "model_selection",
            "batch_processing",
            "quality_threshold_adjustment",
            "retry_optimization",
            "resource_allocation"
        ]
        
        # Cost analysis metrics
        self.cost_metrics = {
            "total_spent": 0.0,
            "cost_per_scene": 0.0,
            "budget_utilization": 0.0,
            "cost_efficiency": 0.0,
            "projected_total_cost": 0.0
        }
    
    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Analyze costs and provide optimization recommendations
        """
        try:
            self.update_status(AgentStatus.RUNNING)
            state.agent_statuses[self.name] = AgentStatus.RUNNING
            state.current_agent = self.name
            
            logger.info(f"Cost Optimization Agent analyzing costs for video {state.video_id}")
            
            # Analyze current cost situation
            cost_analysis = await self.analyze_costs(state)
            
            # Generate optimization recommendations
            optimization = await self.generate_optimization_recommendations(state, cost_analysis)
            
            # Update state with cost optimization
            state.cost_optimization = optimization
            
            # Send recommendations to decision agent if significant savings possible
            if optimization.potential_savings > 0.01:  # More than $0.01 savings
                await self.send_cost_recommendations(optimization, state)
            
            # Update cost metrics
            await self.update_cost_metrics(state)
            
            self.update_status(AgentStatus.COMPLETED)
            state.agent_statuses[self.name] = AgentStatus.COMPLETED
            
            # Log completion
            self.log_action("cost_optimization_completed", {
                "total_cost": state.total_cost,
                "potential_savings": optimization.potential_savings,
                "recommendations": len(optimization.optimization_suggestions)
            })
            
            return state
            
        except Exception as e:
            logger.error(f"Cost Optimization Agent error: {e}")
            return await self.handle_error(state, e)
    
    def can_handle(self, state: PipelineState) -> bool:
        """Check if this agent can handle the current state"""
        return (
            (state.status == PipelineStatus.EVALUATING_QUALITY or
             state.status == PipelineStatus.MAKING_DECISIONS or
             state.status == PipelineStatus.COMPLETED) and
            len(state.generation_results) > 0 and
            self.validate_state(state)
        )
    
    async def analyze_costs(self, state: PipelineState) -> Dict[str, Any]:
        """
        Analyze current cost situation
        """
        # Calculate cost breakdown by model
        model_costs = {}
        for result in state.generation_results:
            if result.success and result.model_used:
                model = result.model_used
                cost = result.cost
                model_costs[model] = model_costs.get(model, 0) + cost
        
        # Calculate cost per scene
        successful_scenes = len([r for r in state.generation_results if r.success])
        cost_per_scene = state.total_cost / successful_scenes if successful_scenes > 0 else 0
        
        # Calculate budget utilization
        budget_utilization = 0.0
        if state.total_budget:
            budget_utilization = state.total_cost / state.total_budget
        
        # Calculate cost efficiency (quality per dollar)
        total_quality = 0.0
        quality_count = 0
        for scene in state.scenes:
            if scene.quality_score is not None:
                total_quality += scene.quality_score
                quality_count += 1
        
        cost_efficiency = (total_quality / quality_count) / cost_per_scene if quality_count > 0 and cost_per_scene > 0 else 0
        
        # Project total cost
        remaining_scenes = len(state.scenes) - state.completed_scenes
        projected_total_cost = state.total_cost + (cost_per_scene * remaining_scenes)
        
        return {
            "model_costs": model_costs,
            "cost_per_scene": cost_per_scene,
            "budget_utilization": budget_utilization,
            "cost_efficiency": cost_efficiency,
            "projected_total_cost": projected_total_cost,
            "remaining_scenes": remaining_scenes
        }
    
    async def generate_optimization_recommendations(self, state: PipelineState, cost_analysis: Dict[str, Any]) -> CostOptimization:
        """
        Generate cost optimization recommendations
        """
        suggestions = []
        potential_savings = 0.0
        recommended_model = None
        
        # Analyze model selection optimization
        model_suggestion, model_savings = await self.optimize_model_selection(state, cost_analysis)
        if model_suggestion:
            suggestions.append(model_suggestion)
            potential_savings += model_savings
            recommended_model = model_suggestion.split("Use ")[-1].split(" ")[0]
        
        # Analyze quality threshold optimization
        quality_suggestion, quality_savings = await self.optimize_quality_threshold(state)
        if quality_suggestion:
            suggestions.append(quality_suggestion)
            potential_savings += quality_savings
        
        # Analyze retry optimization
        retry_suggestion, retry_savings = await self.optimize_retry_strategy(state)
        if retry_suggestion:
            suggestions.append(retry_suggestion)
            potential_savings += retry_savings
        
        # Analyze batch processing
        batch_suggestion, batch_savings = await self.optimize_batch_processing(state)
        if batch_suggestion:
            suggestions.append(batch_suggestion)
            potential_savings += batch_savings
        
        # Create cost optimization object
        optimization = CostOptimization(
            total_cost=state.total_cost,
            budget_limit=state.total_budget,
            cost_per_scene=cost_analysis["cost_per_scene"],
            optimization_suggestions=suggestions,
            recommended_model=recommended_model,
            potential_savings=potential_savings
        )
        
        return optimization
    
    async def optimize_model_selection(self, state: PipelineState, cost_analysis: Dict[str, Any]) -> Tuple[Optional[str], float]:
        """
        Optimize model selection for cost savings
        """
        current_model_costs = cost_analysis["model_costs"]
        
        # Find most expensive model
        if not current_model_costs:
            return None, 0.0
        
        most_expensive_model = max(current_model_costs.keys(), key=lambda x: current_model_costs[x])
        most_expensive_cost = current_model_costs[most_expensive_model]
        
        # Find cheaper alternative with acceptable quality
        cheaper_alternatives = []
        for model, config in self.model_costs.items():
            if config["cost_per_generation"] < most_expensive_cost:
                cheaper_alternatives.append((model, config))
        
        if not cheaper_alternatives:
            return None, 0.0
        
        # Sort by cost (cheapest first) and quality
        cheaper_alternatives.sort(key=lambda x: (x[1]["cost_per_generation"], -x[1]["quality_score"]))
        
        # Select best alternative
        best_alternative = cheaper_alternatives[0]
        alternative_model = best_alternative[0]
        alternative_cost = best_alternative[1]["cost_per_generation"]
        
        # Calculate savings
        scenes_with_expensive_model = len([s for s in state.scenes if s.model_used == most_expensive_model])
        potential_savings = (most_expensive_cost - alternative_cost) * scenes_with_expensive_model
        
        # Only recommend if quality difference is acceptable
        quality_diff = self.model_costs[most_expensive_model]["quality_score"] - best_alternative[1]["quality_score"]
        
        if quality_diff <= 0.1:  # Acceptable quality difference
            suggestion = f"Use {alternative_model} instead of {most_expensive_model} for {potential_savings:.3f} savings"
            return suggestion, potential_savings
        
        return None, 0.0
    
    async def optimize_quality_threshold(self, state: PipelineState) -> Tuple[Optional[str], float]:
        """
        Optimize quality threshold for cost savings
        """
        quality_scores = [s.quality_score for s in state.scenes if s.quality_score is not None]
        
        if len(quality_scores) < 5:
            return None, 0.0
        
        # Analyze quality distribution
        avg_quality = sum(quality_scores) / len(quality_scores)
        below_threshold_count = len([s for s in state.scenes if s.quality_score and s.quality_score < state.quality_threshold])
        
        # If most scenes are well above threshold, could lower it
        if avg_quality > state.quality_threshold + 0.2 and below_threshold_count == 0:
            # Could lower threshold by 0.1
            new_threshold = max(0.3, state.quality_threshold - 0.1)
            
            # Estimate savings from fewer retries
            estimated_retry_reduction = 0.1 * len(state.scenes)  # Assume 10% fewer retries
            avg_cost_per_retry = state.cost_per_scene * 0.5  # Assume half cost for retry
            potential_savings = estimated_retry_reduction * avg_cost_per_retry
            
            suggestion = f"Lower quality threshold to {new_threshold:.1f} for {potential_savings:.3f} savings"
            return suggestion, potential_savings
        
        return None, 0.0
    
    async def optimize_retry_strategy(self, state: PipelineState) -> Tuple[Optional[str], float]:
        """
        Optimize retry strategy for cost savings
        """
        total_retries = sum(scene.retry_count for scene in state.scenes)
        
        if total_retries == 0:
            return None, 0.0
        
        # Calculate retry success rate
        successful_retries = 0
        for scene in state.scenes:
            if scene.retry_count > 0 and scene.status == AgentStatus.COMPLETED:
                successful_retries += 1
        
        retry_success_rate = successful_retries / total_retries if total_retries > 0 else 0
        
        # If retry success rate is low, suggest reducing retries
        if retry_success_rate < 0.3:
            # Suggest reducing max retries by 1
            reduced_retries = max(1, state.max_retries - 1)
            potential_savings = (state.max_retries - reduced_retries) * state.cost_per_scene * 0.5
            
            suggestion = f"Reduce max retries to {reduced_retries} for {potential_savings:.3f} savings"
            return suggestion, potential_savings
        
        return None, 0.0
    
    async def optimize_batch_processing(self, state: PipelineState) -> Tuple[Optional[str], float]:
        """
        Optimize batch processing for cost savings
        """
        # Check if scenes could be batched
        similar_scenes = []
        
        for i, scene1 in enumerate(state.scenes):
            for j, scene2 in enumerate(state.scenes[i+1:], i+1):
                # Simple similarity check based on prompt length and model
                if (scene1.model_used == scene2.model_used and
                    abs(len(scene1.description) - len(scene2.description)) < 50):
                    similar_scenes.append((i, j))
        
        if len(similar_scenes) >= 2:
            # Could batch similar scenes
            potential_savings = len(similar_scenes) * 0.005  # Assume $0.005 savings per batched pair
            suggestion = f"Batch process {len(similar_scenes)} similar scenes for {potential_savings:.3f} savings"
            return suggestion, potential_savings
        
        return None, 0.0
    
    async def send_cost_recommendations(self, optimization: CostOptimization, state: PipelineState):
        """
        Send cost recommendations to decision agent
        """
        recommendation_message = self.send_message(
            recipient="decision_agent",
            message_type="notification",
            content={
                "action": "cost_optimization_recommendations",
                "optimization": optimization.dict(),
                "urgency": "high" if optimization.potential_savings > 0.05 else "medium"
            },
            priority=3
        )
        
        state.messages.append(recommendation_message.dict())
        
        logger.info(f"Sent cost optimization recommendations: {optimization.potential_savings:.3f} potential savings")
    
    async def update_cost_metrics(self, state: PipelineState):
        """
        Update cost metrics in state
        """
        # Update cost breakdown
        if "image_generation" not in state.cost_breakdown:
            state.cost_breakdown["image_generation"] = 0.0
        
        state.cost_breakdown["image_generation"] = sum(
            result.cost for result in state.generation_results if result.success
        )
        
        # Add quality evaluation costs
        if "quality_evaluation" not in state.cost_breakdown:
            state.cost_breakdown["quality_evaluation"] = 0.0
        
        quality_eval_cost = len(state.quality_results) * 0.002  # Assume $0.002 per evaluation
        state.cost_breakdown["quality_evaluation"] = quality_eval_cost
        
        # Update total cost
        state.total_cost = sum(state.cost_breakdown.values())
    
    def get_cost_projection(self, state: PipelineState, remaining_scenes: int) -> Dict[str, Any]:
        """
        Get cost projection for remaining scenes
        """
        if not state.generation_results:
            return {"projected_cost": 0.0, "confidence": 0.0}
        
        # Calculate average cost per scene
        successful_results = [r for r in state.generation_results if r.success]
        if not successful_results:
            return {"projected_cost": 0.0, "confidence": 0.0}
        
        avg_cost_per_scene = sum(r.cost for r in successful_results) / len(successful_results)
        
        # Calculate retry costs
        avg_retries = sum(scene.retry_count for scene in state.scenes) / len(state.scenes)
        retry_cost_multiplier = 1 + (avg_retries * 0.5)  # Assume 50% cost per retry
        
        # Project costs
        projected_cost = remaining_scenes * avg_cost_per_scene * retry_cost_multiplier
        
        # Calculate confidence based on data points
        confidence = min(1.0, len(successful_results) / 10)  # More data = higher confidence
        
        return {
            "projected_cost": projected_cost,
            "confidence": confidence,
            "avg_cost_per_scene": avg_cost_per_scene,
            "retry_cost_multiplier": retry_cost_multiplier
        }
    
    def analyze_cost_trends(self, state: PipelineState) -> Dict[str, Any]:
        """
        Analyze cost trends over time
        """
        if len(state.generation_results) < 3:
            return {"trend": "insufficient_data"}
        
        # Calculate costs over time
        costs_over_time = []
        for i, result in enumerate(state.generation_results):
            if result.success:
                costs_over_time.append((i, result.cost))
        
        if len(costs_over_time) < 3:
            return {"trend": "insufficient_data"}
        
        # Simple trend analysis
        early_costs = [cost for _, cost in costs_over_time[:len(costs_over_time)//2]]
        late_costs = [cost for _, cost in costs_over_time[len(costs_over_time)//2:]]
        
        early_avg = sum(early_costs) / len(early_costs)
        late_avg = sum(late_costs) / len(late_costs)
        
        if late_avg < early_avg * 0.9:
            trend = "decreasing"
        elif late_avg > early_avg * 1.1:
            trend = "increasing"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "early_average": early_avg,
            "late_average": late_avg,
            "change_percentage": ((late_avg - early_avg) / early_avg) * 100
        }
    
    def get_budget_alerts(self, state: PipelineState) -> List[Dict[str, Any]]:
        """
        Get budget alerts and warnings
        """
        alerts = []
        
        if not state.total_budget:
            return alerts
        
        budget_utilization = state.total_cost / state.total_budget
        
        # Budget utilization alerts
        if budget_utilization > 0.9:
            alerts.append({
                "type": "critical",
                "message": f"Budget {budget_utilization:.1%} utilized",
                "remaining": state.total_budget - state.total_cost
            })
        elif budget_utilization > 0.75:
            alerts.append({
                "type": "warning",
                "message": f"Budget {budget_utilization:.1%} utilized",
                "remaining": state.total_budget - state.total_cost
            })
        
        # Projected budget alerts
        if state.cost_optimization and state.cost_optimization.projected_total_cost:
            projected_utilization = state.cost_optimization.projected_total_cost / state.total_budget
            if projected_utilization > 1.0:
                alerts.append({
                    "type": "critical",
                    "message": f"Projected cost exceeds budget by {projected_utilization - 1.0:.1%}",
                    "projected_cost": state.cost_optimization.projected_total_cost
                })
        
        return alerts
    
    def get_optimization_summary(self, state: PipelineState) -> Dict[str, Any]:
        """
        Get summary of cost optimization opportunities
        """
        if not state.cost_optimization:
            return {"status": "no_optimization_available"}
        
        optimization = state.cost_optimization
        
        return {
            "status": "optimization_available",
            "total_cost": optimization.total_cost,
            "potential_savings": optimization.potential_savings,
            "savings_percentage": (optimization.potential_savings / optimization.total_cost) * 100 if optimization.total_cost > 0 else 0,
            "recommendations_count": len(optimization.optimization_suggestions),
            "recommended_model": optimization.recommended_model,
            "budget_status": "on_track" if not state.total_budget or optimization.total_cost < state.total_budget else "over_budget"
        }
