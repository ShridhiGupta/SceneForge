from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.video import Video, Clip, VideoStatus, TaskStatus
from app.services.render_service_mock import RenderService
import os
import uuid

@celery_app.task(bind=True, max_retries=3)
def render_final_video(self, video_id: int):
    """
    Render the final video by combining all clips
    """
    db = SessionLocal()
    try:
        # Update video status
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise Exception(f"Video {video_id} not found")
        
        video.status = VideoStatus.RENDERING
        db.commit()
        
        # Get all completed clips for the video
        clips = db.query(Clip).filter(
            Clip.video_id == video_id,
            Clip.generation_status == TaskStatus.COMPLETED
        ).order_by(Clip.scene_id).all()
        
        if not clips:
            raise Exception(f"No completed clips found for video {video_id}")
        
        # Generate final video path
        filename = f"final_video_{video_id}_{uuid.uuid4().hex[:8]}.mp4"
        final_video_path = os.path.join("uploads", "videos", filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(final_video_path), exist_ok=True)
        
        # Render final video
        render_service = RenderService()
        render_service.render_final_video(
            clip_paths=[clip.clip_path for clip in clips],
            output_path=final_video_path
        )
        
        # Update video with final path
        video.final_video_path = final_video_path
        video.status = VideoStatus.COMPLETED
        video.progress = 100.0
        from datetime import datetime
        video.completed_at = datetime.utcnow()
        db.commit()
        
        return video_id
        
    except Exception as exc:
        # Update video status to failed
        video.status = VideoStatus.FAILED
        video.error_message = str(exc)
        db.commit()
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()
