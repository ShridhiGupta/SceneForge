from typing import Dict, Any, List
import re
import logging
from app.agents.base_agent import BaseAgent
from app.agents.state_schema import PipelineState, Scene, AgentStatus, PipelineStatus

logger = logging.getLogger(__name__)


class SceneAgent(BaseAgent):
    """
    Scene Agent: Processes scripts and breaks them into individual scenes
    Responsibilities:
    - Parse video script into scenes
    - Generate prompts for each scene
    - Estimate scene durations
    - Manage scene ordering and dependencies
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("scene_agent", config)
        self.scene_patterns = [
            r"SCENE\s+\d+[:]\s*(.+)",  # SCENE 1: Description
            r"\[(\d+)\]\s*(.+)",        # [1] Description
            r"Scene\s+(\d+)[:]\s*(.+)", # Scene 1: Description
            r"^(.+?)\n\n",              # Paragraph-based scenes
        ]
    
    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Process script and create scenes
        """
        try:
            self.update_status(AgentStatus.RUNNING)
            state.agent_statuses[self.name] = AgentStatus.RUNNING
            state.current_agent = self.name
            
            logger.info(f"Scene Agent processing script for video {state.video_id}")
            
            # Parse script into scenes
            scenes = await self.parse_script(state.script)
            
            # Generate prompts for each scene
            for scene in scenes:
                scene.prompt = await self.generate_scene_prompt(scene)
                scene.model_used = state.preferred_model
            
            # Update state
            state.scenes = scenes
            state.status = PipelineStatus.PROCESSING_SCENES
            
            # Send notification to next agent
            notification = self.send_message(
                recipient="image_generation_agent",
                message_type="notification",
                content={
                    "action": "scenes_ready",
                    "scene_count": len(scenes),
                    "video_id": state.video_id
                },
                priority=3
            )
            state.messages.append(notification.dict())
            
            self.update_status(AgentStatus.COMPLETED)
            state.agent_statuses[self.name] = AgentStatus.COMPLETED
            
            # Log completion
            self.log_action("script_processed", {
                "scene_count": len(scenes),
                "video_id": state.video_id
            })
            
            return state
            
        except Exception as e:
            logger.error(f"Scene Agent error: {e}")
            return await self.handle_error(state, e)
    
    def can_handle(self, state: PipelineState) -> bool:
        """Check if this agent can handle the current state"""
        return (
            state.status == PipelineStatus.INITIALIZING and
            state.script and
            len(state.scenes) == 0 and
            self.validate_state(state)
        )
    
    async def parse_script(self, script: str) -> List[Scene]:
        """
        Parse script into individual scenes
        """
        scenes = []
        scene_number = 1
        
        # Try different parsing patterns
        for pattern in self.scene_patterns:
            matches = re.finditer(pattern, script, re.MULTILINE | re.IGNORECASE)
            
            for match in matches:
                if len(match.groups()) == 1:
                    description = match.group(1).strip()
                else:
                    description = match.group(2).strip()
                
                # Clean up description
                description = re.sub(r'\s+', ' ', description)
                
                if description and len(description) > 10:  # Filter out very short descriptions
                    scene = Scene(
                        id=scene_number,
                        scene_number=scene_number,
                        description=description,
                        duration=self.estimate_scene_duration(description)
                    )
                    scenes.append(scene)
                    scene_number += 1
            
            # If we found scenes with this pattern, stop trying other patterns
            if scenes:
                break
        
        # If no patterns matched, try paragraph-based parsing
        if not scenes:
            paragraphs = [p.strip() for p in script.split('\n\n') if p.strip()]
            for i, paragraph in enumerate(paragraphs, 1):
                if len(paragraph) > 20:  # Filter out very short paragraphs
                    scene = Scene(
                        id=i,
                        scene_number=i,
                        description=paragraph,
                        duration=self.estimate_scene_duration(paragraph)
                    )
                    scenes.append(scene)
        
        logger.info(f"Parsed {len(scenes)} scenes from script")
        return scenes
    
    async def generate_scene_prompt(self, scene: Scene) -> str:
        """
        Generate AI prompt for scene image generation
        """
        # Extract key elements from scene description
        description = scene.description.lower()
        
        # Identify visual elements
        visual_keywords = []
        
        # Common visual elements
        visual_patterns = [
            r'(person|man|woman|child|people)',
            r'(car|truck|bus|vehicle)',
            r'(house|building|city|street)',
            r'(tree|flower|garden|nature)',
            r'(sun|moon|sky|cloud)',
            r'(water|ocean|river|lake)',
            r'(mountain|hill|valley)',
            r'(animal|dog|cat|bird)',
            r'(indoor|outdoor|inside|outside)',
            r'(day|night|morning|evening)',
            r'(bright|dark|light|shadow)',
            r'(color|red|blue|green|yellow)',
        ]
        
        for pattern in visual_patterns:
            matches = re.findall(pattern, description)
            visual_keywords.extend(matches)
        
        # Build prompt
        base_prompt = scene.description
        
        # Add visual enhancement
        if visual_keywords:
            enhanced_elements = ", ".join(set(visual_keywords))
            base_prompt += f", featuring {enhanced_elements}"
        
        # Add quality and style modifiers
        quality_modifiers = [
            "high quality",
            "detailed",
            "professional photography",
            "cinematic lighting",
            "sharp focus"
        ]
        
        # Add context-appropriate modifiers
        if "night" in description or "dark" in description:
            quality_modifiers.extend(["dramatic lighting", "moody atmosphere"])
        elif "day" in description or "bright" in description:
            quality_modifiers.extend(["natural lighting", "vibrant colors"])
        
        if "person" in description or "people" in description:
            quality_modifiers.extend(["realistic", "natural expression"])
        
        # Combine prompt
        final_prompt = f"{base_prompt}, {', '.join(quality_modifiers)}"
        
        # Limit prompt length
        if len(final_prompt) > 500:
            final_prompt = final_prompt[:500] + "..."
        
        return final_prompt
    
    def estimate_scene_duration(self, description: str) -> float:
        """
        Estimate scene duration based on description complexity
        """
        word_count = len(description.split())
        
        # Base duration: 3 seconds per scene
        base_duration = 3.0
        
        # Add time based on complexity
        if word_count < 10:
            complexity_addition = 2.0  # Simple scene
        elif word_count < 25:
            complexity_addition = 4.0  # Moderate scene
        elif word_count < 50:
            complexity_addition = 6.0  # Complex scene
        else:
            complexity_addition = 8.0  # Very complex scene
        
        # Add time for action elements
        action_keywords = ["run", "walk", "move", "drive", "fly", "jump", "dance"]
        if any(keyword in description.lower() for keyword in action_keywords):
            complexity_addition += 2.0
        
        total_duration = base_duration + complexity_addition
        
        # Cap duration between 3 and 15 seconds
        return max(3.0, min(15.0, total_duration))
    
    def validate_scenes(self, scenes: List[Scene]) -> bool:
        """
        Validate parsed scenes
        """
        if not scenes:
            return False
        
        # Check for duplicate scene numbers
        scene_numbers = [scene.scene_number for scene in scenes]
        if len(scene_numbers) != len(set(scene_numbers)):
            return False
        
        # Check for empty descriptions
        for scene in scenes:
            if not scene.description or len(scene.description.strip()) < 5:
                return False
        
        return True
    
    def get_scene_statistics(self, scenes: List[Scene]) -> Dict[str, Any]:
        """
        Get statistics about parsed scenes
        """
        if not scenes:
            return {}
        
        total_duration = sum(scene.duration for scene in scenes)
        avg_duration = total_duration / len(scenes)
        
        description_lengths = [len(scene.description) for scene in scenes]
        avg_description_length = sum(description_lengths) / len(description_lengths)
        
        return {
            "scene_count": len(scenes),
            "total_duration": total_duration,
            "average_duration": avg_duration,
            "average_description_length": avg_description_length,
            "duration_range": {
                "min": min(scene.duration for scene in scenes),
                "max": max(scene.duration for scene in scenes)
            }
        }
