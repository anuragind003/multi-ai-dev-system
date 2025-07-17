"""
Workflow Endpoints Module

This module contains all workflow-related API endpoints.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, WebSocket, WebSocketDisconnect, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.workflow_service import (
    create_workflow_session,
    get_session_data,
    get_all_sessions,
    run_resumable_graph,
    save_step_results
)
from app.services.approval_service import get_approval_payload_for_stage
from app.websocket_manager import websocket_manager
from models.human_approval import ApprovalPayload
from tools.document_parser import DocumentParser

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/workflow", tags=["workflow"])

# Request/Response models
class WorkflowRequest(BaseModel):
    brd_content: str
    workflow_type: Optional[str] = "phased"
    temperature_strategy: Optional[Dict[str, float]] = None

class WorkflowResponse(BaseModel):
    session_id: str
    status: str
    message: str

class HumanDecisionRequest(BaseModel):
    decision: str
    feedback: Optional[Dict[str, Any]] = None

@router.post("/run_interactive")
async def run_interactive_workflow(
    request: Request, 
    background_tasks: BackgroundTasks,
    brd_file: Optional[UploadFile] = File(None),
    brd_content_json: Optional[str] = None  # NEW: Allow brd_content from form-data
):
    """
    Run an interactive workflow with WebSocket progress monitoring.
    Accepts either a file upload or raw text content.
    """
    brd_content = ""
    file_metadata = {}

    try:
        # Handle form data if brd_file is provided
        if brd_file:
            # Save the uploaded file to a temporary location
            temp_dir = "temp_brd_uploads"
            os.makedirs(temp_dir, exist_ok=True)
            file_path = os.path.join(temp_dir, brd_file.filename)
            
            with open(file_path, "wb") as buffer:
                buffer.write(await brd_file.read())
            
            # Parse the document using the DocumentParser tool
            parser = DocumentParser()
            brd_content = parser.parse(file_path)
            
            file_metadata = {
                "filename": brd_file.filename,
                "content_type": brd_file.content_type,
                "size_kb": round(os.path.getsize(file_path) / 1024, 2)
            }
            logger.info(f"Successfully parsed uploaded BRD file: {brd_file.filename}")

        else:
            # Fallback to JSON body for raw text input
            body = await request.json()
            inputs = body.get("inputs", {})
            brd_content = inputs.get("brd_content", "")
            if not brd_content:
                raise HTTPException(status_code=400, detail="BRD content is required, either as a file upload or as text in the 'brd_content' field.")

        if not brd_content.strip():
            raise HTTPException(status_code=400, detail="The provided BRD document appears to be empty or could not be parsed.")

        # Generate a unique session ID for this workflow run
        session_id = f"session_{uuid.uuid4()}"
        
        # Store session info using workflow service
        session_data = {
            "start_time": datetime.now().isoformat(),
            "status": "running",
            "brd_content": brd_content,
            "file_metadata": file_metadata  # Store file info
        }
        
        from app.services.workflow_service import update_session_data
        update_session_data(session_id, session_data)
        
        # Send workflow status
        background_tasks.add_task(
            websocket_manager.send_workflow_status,
            session_id, 
            "started", 
            "Workflow started", 
            {
                "brd_content_preview": brd_content[:100] + "...",
                **file_metadata  # Add file metadata to the status message
            }
        )
        
        # Start workflow consumer in background
        background_tasks.add_task(run_workflow_consumer, session_id, brd_content)
        
        # Return session ID to client
        logger.info(f"Starting interactive workflow for session {session_id}")
        return {"status": "started", "session_id": session_id}
        
    except HTTPException as http_exc:
        # Re-raise HTTP exceptions to be handled by FastAPI
        raise http_exc
    except Exception as e:
        logger.exception(f"Error running interactive workflow: {e}")
        return JSONResponse(
            status_code=500, 
            content={"status": "error", "message": str(e)}
        )

@router.post("/resume/{session_id}")
async def resume_interactive_workflow(session_id: str, request: Request, background_tasks: BackgroundTasks):
    """Resume an interactive workflow."""
    body = await request.json()
    
    # Extract decision from the correct nested structure
    user_feedback = body.get("user_feedback", {})
    decision = user_feedback.get("decision") or body.get("decision")
    
    logger.info(f"Resume request body structure: {body.keys()}")
    logger.info(f"User feedback structure: {user_feedback}")
    logger.info(f"Extracted decision: {decision}")
    
    if not decision:
        logger.error(f"Decision not found in body: {body}")
        return {"status": "error", "message": "Decision not provided"}, 400

    # Check if this is a termination request
    if decision == "end":
        # Send termination notification to frontend
        try:
            await websocket_manager.send_workflow_status(
                session_id,
                "terminated",
                "Workflow terminated by user",
                {"reason": "user_rejection"}
            )
            logger.info(f"Sent termination status for session {session_id}")
        except Exception as e:
            logger.error(f"Error sending termination status: {e}")
        
        return {"status": "terminated", "session_id": session_id, "message": "Workflow terminated by user"}

    # Retrieve the original BRD content from the session storage
    session_data = get_session_data(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    original_brd_content = session_data.get("brd_content")
    if not original_brd_content:
        raise HTTPException(status_code=404, detail=f"BRD content for session {session_id} not found")

    # Use the entire user_feedback as the feedback payload
    feedback_payload = user_feedback
    
    logger.info(f"Resuming workflow for session {session_id} with decision: {decision}")
    
    # Pass the original BRD content and the feedback payload to the consumer
    background_tasks.add_task(run_workflow_consumer, session_id, original_brd_content, feedback_payload)
    
    return {"status": "resumed", "session_id": session_id}

@router.post("/create", response_model=WorkflowResponse)
async def create_workflow_session_endpoint(request: WorkflowRequest):
    """Create a new workflow session with enhanced recovery capabilities"""
    try:
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        result = await create_workflow_session(session_id, request.brd_content)
        
        return WorkflowResponse(
            session_id=result["session_id"],
            status=result["status"],
            message=result["message"]
        )
        
    except Exception as e:
        logger.error(f"Failed to create workflow session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/{session_id}")
async def get_workflow_results(session_id: str):
    """Get all saved workflow results for a session."""
    try:
        results = {}
        
        # Get from session data
        session_data = get_session_data(session_id)
        if session_data and "session_results" in session_data:
            results = session_data["session_results"]
        
        # Also try to load from files if available
        output_dir = os.path.join("output", "interactive_runs", session_id, "approval_results")
        if os.path.exists(output_dir):
            file_results = {}
            approval_types = [
                ("brd_analysis", "brd_analysis"),
                ("tech_stack", "tech_stack_recommendation"),  # Map frontend key to actual file name
                ("system_design", "system_design"),
                ("implementation_plan", "implementation_plan")
            ]
            
            for result_key, file_prefix in approval_types:
                latest_file = os.path.join(output_dir, f"{file_prefix}_latest.json")
                if os.path.exists(latest_file):
                    try:
                        with open(latest_file, 'r', encoding='utf-8') as f:
                            file_data = json.load(f)
                            file_results[result_key] = {  # Use result_key for frontend compatibility
                                "data": file_data.get("approval_data", {}),
                                "timestamp": file_data.get("timestamp", 0),
                                "filepath": latest_file
                            }
                    except Exception as e:
                        logging.error(f"Error reading {latest_file}: {e}")
            
            # Merge file results with memory results
            results.update(file_results)
        
        return {"session_id": session_id, "results": results}
        
    except Exception as e:
        logging.error(f"Error getting workflow results for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving results: {str(e)}")

@router.get("/status/{session_id}")
async def get_workflow_status(session_id: str):
    """Get the current status of a workflow session."""
    try:
        # Get results to see which steps have been completed
        session_data = get_session_data(session_id)
        results = session_data.get("session_results", {}) if session_data else {}
        
        # Create a status summary
        status = {
            "session_id": session_id,
            "completed_steps": list(results.keys()),
            "step_details": {
                step: {
                    "completed": True,
                    "timestamp": info.get("timestamp", 0),
                    "data_preview": {
                        key: str(value)[:100] + ("..." if len(str(value)) > 100 else "")
                        for key, value in info.get("data", {}).items()
                    } if isinstance(info.get("data"), dict) else "No data available"
                }
                for step, info in results.items()
            },
            "total_steps_completed": len(results),
            "next_expected_steps": [
                "brd_analysis", "tech_stack", "tech_stack_recommendation", "system_design", "implementation_plan"
            ][len(results):len(results)+1] if len(results) < 4 else ["workflow_complete"]
        }
        
        return status
        
    except Exception as e:
        logging.error(f"Error getting workflow status for session {session_id}: {e}")
        return {
            "session_id": session_id, 
            "error": str(e), 
            "completed_steps": [],
            "total_steps_completed": 0
        }

# Consumer wrapper function
async def run_workflow_consumer(session_id: str, brd_content: str, user_feedback: dict = None):
    """Consumer wrapper for run_resumable_graph to ensure the generator is properly iterated"""
    # Import from correct locations instead of app.main
    from utils.shared_memory_hub import get_shared_memory_hub
    from rag_manager import get_rag_manager
    from app.services.workflow_service import get_enhanced_workflow, get_next_stage_name, update_session_data
    
    try:
        logger.info(f"Starting workflow consumer for session: {session_id}")
        interrupt_detected = False

        # Get the workflow runnable using the enhanced workflow
        workflow_components = await get_enhanced_workflow(session_id)
        workflow = workflow_components["graph"]

        # Define the base output directory relative to the project root
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        base_output_dir = os.path.join(project_root, "output", "interactive_runs", session_id)
        os.makedirs(base_output_dir, exist_ok=True)
        
        # Define specific output directories
        code_gen_output_dir = os.path.join(project_root, "output", "code_generation")
        os.makedirs(code_gen_output_dir, exist_ok=True)
        
        # Create a CodeExecutionTool with the correct output directory
        from tools.code_execution_tool import CodeExecutionTool
        code_execution_tool = CodeExecutionTool(output_dir=code_gen_output_dir)

        # Get memory and rag_manager from proper sources
        memory = get_shared_memory_hub()
        rag_manager = get_rag_manager()

        config = {
            "configurable": {
                "thread_id": session_id,
                "memory": memory,
                "rag_manager": rag_manager,
                "code_execution_tool": code_execution_tool,
                "run_output_dir": code_gen_output_dir # Use centralized dir
            },
            "recursion_limit": 10000  # Increase recursion limit to handle complex workflows
        }
        
        # Save the original BRD content to avoid starting over
        session_data = get_session_data(session_id) or {}
        if "brd_content" not in session_data:
            session_data["brd_content"] = brd_content
            update_session_data(session_id, session_data)

        # Determine if this is a new workflow or resuming
        if user_feedback:
            # This is a resumption - handle user feedback
            decision = user_feedback.get("decision", "unknown")
            logger.info(f"[PROCESSING HUMAN FEEDBACK] Decision: {decision} for session {session_id}")
            
            # Update the workflow state with the human decision
            state_update = {
                "human_decision": decision,
                "user_feedback": user_feedback,
                "resume_from_approval": True
            }
            
            # Determine which approval node to update based on current state
            try:
                current_state = workflow.get_state(config)
                if current_state and current_state.next:
                    next_nodes = list(current_state.next)
                    logger.info(f"Next nodes before resumption: {next_nodes}")
                    
                    # Update the state to continue from the approval node
                    for next_node in next_nodes:
                        if "human_approval" in next_node:
                            logger.info(f"Updating state at node: {next_node}")
                            await asyncio.to_thread(workflow.update_state, config, state_update, as_node=next_node)
                            break
                else:
                    logger.warning("No next nodes found in current state")
                    
            except Exception as e:
                logger.error(f"Error updating workflow state for resumption: {e}")
            
            # For resumption, use None as input to continue from interrupt
            initial_state = None
            
            logger.info(f"[STAR] Resuming workflow {session_id} with decision: {decision}")
        else:
            # This is a new workflow start
            initial_state = {
                "brd_content": brd_content,
                "user_feedback": None,
                "resume_from_approval": False
            }
            logger.info(f"[NEW] Starting new workflow {session_id}")
        
        # First, explicitly broadcast that we're starting
        await websocket_manager.send_to_session(session_id, {
            "type": "workflow_event",
            "event": "workflow_started" if not user_feedback else "workflow_resumed",
            "data": {
                "session_id": session_id,
                "message": "Workflow processing started" if not user_feedback else f"Workflow resumed with human decision: {user_feedback.get('decision', 'unknown')}"
            }
        })

        # Use astream to handle the workflow execution
        async for event in workflow.astream(initial_state, config):
            logger.info(f"Workflow step: {list(event.keys()) if isinstance(event, dict) else str(event)[:100]}")
            
            # Broadcast workflow updates
            await websocket_manager.send_to_session(session_id, {
                "type": "workflow_event", 
                "event": "workflow_step",
                "data": {
                    "session_id": session_id,
                    "step_data": event
                }
            })
            
            # Check if this step contains an interrupt
            if isinstance(event, dict) and "__interrupt__" in event:
                logger.info(f"Detected workflow interrupt: {event}")
                interrupt_detected = True
                
                # Extract approval data from the interrupt
                interrupt_data = event.get("__interrupt__", {})
                approval_payload = None
                
                # Handle different interrupt data formats
                if isinstance(interrupt_data, list) and len(interrupt_data) > 0:
                    interrupt_info = interrupt_data[0]
                    approval_payload = interrupt_info.get("value", {})
                elif isinstance(interrupt_data, dict) and interrupt_data:
                    approval_payload = interrupt_data
                
                # If interrupt data is empty, get approval data from workflow state
                if not approval_payload or approval_payload == {}:
                    logger.info("Interrupt data is empty, extracting from workflow state")
                    try:
                        current_state = workflow.get_state(config)
                        current_state_data = current_state.values if current_state else {}
                        next_nodes = list(current_state.next) if current_state and current_state.next else []
                        
                        # Map next nodes to approval types and data keys
                        node_to_approval_map = {
                            "human_approval_brd_node": ("brd_analysis", "requirements_analysis"),
                            "human_approval_tech_stack_node": ("tech_stack_recommendation", "tech_stack_recommendation"), 
                            "human_approval_system_design_node": ("system_design", "system_design"),
                            "human_approval_plan_node": ("implementation_plan", "implementation_plan")
                        }
                        
                        # Find which approval node we're at
                        for next_node in next_nodes:
                            if next_node in node_to_approval_map:
                                approval_type, data_key = node_to_approval_map[next_node]
                                approval_data = current_state_data.get(data_key, {})
                                
                                # Ensure approval data is properly serialized
                                if hasattr(approval_data, 'model_dump'):
                                    approval_data = approval_data.model_dump()
                                elif hasattr(approval_data, 'dict'):
                                    approval_data = approval_data.dict()
                                elif not isinstance(approval_data, dict):
                                    # Handle non-dict data types
                                    try:
                                        import json
                                        if isinstance(approval_data, str):
                                            # Try parsing if it's a JSON string
                                            approval_data = json.loads(approval_data)
                                        else:
                                            # Convert to dict representation
                                            approval_data = {
                                                "content": str(approval_data),
                                                "type": type(approval_data).__name__,
                                                "serialized": True
                                            }
                                    except (json.JSONDecodeError, Exception):
                                        approval_data = {
                                            "content": str(approval_data),
                                            "type": type(approval_data).__name__,
                                            "serialized": True
                                        }
                                
                                approval_payload = {
                                    "message": f"Please review the {approval_type.replace('_', ' ')}. Do you approve?",
                                    "data": approval_data,  # Changed from 'details' to 'data'
                                    "current_node": next_node,
                                    "step_name": approval_type
                                }
                                
                                logger.info(f"Created approval payload for {approval_type}: {next_node}")
                                break
                    
                    except Exception as e:
                        logger.error(f"Error extracting approval data from state: {e}")
                        # Fallback approval payload
                        approval_payload = {
                            "message": "Please review and approve to continue",
                            "data": {},  # Changed from 'details' to 'data'
                            "current_node": "unknown",
                            "step_name": "approval_required"
                        }
                
                if approval_payload:
                    approval_type = approval_payload.get("step_name", "unknown")
                    paused_at_node = approval_payload.get("current_node", "unknown")
                    
                    if approval_type != "unknown":
                        await save_step_results(session_id, approval_type, approval_payload.get("data", {}), event)

                    # Send standardized approval payload to frontend
                    await websocket_manager.send_to_session(session_id, {
                        "type": "workflow_event",
                        "event": "workflow_paused",
                        "data": {
                            "session_id": session_id,
                            "paused_at": paused_at_node,
                            "approval_type": approval_type,
                            "payload": approval_payload
                        }
                    })
                    logger.info(f"Sent approval request for {approval_type} to frontend")
                    logger.info(f"Approval payload structure: {list(approval_payload.keys())}")
                    
                    # Enhanced logging for data structure
                    approval_data = approval_payload.get('data', {})
                    if isinstance(approval_data, dict):
                        logger.info(f"Approval data keys: {list(approval_data.keys())}")
                        logger.info(f"Approval data types: {[(k, type(v).__name__) for k, v in approval_data.items()]}")
                    else:
                        logger.info(f"Approval data is not a dict - type: {type(approval_data).__name__}, value: {str(approval_data)[:100]}...")
                else:
                    logger.error("Could not create approval payload from interrupt")
                
                break  # Stop processing when we hit an interrupt

        # Check if we reached the end without detecting an interrupt
        if not interrupt_detected:
            logger.warning(f"Workflow completed without detecting any interruption points for session {session_id}")
            
            # Check final state to see why workflow ended
            try:
                final_state = workflow.get_state(config)
                
                if final_state and final_state.next:
                    logger.info(f"Workflow ended but has remaining nodes: {final_state.next}")
                    
                    # If we have remaining nodes, this might be an interrupt that we missed
                    # Let's check if the next node is a human approval node
                    next_nodes = list(final_state.next) if final_state.next else []
                    human_approval_nodes = [
                        "human_approval_brd_node",
                        "human_approval_tech_stack_node", 
                        "human_approval_system_design_node",
                        "human_approval_plan_node"
                    ]
                    
                    for next_node in next_nodes:
                        if next_node in human_approval_nodes:
                            logger.info(f"Found pending human approval node: {next_node}")
                            
                            # Extract the current state data to create approval payload
                            current_state_data = final_state.values
                            
                            # Map node names to approval types and data keys
                            node_to_approval_map = {
                                "human_approval_brd_node": ("brd_analysis", "requirements_analysis"),
                                "human_approval_tech_stack_node": ("tech_stack_recommendation", "tech_stack_recommendation"),
                                "human_approval_system_design_node": ("system_design", "system_design"),
                                "human_approval_plan_node": ("implementation_plan", "implementation_plan")
                            }
                            
                            approval_type, data_key = node_to_approval_map.get(next_node, ("unknown", "unknown"))
                            
                            if approval_type != "unknown":
                                approval_data = current_state_data.get(data_key, {})
                                
                                # Ensure approval data is properly serialized (fallback case)
                                if hasattr(approval_data, 'model_dump'):
                                    approval_data = approval_data.model_dump()
                                elif hasattr(approval_data, 'dict'):
                                    approval_data = approval_data.dict()
                                elif not isinstance(approval_data, dict):
                                    # Handle non-dict data types
                                    try:
                                        import json
                                        if isinstance(approval_data, str):
                                            # Try parsing if it's a JSON string
                                            approval_data = json.loads(approval_data)
                                        else:
                                            # Convert to dict representation
                                            approval_data = {
                                                "content": str(approval_data),
                                                "type": type(approval_data).__name__,
                                                "serialized": True
                                            }
                                    except (json.JSONDecodeError, Exception):
                                        approval_data = {
                                            "content": str(approval_data),
                                            "type": type(approval_data).__name__,
                                            "serialized": True
                                        }
                                
                                # Create approval payload
                                approval_payload = {
                                    "message": f"Please review the {approval_type.replace('_', ' ')}. Do you approve?",
                                    "data": approval_data,
                                    "current_node": next_node,
                                    "step_name": approval_type
                                }
                                
                                await save_step_results(session_id, approval_type, approval_data, current_state_data)
                                
                                # Send approval request to frontend
                                await websocket_manager.send_to_session(session_id, {
                                    "type": "workflow_event",
                                    "event": "workflow_paused",
                                    "data": {
                                        "session_id": session_id,
                                        "paused_at": next_node,
                                        "approval_type": approval_type,
                                        "payload": approval_payload
                                    }
                                })
                                interrupt_detected = True
                                break
                    
                    if not interrupt_detected:
                        # Send a message about the remaining work
                        await websocket_manager.send_to_session(session_id, {
                            "type": "workflow_event",
                            "event": "workflow_incomplete",
                            "data": {
                                "session_id": session_id,
                                "message": f"Workflow completed but has remaining nodes: {final_state.next}",
                                "remaining_nodes": next_nodes
                            }
                        })
                else:
                    logger.info(f"Workflow truly completed - no remaining nodes")
                    # Send completion message
                    await websocket_manager.send_to_session(session_id, {
                        "type": "workflow_event",
                        "event": "workflow_completed",
                        "data": {
                            "session_id": session_id,
                            "message": "Workflow completed successfully"
                        }
                    })
            except Exception as state_check_error:
                logger.error(f"Error checking final workflow state: {state_check_error}")
            
    except Exception as e:
        logger.error(f"Workflow consumer error: {str(e)}", exc_info=True)
        await websocket_manager.send_error(
            session_id,
            f"Workflow execution error: {str(e)}"
        )

@router.websocket("/stream/{session_id}")
async def stream_workflow_events_ws(websocket: WebSocket, session_id: str):
    """Handles WebSocket connections for a given session, keeping them alive to receive streamed events."""
    logger.info(f"WebSocket connection attempt for session: {session_id}")
    
    try:
        await websocket_manager.connect(session_id, websocket)
        logger.info(f"WebSocket connected successfully for session: {session_id}")
        
        # Keep the connection alive, waiting for messages or disconnect
        while True:
            # This loop will keep the connection open. We can optionally handle
            # incoming messages here for features like ping/pong in the future.
            await websocket.receive_text() 
    except WebSocketDisconnect:
        logger.info(f"WebSocket client for session {session_id} disconnected.")
        await websocket_manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        await websocket_manager.disconnect(session_id)