import os
import time
from typing import Dict, Any, Optional, List
import logging
from app.agents.base_agent import BaseAgent
from app.agents.state_schema import (
    PipelineState, 
    Scene, 
    QualityResult, 
    AgentStatus, 
    PipelineStatus,
    QualityLevel
)
from app.services.quality_evaluation import quality_evaluator
from app.services.clip_evaluation import clip_evaluator
from app.services.llm_evaluation import llm_evaluator

logger = logging.getLogger(__name__)


class QualityEvaluationAgent(BaseAgent):
    """
    Quality Evaluation Agent: Evaluates generated images using CLIP and LLM
    Responsibilities:
    - Evaluate image quality using multiple methods
    - Determine if quality meets thresholds
    - Provide detailed quality analysis
    - Trigger decision agent for low-quality images
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("quality_evaluation_agent", config)
        self.quality_threshold = config.get("quality_threshold", 0.5) if config else 0.5
        self.enable_clip = config.get("enable_clip", True) if config else True
        self.enable_llm = config.get("enable_llm", True) if config else True
        
        # Quality level thresholds
        self.quality_thresholds = {
            QualityLevel.VERY_HIGH: 0.85,
            QualityLevel.HIGH: 0.70,
            QualityLevel.MEDIUM: 0.50,
            QualityLevel.LOW: 0.30,
            QualityLevel.VERY_LOW: 0.0
        }
    
    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Evaluate quality of generated images
        """
        try:
            self.update_status(AgentStatus.RUNNING)
            state.agent_statuses[self.name] = AgentStatus.RUNNING
            state.current_agent = self.name
            state.status = PipelineStatus.EVALUATING_QUALITY
            
            logger.info(f"Quality Evaluation Agent evaluating {len(state.generation_results)} images")
            
            # Evaluate each generated image
            for i, generation_result in enumerate(state.generation_results):
                if generation_result.success and generation_result.image_path:
                    # Get corresponding scene
                    scene = None
                    for s in state.scenes:
                        if s.image_path == generation_result.image_path:
                            scene = s
                            break
                    
                    if scene:
                        # Evaluate image quality
                        quality_result = await self.evaluate_image_quality(
                            generation_result.image_path,
                            scene.prompt or scene.description,
                            generation_result.model_used
                        )
                        
                        state.quality_results.append(quality_result)
                        
                        # Update scene with quality score
                        scene.quality_score = quality_result.quality_score
                        
                        # Check if quality passes threshold
                        if not quality_result.passes_threshold:
                            # Trigger decision agent for low quality
                            await self.handle_low_quality(scene, quality_result, state)
                        else:
                            # Mark scene as high quality
                            scene.status = AgentStatus.COMPLETED
                            state.completed_scenes += 1
                            
                            # Send success notification
                            notification = self.send_message(
                                recipient="cost_optimization_agent",
                                message_type="notification",
                                content={
                                    "action": "quality_passed",
                                    "scene_id": scene.id,
                                    "quality_score": quality_result.quality_score,
                                    "quality_level": quality_result.quality_level.value
                                },
                                priority=2
                            )
                            state.messages.append(notification.dict())
            
            # Update pipeline status
            if state.completed_scenes == len(state.scenes):
                state.status = PipelineStatus.COMPLETED
            else:
                state.status = PipelineStatus.MAKING_DECISIONS
            
            self.update_status(AgentStatus.COMPLETED)
            state.agent_statuses[self.name] = AgentStatus.COMPLETED
            
            # Log completion
            self.log_action("quality_evaluated", {
                "total_evaluations": len(state.quality_results),
                "passed_threshold": len([r for r in state.quality_results if r.passes_threshold]),
                "failed_threshold": len([r for r in state.quality_results if not r.passes_threshold]),
                "average_quality": sum(r.quality_score for r in state.quality_results) / len(state.quality_results) if state.quality_results else 0
            })
            
            return state
            
        except Exception as e:
            logger.error(f"Quality Evaluation Agent error: {e}")
            return await self.handle_error(state, e)
    
    def can_handle(self, state: PipelineState) -> bool:
        """Check if this agent can handle the current state"""
        return (
            state.status == PipelineStatus.GENERATING_IMAGES and
            len(state.generation_results) > 0 and
            self.validate_state(state)
        )
    
    async def evaluate_image_quality(self, image_path: str, prompt: str, model_used: str) -> QualityResult:
        """
        Evaluate image quality using CLIP and LLM
        """
        start_time = time.time()
        
        try:
            # Verify image exists
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            # Initialize evaluation results
            clip_score = None
            llm_score = None
            reasoning = ""
            
            # CLIP evaluation
            if self.enable_clip and clip_evaluator.is_available():
                try:
                    clip_result = clip_evaluator.evaluate_image_text_similarity(image_path, prompt)
                    clip_score = clip_result.clip_score
                except Exception as e:
                    logger.warning(f"CLIP evaluation failed: {e}")
            
            # LLM evaluation
            if self.enable_llm and llm_evaluator.is_available():
                try:
                    llm_result = await llm_evaluator.evaluate_image_quality(image_path, prompt)
                    llm_score = llm_result.quality_score
                    reasoning = llm_result.reasoning
                except Exception as e:
                    logger.warning(f"LLM evaluation failed: {e}")
            
            # Calculate combined score
            if clip_score is not None and llm_score is not None:
                # Both available: weighted combination
                combined_score = (clip_score * 0.6) + (llm_score * 0.4)
            elif clip_score is not None:
                # Only CLIP available
                combined_score = clip_score
                reasoning = f"CLIP-based evaluation: {clip_score:.2f}"
            elif llm_score is not None:
                # Only LLM available
                combined_score = llm_score
            else:
                # Neither available
                combined_score = 0.5  # Default middle score
                reasoning = "Evaluation services unavailable"
            
            # Determine quality level
            quality_level = self.determine_quality_level(combined_score)
            
            # Check if passes threshold
            passes_threshold = combined_score >= self.quality_threshold
            
            evaluation_time = (time.time() - start_time) * 1000
            
            logger.info(f"Quality evaluation completed: {combined_score:.2f} ({quality_level.value})")
            
            return QualityResult(
                success=True,
                quality_score=combined_score,
                quality_level=quality_level,
                passes_threshold=passes_threshold,
                clip_score=clip_score,
                llm_score=llm_score,
                evaluation_time_ms=evaluation_time,
                reasoning=reasoning
            )
            
        except Exception as e:
            evaluation_time = (time.time() - start_time) * 1000
            logger.error(f"Quality evaluation failed: {e}")
            
            return QualityResult(
                success=False,
                quality_score=0.0,
                quality_level=QualityLevel.VERY_LOW,
                passes_threshold=False,
                evaluation_time_ms=evaluation_time,
                reasoning=f"Evaluation failed: {str(e)}"
            )
    
    def determine_quality_level(self, score: float) -> QualityLevel:
        """
        Determine quality level based on score
        """
        for level, threshold in self.quality_thresholds.items():
            if score >= threshold:
                return level
        return QualityLevel.VERY_LOW
    
    async def handle_low_quality(self, scene: Scene, quality_result: QualityResult, state: PipelineState):
        """
        Handle low quality images by triggering decision agent
        """
        logger.warning(f"Low quality detected for scene {scene.id}: {quality_result.quality_score:.2f}")
        
        # Update scene status
        scene.status = AgentStatus.FAILED
        
        # Create low quality context for decision agent
        low_quality_context = {
            "scene_id": scene.id,
            "image_path": scene.image_path,
            "prompt": scene.prompt or scene.description,
            "model_used": scene.model_used,
            "quality_score": quality_result.quality_score,
            "quality_level": quality_result.quality_level.value,
            "clip_score": quality_result.clip_score,
            "llm_score": quality_result.llm_score,
            "reasoning": quality_result.reasoning,
            "threshold": self.quality_threshold,
            "retry_count": scene.retry_count
        }
        
        # Send low quality notification to decision agent
        decision_message = self.send_message(
            recipient="decision_agent",
            message_type="request",
            content={
                "action": "handle_low_quality",
                "context": low_quality_context,
                "urgency": "high" if quality_result.quality_score < 0.3 else "medium"
            },
            priority=4
        )
        
        state.messages.append(decision_message.dict())
        
        # Log quality failure
        self.log_action("quality_failure", low_quality_context)
    
    async def batch_evaluate(self, image_paths: List[str], prompts: List[str]) -> List[QualityResult]:
        """
        Batch evaluate multiple images
        """
        if len(image_paths) != len(prompts):
            raise ValueError("Number of image paths and prompts must match")
        
        results = []
        for image_path, prompt in zip(image_paths, prompts):
            result = await self.evaluate_image_quality(image_path, prompt, "unknown")
            results.append(result)
        
        return results
    
    def get_quality_statistics(self, quality_results: List[QualityResult]) -> Dict[str, Any]:
        """
        Get statistics about quality evaluations
        """
        if not quality_results:
            return {}
        
        scores = [r.quality_score for r in quality_results]
        passed = [r for r in quality_results if r.passes_threshold]
        failed = [r for r in quality_results if not r.passes_threshold]
        
        # Quality level distribution
        level_counts = {}
        for result in quality_results:
            level = result.quality_level.value
            level_counts[level] = level_counts.get(level, 0) + 1
        
        return {
            "total_evaluations": len(quality_results),
            "average_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "passed_threshold": len(passed),
            "failed_threshold": len(failed),
            "pass_rate": len(passed) / len(quality_results),
            "quality_level_distribution": level_counts,
            "average_evaluation_time": sum(r.evaluation_time_ms or 0 for r in quality_results) / len(quality_results)
        }
    
    def adjust_quality_threshold(self, new_threshold: float):
        """
        Adjust quality threshold dynamically
        """
        if 0.0 <= new_threshold <= 1.0:
            self.quality_threshold = new_threshold
            logger.info(f"Quality threshold adjusted to {new_threshold}")
        else:
            raise ValueError("Quality threshold must be between 0.0 and 1.0")
    
    def get_evaluation_config(self) -> Dict[str, Any]:
        """
        Get current evaluation configuration
        """
        return {
            "quality_threshold": self.quality_threshold,
            "enable_clip": self.enable_clip,
            "enable_llm": self.enable_llm,
            "clip_available": clip_evaluator.is_available(),
            "llm_available": llm_evaluator.is_available(),
            "quality_thresholds": {level.value: threshold for level, threshold in self.quality_thresholds.items()}
        }
    
    def recommend_threshold_adjustment(self, quality_results: List[QualityResult]) -> Dict[str, Any]:
        """
        Recommend threshold adjustments based on evaluation results
        """
        if len(quality_results) < 10:
            return {"recommendation": "insufficient_data", "reason": "Need at least 10 evaluations"}
        
        scores = [r.quality_score for r in quality_results]
        current_pass_rate = len([r for r in quality_results if r.passes_threshold]) / len(quality_results)
        
        recommendations = []
        
        # If pass rate is too low, suggest lowering threshold
        if current_pass_rate < 0.6:
            suggested_threshold = max(0.3, self.quality_threshold - 0.1)
            recommendations.append({
                "type": "lower_threshold",
                "current": self.quality_threshold,
                "suggested": suggested_threshold,
                "reason": f"Current pass rate ({current_pass_rate:.2f}) is too low"
            })
        
        # If pass rate is too high, suggest raising threshold
        elif current_pass_rate > 0.9:
            suggested_threshold = min(0.8, self.quality_threshold + 0.1)
            recommendations.append({
                "type": "raise_threshold",
                "current": self.quality_threshold,
                "suggested": suggested_threshold,
                "reason": f"Current pass rate ({current_pass_rate:.2f}) is very high, could improve quality"
            })
        
        # If scores are consistently high, could raise threshold
        avg_score = sum(scores) / len(scores)
        if avg_score > 0.8 and self.quality_threshold < 0.6:
            recommendations.append({
                "type": "optimize_for_quality",
                "current": self.quality_threshold,
                "suggested": min(0.7, avg_score - 0.1),
                "reason": f"Average score ({avg_score:.2f}) is high, could increase quality standards"
            })
        
        return {
            "current_pass_rate": current_pass_rate,
            "average_score": avg_score,
            "recommendations": recommendations
        }
