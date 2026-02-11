from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class VideoStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    GENERATING_IMAGES = "generating_images"
    GENERATING_CLIPS = "generating_clips"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

class VideoCreate(BaseModel):
    title: str
    script: str

class VideoResponse(BaseModel):
    id: int
    title: str
    script: str
    status: VideoStatusEnum
    progress: float
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    final_video_path: Optional[str] = None
    
    class Config:
        from_attributes = True

class SceneCreate(BaseModel):
    scene_number: int
    description: str
    duration: float

class SceneResponse(BaseModel):
    id: int
    video_id: int
    scene_number: int
    description: str
    duration: float
    image_path: Optional[str] = None
    image_generation_status: TaskStatusEnum
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True

class ClipResponse(BaseModel):
    id: int
    video_id: int
    scene_id: int
    clip_path: Optional[str] = None
    duration: float
    generation_status: TaskStatusEnum
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True

class VideoDetailResponse(VideoResponse):
    scenes: List[SceneResponse] = []
    clips: List[ClipResponse] = []
