from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from app.agents.state_schema import PipelineState, AgentMessage, AgentStatus

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all pipeline agents
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.status = AgentStatus.IDLE
        self.message_history: list[AgentMessage] = []
    
    @abstractmethod
    async def execute(self, state: PipelineState) -> PipelineState:
        """
        Execute the agent's primary function
        """
        pass
    
    @abstractmethod
    def can_handle(self, state: PipelineState) -> bool:
        """
        Check if this agent can handle the current state
        """
        pass
    
    def update_status(self, status: AgentStatus):
        """Update agent status"""
        self.status = status
        logger.info(f"Agent {self.name} status: {status}")
    
    def send_message(self, recipient: str, message_type: str, content: Dict[str, Any], priority: int = 1):
        """Send message to another agent"""
        message = AgentMessage(
            sender=self.name,
            recipient=recipient,
            message_type=message_type,
            content=content,
            priority=priority
        )
        self.message_history.append(message)
        return message
    
    def receive_message(self, message: AgentMessage):
        """Receive message from another agent"""
        self.message_history.append(message)
        logger.info(f"Agent {self.name} received message from {message.sender}: {message.message_type}")
    
    def log_action(self, action: str, details: Dict[str, Any]):
        """Log agent action"""
        log_entry = {
            "agent": self.name,
            "action": action,
            "details": details,
            "timestamp": str(datetime.utcnow())
        }
        logger.info(f"Agent {self.name} action: {action} - {details}")
        return log_entry
    
    def get_error_context(self, state: PipelineState, error: Exception) -> Dict[str, Any]:
        """Get error context for decision making"""
        return {
            "agent": self.name,
            "error": str(error),
            "state": state.dict(),
            "retry_count": state.retry_count,
            "current_scene": state.scenes[state.current_scene_index] if state.current_scene_index < len(state.scenes) else None
        }
    
    async def handle_error(self, state: PipelineState, error: Exception) -> PipelineState:
        """Handle errors during execution"""
        error_context = self.get_error_context(state, error)
        
        # Update state with error information
        state.last_error = str(error)
        state.error_history.append(str(error))
        state.agent_statuses[self.name] = AgentStatus.FAILED
        
        # Log error
        logger.error(f"Agent {self.name} error: {error}")
        
        # Create message for decision agent
        error_message = self.send_message(
            recipient="decision_agent",
            message_type="error",
            content=error_context,
            priority=5  # High priority
        )
        
        state.messages.append(error_message.dict())
        
        return state
    
    def validate_state(self, state: PipelineState) -> bool:
        """Validate that state is ready for this agent"""
        return state is not None and hasattr(state, 'video_id')
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of agent execution"""
        return {
            "agent": self.name,
            "status": self.status,
            "messages_sent": len([m for m in self.message_history if m.sender == self.name]),
            "messages_received": len([m for m in self.message_history if m.recipient == self.name]),
            "config": self.config
        }
