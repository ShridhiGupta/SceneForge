from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.video import Video, Scene, Clip, VideoStatus
from app.schemas.video import VideoCreate, VideoResponse, VideoDetailResponse
from app.tasks.video_tasks import process_video_workflow
import json

router = APIRouter()

@router.post("/", response_model=VideoResponse)
async def create_video(
    video_data: VideoCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Create video record
    db_video = Video(
        title=video_data.title,
        script=video_data.script,
        status=VideoStatus.PENDING
    )
    db.add(db_video)
    db.commit()
    db.refresh(db_video)
    
    # Parse script into scenes (simple implementation - you can enhance this)
    scenes = parse_script_to_scenes(video_data.script)
    
    # Create scene records
    for i, scene_data in enumerate(scenes):
        db_scene = Scene(
            video_id=db_video.id,
            scene_number=i + 1,
            description=scene_data["description"],
            duration=scene_data["duration"]
        )
        db.add(db_scene)
    
    db.commit()
    
    # Enqueue video processing workflow
    background_tasks.add_task(process_video_workflow.delay, db_video.id)
    
    return db_video

@router.get("/", response_model=List[VideoResponse])
async def get_videos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    videos = db.query(Video).offset(skip).limit(limit).all()
    return videos

@router.get("/{video_id}", response_model=VideoDetailResponse)
async def get_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return video

@router.delete("/{video_id}")
async def delete_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    db.delete(video)
    db.commit()
    return {"message": "Video deleted successfully"}

def parse_script_to_scenes(script: str) -> List[dict]:
    """
    Simple script parser - splits script into scenes.
    In a real implementation, you might use AI to parse this more intelligently.
    """
    scenes = []
    paragraphs = script.split('\n\n')
    
    for i, paragraph in enumerate(paragraphs):
        if paragraph.strip():
            scenes.append({
                "description": paragraph.strip(),
                "duration": 5.0  # Default 5 seconds per scene
            })
    
    return scenes
