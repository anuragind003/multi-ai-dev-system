"""
WebSocket Manager for real-time agent monitoring
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Any
import json
import asyncio
import logging
from datetime import datetime
from langchain_core.load.dump import dumpd

logger = logging.getLogger(__name__)

def clean_data(data: Any) -> Any:
    """
    Recursively cleans data to ensure it's JSON serializable.
    Converts complex LangChain objects to strings or dicts.
    """
    if isinstance(data, (str, int, float, bool, type(None))):
        return data
    if isinstance(data, list):
        return [clean_data(item) for item in data]
    if isinstance(data, dict):
        return {key: clean_data(value) for key, value in data.items()}
    
    # For LangChain objects or other complex types, attempt to dump them
    # using LangChain's own serializer, otherwise fall back to a string representation.
    try:
        # dumpd is specifically for langchain serializable objects
        return dumpd(data)
    except Exception:
        # Fallback for any other type
        return str(data)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.agent_sessions: Dict[str, Dict] = {}
        # New: Store resumable graph runs
        self.resumable_runs: Dict[str, Any] = {}
        # Add lock for thread-safe operations
        self._lock = asyncio.Lock()
        self._lock = asyncio.Lock()
    
    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
        
        # Send welcome message with current sessions
        await self.send_to_session(session_id, {
            "type": "connection_established",
            "message": "Connected to Multi-AI Development System",
            "active_sessions": list(self.agent_sessions.keys()),
            "timestamp": datetime.now().isoformat()
        })
    
    async def disconnect(self, session_id: str):
        async with self._lock:
            if session_id in self.active_connections:
                del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_to_session(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                # Clean the message before sending
                cleaned_message = clean_data(message)
                await websocket.send_text(json.dumps(cleaned_message))
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                if session_id in self.active_connections:
                    del self.active_connections[session_id]
    
    def has_active_connections(self) -> bool:
        """Check if there are any active WebSocket connections."""
        return len(self.active_connections) > 0

    async def broadcast(self, data: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
            
        disconnected = []
        # Clean the data before broadcasting
        cleaned_data = clean_data(data)
        for connection in self.active_connections.values():
            try:
                await connection.send_text(json.dumps(cleaned_data))
            except WebSocketDisconnect:
                disconnected.append(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            if conn in self.active_connections:
                del self.active_connections[conn]
    
    async def handle_human_response(self, session_id: str, data: dict):
        """Handle human response to resume a workflow."""
        if session_id in self.resumable_runs:
            graph_runner = self.resumable_runs[session_id]
            await graph_runner.put(data)
        else:
            logger.warning(f"No resumable run found for session_id: {session_id}")

    async def send_agent_event(self, session_id: str, event_type: str, data: dict):
        """Send agent-specific events"""
        event = {
            "type": "agent_event",
            "session_id": session_id,
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(event)
        
        # Update session tracking
        if session_id not in self.agent_sessions:
            self.agent_sessions[session_id] = {
                "started": datetime.now().isoformat(),
                "events": []
            }
        
        self.agent_sessions[session_id]["events"].append(event)
        
        # Keep only last 100 events per session to prevent memory bloat
        if len(self.agent_sessions[session_id]["events"]) > 100:
            self.agent_sessions[session_id]["events"] = self.agent_sessions[session_id]["events"][-100:]
    
    async def send_workflow_status(self, session_id: str, status: str, message: str, data: dict = None, current_node: str = None):
        """Send workflow status update to all connected clients."""
        await self.send_agent_event(
            session_id,
            "workflow_status",
            {
                "status": status,
                "message": message,
                "data": data,
                "current_node": current_node  # Include current node
            }
        )
    
    async def send_agent_thinking(self, session_id: str, agent_name: str, message: str):
        """Send agent thinking/reasoning updates"""
        await self.send_agent_event(session_id, "agent_thinking", {
            "agent": agent_name,
            "message": message
        })
    
    async def send_agent_action(self, session_id: str, agent_name: str, tool_name: str, tool_input: str):
        """Send agent action updates"""
        await self.send_agent_event(session_id, "agent_action", {
            "agent": agent_name,
            "tool": tool_name,
            "input": tool_input
        })
    
    async def send_tool_result(self, session_id: str, agent_name: str, tool_name: str, result: str):
        """Send tool execution results"""
        await self.send_agent_event(session_id, "tool_result", {
            "agent": agent_name,
            "tool": tool_name,
            "result": result[:500] + "..." if len(result) > 500 else result  # Truncate long results
        })
    
    async def send_agent_completed(self, session_id: str, agent_name: str, result: dict):
        """Send agent completion notification"""
        await self.send_agent_event(session_id, "agent_completed", {
            "agent": agent_name,
            "result": result
        })
    
    async def send_error(self, session_id: str, error_message: str, agent_name: str = None):
        """Send error notifications"""
        await self.send_agent_event(session_id, "error", {
            "agent": agent_name,
            "error": error_message
        })
    
    def get_session_history(self, session_id: str) -> List[dict]:
        """Get event history for a specific session"""
        return self.agent_sessions.get(session_id, {}).get("events", [])
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Clean up old sessions to prevent memory leaks"""
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        sessions_to_remove = []
        
        for session_id, session_data in self.agent_sessions.items():
            session_start = datetime.fromisoformat(session_data["started"])
            if session_start < cutoff_time:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.agent_sessions[session_id]
            logger.info(f"Cleaned up old session: {session_id}")

# Global instance
websocket_manager = WebSocketManager()