from celery import group
from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.video import Video, Scene, Clip, VideoStatus, TaskStatus
from app.services.clip_service_mock import ClipGenerationService
import os
import uuid

@celery_app.task(bind=True, max_retries=3)
def generate_video_clips(self, video_id: int):
    """
    Generate video clips from scene images
    """
    db = SessionLocal()
    try:
        # Update video status
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise Exception(f"Video {video_id} not found")
        
        video.status = VideoStatus.GENERATING_CLIPS
        db.commit()
        
        # Get all scenes with completed images
        scenes = db.query(Scene).filter(
            Scene.video_id == video_id,
            Scene.image_generation_status == TaskStatus.COMPLETED
        ).all()
        
        if not scenes:
            raise Exception(f"No completed scenes found for video {video_id}")
        
        # Create a group of clip generation tasks
        clip_tasks = []
        for scene in scenes:
            task = generate_single_clip.s(scene.id)
            clip_tasks.append(task)
        
        # Execute all clip generation tasks in parallel
        job = group(clip_tasks)
        result = job.apply_async()
        
        # Wait for all tasks to complete
        result.get()
        
        # Check if all clips were generated successfully
        failed_clips = db.query(Clip).filter(
            Clip.video_id == video_id,
            Clip.generation_status == TaskStatus.FAILED
        ).count()
        
        if failed_clips > 0:
            raise Exception(f"{failed_clips} clips failed to generate")
        
        return video_id
        
    except Exception as exc:
        # Update video status to failed
        video.status = VideoStatus.FAILED
        video.error_message = str(exc)
        db.commit()
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=3)
def generate_single_clip(self, scene_id: int):
    """
    Generate a single video clip from a scene image
    """
    db = SessionLocal()
    try:
        scene = db.query(Scene).filter(Scene.id == scene_id).first()
        if not scene:
            raise Exception(f"Scene {scene_id} not found")
        
        if not scene.image_path:
            raise Exception(f"No image found for scene {scene_id}")
        
        # Create clip record
        clip = Clip(
            video_id=scene.video_id,
            scene_id=scene.id,
            duration=scene.duration,
            generation_status=TaskStatus.PROCESSING,
            generation_task_id=self.request.id
        )
        db.add(clip)
        db.commit()
        db.refresh(clip)
        
        # Generate clip using video service
        clip_service = ClipGenerationService()
        
        # Generate unique filename
        filename = f"clip_{scene.video_id}_{scene.scene_number}_{uuid.uuid4().hex[:8]}.mp4"
        clip_path = os.path.join("uploads", "clips", filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(clip_path), exist_ok=True)
        
        # Generate the clip
        clip_service.generate_clip(
            image_path=scene.image_path,
            duration=scene.duration,
            output_path=clip_path
        )
        
        # Update clip with path
        clip.clip_path = clip_path
        clip.generation_status = TaskStatus.COMPLETED
        db.commit()
        
        return clip.id
        
    except Exception as exc:
        # Update clip status to failed
        clip.generation_status = TaskStatus.FAILED
        clip.error_message = str(exc)
        db.commit()
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()
