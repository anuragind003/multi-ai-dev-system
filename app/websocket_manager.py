"""
WebSocket Manager for real-time agent monitoring
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Any
import json
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.agent_sessions: Dict[str, Dict] = {}
        # New: Store resumable graph runs
        self.resumable_runs: Dict[str, Any] = {}
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
        
        # Send welcome message with current sessions
        await self.send_to_websocket(websocket, {
            "type": "connection_established",
            "message": "Connected to Multi-AI Development System",
            "active_sessions": list(self.agent_sessions.keys()),
            "timestamp": datetime.now().isoformat()
        })
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_to_websocket(self, websocket: WebSocket, data: dict):
        try:
            await websocket.send_text(json.dumps(data))
        except Exception as e:
            logger.error(f"Error sending to WebSocket: {e}")
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
    
    async def broadcast(self, data: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
            
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(data))
            except WebSocketDisconnect:
                disconnected.append(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)
    
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
    
    async def send_workflow_status(self, session_id: str, status: str, message: str, data: dict = None):
        """Send workflow status updates"""
        await self.send_agent_event(session_id, "workflow_status", {
            "status": status,
            "message": message,
            "data": data or {}
        })
    
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