import os
import uuid
import time
import asyncio
from typing import Dict, Any, Optional
import logging
from app.agents.base_agent import BaseAgent
from app.agents.state_schema import PipelineState, Scene, GenerationResult, AgentStatus, PipelineStatus
from app.services.image_service import ImageGenerationService
from app.services.quality_evaluation import quality_evaluator

logger = logging.getLogger(__name__)


class ImageGenerationAgent(BaseAgent):
    """
    Image Generation Agent: Generates images for scenes using various AI models
    Responsibilities:
    - Select optimal model for each scene
    - Generate images using AI services
    - Handle model switching and fallbacks
    - Track generation costs and performance
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("image_generation_agent", config)
        self.image_service = ImageGenerationService()
        
        # Model configuration
        self.models = {
            "stable-diffusion-xl": {
                "cost": 0.02,
                "quality": "high",
                "speed": "medium",
                "max_retries": 3
            },
            "dall-e-3": {
                "cost": 0.04,
                "quality": "very_high",
                "speed": "slow",
                "max_retries": 2
            },
            "stable-diffusion-v1-5": {
                "cost": 0.01,
                "quality": "medium",
                "speed": "fast",
                "max_retries": 3
            },
            "midjourney": {
                "cost": 0.05,
                "quality": "excellent",
                "speed": "very_slow",
                "max_retries": 1
            }
        }
        
        self.default_model = "stable-diffusion-xl"
    
    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Generate images for all scenes
        """
        try:
            self.update_status(AgentStatus.RUNNING)
            state.agent_statuses[self.name] = AgentStatus.RUNNING
            state.current_agent = self.name
            state.status = PipelineStatus.GENERATING_IMAGES
            
            logger.info(f"Image Generation Agent processing {len(state.scenes)} scenes")
            
            # Process each scene
            for i, scene in enumerate(state.scenes):
                if state.current_scene_index <= i < len(state.scenes):
                    state.current_scene_index = i
                    
                    # Generate image for current scene
                    result = await self.generate_scene_image(scene, state)
                    state.generation_results.append(result)
                    
                    # Update scene with generation result
                    if result.success:
                        scene.image_path = result.image_path
                        scene.model_used = result.model_used
                        scene.cost = result.cost
                        scene.status = AgentStatus.COMPLETED
                        
                        # Send notification to quality agent
                        notification = self.send_message(
                            recipient="quality_evaluation_agent",
                            message_type="notification",
                            content={
                                "action": "image_generated",
                                "scene_id": scene.id,
                                "image_path": result.image_path,
                                "prompt": scene.prompt
                            },
                            priority=3
                        )
                        state.messages.append(notification.dict())
                    else:
                        scene.status = AgentStatus.FAILED
                        
                        # Send error to decision agent
                        error_message = self.send_message(
                            recipient="decision_agent",
                            message_type="error",
                            content={
                                "action": "generation_failed",
                                "scene_id": scene.id,
                                "error": result.error_message,
                                "model_used": result.model_used
                            },
                            priority=5
                        )
                        state.messages.append(error_message.dict())
            
            # Update total cost
            state.total_cost += sum(result.cost for result in state.generation_results if result.success)
            state.cost_breakdown["image_generation"] = sum(result.cost for result in state.generation_results)
            
            self.update_status(AgentStatus.COMPLETED)
            state.agent_statuses[self.name] = AgentStatus.COMPLETED
            
            # Log completion
            self.log_action("images_generated", {
                "total_scenes": len(state.scenes),
                "successful_generations": len([r for r in state.generation_results if r.success]),
                "total_cost": state.total_cost
            })
            
            return state
            
        except Exception as e:
            logger.error(f"Image Generation Agent error: {e}")
            return await self.handle_error(state, e)
    
    def can_handle(self, state: PipelineState) -> bool:
        """Check if this agent can handle the current state"""
        return (
            state.status == PipelineStatus.PROCESSING_SCENES and
            len(state.scenes) > 0 and
            self.validate_state(state)
        )
    
    async def generate_scene_image(self, scene: Scene, state: PipelineState) -> GenerationResult:
        """
        Generate image for a specific scene
        """
        start_time = time.time()
        
        try:
            # Select optimal model
            selected_model = await self.select_model(scene, state)
            
            # Generate unique filename
            filename = f"scene_{scene.video_id}_{scene.scene_number}_{uuid.uuid4().hex[:8]}.png"
            image_path = os.path.join("uploads", "images", filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            
            # Generate image
            await self.generate_image_with_retry(
                prompt=scene.prompt,
                output_path=image_path,
                model=selected_model,
                scene=scene
            )
            
            generation_time = (time.time() - start_time) * 1000
            
            # Calculate cost
            cost = self.models.get(selected_model, {}).get("cost", 0.02)
            
            logger.info(f"Generated image for scene {scene.id} using {selected_model}")
            
            return GenerationResult(
                success=True,
                image_path=image_path,
                model_used=selected_model,
                cost=cost,
                generation_time_ms=generation_time
            )
            
        except Exception as e:
            generation_time = (time.time() - start_time) * 1000
            logger.error(f"Failed to generate image for scene {scene.id}: {e}")
            
            return GenerationResult(
                success=False,
                error_message=str(e),
                generation_time_ms=generation_time
            )
    
    async def select_model(self, scene: Scene, state: PipelineState) -> str:
        """
        Select optimal model for scene generation
        """
        # Check if specific model is requested
        if scene.model_used and scene.model_used in self.models:
            return scene.model_used
        
        # Check budget constraints
        if state.total_budget:
            remaining_budget = state.total_budget - state.total_cost
            affordable_models = [
                model for model, config in self.models.items()
                if config["cost"] <= remaining_budget / max(1, len(state.scenes) - state.current_scene_index)
            ]
            
            if affordable_models:
                # Select best affordable model
                affordable_models.sort(key=lambda x: self.models[x]["quality"], reverse=True)
                return affordable_models[0]
        
        # Select based on scene complexity
        scene_complexity = self.assess_scene_complexity(scene)
        
        if scene_complexity == "simple":
            return "stable-diffusion-v1-5"  # Fast and cheap
        elif scene_complexity == "moderate":
            return "stable-diffusion-xl"    # Good balance
        elif scene_complexity == "complex":
            return "dall-e-3"              # High quality
        else:
            return self.default_model
    
    def assess_scene_complexity(self, scene: Scene) -> str:
        """
        Assess scene complexity for model selection
        """
        description = scene.description.lower()
        prompt = scene.prompt.lower() if scene.prompt else ""
        
        complexity_indicators = {
            "simple": ["simple", "basic", "plain", "minimal"],
            "moderate": ["detailed", "multiple", "several", "various"],
            "complex": ["complex", "intricate", "detailed", "multiple people", "crowd", "landscape", "architecture"]
        }
        
        # Count complexity indicators
        complexity_scores = {}
        for complexity, indicators in complexity_indicators.items():
            score = sum(1 for indicator in indicators if indicator in description or indicator in prompt)
            complexity_scores[complexity] = score
        
        # Determine complexity based on highest score
        if complexity_scores["complex"] > 0:
            return "complex"
        elif complexity_scores["moderate"] > 1:
            return "moderate"
        else:
            return "simple"
    
    async def generate_image_with_retry(self, prompt: str, output_path: str, model: str, scene: Scene):
        """
        Generate image with retry logic
        """
        max_retries = self.models.get(model, {}).get("max_retries", 3)
        
        for attempt in range(max_retries):
            try:
                # Update scene retry count
                scene.retry_count = attempt
                
                # Generate image
                self.image_service.generate_image(
                    prompt=prompt,
                    output_path=output_path,
                    model_name=model,
                    task_id=f"scene_{scene.id}"
                )
                
                # Verify image was created
                if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                    raise Exception("Generated image is empty or missing")
                
                return  # Success
                
            except Exception as e:
                logger.warning(f"Image generation attempt {attempt + 1} failed: {e}")
                
                if attempt == max_retries - 1:
                    # Last attempt failed, try fallback model
                    fallback_model = await self.get_fallback_model(model, scene)
                    if fallback_model != model:
                        logger.info(f"Trying fallback model: {fallback_model}")
                        return await self.generate_image_with_retry(prompt, output_path, fallback_model, scene)
                    
                    # No fallback available, raise exception
                    raise Exception(f"Failed to generate image after {max_retries} attempts: {e}")
                
                # Wait before retry
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    async def get_fallback_model(self, failed_model: str, scene: Scene) -> str:
        """
        Get fallback model when primary model fails
        """
        # Model fallback hierarchy
        fallback_hierarchy = {
            "midjourney": "dall-e-3",
            "dall-e-3": "stable-diffusion-xl",
            "stable-diffusion-xl": "stable-diffusion-v1-5",
            "stable-diffusion-v1-5": "dall-e-3"
        }
        
        return fallback_hierarchy.get(failed_model, self.default_model)
    
    def get_model_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for different models
        """
        stats = {}
        for model, config in self.models.items():
            stats[model] = {
                "cost": config["cost"],
                "quality": config["quality"],
                "speed": config["speed"],
                "max_retries": config["max_retries"]
            }
        return stats
    
    def estimate_total_cost(self, scenes: list[Scene]) -> float:
        """
        Estimate total cost for generating all scenes
        """
        total_cost = 0.0
        
        for scene in scenes:
            model = scene.model_used or self.default_model
            cost_per_generation = self.models.get(model, {}).get("cost", 0.02)
            estimated_retries = 1.5  # Average retry attempts
            total_cost += cost_per_generation * estimated_retries
        
        return total_cost
    
    def optimize_model_selection(self, scenes: list[Scene], budget: float) -> Dict[str, str]:
        """
        Optimize model selection within budget constraints
        """
        # Simple optimization: prioritize important scenes
        scene_priorities = []
        
        for i, scene in enumerate(scenes):
            priority = len(scene.description) / 100  # Simple priority based on description length
            scene_priorities.append((i, priority, scene))
        
        # Sort by priority (descending)
        scene_priorities.sort(key=lambda x: x[1], reverse=True)
        
        # Assign models based on priority and budget
        model_assignments = {}
        remaining_budget = budget
        
        for scene_index, priority, scene in scene_priorities:
            if remaining_budget <= 0:
                model_assignments[scene_index] = "stable-diffusion-v1-5"  # Cheapest option
                continue
            
            # Try to assign best affordable model
            for model in ["dall-e-3", "stable-diffusion-xl", "stable-diffusion-v1-5"]:
                cost = self.models[model]["cost"]
                if cost <= remaining_budget:
                    model_assignments[scene_index] = model
                    remaining_budget -= cost
                    break
            else:
                model_assignments[scene_index] = "stable-diffusion-v1-5"
        
        return model_assignments
