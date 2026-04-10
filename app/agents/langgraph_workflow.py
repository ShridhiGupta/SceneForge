import asyncio
import time
from typing import Dict, Any, List, Optional, Callable
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
import logging

from app.agents.state_schema import PipelineState, PipelineStatus, AgentStatus
from app.agents.scene_agent import SceneAgent
from app.agents.image_generation_agent import ImageGenerationAgent
from app.agents.quality_evaluation_agent import QualityEvaluationAgent
from app.agents.decision_agent import DecisionAgent
from app.agents.cost_optimization_agent import CostOptimizationAgent

logger = logging.getLogger(__name__)


class MultiAgentWorkflow:
    """
    Multi-agent workflow using LangGraph for intelligent video generation pipeline
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Initialize agents
        self.scene_agent = SceneAgent(self.config.get("scene_agent", {}))
        self.image_generation_agent = ImageGenerationAgent(self.config.get("image_generation_agent", {}))
        self.quality_evaluation_agent = QualityEvaluationAgent(self.config.get("quality_evaluation_agent", {}))
        self.decision_agent = DecisionAgent(self.config.get("decision_agent", {}))
        self.cost_optimization_agent = CostOptimizationAgent(self.config.get("cost_optimization_agent", {}))
        
        self.agents = {
            "scene_agent": self.scene_agent,
            "image_generation_agent": self.image_generation_agent,
            "quality_evaluation_agent": self.quality_evaluation_agent,
            "decision_agent": self.decision_agent,
            "cost_optimization_agent": self.cost_optimization_agent
        }
        
        # Initialize LangGraph workflow
        self.workflow = self._create_workflow()
        self.checkpointer = MemorySaver()
        
        # Workflow statistics
        self.workflow_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0
        }
    
    def _create_workflow(self) -> StateGraph:
        """
        Create LangGraph workflow with all agents
        """
        # Create workflow graph
        workflow = StateGraph(PipelineState)
        
        # Add nodes for each agent
        workflow.add_node("scene_processing", self._scene_processing_node)
        workflow.add_node("image_generation", self._image_generation_node)
        workflow.add_node("quality_evaluation", self._quality_evaluation_node)
        workflow.add_node("decision_making", self._decision_making_node)
        workflow.add_node("cost_optimization", self._cost_optimization_node)
        workflow.add_node("error_handling", self._error_handling_node)
        workflow.add_node("completion", self._completion_node)
        
        # Add conditional edges for workflow routing
        workflow.add_conditional_edges(
            "scene_processing",
            self._route_after_scene_processing,
            {
                "image_generation": "image_generation",
                "error": "error_handling",
                "completion": "completion"
            }
        )
        
        workflow.add_conditional_edges(
            "image_generation",
            self._route_after_image_generation,
            {
                "quality_evaluation": "quality_evaluation",
                "decision_making": "decision_making",
                "error": "error_handling",
                "completion": "completion"
            }
        )
        
        workflow.add_conditional_edges(
            "quality_evaluation",
            self._route_after_quality_evaluation,
            {
                "decision_making": "decision_making",
                "cost_optimization": "cost_optimization",
                "completion": "completion",
                "error": "error_handling"
            }
        )
        
        workflow.add_conditional_edges(
            "decision_making",
            self._route_after_decision_making,
            {
                "image_generation": "image_generation",  # Retry loop
                "quality_evaluation": "quality_evaluation",  # Re-evaluate
                "cost_optimization": "cost_optimization",
                "completion": "completion",
                "error": "error_handling"
            }
        )
        
        workflow.add_conditional_edges(
            "cost_optimization",
            self._route_after_cost_optimization,
            {
                "decision_making": "decision_making",
                "completion": "completion",
                "error": "error_handling"
            }
        )
        
        workflow.add_conditional_edges(
            "error_handling",
            self._route_after_error_handling,
            {
                "decision_making": "decision_making",
                "completion": "completion",
                "end": END
            }
        )
        
        workflow.add_edge("completion", END)
        
        # Set entry point
        workflow.set_entry_point("scene_processing")
        
        return workflow
    
    async def _scene_processing_node(self, state: PipelineState) -> PipelineState:
        """Scene processing node"""
        logger.info("Entering scene processing node")
        
        try:
            if self.scene_agent.can_handle(state):
                state = await self.scene_agent.execute(state)
                state.status = PipelineStatus.PROCESSING_SCENES
            else:
                state.status = PipelineStatus.COMPLETED
                
        except Exception as e:
            logger.error(f"Scene processing error: {e}")
            state.last_error = str(e)
            state.status = PipelineStatus.FAILED
        
        return state
    
    async def _image_generation_node(self, state: PipelineState) -> PipelineState:
        """Image generation node"""
        logger.info("Entering image generation node")
        
        try:
            if self.image_generation_agent.can_handle(state):
                state = await self.image_generation_agent.execute(state)
                state.status = PipelineStatus.GENERATING_IMAGES
            else:
                state.status = PipelineStatus.COMPLETED
                
        except Exception as e:
            logger.error(f"Image generation error: {e}")
            state.last_error = str(e)
            state.status = PipelineStatus.FAILED
        
        return state
    
    async def _quality_evaluation_node(self, state: PipelineState) -> PipelineState:
        """Quality evaluation node"""
        logger.info("Entering quality evaluation node")
        
        try:
            if self.quality_evaluation_agent.can_handle(state):
                state = await self.quality_evaluation_agent.execute(state)
                state.status = PipelineStatus.EVALUATING_QUALITY
            else:
                state.status = PipelineStatus.COMPLETED
                
        except Exception as e:
            logger.error(f"Quality evaluation error: {e}")
            state.last_error = str(e)
            state.status = PipelineStatus.FAILED
        
        return state
    
    async def _decision_making_node(self, state: PipelineState) -> PipelineState:
        """Decision making node"""
        logger.info("Entering decision making node")
        
        try:
            if self.decision_agent.can_handle(state):
                state = await self.decision_agent.execute(state)
                state.status = PipelineStatus.MAKING_DECISIONS
            else:
                state.status = PipelineStatus.COMPLETED
                
        except Exception as e:
            logger.error(f"Decision making error: {e}")
            state.last_error = str(e)
            state.status = PipelineStatus.FAILED
        
        return state
    
    async def _cost_optimization_node(self, state: PipelineState) -> PipelineState:
        """Cost optimization node"""
        logger.info("Entering cost optimization node")
        
        try:
            if self.cost_optimization_agent.can_handle(state):
                state = await self.cost_optimization_agent.execute(state)
            else:
                state.status = PipelineStatus.COMPLETED
                
        except Exception as e:
            logger.error(f"Cost optimization error: {e}")
            state.last_error = str(e)
            state.status = PipelineStatus.FAILED
        
        return state
    
    async def _error_handling_node(self, state: PipelineState) -> PipelineState:
        """Error handling node"""
        logger.info("Entering error handling node")
        
        # Log error details
        logger.error(f"Handling error: {state.last_error}")
        
        # Check if we should retry or fail
        if state.retry_count < state.max_retries:
            state.status = PipelineStatus.RETRYING
            state.retry_count += 1
            logger.info(f"Retrying (attempt {state.retry_count}/{state.max_retries})")
        else:
            state.status = PipelineStatus.FAILED
            logger.error("Max retries exceeded, failing pipeline")
        
        return state
    
    async def _completion_node(self, state: PipelineState) -> PipelineState:
        """Completion node"""
        logger.info("Entering completion node")
        
        # Update final status
        state.status = PipelineStatus.COMPLETED
        state.end_time = time.time()
        state.execution_time_ms = (state.end_time - state.start_time) * 1000
        
        # Log completion
        logger.info(f"Pipeline completed in {state.execution_time_ms:.0f}ms")
        logger.info(f"Total cost: ${state.total_cost:.4f}")
        logger.info(f"Scenes completed: {state.completed_scenes}/{len(state.scenes)}")
        
        return state
    
    def _route_after_scene_processing(self, state: PipelineState) -> str:
        """Route after scene processing"""
        if state.status == PipelineStatus.FAILED:
            return "error"
        elif len(state.scenes) == 0:
            return "completion"
        else:
            return "image_generation"
    
    def _route_after_image_generation(self, state: PipelineState) -> str:
        """Route after image generation"""
        if state.status == PipelineStatus.FAILED:
            return "error"
        elif len(state.generation_results) == 0:
            return "completion"
        else:
            return "quality_evaluation"
    
    def _route_after_quality_evaluation(self, state: PipelineState) -> str:
        """Route after quality evaluation"""
        if state.status == PipelineStatus.FAILED:
            return "error"
        elif len(state.quality_results) == 0:
            return "completion"
        elif any(not result.passes_threshold for result in state.quality_results):
            return "decision_making"
        else:
            return "cost_optimization"
    
    def _route_after_decision_making(self, state: PipelineState) -> str:
        """Route after decision making"""
        if state.status == PipelineStatus.FAILED:
            return "error"
        elif state.status == PipelineStatus.RETRYING:
            # Check what needs to be retried
            if state.current_scene_index < len(state.scenes):
                return "image_generation"
            else:
                return "quality_evaluation"
        elif state.status == PipelineStatus.COMPLETED:
            return "completion"
        else:
            return "cost_optimization"
    
    def _route_after_cost_optimization(self, state: PipelineState) -> str:
        """Route after cost optimization"""
        if state.status == PipelineStatus.FAILED:
            return "error"
        elif state.status == PipelineStatus.COMPLETED:
            return "completion"
        else:
            return "decision_making"
    
    def _route_after_error_handling(self, state: PipelineState) -> str:
        """Route after error handling"""
        if state.status == PipelineStatus.RETRYING:
            return "decision_making"
        elif state.status == PipelineStatus.FAILED:
            return "end"
        else:
            return "completion"
    
    async def execute_workflow(self, initial_state: PipelineState) -> PipelineState:
        """
        Execute the complete workflow
        """
        start_time = time.time()
        self.workflow_stats["total_executions"] += 1
        
        try:
            logger.info(f"Starting workflow execution for video {initial_state.video_id}")
            
            # Create compiled workflow
            compiled_workflow = self.workflow.compile(checkpointer=self.checkpointer)
            
            # Execute workflow
            config = {"configurable": {"thread_id": f"video_{initial_state.video_id}"}}
            
            final_state = None
            async for event in compiled_workflow.astream(initial_state, config=config):
                node_name = event.get("metadata", {}).get("checkpoint_ns", "unknown")
                logger.info(f"Workflow event: {node_name}")
                
                # Update state with current node
                if "__end__" not in event:
                    final_state = PipelineState(**event[next(iter(event.keys()))])
                    final_state.current_agent = node_name
            
            # Calculate execution time
            execution_time = (time.time() - start_time) * 1000
            
            if final_state:
                final_state.execution_time_ms = execution_time
                
                # Update statistics
                if final_state.status == PipelineStatus.COMPLETED:
                    self.workflow_stats["successful_executions"] += 1
                else:
                    self.workflow_stats["failed_executions"] += 1
                
                # Update average execution time
                total_time = self.workflow_stats["average_execution_time"] * (self.workflow_stats["total_executions"] - 1)
                self.workflow_stats["average_execution_time"] = (total_time + execution_time) / self.workflow_stats["total_executions"]
                
                logger.info(f"Workflow completed: {final_state.status.value} in {execution_time:.0f}ms")
                return final_state
            else:
                raise Exception("Workflow completed without final state")
                
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            self.workflow_stats["failed_executions"] += 1
            
            # Return error state
            error_state = initial_state.copy()
            error_state.status = PipelineStatus.FAILED
            error_state.last_error = str(e)
            error_state.execution_time_ms = (time.time() - start_time) * 1000
            
            return error_state
    
    async def execute_step(self, state: PipelineState, node_name: str) -> PipelineState:
        """
        Execute a single step/node in the workflow
        """
        node_functions = {
            "scene_processing": self._scene_processing_node,
            "image_generation": self._image_generation_node,
            "quality_evaluation": self._quality_evaluation_node,
            "decision_making": self._decision_making_node,
            "cost_optimization": self._cost_optimization_node,
            "error_handling": self._error_handling_node,
            "completion": self._completion_node
        }
        
        if node_name not in node_functions:
            raise ValueError(f"Unknown node: {node_name}")
        
        node_function = node_functions[node_name]
        return await node_function(state)
    
    def get_workflow_graph(self) -> Dict[str, Any]:
        """
        Get workflow graph representation
        """
        return {
            "nodes": [
                "scene_processing",
                "image_generation", 
                "quality_evaluation",
                "decision_making",
                "cost_optimization",
                "error_handling",
                "completion"
            ],
            "edges": [
                ("scene_processing", "image_generation"),
                ("scene_processing", "error_handling"),
                ("scene_processing", "completion"),
                ("image_generation", "quality_evaluation"),
                ("image_generation", "decision_making"),
                ("image_generation", "error_handling"),
                ("image_generation", "completion"),
                ("quality_evaluation", "decision_making"),
                ("quality_evaluation", "cost_optimization"),
                ("quality_evaluation", "completion"),
                ("quality_evaluation", "error_handling"),
                ("decision_making", "image_generation"),
                ("decision_making", "quality_evaluation"),
                ("decision_making", "cost_optimization"),
                ("decision_making", "completion"),
                ("decision_making", "error_handling"),
                ("cost_optimization", "decision_making"),
                ("cost_optimization", "completion"),
                ("cost_optimization", "error_handling"),
                ("error_handling", "decision_making"),
                ("error_handling", "completion"),
                ("error_handling", "end"),
                ("completion", "end")
            ],
            "entry_point": "scene_processing",
            "end_points": ["completion", "end"]
        }
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """
        Get workflow status and statistics
        """
        return {
            "agents": {
                name: {
                    "status": agent.status.value,
                    "can_handle": agent.can_handle,
                    "config": agent.config
                }
                for name, agent in self.agents.items()
            },
            "statistics": self.workflow_stats,
            "graph": self.get_workflow_graph()
        }
    
    def reset_statistics(self):
        """Reset workflow statistics"""
        self.workflow_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0
        }
    
    async def validate_workflow(self, state: PipelineState) -> Dict[str, Any]:
        """
        Validate workflow execution
        """
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check initial state
        if not state.video_id:
            validation_results["errors"].append("Missing video_id")
            validation_results["valid"] = False
        
        if not state.script:
            validation_results["errors"].append("Missing script")
            validation_results["valid"] = False
        
        # Check agent configurations
        for name, agent in self.agents.items():
            if not agent.validate_state(state):
                validation_results["warnings"].append(f"Agent {name} cannot handle current state")
        
        # Check budget constraints
        if state.total_budget and state.total_budget <= 0:
            validation_results["errors"].append("Invalid budget limit")
            validation_results["valid"] = False
        
        return validation_results


# Singleton instance
multi_agent_workflow = MultiAgentWorkflow()
