import json
import time
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import contextmanager
import traceback


class StructuredLogger:
    """JSON structured logger for production metrics tracking"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Create JSON formatter
        formatter = JsonFormatter()
        
        # Create handler
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_task_start(self, task_name: str, **kwargs):
        """Log task start with timestamp and context"""
        self._log("task_start", task_name=task_name, **kwargs)
    
    def log_task_success(self, task_name: str, execution_time_ms: float, **kwargs):
        """Log successful task completion"""
        self._log("task_success", task_name=task_name, execution_time_ms=execution_time_ms, **kwargs)
    
    def log_task_failure(self, task_name: str, error: str, execution_time_ms: float, **kwargs):
        """Log task failure with error details"""
        self._log("task_failure", task_name=task_name, error=error, execution_time_ms=execution_time_ms, **kwargs)
    
    def log_decision(self, decision_type: str, action: str, confidence: float, **kwargs):
        """Log decision making"""
        self._log("decision", decision_type=decision_type, action=action, confidence=confidence, **kwargs)
    
    def log_quality_metrics(self, quality_before: float, quality_after: float, **kwargs):
        """Log quality improvement metrics"""
        improvement = quality_after - quality_before
        self._log("quality_metrics", 
                quality_before=quality_before, 
                quality_after=quality_after, 
                improvement=improvement, 
                **kwargs)
    
    def log_cost_metrics(self, cost: float, task_name: str, **kwargs):
        """Log cost metrics"""
        self._log("cost_metrics", cost=cost, task_name=task_name, **kwargs)
    
    def log_retry(self, task_name: str, retry_count: int, original_error: str, **kwargs):
        """Log retry attempt"""
        self._log("retry", task_name=task_name, retry_count=retry_count, original_error=original_error, **kwargs)
    
    def _log(self, event_type: str, **kwargs):
        """Internal logging method"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "request_id": str(uuid.uuid4()),
            **kwargs
        }
        self.logger.info(json.dumps(log_data))


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        try:
            log_data = json.loads(record.getMessage())
            return json.dumps(log_data, default=str)
        except:
            return record.getMessage()


# Global logger instances
pipeline_logger = StructuredLogger("pipeline")
metrics_logger = StructuredLogger("metrics")
decision_logger = StructuredLogger("decisions")
