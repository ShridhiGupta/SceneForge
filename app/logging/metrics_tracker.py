import time
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from app.logging.structured_logger import metrics_logger


@dataclass
class TaskMetrics:
    """Metrics for individual task execution"""
    task_id: str
    task_name: str
    start_time: float
    end_time: Optional[float] = None
    execution_time_ms: Optional[float] = None
    success: bool = False
    failure_type: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    cost: float = 0.0
    quality_before: Optional[float] = None
    quality_after: Optional[float] = None
    action_taken: Optional[str] = None
    model_used: Optional[str] = None
    video_id: Optional[int] = None
    scene_id: Optional[int] = None


@dataclass
class DecisionMetrics:
    """Metrics for decision making"""
    decision_id: str
    task_id: str
    decision_type: str
    action: str
    confidence: float
    reasoning: Optional[str] = None
    rag_context_used: bool = False
    similar_failures_found: int = 0
    cost_impact: float = 0.0
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class QualityMetrics:
    """Metrics for quality evaluation"""
    evaluation_id: str
    task_id: str
    clip_score: Optional[float] = None
    llm_score: Optional[float] = None
    combined_score: float = 0.0
    quality_level: str = "unknown"
    passes_threshold: bool = False
    threshold_used: float = 0.5
    evaluation_time_ms: float = 0.0
    model_used: Optional[str] = None


class MetricsTracker:
    """Production metrics tracking system"""
    
    def __init__(self):
        self.active_tasks: Dict[str, TaskMetrics] = {}
        self.completed_tasks: List[TaskMetrics] = []
        self.decisions: List[DecisionMetrics] = []
        self.quality_evaluations: List[QualityMetrics] = []
        
        # Aggregate metrics
        self.total_cost = 0.0
        self.total_execution_time = 0.0
        self.failure_counts: Dict[str, int] = {}
        self.action_counts: Dict[str, int] = {}
        self.quality_improvements: List[float] = []
    
    def start_task(self, task_name: str, video_id: Optional[int] = None, 
                   scene_id: Optional[int] = None, **kwargs) -> str:
        """Start tracking a new task"""
        task_id = str(uuid.uuid4())
        task_metrics = TaskMetrics(
            task_id=task_id,
            task_name=task_name,
            start_time=time.time(),
            video_id=video_id,
            scene_id=scene_id,
            **kwargs
        )
        
        self.active_tasks[task_id] = task_metrics
        
        # Log task start
        metrics_logger.log_task_start(
            task_name=task_name,
            task_id=task_id,
            video_id=video_id,
            scene_id=scene_id
        )
        
        return task_id
    
    def complete_task(self, task_id: str, success: bool, cost: float = 0.0,
                     quality_before: Optional[float] = None, 
                     quality_after: Optional[float] = None,
                     action_taken: Optional[str] = None, **kwargs):
        """Complete task tracking"""
        if task_id not in self.active_tasks:
            return
        
        task = self.active_tasks.pop(task_id)
        task.end_time = time.time()
        task.execution_time_ms = (task.end_time - task.start_time) * 1000
        task.success = success
        task.cost = cost
        task.quality_before = quality_before
        task.quality_after = quality_after
        task.action_taken = action_taken
        
        # Update task with additional data
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        self.completed_tasks.append(task)
        
        # Update aggregates
        self.total_cost += cost
        self.total_execution_time += task.execution_time_ms
        
        # Track quality improvements
        if quality_before is not None and quality_after is not None:
            improvement = quality_after - quality_before
            self.quality_improvements.append(improvement)
        
        # Log task completion
        if success:
            metrics_logger.log_task_success(
                task_name=task.task_name,
                execution_time_ms=task.execution_time_ms,
                cost=cost,
                quality_before=quality_before,
                quality_after=quality_after,
                action_taken=action_taken,
                task_id=task_id
            )
        else:
            metrics_logger.log_task_failure(
                task_name=task.task_name,
                error=task.error_message or "Unknown error",
                execution_time_ms=task.execution_time_ms,
                cost=cost,
                failure_type=task.failure_type,
                task_id=task_id
            )
    
    def log_failure(self, task_id: str, failure_type: str, error_message: str, **kwargs):
        """Log task failure"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.failure_type = failure_type
            task.error_message = error_message
            
            # Update failure counts
            self.failure_counts[failure_type] = self.failure_counts.get(failure_type, 0) + 1
            
            # Update task with additional data
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
    
    def log_retry(self, task_id: str, retry_count: int, original_error: str, **kwargs):
        """Log retry attempt"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.retry_count = retry_count
            
            # Log retry
            metrics_logger.log_retry(
                task_name=task.task_name,
                retry_count=retry_count,
                original_error=original_error,
                task_id=task_id
            )
    
    def log_decision(self, task_id: str, decision_type: str, action: str, 
                    confidence: float, reasoning: Optional[str] = None,
                    rag_context_used: bool = False, similar_failures_found: int = 0,
                    cost_impact: float = 0.0, **kwargs):
        """Log decision making"""
        decision = DecisionMetrics(
            decision_id=str(uuid.uuid4()),
            task_id=task_id,
            decision_type=decision_type,
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            rag_context_used=rag_context_used,
            similar_failures_found=similar_failures_found,
            cost_impact=cost_impact
        )
        
        self.decisions.append(decision)
        
        # Update action counts
        self.action_counts[action] = self.action_counts.get(action, 0) + 1
        
        # Log decision
        metrics_logger.log_decision(
            decision_type=decision_type,
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            rag_context_used=rag_context_used,
            similar_failures_found=similar_failures_found,
            cost_impact=cost_impact,
            task_id=task_id
        )
    
    def log_quality_evaluation(self, task_id: str, clip_score: Optional[float] = None,
                             llm_score: Optional[float] = None, combined_score: float = 0.0,
                             quality_level: str = "unknown", passes_threshold: bool = False,
                             threshold_used: float = 0.5, evaluation_time_ms: float = 0.0,
                             model_used: Optional[str] = None):
        """Log quality evaluation"""
        quality = QualityMetrics(
            evaluation_id=str(uuid.uuid4()),
            task_id=task_id,
            clip_score=clip_score,
            llm_score=llm_score,
            combined_score=combined_score,
            quality_level=quality_level,
            passes_threshold=passes_threshold,
            threshold_used=threshold_used,
            evaluation_time_ms=evaluation_time_ms,
            model_used=model_used
        )
        
        self.quality_evaluations.append(quality)
    
    def get_task_metrics(self, task_id: str) -> Optional[TaskMetrics]:
        """Get metrics for specific task"""
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]
        
        for task in self.completed_tasks:
            if task.task_id == task_id:
                return task
        
        return None
    
    def get_aggregate_metrics(self) -> Dict[str, Any]:
        """Get aggregate metrics for analysis"""
        if not self.completed_tasks:
            return {}
        
        successful_tasks = [t for t in self.completed_tasks if t.success]
        failed_tasks = [t for t in self.completed_tasks if not t.success]
        
        # Calculate averages
        avg_execution_time = sum(t.execution_time_ms or 0 for t in self.completed_tasks) / len(self.completed_tasks)
        avg_cost_per_task = sum(t.cost for t in self.completed_tasks) / len(self.completed_tasks)
        
        # Quality metrics
        quality_scores = [t.quality_after for t in self.completed_tasks if t.quality_after is not None]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Improvement metrics
        avg_improvement = sum(self.quality_improvements) / len(self.quality_improvements) if self.quality_improvements else 0
        
        # Failure analysis
        failure_rate = len(failed_tasks) / len(self.completed_tasks) if self.completed_tasks else 0
        
        # Cost analysis
        total_cost = sum(t.cost for t in self.completed_tasks)
        
        return {
            "total_tasks": len(self.completed_tasks),
            "successful_tasks": len(successful_tasks),
            "failed_tasks": len(failed_tasks),
            "failure_rate": failure_rate,
            "average_execution_time_ms": avg_execution_time,
            "average_cost_per_task": avg_cost_per_task,
            "total_cost": total_cost,
            "average_quality_score": avg_quality,
            "average_quality_improvement": avg_improvement,
            "failure_counts": self.failure_counts,
            "action_counts": self.action_counts,
            "total_decisions": len(self.decisions),
            "total_quality_evaluations": len(self.quality_evaluations)
        }
    
    def get_improvement_metrics(self) -> Dict[str, Any]:
        """Calculate improvement metrics to prove system effectiveness"""
        if not self.completed_tasks:
            return {}
        
        # Compare tasks with and without decision engine
        tasks_with_decisions = [t for t in self.completed_tasks 
                               if any(d.task_id == t.task_id for d in self.decisions)]
        tasks_without_decisions = [t for t in self.completed_tasks 
                                  if not any(d.task_id == t.task_id for d in self.decisions)]
        
        # Quality improvements
        with_decision_improvements = [t.quality_after - t.quality_before 
                                     for t in tasks_with_decisions 
                                     if t.quality_before is not None and t.quality_after is not None]
        without_decision_improvements = [t.quality_after - t.quality_before 
                                       for t in tasks_without_decisions 
                                       if t.quality_before is not None and t.quality_after is not None]
        
        # Success rates
        with_decision_success_rate = len([t for t in tasks_with_decisions if t.success]) / len(tasks_with_decisions) if tasks_with_decisions else 0
        without_decision_success_rate = len([t for t in tasks_without_decisions if t.success]) / len(tasks_without_decisions) if tasks_without_decisions else 0
        
        # Cost efficiency
        with_decision_avg_cost = sum(t.cost for t in tasks_with_decisions) / len(tasks_with_decisions) if tasks_with_decisions else 0
        without_decision_avg_cost = sum(t.cost for t in tasks_without_decisions) / len(tasks_without_decisions) if tasks_without_decisions else 0
        
        # Retry effectiveness
        tasks_with_retries = [t for t in self.completed_tasks if t.retry_count > 0]
        retry_success_rate = len([t for t in tasks_with_retries if t.success]) / len(tasks_with_retries) if tasks_with_retries else 0
        
        return {
            "quality_improvement": {
                "with_decision_engine": {
                    "average_improvement": sum(with_decision_improvements) / len(with_decision_improvements) if with_decision_improvements else 0,
                    "sample_size": len(with_decision_improvements)
                },
                "without_decision_engine": {
                    "average_improvement": sum(without_decision_improvements) / len(without_decision_improvements) if without_decision_improvements else 0,
                    "sample_size": len(without_decision_improvements)
                },
                "improvement_difference": (sum(with_decision_improvements) / len(with_decision_improvements) if with_decision_improvements else 0) - 
                                        (sum(without_decision_improvements) / len(without_decision_improvements) if without_decision_improvements else 0)
            },
            "success_rate": {
                "with_decision_engine": with_decision_success_rate,
                "without_decision_engine": without_decision_success_rate,
                "improvement": with_decision_success_rate - without_decision_success_rate
            },
            "cost_efficiency": {
                "with_decision_engine": with_decision_avg_cost,
                "without_decision_engine": without_decision_avg_cost,
                "cost_reduction": without_decision_avg_cost - with_decision_avg_cost
            },
            "retry_effectiveness": {
                "retry_success_rate": retry_success_rate,
                "tasks_with_retries": len(tasks_with_retries),
                "average_retries": sum(t.retry_count for t in tasks_with_retries) / len(tasks_with_retries) if tasks_with_retries else 0
            },
            "decision_effectiveness": {
                "total_decisions": len(self.decisions),
                "average_confidence": sum(d.confidence for d in self.decisions) / len(self.decisions) if self.decisions else 0,
                "rag_usage_rate": len([d for d in self.decisions if d.rag_context_used]) / len(self.decisions) if self.decisions else 0,
                "average_similar_failures_found": sum(d.similar_failures_found for d in self.decisions) / len(self.decisions) if self.decisions else 0
            }
        }
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics for analysis"""
        return {
            "aggregate_metrics": self.get_aggregate_metrics(),
            "improvement_metrics": self.get_improvement_metrics(),
            "completed_tasks": [asdict(task) for task in self.completed_tasks],
            "decisions": [asdict(decision) for decision in self.decisions],
            "quality_evaluations": [asdict(quality) for quality in self.quality_evaluations]
        }


# Global metrics tracker instance
metrics_tracker = MetricsTracker()
