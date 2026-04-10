from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, JSON, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class RecoveryAction(enum.Enum):
    RETRY = "retry"
    MODIFY_PROMPT = "modify_prompt"
    SWITCH_MODEL = "switch_model"
    ADJUST_PARAMETERS = "adjust_parameters"
    SKIP_TASK = "skip_task"
    ESCALATE_RESOURCES = "escalate_resources"


class FailureType(enum.Enum):
    TIMEOUT = "timeout"
    API_ERROR = "api_error"
    LOW_QUALITY = "low_quality"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    UNKNOWN = "unknown"


class PipelineStage(enum.Enum):
    SCENE = "scene"
    IMAGE = "image"
    CLIP = "clip"
    RENDER = "render"


class FailureMemoryDB(Base):
    """Database model for failure memory"""
    __tablename__ = "failure_memories"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Core failure information
    failure_type = Column(Enum(FailureType), nullable=False, index=True)
    stage = Column(Enum(PipelineStage), nullable=False, index=True)
    error_logs = Column(Text, nullable=False)
    prompt_used = Column(Text, nullable=False)
    model_used = Column(String, nullable=False, index=True)
    
    # Decision and outcome
    action_taken = Column(Enum(RecoveryAction), nullable=False, index=True)
    new_prompt = Column(Text, nullable=True)
    new_model = Column(String, nullable=True)
    parameter_changes = Column(JSON, nullable=True)
    
    # Results
    success = Column(Boolean, nullable=False, index=True)
    final_quality_score = Column(Float, nullable=True)
    total_cost = Column(Float, default=0.0)
    retry_count = Column(Integer, default=0)
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    task_id = Column(String, nullable=True, index=True)
    video_id = Column(Integer, nullable=True, index=True)
    scene_id = Column(Integer, nullable=True, index=True)
    
    # Vector database reference
    embedding_id = Column(String, nullable=True, unique=True, index=True)
    similarity_threshold = Column(Float, default=0.7)
    
    # Search optimization fields
    error_summary = Column(String, nullable=True, index=True)  # First 100 chars of error
    prompt_summary = Column(String, nullable=True, index=True)  # First 100 chars of prompt


class MemoryEmbedding(Base):
    """Model for storing embeddings metadata"""
    __tablename__ = "memory_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    memory_id = Column(Integer, ForeignKey("failure_memories.id"), nullable=False)
    embedding_id = Column(String, nullable=False, unique=True, index=True)
    embedding_model = Column(String, nullable=False, default="text-embedding-ada-002")
    embedding_dimension = Column(Integer, default=1536)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    memory = relationship("FailureMemoryDB", backref="embeddings")


class MemoryStats(Base):
    """Model for caching memory statistics"""
    __tablename__ = "memory_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    stat_type = Column(String, nullable=False, index=True)  # daily, weekly, monthly
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)
    
    # Statistics
    total_memories = Column(Integer, default=0)
    successful_recoveries = Column(Integer, default=0)
    failed_recoveries = Column(Integer, default=0)
    
    # Breakdown by dimensions
    memories_by_stage = Column(JSON, nullable=True)
    memories_by_failure_type = Column(JSON, nullable=True)
    success_rate_by_action = Column(JSON, nullable=True)
    
    # Performance metrics
    avg_similarity_score = Column(Float, default=0.0)
    avg_recovery_time = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
