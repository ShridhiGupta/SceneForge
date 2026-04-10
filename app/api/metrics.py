from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from typing import Dict, Any, Optional, List
from app.logging.metrics_tracker import metrics_tracker
from app.logging.log_analyzer import LogAnalyzer
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/overview")
async def get_metrics_overview():
    """
    Get comprehensive metrics overview
    """
    try:
        aggregate_metrics = metrics_tracker.get_aggregate_metrics()
        improvement_metrics = metrics_tracker.get_improvement_metrics()
        
        return {
            "aggregate_metrics": aggregate_metrics,
            "improvement_metrics": improvement_metrics,
            "timestamp": metrics_tracker.completed_tasks[-1].end_time if metrics_tracker.completed_tasks else None
        }
        
    except Exception as e:
        logger.error(f"Failed to get metrics overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quality")
async def get_quality_metrics():
    """
    Get quality metrics and improvements
    """
    try:
        quality_evaluations = metrics_tracker.quality_evaluations
        
        if not quality_evaluations:
            return {"message": "No quality evaluations available"}
        
        # Calculate quality statistics
        quality_scores = [q.combined_score for q in quality_evaluations]
        clip_scores = [q.clip_score for q in quality_evaluations if q.clip_score is not None]
        llm_scores = [q.llm_score for q in quality_evaluations if q.llm_score is not None]
        
        # Quality improvements
        improvements = []
        for task in metrics_tracker.completed_tasks:
            if task.quality_before is not None and task.quality_after is not None:
                improvements.append(task.quality_after - task.quality_before)
        
        return {
            "total_evaluations": len(quality_evaluations),
            "average_quality_score": sum(quality_scores) / len(quality_scores),
            "average_clip_score": sum(clip_scores) / len(clip_scores) if clip_scores else 0,
            "average_llm_score": sum(llm_scores) / len(llm_scores) if llm_scores else 0,
            "quality_improvements": {
                "count": len(improvements),
                "average_improvement": sum(improvements) / len(improvements) if improvements else 0,
                "improvement_rate": len([i for i in improvements if i > 0]) / len(improvements) if improvements else 0,
                "best_improvement": max(improvements) if improvements else 0,
                "worst_improvement": min(improvements) if improvements else 0
            },
            "quality_distribution": {
                "very_high": len([q for q in quality_evaluations if q.quality_level == "very_high"]),
                "high": len([q for q in quality_evaluations if q.quality_level == "high"]),
                "medium": len([q for q in quality_evaluations if q.quality_level == "medium"]),
                "low": len([q for q in quality_evaluations if q.quality_level == "low"]),
                "very_low": len([q for q in quality_evaluations if q.quality_level == "very_low"])
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get quality metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/failures")
async def get_failure_metrics():
    """
    Get failure analysis metrics
    """
    try:
        failure_counts = metrics_tracker.failure_counts
        failed_tasks = [t for t in metrics_tracker.completed_tasks if not t.success]
        
        # Failure analysis
        failure_by_task = {}
        failure_by_agent = {}
        failure_rates = {}
        
        for task in failed_tasks:
            task_name = task.task_name
            agent_name = getattr(task, 'agent_name', 'unknown')
            
            failure_by_task[task_name] = failure_by_task.get(task_name, 0) + 1
            failure_by_agent[agent_name] = failure_by_agent.get(agent_name, 0) + 1
        
        # Calculate failure rates
        total_tasks = len(metrics_tracker.completed_tasks)
        for task_name, count in failure_by_task.items():
            task_total = len([t for t in metrics_tracker.completed_tasks if t.task_name == task_name])
            failure_rates[task_name] = count / task_total if task_total > 0 else 0
        
        return {
            "total_failures": len(failed_tasks),
            "failure_rate": len(failed_tasks) / total_tasks if total_tasks > 0 else 0,
            "failure_types": failure_counts,
            "failure_by_task": failure_by_task,
            "failure_by_agent": failure_by_agent,
            "failure_rates": failure_rates,
            "most_common_failures": sorted(failure_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }
        
    except Exception as e:
        logger.error(f"Failed to get failure metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/decisions")
async def get_decision_metrics():
    """
    Get decision making metrics
    """
    try:
        decisions = metrics_tracker.decisions
        
        if not decisions:
            return {"message": "No decisions available"}
        
        # Decision analysis
        actions = {}
        confidence_scores = []
        rag_usage = 0
        similar_failures = []
        
        for decision in decisions:
            action = decision.action
            confidence_scores.append(decision.confidence)
            
            actions[action] = actions.get(action, 0) + 1
            
            if decision.rag_context_used:
                rag_usage += 1
            
            if decision.similar_failures_found > 0:
                similar_failures.append(decision.similar_failures_found)
        
        return {
            "total_decisions": len(decisions),
            "action_distribution": actions,
            "average_confidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            "rag_usage_rate": rag_usage / len(decisions) if decisions else 0,
            "average_similar_failures_found": sum(similar_failures) / len(similar_failures) if similar_failures else 0,
            "decisions_with_rag_context": rag_usage,
            "decisions_with_similar_failures": len(similar_failures)
        }
        
    except Exception as e:
        logger.error(f"Failed to get decision metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/costs")
async def get_cost_metrics():
    """
    Get cost analysis metrics
    """
    try:
        total_cost = metrics_tracker.total_cost
        completed_tasks = metrics_tracker.completed_tasks
        
        if not completed_tasks:
            return {"message": "No cost data available"}
        
        # Cost analysis
        costs_by_task = {}
        costs_by_agent = {}
        costs_by_model = {}
        
        for task in completed_tasks:
            task_name = task.task_name
            agent_name = getattr(task, 'agent_name', 'unknown')
            model_used = getattr(task, 'model_used', 'unknown')
            cost = task.cost
            
            costs_by_task[task_name] = costs_by_task.get(task_name, 0) + cost
            costs_by_agent[agent_name] = costs_by_agent.get(agent_name, 0) + cost
            costs_by_model[model_used] = costs_by_model.get(model_used, 0) + cost
        
        return {
            "total_cost": total_cost,
            "average_cost_per_task": total_cost / len(completed_tasks),
            "costs_by_task": costs_by_task,
            "costs_by_agent": costs_by_agent,
            "costs_by_model": costs_by_model,
            "most_expensive_task": max(costs_by_task.items(), key=lambda x: x[1]) if costs_by_task else None,
            "most_expensive_model": max(costs_by_model.items(), key=lambda x: x[1]) if costs_by_model else None
        }
        
    except Exception as e:
        logger.error(f"Failed to get cost metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_performance_metrics():
    """
    Get performance metrics (execution time, retries, etc.)
    """
    try:
        completed_tasks = metrics_tracker.completed_tasks
        
        if not completed_tasks:
            return {"message": "No performance data available"}
        
        # Execution time analysis
        execution_times = [t.execution_time_ms for t in completed_tasks if t.execution_time_ms is not None]
        
        # Retry analysis
        tasks_with_retries = [t for t in completed_tasks if t.retry_count > 0]
        retry_counts = [t.retry_count for t in tasks_with_retries]
        
        # Success rate analysis
        successful_tasks = [t for t in completed_tasks if t.success]
        
        return {
            "total_tasks": len(completed_tasks),
            "successful_tasks": len(successful_tasks),
            "success_rate": len(successful_tasks) / len(completed_tasks),
            "execution_time": {
                "average_ms": sum(execution_times) / len(execution_times) if execution_times else 0,
                "median_ms": sorted(execution_times)[len(execution_times) // 2] if execution_times else 0,
                "min_ms": min(execution_times) if execution_times else 0,
                "max_ms": max(execution_times) if execution_times else 0
            },
            "retry_analysis": {
                "tasks_with_retries": len(tasks_with_retries),
                "retry_rate": len(tasks_with_retries) / len(completed_tasks),
                "average_retries": sum(retry_counts) / len(retry_counts) if retry_counts else 0,
                "max_retries": max(retry_counts) if retry_counts else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/improvement")
async def get_improvement_metrics():
    """
    Get improvement metrics to prove system effectiveness
    """
    try:
        improvement_metrics = metrics_tracker.get_improvement_metrics()
        
        return improvement_metrics
        
    except Exception as e:
        logger.error(f"Failed to get improvement metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-logs")
async def analyze_logs(file: UploadFile = File(...)):
    """
    Analyze uploaded log files
    """
    try:
        # Read uploaded file
        content = await file.read()
        log_data = content.decode('utf-8')
        
        # Create analyzer and analyze
        analyzer = LogAnalyzer()
        analyzer.load_logs_from_string(log_data)
        
        # Generate report
        report = analyzer.generate_report()
        
        return report
        
    except Exception as e:
        logger.error(f"Failed to analyze logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_metrics():
    """
    Export all metrics for external analysis
    """
    try:
        export_data = metrics_tracker.export_metrics()
        
        return export_data
        
    except Exception as e:
        logger.error(f"Failed to export metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_metrics():
    """
    Reset all metrics (use with caution)
    """
    try:
        # Reset metrics tracker
        metrics_tracker.active_tasks.clear()
        metrics_tracker.completed_tasks.clear()
        metrics_tracker.decisions.clear()
        metrics_tracker.quality_evaluations.clear()
        metrics_tracker.total_cost = 0.0
        metrics_tracker.total_execution_time = 0.0
        metrics_tracker.failure_counts.clear()
        metrics_tracker.action_counts.clear()
        metrics_tracker.quality_improvements.clear()
        
        return {"message": "Metrics reset successfully"}
        
    except Exception as e:
        logger.error(f"Failed to reset metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_dashboard_data():
    """
    Get comprehensive dashboard data
    """
    try:
        # Get all metrics
        aggregate = metrics_tracker.get_aggregate_metrics()
        improvement = metrics_tracker.get_improvement_metrics()
        
        # Calculate key performance indicators
        kpis = {
            "overall_health": 0,
            "quality_score": 0,
            "cost_efficiency": 0,
            "success_rate": 0,
            "improvement_trend": "stable"
        }
        
        # Calculate KPIs
        if aggregate:
            kpis["success_rate"] = (aggregate["successful_tasks"] / aggregate["total_tasks"]) * 100 if aggregate["total_tasks"] > 0 else 0
            kpis["quality_score"] = aggregate["average_quality_score"] * 100
            kpis["cost_efficiency"] = max(0, 100 - (aggregate["average_cost_per_task"] * 1000))  # Normalize cost
        
        # Calculate overall health
        if improvement:
            quality_imp = improvement.get("quality_improvement", {}).get("improvement_difference", 0)
            success_imp = improvement.get("success_rate", {}).get("improvement", 0)
            cost_imp = improvement.get("cost_efficiency", {}).get("cost_reduction", 0)
            
            kpis["overall_health"] = min(100, max(0, (kpis["success_rate"] * 0.4) + (kpis["quality_score"] * 0.3) + (kpis["cost_efficiency"] * 0.3)))
            
            # Determine trend
            if quality_imp > 0.1 or success_imp > 0.1 or cost_imp > 0.01:
                kpis["improvement_trend"] = "improving"
            elif quality_imp < -0.1 or success_imp < -0.1 or cost_imp < -0.01:
                kpis["improvement_trend"] = "declining"
        
        return {
            "kpis": kpis,
            "aggregate_metrics": aggregate,
            "improvement_metrics": improvement,
            "last_updated": metrics_tracker.completed_tasks[-1].end_time if metrics_tracker.completed_tasks else None
        }
        
    except Exception as e:
        logger.error(f"Failed to get dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def metrics_health_check():
    """
    Health check for metrics system
    """
    try:
        return {
            "status": "healthy",
            "active_tasks": len(metrics_tracker.active_tasks),
            "completed_tasks": len(metrics_tracker.completed_tasks),
            "total_decisions": len(metrics_tracker.decisions),
            "total_cost": metrics_tracker.total_cost,
            "system_health": "operational"
        }
        
    except Exception as e:
        logger.error(f"Metrics health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
