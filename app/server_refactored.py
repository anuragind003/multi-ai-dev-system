"""
Refactored Multi-AI Development System Server

This is the main server file that brings together all the modular components
for the Multi-AI Development System API.
"""

import asyncio
import json
import logging
import mimetypes
import os
import signal
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from langserve import add_routes
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel

# Core application setup
from app.core.setup import (
    create_app, 
    setup_openapi_schema, 
    setup_startup_tasks, 
    setup_shutdown_tasks,
    get_temperature_strategy,
    API_VERSION, 
    SERVER_VERSION
)

# Service imports
from app.services.workflow_service import (
    get_all_sessions,
    get_session_data,
    update_session_data
)
from app.services.approval_service import get_approval_payload_for_stage

# Endpoint routers
from app.endpoints.workflow_endpoints import router as workflow_router

# WebSocket and middleware
from app.websocket_manager import websocket_manager
from app.websocket_schema import (
    WebSocketMessageBase, 
    AgentEventMessage, 
    WorkflowStatusMessage, 
    WorkflowPausedMessage,
    ErrorMessage,
    HealthCheckMessage
)

# Recovery endpoints
from app.recovery_endpoints import recovery_router

# Utilities and config
from utils.windows_logging_fix import setup_windows_compatible_logging
from config import get_llm

# Initialize logger
logger = setup_windows_compatible_logging()

# Define response models
class VersionResponse(BaseModel):
    api_version: str = API_VERSION
    server_version: str = SERVER_VERSION
    compatible: bool = True

# Create the FastAPI application
app = create_app()

# Setup OpenAPI schema
setup_openapi_schema(app)

# Include routers
app.include_router(recovery_router)
app.include_router(workflow_router)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    await setup_startup_tasks(app)

@app.on_event("shutdown") 
async def shutdown_event():
    """Cleanup on shutdown."""
    await setup_shutdown_tasks(app)

@app.get("/")
def read_root():
    """Root endpoint providing API information and navigation."""
    return {
        "message": "Multi-AI Development System API",
        "documentation": "/docs",
        "examples": "/static/examples.html",
        "api": "/api/workflow",
        "temperature_strategy": get_temperature_strategy()["agent_temperatures"]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint with temperature strategy info."""
    return {
        "status": "healthy",
        "temperature_strategy_enabled": True,
        "temperature_ranges": {
            "analytical": "0.1-0.2",
            "creative": "0.3-0.4",
            "code_generation": "0.1"
        }
    }

@app.get("/api/health", response_model=VersionResponse)
async def api_health_check():
    """
    Health check endpoint that returns version information
    and compatibility status between frontend and backend
    """
    return VersionResponse(
        api_version=API_VERSION,
        server_version=SERVER_VERSION,
        compatible=True
    )

@app.websocket("/ws/agent-monitor")
async def websocket_agent_monitor_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time agent monitoring and session management."""
    # Use a unique ID for the connection itself
    connection_id = str(uuid.uuid4())
    await websocket_manager.connect(connection_id, websocket)
    
    # Send health check message when client connects
    try:
        health_msg = HealthCheckMessage(
            version=SERVER_VERSION,
            api_version=API_VERSION
        ).dict()
        await websocket.send_text(json.dumps(health_msg))
        
        # Check for any interrupted sessions that need attention
        active_sessions = get_all_sessions().keys()
        
        # For each active session, check if it's paused at a human approval node
        for session_id in active_sessions:
            try:
                # Use app.state.workflow_runnable if available
                if hasattr(app.state, 'workflow_runnable') and app.state.workflow_runnable:
                    workflow = app.state.workflow_runnable
                    config = {"configurable": {"thread_id": session_id}}
                    
                    # Get current state to check if it's paused
                    current_state = workflow.get_state(config)
                    
                    if current_state and current_state.next:
                        paused_at_nodes = current_state.next
                        paused_at_node = paused_at_nodes[0] if paused_at_nodes else None
                        
                        if paused_at_node and "human_approval" in paused_at_node:
                            logger.info(f"Found interrupted session {session_id} at node {paused_at_node}")
                            
                            # Determine approval type using the same logic as the main consumer
                            node_to_stage_map = {
                                "brd": "brd_analysis",
                                "tech_stack": "tech_stack_recommendation", 
                                "system_design": "system_design",
                                "design": "system_design",
                                "plan": "implementation_plan"
                            }
                            
                            approval_type = "unknown"
                            for node_key, stage in node_to_stage_map.items():
                                if node_key in paused_at_node:
                                    approval_type = stage
                                    break
                            
                            # Create standardized approval payload
                            try:
                                if approval_type != "unknown":
                                    approval_payload = await get_approval_payload_for_stage(
                                        approval_type, 
                                        current_state.values
                                    )
                                    approval_data = approval_payload.data
                                else:
                                    # Fallback for unknown cases
                                    from app.services.approval_service import extract_brd_analysis_data
                                    approval_data = await extract_brd_analysis_data(current_state.values)
                                    from models.human_approval import ApprovalPayload
                                    approval_payload = ApprovalPayload(
                                        step_name="unknown",
                                        display_name="Unknown Stage",
                                        data=approval_data,
                                        instructions="Please review the workflow state.",
                                        is_revision=False,
                                        previous_feedback=None
                                    )
                            except Exception as e:
                                logger.error(f"Error creating approval payload: {e}")
                                approval_data = {"error": str(e)}
                                from models.human_approval import ApprovalPayload
                                approval_payload = ApprovalPayload(
                                    step_name="error",
                                    display_name="Error",
                                    data=approval_data,
                                    instructions="An error occurred while preparing the approval data.",
                                    is_revision=False,
                                    previous_feedback=None
                                )
                            
                            # Store paused session info (if needed)
                            # paused_sessions[session_id] = {
                            #     "session_id": session_id,
                            #     "paused_at": paused_at_nodes,
                            #     "approval_type": approval_type,
                            #     "approval_data": approval_data,
                            #     "payload": approval_payload.model_dump()
                            # }
            except Exception as e:
                logger.error(f"Error checking session {session_id}: {e}")
    except Exception as e:
        logger.error(f"Failed to send initial messages: {e}")
    
    try:
        while True:
            # Wait for messages from the client
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                
                # Handle health check requests
                if message.get("type") == "health_check_request":
                    health_msg = HealthCheckMessage(
                        version=SERVER_VERSION,
                        api_version=API_VERSION
                    ).dict()
                    await websocket.send_text(json.dumps(health_msg))
                
                # Handle human decision responses
                elif message.get("type") == "human_response" and message.get("session_id"):
                    session_id = message.get("session_id")
                    decision = message.get("decision")
                    feedback = message.get("feedback", {})
                    
                    if session_id and decision:
                        await websocket_manager.handle_human_response(session_id, {
                            "decision": decision,
                            "feedback": feedback
                        })
                    else:
                        await websocket_manager.send_error(None, "Invalid human response format")
            except json.JSONDecodeError:
                logger.warning(f"Received invalid JSON from client {connection_id}")
                continue
            except Exception as e:
                logger.error(f"Error handling client message: {e}")
                await websocket_manager.send_error(None, f"Error processing message: {str(e)}")
            
    except WebSocketDisconnect:
        logging.info(f"WebSocket client {connection_id} disconnected.")
        await websocket_manager.disconnect(connection_id)
    except Exception as e:
        logging.error(f"WebSocket error for client {connection_id}: {e}")
        await websocket_manager.disconnect(connection_id)

@app.post("/api/workflow-with-monitoring")
async def workflow_with_monitoring(request: Request):
    """Enhanced workflow endpoint with WebSocket monitoring support."""
    json_body = await request.json()
    
    # Generate session ID for this workflow run
    session_id = str(uuid.uuid4())
    
    # Add session_id to the request for callback handler
    json_body["session_id"] = session_id
    
    # Notify WebSocket clients that a new workflow is starting
    await websocket_manager.send_workflow_status(
        session_id, 
        "workflow_started", 
        "Multi-AI Development Workflow Started",
        {"brd_content_length": len(json_body.get("brd_content", ""))}
    )
    
    try:
        # Run the workflow
        workflow_runnable = app.state.workflow_runnable
        result = workflow_runnable.invoke(json_body)
        
        # Notify completion
        await websocket_manager.send_workflow_status(
            session_id,
            "workflow_completed",
            "Multi-AI Development Workflow Completed Successfully",
            {"result_keys": list(result.keys()) if isinstance(result, dict) else []}
        )
        
        return {
            "session_id": session_id,
            "result": result,
            "status": "completed"
        }
        
    except Exception as e:
        # Notify error
        await websocket_manager.send_error(
            session_id,
            f"Workflow failed: {str(e)}"
        )
        
        return {
            "session_id": session_id,
            "error": str(e),
            "status": "failed"
        }

# Get LLM for additional routes
try:
    llm = get_llm()
    
    # Create a prompt template
    prompt_template = PromptTemplate.from_template("You are a helpful assistant. {question}")
    
    # Create a runnable sequence
    assistant_chain = prompt_template | llm
    
    # Add additional route
    try:
        add_routes(
            app,
            assistant_chain,
            path="/api/llm"
        )
    except Exception as e:
        logger.warning(f"Error adding LLM routes: {str(e)}")
        # Add a placeholder route so the API still works
        @app.post("/api/llm")
        async def manual_llm_route(request: Request):
            """Manual implementation of LLM route if LangServe route registration fails."""
            json_body = await request.json()
            result = assistant_chain.invoke(json_body)
            return result
except Exception as e:
    logger.error(f"Error setting up LLM: {e}")

# Add endpoint to retrieve available agents and their temperature settings
@app.get("/api/temperature-strategy")
async def get_temperature_strategy_endpoint():
    """Get the temperature strategy for all agents."""
    return get_temperature_strategy()

@app.get("/api/agent-sessions")
async def get_active_sessions():
    """Get list of active agent sessions."""
    return {
        "active_sessions": list(websocket_manager.agent_sessions.keys()),
        "total_connections": len(websocket_manager.active_connections),
        "sessions": {
            session_id: {
                "started": session_data["started"],
                "event_count": len(session_data["events"])
            }
            for session_id, session_data in websocket_manager.agent_sessions.items()
        }
    }

@app.get("/api/agent-sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """Get event history for a specific agent session."""
    history = websocket_manager.get_session_history(session_id)
    return {
        "session_id": session_id,
        "event_count": len(history),
        "events": history
    }

@app.get("/api/session-files/{session_id}")
async def get_session_files(session_id: str):
    """
    Get the file tree for a specific session's generated output.
    This now checks the centralized output directory.
    """
    # The primary, centralized output directory for all code generation
    session_output_dir = os.path.join("output", "code_generation")
    
    if not os.path.exists(session_output_dir):
        # Fallback for older, session-specific directories if needed
        session_output_dir = os.path.join("output", "interactive_runs", session_id, "generated_code")
        if not os.path.exists(session_output_dir):
            raise HTTPException(status_code=404, detail=f"No generated code output directory found for session {session_id}")

    def _get_file_tree(base_path: str, current_path: str):
        tree = []
        for item in os.listdir(current_path):
            item_path = os.path.join(current_path, item)
            relative_path = os.path.relpath(item_path, base_path)
            if os.path.isdir(item_path):
                tree.append({
                    "name": item,
                    "type": "directory",
                    "path": relative_path.replace("\\", "/"),
                    "children": _get_file_tree(base_path, item_path)
                })
            else:
                tree.append({
                    "name": item,
                    "type": "file",
                    "path": relative_path.replace("\\", "/"),
                    "size": os.path.getsize(item_path)
                })
        return tree

    try:
        file_tree = _get_file_tree(session_output_dir, session_output_dir)
        return {"session_id": session_id, "files": file_tree}
    except Exception as e:
        logger.error(f"Error generating file tree for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating file tree: {str(e)}")

@app.get("/api/session-file-content/{session_id}/{file_path:path}")
async def get_session_file_content(session_id: str, file_path: str):
    """
    Get the content of a specific file within a session's generated output.
    This now checks the centralized output directory.
    """
    import urllib.parse
    
    # Decode the file path in case it was URL encoded
    file_path = urllib.parse.unquote(file_path)
    logger.info(f"Fetching file content for session {session_id}, file: {file_path}")
    
    # Centralized directory
    base_dir = os.path.join("output", "code_generation")
    
    # Sanitize file_path to prevent directory traversal
    abs_file_path = os.path.abspath(os.path.join(base_dir, file_path))
    
    # Fallback to session-specific directory
    if not os.path.exists(abs_file_path):
        base_dir = os.path.join("output", "interactive_runs", session_id, "generated_code")
        abs_file_path = os.path.abspath(os.path.join(base_dir, file_path))
        logger.info(f"Fallback to session-specific directory: {abs_file_path}")

    if not abs_file_path.startswith(os.path.abspath(base_dir)):
        logger.error(f"Security violation: Path traversal attempt for {file_path}")
        raise HTTPException(status_code=403, detail="Access denied: Invalid file path.")

    if not os.path.exists(abs_file_path):
        logger.error(f"File not found: {abs_file_path}")
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
    if not os.path.isfile(abs_file_path):
        logger.error(f"Path is not a file: {abs_file_path}")
        raise HTTPException(status_code=404, detail=f"Path is not a file: {file_path}")

    try:
        with open(abs_file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Determine mimetype for frontend
        mime_type, _ = mimetypes.guess_type(abs_file_path)
        
        logger.info(f"Successfully read file {file_path}, content length: {len(content)}")
        
        return {
            "session_id": session_id,
            "file_path": file_path,
            "content": content,
            "mime_type": mime_type or "text/plain"
        }
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error reading file {file_path}: {e}")
        raise HTTPException(status_code=422, detail=f"Cannot decode file as text: {str(e)}")
    except Exception as e:
        logger.error(f"Error reading file {file_path} for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 