"""
WebSocket Message Schema - Backend
Defines the structure for all WebSocket messages between frontend and backend
"""

from typing import Dict, List, Any, Optional, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime

# Common message structure
class WebSocketMessageBase(BaseModel):
    type: str
    session_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    event: Optional[str] = None

# Agent event types
AgentEventType = Literal[
    'node_end',
    'agent_thinking',
    'node_update',
    'agent_action',
    'tool_result',
    'agent_completed',
    'workflow_status'
]

# Agent event message
class AgentEventMessage(WebSocketMessageBase):
    type: str = "agent_event"
    event_type: AgentEventType
    data: Dict[str, Any]

# Workflow status message
class WorkflowStatusMessage(AgentEventMessage):
    event_type: Literal["workflow_status"] = "workflow_status"
    data: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(cls, session_id: str, status: str, message: str, data: Any = None, current_node: str = None):
        """Create a workflow status message"""
        status_data = {
            "status": status,
            "message": message
        }
        if data:
            status_data["data"] = data
        if current_node:
            status_data["current_node"] = current_node
            
        return cls(
            session_id=session_id,
            data=status_data,
            timestamp=datetime.now().isoformat()
        )

# Workflow paused message
class WorkflowPausedMessage(WebSocketMessageBase):
    event: Literal["workflow_paused"] = "workflow_paused"
    data: Dict[str, Any] = Field(...)

# Human response model
class HumanResponseMessage(BaseModel):
    decision: Literal["proceed", "revise", "end"]
    feedback: Optional[Dict[str, Any]] = None

# Error message
class ErrorMessage(WebSocketMessageBase):
    type: Literal["error"] = "error"
    error: str
    details: Optional[Any] = None

# Health check message
class HealthCheckMessage(WebSocketMessageBase):
    type: Literal["health_check"] = "health_check"
    status: Literal["ok"] = "ok"
    version: str
    api_version: str

# Union type for all possible message types
WebSocketMessageTypes = Union[
    AgentEventMessage,
    WorkflowStatusMessage,
    WorkflowPausedMessage,
    ErrorMessage,
    HealthCheckMessage
]
