from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.schemas.decision_engine import FailureContext
from app.agents.state_schema import PipelineState
from app.agents.multi_agent_orchestrator import multi_agent_orchestrator
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/multi-agent", tags=["multi-agent"])


@router.post("/execute")
async def execute_video_pipeline(
    video_id: int,
    script: str,
    title: Optional[str] = None,
    total_budget: Optional[float] = None,
    quality_threshold: float = 0.5,
    preferred_model: str = "stable-diffusion-xl",
    max_retries: int = 3,
    enable_cost_optimization: bool = True
):
    """
    Execute video pipeline using multi-agent system
    """
    try:
        result = await multi_agent_orchestrator.execute_video_pipeline(
            video_id=video_id,
            script=script,
            title=title,
            total_budget=total_budget,
            quality_threshold=quality_threshold,
            preferred_model=preferred_model,
            max_retries=max_retries,
            enable_cost_optimization=enable_cost_optimization
        )
        
        return {
            "success": True,
            "video_id": video_id,
            "status": result.status.value,
            "execution_time_ms": result.execution_time_ms,
            "total_cost": result.total_cost,
            "completed_scenes": result.completed_scenes,
            "total_scenes": len(result.scenes),
            "final_state": result.dict()
        }
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{video_id}")
async def get_execution_status(video_id: int):
    """
    Get status of active pipeline execution
    """
    try:
        status = await multi_agent_orchestrator.get_execution_status(video_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="No active execution found")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel/{video_id}")
async def cancel_execution(video_id: int):
    """
    Cancel active pipeline execution
    """
    try:
        success = await multi_agent_orchestrator.cancel_execution(video_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="No active execution found")
        
        return {
            "success": True,
            "message": f"Execution for video {video_id} cancelled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retry/{video_id}")
async def retry_execution(video_id: int):
    """
    Retry failed pipeline execution
    """
    try:
        result = await multi_agent_orchestrator.retry_execution(video_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Video not found or cannot retry")
        
        return {
            "success": True,
            "video_id": video_id,
            "status": result.status.value,
            "execution_time_ms": result.execution_time_ms,
            "total_cost": result.total_cost,
            "completed_scenes": result.completed_scenes,
            "total_scenes": len(result.scenes)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system-status")
async def get_system_status():
    """
    Get multi-agent system status
    """
    try:
        return multi_agent_orchestrator.get_system_status()
        
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflow-graph")
async def get_workflow_graph():
    """
    Get workflow graph representation
    """
    try:
        return multi_agent_orchestrator.workflow.get_workflow_graph()
        
    except Exception as e:
        logger.error(f"Failed to get workflow graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-status")
async def get_agent_status():
    """
    Get status of all agents
    """
    try:
        workflow_status = multi_agent_orchestrator.workflow.get_workflow_status()
        return workflow_status["agents"]
        
    except Exception as e:
        logger.error(f"Failed to get agent status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-step")
async def test_workflow_step(
    video_id: int,
    script: str,
    step: str,
    title: Optional[str] = None
):
    """
    Test a single step in the workflow
    """
    try:
        # Create initial state
        initial_state = multi_agent_orchestrator._create_initial_state(
            video_id=video_id,
            script=script,
            title=title
        )
        
        # Execute specific step
        result_state = await multi_agent_orchestrator.workflow.execute_step(initial_state, step)
        
        return {
            "success": True,
            "step": step,
            "status": result_state.status.value,
            "current_agent": result_state.current_agent,
            "state": result_state.dict()
        }
        
    except Exception as e:
        logger.error(f"Test step failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_workflow_statistics():
    """
    Get workflow execution statistics
    """
    try:
        return multi_agent_orchestrator.workflow.workflow_stats
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-statistics")
async def reset_statistics():
    """
    Reset workflow statistics
    """
    try:
        multi_agent_orchestrator.workflow.reset_statistics()
        
        return {
            "success": True,
            "message": "Statistics reset successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to reset statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check for multi-agent system
    """
    try:
        system_status = multi_agent_orchestrator.get_system_status()
        health = system_status["system_health"]
        
        return {
            "status": health["status"],
            "active_executions": system_status["active_executions"],
            "issues": health["issues"]
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
