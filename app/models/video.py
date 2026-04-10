from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class VideoStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    GENERATING_IMAGES = "generating_images"
    GENERATING_CLIPS = "generating_clips"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"

class Video(Base):
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    script = Column(Text, nullable=False)
    status = Column(Enum(VideoStatus), default=VideoStatus.PENDING)
    progress = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    scenes = relationship("Scene", back_populates="video", cascade="all, delete-orphan")
    clips = relationship("Clip", back_populates="video", cascade="all, delete-orphan")
    final_video_path = Column(String, nullable=True)

class Scene(Base):
    __tablename__ = "scenes"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    scene_number = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    duration = Column(Float, nullable=False)  # in seconds
    image_path = Column(String, nullable=True)
    image_generation_status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    image_generation_task_id = Column(String, nullable=True)
    retry_count = Column(Integer, default=0)
    generation_cost = Column(Float, default=0.0)
    model_used = Column(String, nullable=True)
    quality_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    video = relationship("Video", back_populates="scenes")
    clips = relationship("Clip", back_populates="scene")

class Clip(Base):
    __tablename__ = "clips"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    scene_id = Column(Integer, ForeignKey("scenes.id"), nullable=False)
    clip_path = Column(String, nullable=True)
    duration = Column(Float, nullable=False)
    generation_status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    generation_task_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    video = relationship("Video", back_populates="clips")
    scene = relationship("Scene", back_populates="clips")

class TaskLog(Base):
    __tablename__ = "task_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, nullable=False, index=True)
    task_type = Column(String, nullable=False)  # image_generation, clip_generation, rendering
    status = Column(Enum(TaskStatus), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    task_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
