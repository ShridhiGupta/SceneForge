from celery import chain, group
from app.celery_app import celery_app
from app.tasks.image_tasks import generate_scene_images
from app.tasks.clip_tasks import generate_video_clips
from app.tasks.render_tasks import render_final_video
from app.core.database import SessionLocal
from app.models.video import Video, VideoStatus

@celery_app.task(bind=True, max_retries=3)
def process_video_workflow(self, video_id: int):
    """
    Main workflow task that orchestrates the entire video generation process
    """
    db = SessionLocal()
    try:
        # Update video status to processing
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise Exception(f"Video {video_id} not found")
        
        video.status = VideoStatus.PROCESSING
        db.commit()
        
        # Create the workflow chain
        workflow = chain(
            generate_scene_images.s(video_id),
            generate_video_clips.s(video_id),
            render_final_video.s(video_id)
        )
        
        # Execute the workflow
        workflow.apply_async()
        
    except Exception as exc:
        # Update video status to failed
        video.status = VideoStatus.FAILED
        video.error_message = str(exc)
        db.commit()
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()

@celery_app.task
def update_video_progress(video_id: int, progress: float):
    """
    Update video progress
    """
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.progress = min(100.0, progress)
            db.commit()
    finally:
        db.close()
