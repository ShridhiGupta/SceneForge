import asyncio
from typing import Dict, Any, Optional
from app.schemas.decision_engine import LLMDecision, RecoveryAction, FailureContext
from app.schemas.rag_memory import FailureMemory
from app.services.decision_engine import decision_engine
from app.services.rag_memory import rag_memory_service
from app.core.database import SessionLocal
from app.models.video import Video, Scene, TaskStatus
import logging
import uuid

logger = logging.getLogger(__name__)


class DecisionExecutor:
    """
    Executes LLM decisions by applying them to the pipeline
    """
    
    def __init__(self):
        self.decision_engine = decision_engine
    
    async def handle_failure(self, context: FailureContext) -> Dict[str, Any]:
        """
        Handle failure by getting LLM decision and executing it
        """
        try:
            # Get decision from LLM
            decision = await self.decision_engine.analyze_failure(context)
            
            logger.info(f"LLM Decision: {decision.action} - {decision.reason}")
            
            # Execute the decision
            result = await self._execute_decision(context, decision)
            
            # Store the decision and outcome in RAG memory
            await self._store_decision_outcome(context, decision, result)
            
            return {
                "decision": decision.dict(),
                "execution_result": result,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Decision execution failed: {e}")
            return {
                "decision": None,
                "execution_result": None,
                "success": False,
                "error": str(e)
            }
    
    async def _execute_decision(self, context: FailureContext, decision: LLMDecision) -> Dict[str, Any]:
        """
        Execute the specific decision
        """
        if decision.action == RecoveryAction.RETRY:
            return await self._execute_retry(context, decision)
        elif decision.action == RecoveryAction.MODIFY_PROMPT:
            return await self._execute_modify_prompt(context, decision)
        elif decision.action == RecoveryAction.SWITCH_MODEL:
            return await self._execute_switch_model(context, decision)
        elif decision.action == RecoveryAction.ADJUST_PARAMETERS:
            return await self._execute_adjust_parameters(context, decision)
        elif decision.action == RecoveryAction.SKIP_TASK:
            return await self._execute_skip_task(context, decision)
        elif decision.action == RecoveryAction.ESCALATE_RESOURCES:
            return await self._execute_escalate_resources(context, decision)
        else:
            raise ValueError(f"Unknown action: {decision.action}")
    
    async def _execute_retry(self, context: FailureContext, decision: LLMDecision) -> Dict[str, Any]:
        """
        Execute retry with same configuration
        """
        db = SessionLocal()
        try:
            # Update retry count in database
            if context.stage.value == "image":
                scene = db.query(Scene).filter(Scene.id == context.additional_context.get("scene_id")).first()
                if scene:
                    scene.retry_count = context.retry_count + 1
                    db.commit()
            
            return {
                "action": "retry_scheduled",
                "retry_count": context.retry_count + 1,
                "delay": self._calculate_retry_delay(context.retry_count)
            }
        finally:
            db.close()
    
    async def _execute_modify_prompt(self, context: FailureContext, decision: LLMDecision) -> Dict[str, Any]:
        """
        Execute prompt modification
        """
        db = SessionLocal()
        try:
            new_prompt = decision.new_prompt or context.prompt_used
            
            # Update prompt in database
            if context.stage.value == "image":
                scene_id = context.additional_context.get("scene_id")
                if scene_id:
                    scene = db.query(Scene).filter(Scene.id == scene_id).first()
                    if scene:
                        scene.description = new_prompt
                        scene.retry_count = 0  # Reset retry count for new prompt
                        db.commit()
            
            return {
                "action": "prompt_modified",
                "old_prompt": context.prompt_used,
                "new_prompt": new_prompt
            }
        finally:
            db.close()
    
    async def _execute_switch_model(self, context: FailureContext, decision: LLMDecision) -> Dict[str, Any]:
        """
        Execute model switch
        """
        new_model = decision.new_model or "fallback-model"
        
        # Update model configuration (this would depend on your service implementation)
        return {
            "action": "model_switched",
            "old_model": context.model_used,
            "new_model": new_model
        }
    
    async def _execute_adjust_parameters(self, context: FailureContext, decision: LLMDecision) -> Dict[str, Any]:
        """
        Execute parameter adjustments
        """
        param_changes = decision.parameter_changes or {}
        
        # Update task parameters (implementation depends on your service)
        return {
            "action": "parameters_adjusted",
            "parameter_changes": param_changes
        }
    
    async def _execute_skip_task(self, context: FailureContext, decision: LLMDecision) -> Dict[str, Any]:
        """
        Execute task skip
        """
        db = SessionLocal()
        try:
            # Mark task as skipped
            if context.stage.value == "image":
                scene_id = context.additional_context.get("scene_id")
                if scene_id:
                    scene = db.query(Scene).filter(Scene.id == scene_id).first()
                    if scene:
                        scene.image_generation_status = TaskStatus.SKIPPED
                        scene.error_message = f"Skipped: {decision.reason}"
                        db.commit()
            
            return {
                "action": "task_skipped",
                "reason": decision.reason
            }
        finally:
            db.close()
    
    async def _execute_escalate_resources(self, context: FailureContext, decision: LLMDecision) -> Dict[str, Any]:
        """
        Execute resource escalation
        """
        param_changes = decision.parameter_changes or {}
        
        # Update resource limits (implementation depends on your infrastructure)
        return {
            "action": "resources_escalated",
            "resource_changes": param_changes
        }
    
    async def _store_decision_outcome(self, context: FailureContext, decision: LLMDecision, execution_result: Dict[str, Any]):
        """
        Store the decision and its outcome in RAG memory for future learning
        """
        try:
            # Determine if the decision was successful
            success = execution_result.get("success", False)
            
            # Get quality score if available
            quality_score = context.output_quality_score
            
            # Create failure memory record
            memory = FailureMemory(
                failure_type=self._classify_failure_type(context.error_logs),
                stage=context.stage,
                error_logs=context.error_logs,
                prompt_used=context.prompt_used,
                model_used=context.model_used,
                action_taken=decision.action,
                new_prompt=decision.new_prompt,
                new_model=decision.new_model,
                parameter_changes=decision.parameter_changes,
                success=success,
                final_quality_score=quality_score,
                total_cost=context.cost_so_far,
                retry_count=context.retry_count,
                task_id=str(uuid.uuid4()),  # Generate unique task ID
                video_id=context.additional_context.get("video_id") if context.additional_context else None,
                scene_id=context.additional_context.get("scene_id") if context.additional_context else None
            )
            
            # Store in RAG memory
            memory_id = await rag_memory_service.store_failure_memory(memory)
            
            if memory_id:
                logger.info(f"Stored decision outcome in memory: {memory_id}")
            else:
                logger.warning("Failed to store decision outcome in memory")
                
        except Exception as e:
            logger.error(f"Failed to store decision outcome: {e}")
    
    def _classify_failure_type(self, error_logs: str) -> str:
        """
        Classify failure type from error logs
        """
        from app.schemas.rag_memory import FailureType
        
        error_lower = error_logs.lower()
        
        if "timeout" in error_lower or "time limit" in error_lower:
            return FailureType.TIMEOUT
        elif "api" in error_lower or "http" in error_lower or "connection" in error_lower:
            return FailureType.API_ERROR
        elif "quality" in error_lower or "low score" in error_lower:
            return FailureType.LOW_QUALITY
        elif "memory" in error_lower or "resource" in error_lower or "gpu" in error_lower:
            return FailureType.RESOURCE_EXHAUSTION
        else:
            return FailureType.UNKNOWN
    
    def _calculate_retry_delay(self, retry_count: int) -> int:
        """
        Calculate exponential backoff delay
        """
        return min(60 * (2 ** retry_count), 300)  # Max 5 minutes
    
    async def should_use_decision_engine(self, context: FailureContext) -> bool:
        """
        Decide if decision engine should be used for this failure
        """
        # Don't use decision engine for first failure (simple retry)
        if context.retry_count == 0:
            return False
        
        # Don't use if decision engine not available
        if not self.decision_engine.is_available():
            return False
        
        # Use decision engine for multiple failures or complex errors
        return context.retry_count >= 1 or len(context.error_logs) > 100


# Singleton instance
decision_executor = DecisionExecutor()
