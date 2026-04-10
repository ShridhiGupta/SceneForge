"""
Database migration script for decision engine integration
Run this to add the new fields to your existing database
"""

from sqlalchemy import create_engine, text
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def migrate_database():
    """
    Add decision engine fields to existing database
    """
    engine = create_engine(settings.database_url)
    
    migrations = [
        # Add retry_count to scenes table
        "ALTER TABLE scenes ADD COLUMN retry_count INTEGER DEFAULT 0",
        
        # Add generation_cost to scenes table  
        "ALTER TABLE scenes ADD COLUMN generation_cost FLOAT DEFAULT 0.0",
        
        # Add model_used to scenes table
        "ALTER TABLE scenes ADD COLUMN model_used VARCHAR(100)",
        
        # Add SKIPPED to task_status enum (SQLite doesn't support ALTER ENUM, so we handle it differently)
        # For SQLite, we need to recreate the table
    ]
    
    with engine.connect() as conn:
        # Check if columns already exist
        existing_columns = conn.execute(text("PRAGMA table_info(scenes)")).fetchall()
        column_names = [col[1] for col in existing_columns]
        
        # Add missing columns
        if "retry_count" not in column_names:
            try:
                conn.execute(text("ALTER TABLE scenes ADD COLUMN retry_count INTEGER DEFAULT 0"))
                logger.info("Added retry_count column to scenes")
            except Exception as e:
                logger.error(f"Failed to add retry_count: {e}")
        
        if "generation_cost" not in column_names:
            try:
                conn.execute(text("ALTER TABLE scenes ADD COLUMN generation_cost FLOAT DEFAULT 0.0"))
                logger.info("Added generation_cost column to scenes")
            except Exception as e:
                logger.error(f"Failed to add generation_cost: {e}")
        
        if "model_used" not in column_names:
            try:
                conn.execute(text("ALTER TABLE scenes ADD COLUMN model_used VARCHAR(100)"))
                logger.info("Added model_used column to scenes")
            except Exception as e:
                logger.error(f"Failed to add model_used: {e}")
        
        conn.commit()
    
    logger.info("Migration completed successfully")

if __name__ == "__main__":
    migrate_database()
