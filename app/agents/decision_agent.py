import json
import time
from typing import Dict, Any, Optional, List
import logging
from app.agents.base_agent import BaseAgent
from app.agents.state_schema import (
    PipelineState, 
    Scene, 
    DecisionResult, 
    DecisionAction,
    AgentStatus, 
    PipelineStatus,
    FailureType
)
from app.services.decision_engine import decision_engine
from app.services.rag_memory import rag_memory_service
from app.schemas.rag_memory import MemoryQuery, PipelineStage as RAGPipelineStage

logger = logging.getLogger(__name__)


class DecisionAgent(BaseAgent):
    """
    Decision Agent: Makes intelligent decisions using LLM and RAG memory
    Responsibilities:
    - Analyze failures and quality issues
    - Retrieve similar past experiences from RAG memory
    - Make informed recovery decisions
    - Coordinate retry loops and parameter adjustments
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("decision_agent", config)
        self.decision_engine = decision_engine
        self.rag_memory = rag_memory_service
        self.decision_history: List[DecisionResult] = []
        
        # Decision confidence thresholds
        self.confidence_thresholds = {
            "high_confidence": 0.8,
            "medium_confidence": 0.6,
            "low_confidence": 0.4
        }
        
        # Action priorities based on urgency
        self.action_priorities = {
            DecisionAction.ESCALATE_RESOURCES: 5,
            DecisionAction.SWITCH_MODEL: 4,
            DecisionAction.MODIFY_PROMPT: 3,
            DecisionAction.ADJUST_PARAMETERS: 2,
            DecisionAction.RETRY: 1,
            DecisionAction.SKIP_TASK: 0
        }
    
    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Process pending decisions and make recovery choices
        """
        try:
            self.update_status(AgentStatus.RUNNING)
            state.agent_statuses[self.name] = AgentStatus.RUNNING
            state.current_agent = self.name
            state.status = PipelineStatus.MAKING_DECISIONS
            
            logger.info(f"Decision Agent processing {len(state.messages)} messages")
            
            # Process messages that require decisions
            decision_messages = [msg for msg in state.messages if msg.get("recipient") == self.name]
            
            for message in decision_messages:
                await self.process_decision_message(message, state)
            
            # Check for any failed scenes that need decisions
            failed_scenes = [scene for scene in state.scenes if scene.status == AgentStatus.FAILED]
            for scene in failed_scenes:
                await self.make_scene_decision(scene, state)
            
            # Update pipeline status based on decisions
            await self.update_pipeline_status(state)
            
            self.update_status(AgentStatus.COMPLETED)
            state.agent_statuses[self.name] = AgentStatus.COMPLETED
            
            # Log completion
            self.log_action("decisions_made", {
                "messages_processed": len(decision_messages),
                "decisions_made": len(self.decision_history),
                "failed_scenes_handled": len(failed_scenes)
            })
            
            return state
            
        except Exception as e:
            logger.error(f"Decision Agent error: {e}")
            return await self.handle_error(state, e)
    
    def can_handle(self, state: PipelineState) -> bool:
        """Check if this agent can handle the current state"""
        return (
            (state.status == PipelineStatus.EVALUATING_QUALITY or 
             state.status == PipelineStatus.MAKING_DECISIONS or
             state.status == PipelineStatus.FAILED or
             state.status == PipelineStatus.RETRYING) and
            self.validate_state(state)
        )
    
    async def process_decision_message(self, message: Dict[str, Any], state: PipelineState):
        """
        Process individual decision message
        """
        try:
            message_type = message.get("message_type")
            content = message.get("content", {})
            
            if message_type == "request":
                action = content.get("action")
                
                if action == "handle_low_quality":
                    await self.handle_low_quality_decision(content, state)
                elif action == "handle_generation_error":
                    await self.handle_generation_error_decision(content, state)
                elif action == "handle_pipeline_error":
                    await self.handle_pipeline_error_decision(content, state)
                else:
                    logger.warning(f"Unknown decision action: {action}")
            
            elif message_type == "error":
                await self.handle_error_message(content, state)
            
        except Exception as e:
            logger.error(f"Failed to process decision message: {e}")
    
    async def handle_low_quality_decision(self, context: Dict[str, Any], state: PipelineState):
        """
        Make decision for low quality image
        """
        scene_id = context.get("scene_id")
        quality_score = context.get("quality_score", 0.0)
        prompt = context.get("prompt", "")
        model_used = context.get("model_used", "")
        retry_count = context.get("retry_count", 0)
        
        # Get scene
        scene = None
        for s in state.scenes:
            if s.id == scene_id:
                scene = s
                break
        
        if not scene:
            logger.error(f"Scene {scene_id} not found")
            return
        
        # Create failure context for decision engine
        failure_context = self.create_failure_context(
            failure_type=FailureType.LOW_QUALITY,
            stage=RAGPipelineStage.IMAGE,
            error_logs=f"Quality score {quality_score:.2f} below threshold",
            prompt=prompt,
            model=model_used,
            retry_count=retry_count,
            scene=scene,
            state=state
        )
        
        # Make decision
        decision_result = await self.make_intelligent_decision(failure_context, state)
        
        # Execute decision
        await self.execute_decision(decision_result, scene, state)
    
    async def handle_generation_error_decision(self, context: Dict[str, Any], state: PipelineState):
        """
        Make decision for generation error
        """
        scene_id = context.get("scene_id")
        error_message = context.get("error", "")
        model_used = context.get("model_used", "")
        
        # Get scene
        scene = None
        for s in state.scenes:
            if s.id == scene_id:
                scene = s
                break
        
        if not scene:
            logger.error(f"Scene {scene_id} not found")
            return
        
        # Classify failure type
        failure_type = self.classify_failure_type(error_message)
        
        # Create failure context
        failure_context = self.create_failure_context(
            failure_type=failure_type,
            stage=RAGPipelineStage.IMAGE,
            error_logs=error_message,
            prompt=scene.prompt or scene.description,
            model=model_used,
            retry_count=scene.retry_count,
            scene=scene,
            state=state
        )
        
        # Make decision
        decision_result = await self.make_intelligent_decision(failure_context, state)
        
        # Execute decision
        await self.execute_decision(decision_result, scene, state)
    
    async def handle_pipeline_error_decision(self, context: Dict[str, Any], state: PipelineState):
        """
        Make decision for pipeline-level error
        """
        error_message = context.get("error", "")
        
        # Classify failure type
        failure_type = self.classify_failure_type(error_message)
        
        # Create failure context for pipeline
        failure_context = self.create_failure_context(
            failure_type=failure_type,
            stage=RAGPipelineStage.IMAGE,  # Default to image stage
            error_logs=error_message,
            prompt="",
            model="",
            retry_count=state.retry_count,
            scene=None,
            state=state
        )
        
        # Make decision
        decision_result = await self.make_intelligent_decision(failure_context, state)
        
        # Execute pipeline-level decision
        await self.execute_pipeline_decision(decision_result, state)
    
    async def handle_error_message(self, context: Dict[str, Any], state: PipelineState):
        """
        Handle general error message
        """
        error_message = context.get("error", "")
        agent = context.get("agent", "unknown")
        
        logger.warning(f"Error from {agent}: {error_message}")
        
        # Add to error history
        state.error_history.append(f"{agent}: {error_message}")
        
        # If too many errors, consider escalating
        if len(state.error_history) > 5:
            await self.escalate_pipeline_error(state)
    
    def create_failure_context(self, failure_type: FailureType, stage: RAGPipelineStage, 
                             error_logs: str, prompt: str, model: str, retry_count: int,
                             scene: Optional[Scene], state: PipelineState) -> Dict[str, Any]:
        """
        Create failure context for decision engine
        """
        from app.schemas.decision_engine import FailureContext
        
        return {
            "task_name": f"{stage.value}_generation",
            "stage": stage,
            "error_logs": error_logs,
            "retry_count": retry_count,
            "output_quality_score": scene.quality_score if scene else None,
            "cost_so_far": state.total_cost,
            "model_used": model,
            "prompt_used": prompt,
            "additional_context": {
                "scene_id": scene.id if scene else None,
                "video_id": state.video_id,
                "total_scenes": len(state.scenes),
                "completed_scenes": state.completed_scenes,
                "failure_type": failure_type.value
            }
        }
    
    async def make_intelligent_decision(self, failure_context: Dict[str, Any], state: PipelineState) -> DecisionResult:
        """
        Make intelligent decision using LLM and RAG memory
        """
        start_time = time.time()
        
        try:
            # Retrieve similar past failures from RAG memory
            similar_failures = await self.retrieve_similar_failures(failure_context)
            
            # Get decision from decision engine with RAG context
            from app.schemas.decision_engine import FailureContext as DecisionFailureContext
            
            decision_context = DecisionFailureContext(**failure_context)
            decision = await self.decision_engine.analyze_failure(decision_context)
            
            # Create decision result
            decision_result = DecisionResult(
                action=DecisionAction(decision.action),
                confidence=decision.confidence,
                reasoning=decision.reason,
                new_prompt=decision.new_prompt,
                new_model=decision.new_model,
                parameter_changes=decision.parameter_changes,
                estimated_cost_impact=self.estimate_cost_impact(decision.action, decision.new_model)
            )
            
            # Store decision in history
            self.decision_history.append(decision_result)
            
            # Store decision in RAG memory for future learning
            await self.store_decision_outcome(failure_context, decision_result, similar_failures)
            
            decision_time = (time.time() - start_time) * 1000
            logger.info(f"Decision made: {decision.action.value} (confidence: {decision.confidence:.2f}, time: {decision_time:.0f}ms)")
            
            return decision_result
            
        except Exception as e:
            logger.error(f"Decision making failed: {e}")
            # Fallback decision
            return self.get_fallback_decision(failure_context)
    
    async def retrieve_similar_failures(self, failure_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Retrieve similar failures from RAG memory
        """
        try:
            # Create memory query
            query = MemoryQuery(
                failure_type=FailureType[failure_context["additional_context"]["failure_type"].upper()],
                stage=failure_context["stage"],
                error_logs=failure_context["error_logs"],
                prompt_used=failure_context["prompt_used"],
                model_used=failure_context["model_used"],
                top_k=5,
                min_similarity=0.6,
                require_success=True
            )
            
            # Search RAG memory
            search_response = await self.rag_memory.search_similar_failures(query)
            
            # Convert to list of dicts
            similar_failures = []
            for result in search_response.results:
                similar_failures.append({
                    "memory": result.memory.dict(),
                    "similarity": result.similarity_score,
                    "relevance": result.relevance_explanation
                })
            
            return similar_failures
            
        except Exception as e:
            logger.warning(f"Failed to retrieve similar failures: {e}")
            return []
    
    async def store_decision_outcome(self, failure_context: Dict[str, Any], 
                                   decision_result: DecisionResult, 
                                   similar_failures: List[Dict[str, Any]]):
        """
        Store decision outcome in RAG memory for future learning
        """
        try:
            from app.schemas.rag_memory import FailureMemory, RecoveryAction, PipelineStage as RAGPipelineStage
            
            # Create memory record
            memory = FailureMemory(
                failure_type=FailureType[failure_context["additional_context"]["failure_type"].upper()],
                stage=RAGPipelineStage(failure_context["stage"].value),
                error_logs=failure_context["error_logs"],
                prompt_used=failure_context["prompt_used"],
                model_used=failure_context["model_used"],
                action_taken=RecoveryAction(decision_result.action.value),
                new_prompt=decision_result.new_prompt,
                new_model=decision_result.new_model,
                parameter_changes=decision_result.parameter_changes,
                success=True,  # Will be updated based on actual outcome
                final_quality_score=None,  # Will be updated after execution
                total_cost=failure_context["cost_so_far"],
                retry_count=failure_context["retry_count"],
                video_id=failure_context["additional_context"].get("video_id"),
                scene_id=failure_context["additional_context"].get("scene_id")
            )
            
            # Store in RAG memory
            memory_id = await self.rag_memory.store_failure_memory(memory)
            
            if memory_id:
                logger.info(f"Decision outcome stored in memory: {memory_id}")
            
        except Exception as e:
            logger.error(f"Failed to store decision outcome: {e}")
    
    def get_fallback_decision(self, failure_context: Dict[str, Any]) -> DecisionResult:
        """
        Get fallback decision when LLM fails
        """
        failure_type = failure_context["additional_context"]["failure_type"]
        retry_count = failure_context["retry_count"]
        
        # Simple rule-based fallback
        if failure_type == "timeout" and retry_count < 2:
            return DecisionResult(
                action=DecisionAction.RETRY,
                confidence=0.6,
                reasoning="Timeout detected, retrying",
                estimated_cost_impact=0.0
            )
        elif failure_type == "api_error" and retry_count < 3:
            return DecisionResult(
                action=DecisionAction.SWITCH_MODEL,
                confidence=0.7,
                reasoning="API error, switching model",
                new_model="stable-diffusion-v1-5",
                estimated_cost_impact=-0.01  # Cheaper model
            )
        elif failure_type == "low_quality":
            return DecisionResult(
                action=DecisionAction.MODIFY_PROMPT,
                confidence=0.8,
                reasoning="Low quality, improving prompt",
                new_prompt=failure_context["prompt_used"] + ", high quality, detailed, professional",
                estimated_cost_impact=0.0
            )
        else:
            return DecisionResult(
                action=DecisionAction.RETRY,
                confidence=0.5,
                reasoning="Unknown error, retrying",
                estimated_cost_impact=0.0
            )
    
    async def execute_decision(self, decision: DecisionResult, scene: Scene, state: PipelineState):
        """
        Execute decision for specific scene
        """
        action = decision.action
        
        if action == DecisionAction.RETRY:
            scene.retry_count += 1
            scene.status = AgentStatus.IDLE  # Reset for retry
            state.current_scene_index = scene.scene_number - 1  # Re-process this scene
            
        elif action == DecisionAction.MODIFY_PROMPT:
            if decision.new_prompt:
                scene.prompt = decision.new_prompt
            scene.status = AgentStatus.IDLE
            state.current_scene_index = scene.scene_number - 1
            
        elif action == DecisionAction.SWITCH_MODEL:
            if decision.new_model:
                scene.model_used = decision.new_model
            scene.status = AgentStatus.IDLE
            state.current_scene_index = scene.scene_number - 1
            
        elif action == DecisionAction.ADJUST_PARAMETERS:
            # Update shared context with parameter changes
            if decision.parameter_changes:
                state.shared_context.update(decision.parameter_changes)
            scene.status = AgentStatus.IDLE
            state.current_scene_index = scene.scene_number - 1
            
        elif action == DecisionAction.SKIP_TASK:
            scene.status = AgentStatus.COMPLETED  # Mark as completed (skipped)
            state.completed_scenes += 1
            
        elif action == DecisionAction.ESCALATE_RESOURCES:
            # Add resource escalation to shared context
            state.shared_context["resource_escalation"] = True
            state.shared_context["escalated_resources"] = decision.parameter_changes or {}
            scene.status = AgentStatus.IDLE
            state.current_scene_index = scene.scene_number - 1
        
        # Update pipeline status for retry
        if action in [DecisionAction.RETRY, DecisionAction.MODIFY_PROMPT, 
                     DecisionAction.SWITCH_MODEL, DecisionAction.ADJUST_PARAMETERS,
                     DecisionAction.ESCALATE_RESOURCES]:
            state.status = PipelineStatus.RETRYING
            state.retry_count += 1
        
        # Log decision execution
        self.log_action("decision_executed", {
            "scene_id": scene.id,
            "action": action.value,
            "confidence": decision.confidence,
            "reasoning": decision.reasoning
        })
    
    async def execute_pipeline_decision(self, decision: DecisionResult, state: PipelineState):
        """
        Execute pipeline-level decision
        """
        action = decision.action
        
        if action == DecisionAction.ESCALATE_RESOURCES:
            state.shared_context["pipeline_escalation"] = True
            state.shared_context["escalated_resources"] = decision.parameter_changes or {}
            
        elif action == DecisionAction.SKIP_TASK:
            # Mark all failed scenes as skipped
            for scene in state.scenes:
                if scene.status == AgentStatus.FAILED:
                    scene.status = AgentStatus.COMPLETED
                    state.completed_scenes += 1
        
        # Update pipeline status
        if action in [DecisionAction.RETRY, DecisionAction.ESCALATE_RESOURCES]:
            state.status = PipelineStatus.RETRYING
            state.retry_count += 1
        elif action == DecisionAction.SKIP_TASK:
            state.status = PipelineStatus.COMPLETED
    
    def classify_failure_type(self, error_message: str) -> FailureType:
        """
        Classify failure type from error message
        """
        error_lower = error_message.lower()
        
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
    
    def estimate_cost_impact(self, action: DecisionAction, new_model: Optional[str]) -> float:
        """
        Estimate cost impact of decision
        """
        model_costs = {
            "stable-diffusion-xl": 0.02,
            "dall-e-3": 0.04,
            "stable-diffusion-v1-5": 0.01,
            "midjourney": 0.05
        }
        
        if action == DecisionAction.SWITCH_MODEL and new_model:
            return model_costs.get(new_model, 0.02) - 0.02  # Difference from default
        elif action == DecisionAction.ESCALATE_RESOURCES:
            return 0.01  # Additional resource cost
        else:
            return 0.0
    
    async def update_pipeline_status(self, state: PipelineState):
        """
        Update pipeline status based on current state
        """
        # Check if all scenes are completed
        if all(scene.status == AgentStatus.COMPLETED for scene in state.scenes):
            state.status = PipelineStatus.COMPLETED
            state.end_time = time.time()
            state.execution_time_ms = (state.end_time - state.start_time) * 1000
        
        # Check if too many retries
        elif state.retry_count >= state.max_retries:
            state.status = PipelineStatus.FAILED
        
        # Check if budget exceeded
        elif state.total_budget and state.total_cost > state.total_budget:
            state.status = PipelineStatus.FAILED
            state.last_error = "Budget exceeded"
    
    async def escalate_pipeline_error(self, state: PipelineState):
        """
        Escalate pipeline error to higher level
        """
        logger.error(f"Pipeline error escalation: {len(state.error_history)} errors detected")
        
        # Create escalation decision
        escalation_decision = DecisionResult(
            action=DecisionAction.ESCALATE_RESOURCES,
            confidence=0.9,
            reasoning="Multiple errors detected, escalating resources",
            parameter_changes={"timeout": 600, "retry_limit": 5},
            estimated_cost_impact=0.02
        )
        
        await self.execute_pipeline_decision(escalation_decision, state)
    
    def get_decision_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about decisions made
        """
        if not self.decision_history:
            return {}
        
        action_counts = {}
        confidence_scores = []
        
        for decision in self.decision_history:
            action = decision.action.value
            action_counts[action] = action_counts.get(action, 0) + 1
            confidence_scores.append(decision.confidence)
        
        return {
            "total_decisions": len(self.decision_history),
            "action_distribution": action_counts,
            "average_confidence": sum(confidence_scores) / len(confidence_scores),
            "high_confidence_decisions": len([c for c in confidence_scores if c >= 0.8]),
            "medium_confidence_decisions": len([c for c in confidence_scores if 0.6 <= c < 0.8]),
            "low_confidence_decisions": len([c for c in confidence_scores if c < 0.6])
        }
