"""
Database migration script for quality evaluation system
Run this to add the quality_score field to existing scenes table
"""

from sqlalchemy import create_engine, text
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def migrate_quality_evaluation():
    """
    Add quality evaluation fields to existing database
    """
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Check if quality_score column exists
        result = conn.execute(text("PRAGMA table_info(scenes)")).fetchall()
        existing_columns = [col[1] for col in result]
        
        # Add quality_score column if it doesn't exist
        if "quality_score" not in existing_columns:
            try:
                conn.execute(text("ALTER TABLE scenes ADD COLUMN quality_score REAL DEFAULT 0.0"))
                logger.info("Added quality_score column to scenes table")
            except Exception as e:
                logger.error(f"Failed to add quality_score column: {e}")
        else:
            logger.info("quality_score column already exists")
        
        conn.commit()
    
    logger.info("Quality evaluation migration completed successfully")

if __name__ == "__main__":
    migrate_quality_evaluation()
