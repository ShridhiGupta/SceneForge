from functools import wraps
from typing import Dict, Any, Optional
import time
from app.logging.metrics_tracker import metrics_tracker
from app.logging.structured_logger import pipeline_logger


def track_agent_metrics(agent_name: str):
    """Decorator to track agent execution metrics"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, state, *args, **kwargs):
            # Start tracking
            task_id = metrics_tracker.start_task(
                task_name=f"{agent_name}_execution",
                video_id=state.video_id,
                agent_name=agent_name,
                agent_status=getattr(self, 'status', 'unknown')
            )
            
            try:
                # Execute agent function
                start_time = time.time()
                result = await func(self, state, *args, **kwargs)
                execution_time = (time.time() - start_time) * 1000
                
                # Complete task tracking
                metrics_tracker.complete_task(
                    task_id=task_id,
                    success=True,
                    execution_time_ms=execution_time,
                    agent_name=agent_name
                )
                
                return result
                
            except Exception as e:
                # Log failure
                metrics_tracker.log_failure(
                    task_id=task_id,
                    failure_type="agent_error",
                    error_message=str(e)
                )
                
                metrics_tracker.complete_task(
                    task_id=task_id,
                    success=False,
                    error_message=str(e),
                    agent_name=agent_name
                )
                
                raise
                
        return wrapper
    return decorator


def track_image_generation_metrics():
    """Track image generation specific metrics"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, scene, *args, **kwargs):
            # Start tracking
            task_id = metrics_tracker.start_task(
                task_name="image_generation",
                video_id=scene.video_id,
                scene_id=scene.id,
                model_used=getattr(scene, 'model_used', None),
                prompt=getattr(scene, 'prompt', None)
            )
            
            try:
                # Execute image generation
                start_time = time.time()
                result = await func(self, scene, *args, **kwargs)
                execution_time = (time.time() - start_time) * 1000
                
                # Extract cost from result
                cost = getattr(result, 'cost', 0.0)
                model_used = getattr(result, 'model_used', None)
                
                # Complete task tracking
                metrics_tracker.complete_task(
                    task_id=task_id,
                    success=getattr(result, 'success', True),
                    cost=cost,
                    execution_time_ms=execution_time,
                    model_used=model_used,
                    scene_id=scene.id
                )
                
                return result
                
            except Exception as e:
                # Log failure
                metrics_tracker.log_failure(
                    task_id=task_id,
                    failure_type="generation_error",
                    error_message=str(e),
                    model_used=getattr(scene, 'model_used', None)
                )
                
                metrics_tracker.complete_task(
                    task_id=task_id,
                    success=False,
                    error_message=str(e),
                    model_used=getattr(scene, 'model_used', None)
                )
                
                raise
                
        return wrapper
    return decorator


def track_quality_metrics():
    """Track quality evaluation specific metrics"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, image_path, prompt, *args, **kwargs):
            # Start tracking
            task_id = metrics_tracker.start_task(
                task_name="quality_evaluation",
                image_path=image_path,
                prompt=prompt
            )
            
            try:
                # Execute quality evaluation
                start_time = time.time()
                result = await func(self, image_path, prompt, *args, **kwargs)
                execution_time = (time.time() - start_time) * 1000
                
                # Extract quality metrics
                quality_score = getattr(result, 'quality_score', 0.0)
                clip_score = getattr(result, 'clip_score', None)
                llm_score = getattr(result, 'llm_score', None)
                passes_threshold = getattr(result, 'passes_threshold', False)
                
                # Log quality evaluation
                metrics_tracker.log_quality_evaluation(
                    task_id=task_id,
                    clip_score=clip_score,
                    llm_score=llm_score,
                    combined_score=quality_score,
                    passes_threshold=passes_threshold,
                    evaluation_time_ms=execution_time
                )
                
                # Complete task tracking
                metrics_tracker.complete_task(
                    task_id=task_id,
                    success=True,
                    execution_time_ms=execution_time,
                    quality_after=quality_score
                )
                
                return result
                
            except Exception as e:
                # Log failure
                metrics_tracker.log_failure(
                    task_id=task_id,
                    failure_type="quality_evaluation_error",
                    error_message=str(e)
                )
                
                metrics_tracker.complete_task(
                    task_id=task_id,
                    success=False,
                    error_message=str(e)
                )
                
                raise
                
        return wrapper
    return decorator


def track_decision_metrics():
    """Track decision making specific metrics"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, failure_context, *args, **kwargs):
            # Start tracking
            task_id = metrics_tracker.start_task(
                task_name="decision_making",
                failure_type=getattr(failure_context, 'failure_type', 'unknown'),
                stage=getattr(failure_context, 'stage', 'unknown'),
                retry_count=getattr(failure_context, 'retry_count', 0)
            )
            
            try:
                # Execute decision making
                start_time = time.time()
                result = await func(self, failure_context, *args, **kwargs)
                execution_time = (time.time() - start_time) * 1000
                
                # Extract decision metrics
                action = getattr(result, 'action', 'unknown')
                confidence = getattr(result, 'confidence', 0.0)
                reasoning = getattr(result, 'reasoning', None)
                cost_impact = getattr(result, 'estimated_cost_impact', 0.0)
                
                # Check if RAG was used (simplified check)
                rag_context_used = 'similar_failures' in str(failure_context).lower()
                similar_failures_found = len(getattr(failure_context, 'similar_failures', []))
                
                # Log decision
                metrics_tracker.log_decision(
                    task_id=task_id,
                    decision_type="failure_recovery",
                    action=action.value if hasattr(action, 'value') else str(action),
                    confidence=confidence,
                    reasoning=reasoning,
                    rag_context_used=rag_context_used,
                    similar_failures_found=similar_failures_found,
                    cost_impact=cost_impact
                )
                
                # Complete task tracking
                metrics_tracker.complete_task(
                    task_id=task_id,
                    success=True,
                    execution_time_ms=execution_time,
                    action_taken=action.value if hasattr(action, 'value') else str(action)
                )
                
                return result
                
            except Exception as e:
                # Log failure
                metrics_tracker.log_failure(
                    task_id=task_id,
                    failure_type="decision_error",
                    error_message=str(e)
                )
                
                metrics_tracker.complete_task(
                    task_id=task_id,
                    success=False,
                    error_message=str(e)
                )
                
                raise
                
        return wrapper
    return decorator


def track_retry_metrics():
    """Track retry attempts"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Extract retry information
            retry_count = getattr(self, 'retry_count', 0)
            original_error = getattr(self, 'last_error', 'Unknown error')
            
            # Start tracking
            task_id = metrics_tracker.start_task(
                task_name="retry_attempt",
                retry_count=retry_count,
                original_error=original_error
            )
            
            try:
                # Execute retry
                start_time = time.time()
                result = await func(self, *args, **kwargs)
                execution_time = (time.time() - start_time) * 1000
                
                # Log retry
                metrics_tracker.log_retry(
                    task_id=task_id,
                    retry_count=retry_count,
                    original_error=original_error
                )
                
                # Complete task tracking
                metrics_tracker.complete_task(
                    task_id=task_id,
                    success=True,
                    execution_time_ms=execution_time
                )
                
                return result
                
            except Exception as e:
                # Log retry failure
                metrics_tracker.log_failure(
                    task_id=task_id,
                    failure_type="retry_failed",
                    error_message=str(e)
                )
                
                metrics_tracker.complete_task(
                    task_id=task_id,
                    success=False,
                    error_message=str(e)
                )
                
                raise
                
        return wrapper
    return decorator


def track_cost_optimization_metrics():
    """Track cost optimization specific metrics"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, state, *args, **kwargs):
            # Start tracking
            task_id = metrics_tracker.start_task(
                task_name="cost_optimization",
                total_cost=getattr(state, 'total_cost', 0.0),
                budget_limit=getattr(state, 'total_budget', None)
            )
            
            try:
                # Execute cost optimization
                start_time = time.time()
                result = await func(self, state, *args, **kwargs)
                execution_time = (time.time() - start_time) * 1000
                
                # Extract optimization metrics
                potential_savings = getattr(result, 'potential_savings', 0.0)
                recommendations = getattr(result, 'optimization_suggestions', [])
                
                # Complete task tracking
                metrics_tracker.complete_task(
                    task_id=task_id,
                    success=True,
                    execution_time_ms=execution_time,
                    cost=potential_savings,
                    action_taken=f"optimization_suggestions_{len(recommendations)}"
                )
                
                return result
                
            except Exception as e:
                # Log failure
                metrics_tracker.log_failure(
                    task_id=task_id,
                    failure_type="cost_optimization_error",
                    error_message=str(e)
                )
                
                metrics_tracker.complete_task(
                    task_id=task_id,
                    success=False,
                    error_message=str(e)
                )
                
                raise
                
        return wrapper
    return decorator


class MetricsContext:
    """Context manager for manual metrics tracking"""
    
    def __init__(self, task_name: str, **kwargs):
        self.task_name = task_name
        self.kwargs = kwargs
        self.task_id = None
        self.start_time = None
    
    def __enter__(self):
        self.task_id = metrics_tracker.start_task(self.task_name, **self.kwargs)
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        execution_time = (time.time() - self.start_time) * 1000
        
        if exc_type is None:
            metrics_tracker.complete_task(
                self.task_id,
                success=True,
                execution_time_ms=execution_time
            )
        else:
            metrics_tracker.log_failure(
                self.task_id,
                failure_type="context_error",
                error_message=str(exc_val)
            )
            
            metrics_tracker.complete_task(
                self.task_id,
                success=False,
                error_message=str(exc_val),
                execution_time_ms=execution_time
            )
    
    def log_quality_before_after(self, quality_before: float, quality_after: float):
        """Log quality improvement within context"""
        if self.task_id:
            metrics_tracker.complete_task(
                self.task_id,
                success=True,
                quality_before=quality_before,
                quality_after=quality_after
            )
    
    def log_cost(self, cost: float):
        """Log cost within context"""
        if self.task_id:
            task = metrics_tracker.get_task_metrics(self.task_id)
            if task:
                task.cost = cost
