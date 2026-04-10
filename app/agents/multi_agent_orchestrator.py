import asyncio
import logging
from typing import Dict, Any, Optional, List
from app.agents.state_schema import PipelineState, PipelineStatus
from app.agents.langgraph_workflow import MultiAgentWorkflow, multi_agent_workflow
from app.core.database import SessionLocal
from app.models.video import Video

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """
    Orchestrator for managing multi-agent workflow execution
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.workflow = multi_agent_workflow
        self.active_executions: Dict[str, PipelineState] = {}
        
    async def execute_video_pipeline(self, video_id: int, script: str, **kwargs) -> PipelineState:
        """
        Execute complete video pipeline using multi-agent system
        """
        try:
            # Create initial state
            initial_state = self._create_initial_state(video_id, script, **kwargs)
            
            # Validate workflow
            validation = await self.workflow.validate_workflow(initial_state)
            if not validation["valid"]:
                raise ValueError(f"Workflow validation failed: {validation['errors']}")
            
            # Log warnings
            for warning in validation["warnings"]:
                logger.warning(f"Workflow warning: {warning}")
            
            # Add to active executions
            self.active_executions[str(video_id)] = initial_state
            
            # Execute workflow
            final_state = await self.workflow.execute_workflow(initial_state)
            
            # Save results to database
            await self._save_results(final_state)
            
            # Remove from active executions
            self.active_executions.pop(str(video_id), None)
            
            return final_state
            
        except Exception as e:
            logger.error(f"Video pipeline execution failed: {e}")
            
            # Clean up active execution
            self.active_executions.pop(str(video_id), None)
            
            # Create error state
            error_state = PipelineState(
                video_id=video_id,
                title=kwargs.get("title", f"Video {video_id}"),
                script=script,
                status=PipelineStatus.FAILED,
                last_error=str(e)
            )
            
            return error_state
    
    def _create_initial_state(self, video_id: int, script: str, **kwargs) -> PipelineState:
        """
        Create initial pipeline state
        """
        return PipelineState(
            video_id=video_id,
            title=kwargs.get("title", f"Video {video_id}"),
            script=script,
            total_budget=kwargs.get("total_budget"),
            quality_threshold=kwargs.get("quality_threshold", 0.5),
            preferred_model=kwargs.get("preferred_model", "stable-diffusion-xl"),
            max_retries=kwargs.get("max_retries", 3),
            enable_cost_optimization=kwargs.get("enable_cost_optimization", True)
        )
    
    async def _save_results(self, state: PipelineState):
        """
        Save pipeline results to database
        """
        db = SessionLocal()
        try:
            # Get video record
            video = db.query(Video).filter(Video.id == state.video_id).first()
            if not video:
                logger.warning(f"Video {state.video_id} not found in database")
                return
            
            # Update video with results
            if state.status == PipelineStatus.COMPLETED:
                video.status = "completed"
                video.progress = 100.0
            elif state.status == PipelineStatus.FAILED:
                video.status = "failed"
                video.error_message = state.last_error
            else:
                video.status = "processing"
                video.progress = (state.completed_scenes / len(state.scenes)) * 100 if state.scenes else 0
            
            # Update cost information
            if hasattr(video, 'total_cost'):
                video.total_cost = state.total_cost
            
            db.commit()
            logger.info(f"Saved results for video {state.video_id}")
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def get_execution_status(self, video_id: int) -> Optional[Dict[str, Any]]:
        """
        Get status of active execution
        """
        execution = self.active_executions.get(str(video_id))
        if not execution:
            return None
        
        return {
            "video_id": video_id,
            "status": execution.status.value,
            "current_agent": execution.current_agent,
            "progress": {
                "completed_scenes": execution.completed_scenes,
                "total_scenes": len(execution.scenes),
                "progress_percentage": (execution.completed_scenes / len(execution.scenes)) * 100 if execution.scenes else 0
            },
            "cost": {
                "total_cost": execution.total_cost,
                "budget_utilization": execution.total_cost / execution.total_budget if execution.total_budget else None
            },
            "retry_count": execution.retry_count,
            "last_error": execution.last_error
        }
    
    async def cancel_execution(self, video_id: int) -> bool:
        """
        Cancel active execution
        """
        if str(video_id) in self.active_executions:
            execution = self.active_executions[str(video_id)]
            execution.status = PipelineStatus.FAILED
            execution.last_error = "Execution cancelled by user"
            
            # Remove from active executions
            self.active_executions.pop(str(video_id), None)
            
            logger.info(f"Cancelled execution for video {video_id}")
            return True
        
        return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get overall system status
        """
        return {
            "active_executions": len(self.active_executions),
            "workflow_status": self.workflow.get_workflow_status(),
            "system_health": self._check_system_health()
        }
    
    def _check_system_health(self) -> Dict[str, Any]:
        """
        Check system health
        """
        health = {
            "status": "healthy",
            "issues": []
        }
        
        # Check active executions
        if len(self.active_executions) > 10:
            health["issues"].append("High number of active executions")
            health["status"] = "degraded"
        
        # Check workflow statistics
        stats = self.workflow.workflow_stats
        if stats["total_executions"] > 0:
            failure_rate = stats["failed_executions"] / stats["total_executions"]
            if failure_rate > 0.2:
                health["issues"].append(f"High failure rate: {failure_rate:.1%}")
                health["status"] = "degraded"
        
        return health
    
    async def retry_execution(self, video_id: int) -> Optional[PipelineState]:
        """
        Retry failed execution
        """
        # Get last execution state
        db = SessionLocal()
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                logger.error(f"Video {video_id} not found")
                return None
            
            # Reset retry count
            state = PipelineState(
                video_id=video_id,
                title=video.title,
                script=video.script,
                status=PipelineStatus.INITIALIZING,
                retry_count=0
            )
            
            # Execute workflow
            return await self.workflow.execute_workflow(state)
            
        except Exception as e:
            logger.error(f"Retry execution failed: {e}")
            return None
        finally:
            db.close()


# Singleton instance
multi_agent_orchestrator = MultiAgentOrchestrator()
