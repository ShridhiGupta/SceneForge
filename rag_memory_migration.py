"""
Database migration script for RAG memory system
Run this to add the new tables for failure memory storage
"""

from sqlalchemy import create_engine, text
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def migrate_rag_memory():
    """
    Add RAG memory tables to existing database
    """
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Create failure_memories table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS failure_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                failure_type VARCHAR(20) NOT NULL,
                stage VARCHAR(10) NOT NULL,
                error_logs TEXT NOT NULL,
                prompt_used TEXT NOT NULL,
                model_used VARCHAR(100) NOT NULL,
                action_taken VARCHAR(20) NOT NULL,
                new_prompt TEXT,
                new_model VARCHAR(100),
                parameter_changes JSON,
                success BOOLEAN NOT NULL,
                final_quality_score REAL,
                total_cost REAL DEFAULT 0.0,
                retry_count INTEGER DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                task_id VARCHAR(100),
                video_id INTEGER,
                scene_id INTEGER,
                embedding_id VARCHAR(100) UNIQUE,
                similarity_threshold REAL DEFAULT 0.7,
                error_summary VARCHAR(100),
                prompt_summary VARCHAR(100)
            )
        """))
        
        # Create indexes for performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_failure_memories_type ON failure_memories(failure_type)",
            "CREATE INDEX IF NOT EXISTS idx_failure_memories_stage ON failure_memories(stage)",
            "CREATE INDEX IF NOT EXISTS idx_failure_memories_model ON failure_memories(model_used)",
            "CREATE INDEX IF NOT EXISTS idx_failure_memories_action ON failure_memories(action_taken)",
            "CREATE INDEX IF NOT EXISTS idx_failure_memories_success ON failure_memories(success)",
            "CREATE INDEX IF NOT EXISTS idx_failure_memories_timestamp ON failure_memories(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_failure_memories_task_id ON failure_memories(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_failure_memories_embedding_id ON failure_memories(embedding_id)",
            "CREATE INDEX IF NOT EXISTS idx_failure_memories_error_summary ON failure_memories(error_summary)",
            "CREATE INDEX IF NOT EXISTS idx_failure_memories_prompt_summary ON failure_memories(prompt_summary)"
        ]
        
        for index_sql in indexes:
            try:
                conn.execute(text(index_sql))
                logger.info(f"Created index: {index_sql}")
            except Exception as e:
                logger.warning(f"Index creation failed (may already exist): {e}")
        
        # Create memory_embeddings table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS memory_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id INTEGER NOT NULL,
                embedding_id VARCHAR(100) NOT NULL UNIQUE,
                embedding_model VARCHAR(100) DEFAULT 'text-embedding-ada-002',
                embedding_dimension INTEGER DEFAULT 1536,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (memory_id) REFERENCES failure_memories (id)
            )
        """))
        
        # Create memory_stats table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS memory_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stat_type VARCHAR(20) NOT NULL,
                period_start DATETIME NOT NULL,
                period_end DATETIME NOT NULL,
                total_memories INTEGER DEFAULT 0,
                successful_recoveries INTEGER DEFAULT 0,
                failed_recoveries INTEGER DEFAULT 0,
                memories_by_stage JSON,
                memories_by_failure_type JSON,
                success_rate_by_action JSON,
                avg_similarity_score REAL DEFAULT 0.0,
                avg_recovery_time REAL DEFAULT 0.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create indexes for stats table
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_stats_type ON memory_stats(stat_type)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_stats_period ON memory_stats(period_start, period_end)"))
        
        conn.commit()
    
    logger.info("RAG memory migration completed successfully")

def create_sample_data():
    """
    Create sample failure memory data for testing
    """
    from app.services.rag_memory import rag_memory_service
    from app.schemas.rag_memory import FailureMemory, FailureType, RecoveryAction, PipelineStage
    from datetime import datetime, timedelta
    import asyncio
    
    sample_memories = [
        FailureMemory(
            failure_type=FailureType.TIMEOUT,
            stage=PipelineStage.IMAGE,
            error_logs="API timeout after 30 seconds while generating image",
            prompt_used="A beautiful sunset",
            model_used="stable-diffusion-xl",
            action_taken=RecoveryAction.RETRY,
            success=True,
            final_quality_score=0.8,
            total_cost=0.05,
            retry_count=1,
            timestamp=datetime.utcnow() - timedelta(days=1)
        ),
        FailureMemory(
            failure_type=FailureType.API_ERROR,
            stage=PipelineStage.IMAGE,
            error_logs="HTTP 503 Service Unavailable from image generation API",
            prompt_used="A car driving on a highway",
            model_used="dall-e-3",
            action_taken=RecoveryAction.SWITCH_MODEL,
            new_model="dall-e-2",
            success=True,
            final_quality_score=0.7,
            total_cost=0.08,
            retry_count=2,
            timestamp=datetime.utcnow() - timedelta(hours=12)
        ),
        FailureMemory(
            failure_type=FailureType.LOW_QUALITY,
            stage=PipelineStage.IMAGE,
            error_logs="Generated image quality score 0.2 below threshold 0.5",
            prompt_used="A person",
            model_used="stable-diffusion-xl",
            action_taken=RecoveryAction.MODIFY_PROMPT,
            new_prompt="A person, high quality, detailed, professional, 4K resolution",
            success=True,
            final_quality_score=0.9,
            total_cost=0.06,
            retry_count=1,
            timestamp=datetime.utcnow() - timedelta(hours=6)
        ),
        FailureMemory(
            failure_type=FailureType.RESOURCE_EXHAUSTION,
            stage=PipelineStage.IMAGE,
            error_logs="GPU memory exhausted during image generation",
            prompt_used="A complex landscape with many details",
            model_used="stable-diffusion-xl",
            action_taken=RecoveryAction.ESCALATE_RESOURCES,
            parameter_changes={"memory": "8GB", "batch_size": 1},
            success=True,
            final_quality_score=0.85,
            total_cost=0.07,
            retry_count=1,
            timestamp=datetime.utcnow() - timedelta(hours=3)
        ),
        FailureMemory(
            failure_type=FailureType.TIMEOUT,
            stage=PipelineStage.CLIP,
            error_logs="Video rendering timeout after 120 seconds",
            prompt_used="Create video from images",
            model_used="ffmpeg",
            action_taken=RecoveryAction.ADJUST_PARAMETERS,
            parameter_changes={"timeout": 300, "quality": "medium"},
            success=False,
            final_quality_score=0.0,
            total_cost=0.10,
            retry_count=3,
            timestamp=datetime.utcnow() - timedelta(hours=1)
        )
    ]
    
    async def store_samples():
        for memory in sample_memories:
            memory_id = await rag_memory_service.store_failure_memory(memory)
            if memory_id:
                logger.info(f"Stored sample memory: {memory_id}")
            else:
                logger.warning("Failed to store sample memory")
    
    # Run the async function
    asyncio.run(store_samples())
    logger.info("Sample data creation completed")

if __name__ == "__main__":
    print("Running RAG memory migration...")
    migrate_rag_memory()
    
    print("Creating sample data...")
    create_sample_data()
    
    print("Migration completed successfully!")
