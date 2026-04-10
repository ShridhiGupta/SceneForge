import asyncio
from typing import Dict, Any, Optional
from app.schemas.decision_engine import FailureContext, PipelineStage
from app.services.decision_executor import decision_executor
from app.core.database import SessionLocal
from app.models.video import Scene, Video
import logging

logger = logging.getLogger(__name__)


class TaskFailureHandler:
    """
    Utility class for handling task failures with LLM decision engine
    """
    
    @staticmethod
    async def handle_task_failure(
        task_name: str,
        stage: PipelineStage,
        error: Exception,
        retry_count: int,
        model_used: str = "unknown",
        prompt_used: str = "",
        quality_score: Optional[float] = None,
        cost_so_far: float = 0.0,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle task failure using LLM decision engine
        """
        # Create failure context
        context = FailureContext(
            task_name=task_name,
            stage=stage,
            error_logs=str(error),
            retry_count=retry_count,
            output_quality_score=quality_score,
            cost_so_far=cost_so_far,
            model_used=model_used,
            prompt_used=prompt_used,
            additional_context=additional_context or {}
        )
        
        # Check if we should use decision engine
        if await decision_executor.should_use_decision_engine(context):
            logger.info(f"Using LLM decision engine for {task_name} failure")
            result = await decision_executor.handle_failure(context)
            return result
        else:
            logger.info(f"Using simple retry for {task_name} failure (attempt {retry_count})")
            return {
                "decision": None,
                "execution_result": {
                    "action": "simple_retry",
                    "retry_count": retry_count + 1
                },
                "success": True
            }
    
    @staticmethod
    def get_scene_context(scene_id: int) -> Dict[str, Any]:
        """
        Get context data for a scene
        """
        db = SessionLocal()
        try:
            scene = db.query(Scene).filter(Scene.id == scene_id).first()
            if not scene:
                return {}
            
            return {
                "scene_id": scene.id,
                "video_id": scene.video_id,
                "scene_number": scene.scene_number,
                "description": scene.description,
                "retry_count": scene.retry_count or 0
            }
        finally:
            db.close()
    
    @staticmethod
    def get_video_context(video_id: int) -> Dict[str, Any]:
        """
        Get context data for a video
        """
        db = SessionLocal()
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                return {}
            
            return {
                "video_id": video.id,
                "title": video.title,
                "status": video.status,
                "total_cost": getattr(video, 'total_cost', 0.0)
            }
        finally:
            db.close()


def with_failure_handling(stage: PipelineStage):
    """
    Decorator for adding failure handling to Celery tasks
    """
    def decorator(func):
        async def async_wrapper(self, *args, **kwargs):
            try:
                return await func(self, *args, **kwargs)
            except Exception as e:
                # Extract context from task
                task_name = self.name
                retry_count = self.request.retries
                
                # Try to extract additional context from args/kwargs
                additional_context = {}
                prompt_used = ""
                model_used = "unknown"
                
                if stage == PipelineStage.IMAGE and len(args) > 0:
                    scene_id = args[0]
                    additional_context = TaskFailureHandler.get_scene_context(scene_id)
                    prompt_used = additional_context.get("description", "")
                
                # Handle failure
                result = await TaskFailureHandler.handle_task_failure(
                    task_name=task_name,
                    stage=stage,
                    error=e,
                    retry_count=retry_count,
                    model_used=model_used,
                    prompt_used=prompt_used,
                    additional_context=additional_context
                )
                
                # Execute the decision
                if result["success"] and result["execution_result"]:
                    execution_result = result["execution_result"]
                    action = execution_result.get("action")
                    
                    if action == "simple_retry" or action == "retry_scheduled":
                        # Simple retry
                        delay = execution_result.get("delay", 60)
                        raise self.retry(exc=e, countdown=delay)
                    elif action == "prompt_modified":
                        # Retry with new prompt
                        logger.info(f"Retrying with modified prompt")
                        raise self.retry(exc=e, countdown=30)
                    elif action == "model_switched":
                        # Retry with new model (implementation specific)
                        logger.info(f"Retrying with switched model: {execution_result.get('new_model')}")
                        raise self.retry(exc=e, countdown=30)
                    elif action == "parameters_adjusted":
                        # Retry with new parameters
                        logger.info(f"Retrying with adjusted parameters")
                        raise self.retry(exc=e, countdown=30)
                    elif action == "task_skipped":
                        # Don't retry, just mark as failed
                        logger.info(f"Task skipped: {execution_result.get('reason')}")
                        raise e
                    elif action == "resources_escalated":
                        # Retry with escalated resources
                        logger.info(f"Retrying with escalated resources")
                        raise self.retry(exc=e, countdown=60)
                    else:
                        # Default retry
                        raise self.retry(exc=e, countdown=60)
                else:
                    # Decision engine failed, fall back to simple retry
                    raise self.retry(exc=e, countdown=60)
        
        def sync_wrapper(self, *args, **kwargs):
            # Run async wrapper in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(async_wrapper(self, *args, **kwargs))
            finally:
                loop.close()
        
        return sync_wrapper
    return decorator
