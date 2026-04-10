from celery import group
from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.video import Video, Scene, VideoStatus, TaskStatus
from app.services.image_service import ImageGenerationService
from app.services.quality_evaluation import quality_evaluator
from app.utils.task_utils import with_failure_handling, TaskFailureHandler
from app.schemas.decision_engine import PipelineStage
import os
import uuid
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3)
def generate_scene_images(self, video_id: int):
    """
    Generate images for all scenes in a video
    """
    db = SessionLocal()
    try:
        # Update video status
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise Exception(f"Video {video_id} not found")
        
        video.status = VideoStatus.GENERATING_IMAGES
        db.commit()
        
        # Get all scenes for the video
        scenes = db.query(Scene).filter(Scene.video_id == video_id).all()
        
        if not scenes:
            raise Exception(f"No scenes found for video {video_id}")
        
        # Create a group of image generation tasks
        image_tasks = []
        for scene in scenes:
            task = generate_single_image.s(scene.id)
            image_tasks.append(task)
        
        # Execute all image generation tasks in parallel
        job = group(image_tasks)
        result = job.apply_async()
        
        # Wait for all tasks to complete
        result.get()
        
        # Check if all images were generated successfully
        failed_scenes = db.query(Scene).filter(
            Scene.video_id == video_id,
            Scene.image_generation_status == TaskStatus.FAILED
        ).count()
        
        if failed_scenes > 0:
            raise Exception(f"{failed_scenes} scenes failed to generate images")
        
        return video_id
        
    except Exception as exc:
        # Update video status to failed
        video.status = VideoStatus.FAILED
        video.error_message = str(exc)
        db.commit()
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=5)
@with_failure_handling(PipelineStage.IMAGE)
def generate_single_image(self, scene_id: int):
    """
    Generate a single image for a scene
    """
    db = SessionLocal()
    try:
        scene = db.query(Scene).filter(Scene.id == scene_id).first()
        if not scene:
            raise Exception(f"Scene {scene_id} not found")
        
        # Update scene status
        scene.image_generation_status = TaskStatus.PROCESSING
        scene.image_generation_task_id = self.request.id
        scene.retry_count = self.request.retries
        db.commit()
        
        # Generate image using AI service
        image_service = ImageGenerationService()
        
        # Generate unique filename
        filename = f"scene_{scene.video_id}_{scene.scene_number}_{uuid.uuid4().hex[:8]}.png"
        image_path = os.path.join("uploads", "images", filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        
        # Generate the image with current context
        image_service.generate_image(
            prompt=scene.description,
            output_path=image_path,
            model_name="stable-diffusion-xl",  # This would come from config
            task_id=self.request.id
        )
        
        # Evaluate image quality
        quality_result = None
        try:
            quality_result = quality_evaluator.quick_evaluate(
                image_path=image_path,
                prompt=scene.description,
                threshold=0.5  # Configurable threshold
            )
            
            # Update scene with quality score
            scene.quality_score = quality_result.final_score
            
            logger.info(f"Image quality evaluation: {quality_result.final_score:.2f}")
            
            # Check if quality passes threshold
            if not quality_result.passes_threshold:
                # Trigger low quality failure
                quality_error = f"Image quality score {quality_result.final_score:.2f} below threshold 0.5"
                logger.warning(quality_error)
                
                # Update scene status to failed
                scene.image_generation_status = TaskStatus.FAILED
                scene.error_message = quality_error
                db.commit()
                
                # Raise exception to trigger decision engine
                raise Exception(quality_error)
            
        except Exception as e:
            logger.warning(f"Quality evaluation failed: {e}")
            scene.quality_score = 0.0
            
            # If this is a quality failure, re-raise to trigger decision engine
            if "quality score" in str(e).lower():
                raise e
        
        # Update scene with image path
        scene.image_path = image_path
        scene.image_generation_status = TaskStatus.COMPLETED
        db.commit()
        
        return scene_id
        
    finally:
        db.close()
