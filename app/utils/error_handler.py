import logging
from functools import wraps
from typing import Callable, Any
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import SessionLocal
from app.models.video import TaskLog, TaskStatus

logger = logging.getLogger(__name__)

def handle_task_errors(task_func: Callable) -> Callable:
    """
    Decorator for handling task errors and implementing retry logic
    """
    @wraps(task_func)
    def wrapper(*args, **kwargs):
        task_id = None
        task_type = task_func.__name__
        
        try:
            # Extract task_id from Celery task context if available
            if hasattr(args[0], 'request') and hasattr(args[0].request, 'id'):
                task_id = args[0].request.id
            
            # Log task start
            if task_id:
                log_task_start(task_id, task_type)
            
            # Execute the task
            result = task_func(*args, **kwargs)
            
            # Log task completion
            if task_id:
                log_task_completion(task_id, task_type)
            
            return result
            
        except Exception as e:
            # Log task failure
            if task_id:
                log_task_failure(task_id, task_type, str(e))
            
            logger.error(f"Task {task_type} failed: {str(e)}")
            raise
    
    return wrapper

def log_task_start(task_id: str, task_type: str):
    """
    Log the start of a task
    """
    db = SessionLocal()
    try:
        log_entry = TaskLog(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PROCESSING,
            started_at=datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log task start: {str(e)}")
    finally:
        db.close()

def log_task_completion(task_id: str, task_type: str):
    """
    Log the completion of a task
    """
    db = SessionLocal()
    try:
        log_entry = db.query(TaskLog).filter(TaskLog.task_id == task_id).first()
        if log_entry:
            log_entry.status = TaskStatus.COMPLETED
            log_entry.completed_at = datetime.utcnow()
            db.commit()
    except Exception as e:
        logger.error(f"Failed to log task completion: {str(e)}")
    finally:
        db.close()

def log_task_failure(task_id: str, task_type: str, error_message: str):
    """
    Log the failure of a task
    """
    db = SessionLocal()
    try:
        log_entry = db.query(TaskLog).filter(TaskLog.task_id == task_id).first()
        if log_entry:
            log_entry.status = TaskStatus.FAILED
            log_entry.error_message = error_message
            log_entry.completed_at = datetime.utcnow()
            log_entry.retry_count += 1
            db.commit()
        else:
            # Create new log entry if it doesn't exist
            log_entry = TaskLog(
                task_id=task_id,
                task_type=task_type,
                status=TaskStatus.FAILED,
                error_message=error_message,
                completed_at=datetime.utcnow(),
                retry_count=1
            )
            db.add(log_entry)
            db.commit()
    except Exception as e:
        logger.error(f"Failed to log task failure: {str(e)}")
    finally:
        db.close()

class RetryableException(Exception):
    """
    Exception that can be retried
    """
    def __init__(self, message: str, max_retries: int = 3):
        super().__init__(message)
        self.max_retries = max_retries

class NonRetryableException(Exception):
    """
    Exception that should not be retried
    """
    pass
