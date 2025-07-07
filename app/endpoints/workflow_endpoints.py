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

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, WebSocket, WebSocketDisconnect
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
async def run_interactive_workflow(request: Request, background_tasks: BackgroundTasks):
    """Run an interactive workflow with WebSocket progress monitoring."""
    try:
        body = await request.json()
        inputs = body.get("inputs", {})
        brd_content = inputs.get("brd_content", "")
        
        if not brd_content:
            return JSONResponse(
                status_code=400, 
                content={"status": "error", "message": "BRD content is required"}
            )
        
        # Generate a unique session ID for this workflow run
        session_id = f"session_{uuid.uuid4()}"
        
        # Store session info using workflow service
        session_data = {
            "start_time": datetime.now().isoformat(),
            "status": "running",
            "brd_content": brd_content
        }
        
        from app.services.workflow_service import update_session_data
        update_session_data(session_id, session_data)
        
        # Send workflow status
        background_tasks.add_task(
            websocket_manager.send_workflow_status,
            session_id, 
            "started", 
            "Workflow started", 
            {"brd_content_preview": brd_content[:100] + "..."}
        )
        
        # Start workflow consumer in background
        background_tasks.add_task(run_workflow_consumer, session_id, brd_content)
        
        # Return session ID to client
        logger.info(f"Starting interactive workflow for session {session_id}")
        return {"status": "started", "session_id": session_id}
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
            for approval_type in ["brd_analysis", "tech_stack", "system_design", "implementation_plan"]:
                latest_file = os.path.join(output_dir, f"{approval_type}_latest.json")
                if os.path.exists(latest_file):
                    try:
                        with open(latest_file, 'r', encoding='utf-8') as f:
                            file_data = json.load(f)
                            file_results[approval_type] = {
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
                "brd_analysis", "tech_stack", "system_design", "implementation_plan"
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
    try:
        logger.info(f"Starting workflow consumer for session: {session_id}")
        interrupt_detected = False

        # Save the original BRD content to avoid starting over
        session_data = get_session_data(session_id) or {}
        if "brd_content" not in session_data:
            session_data["brd_content"] = brd_content
            from app.services.workflow_service import update_session_data
            update_session_data(session_id, session_data)

        # Enhanced logging for user feedback
        if user_feedback:
            decision = user_feedback.get("decision", "unknown")
            logger.info(f"[PROCESSING HUMAN FEEDBACK] Decision: {decision} for session {session_id}")
            
        # If we have user feedback indicating an approval, explicitly log it
        if user_feedback and user_feedback.get("decision") in ["proceed", "continue"]:
            logger.info(f"[STAR] Explicit approval received for session {session_id}. "
                        f"Will ensure continuation to next step.")
            
            # Set a marker to indicate this session should move forward
            from app.services.workflow_service import get_next_stage_name, update_session_data
            current_stage = session_data.get("last_approval_type", "brd_analysis")
            session_updates = {
                "approved_for_next_step": True,
                "current_approved_stage": current_stage,
                "next_stage": get_next_stage_name(current_stage),
                "human_decision": user_feedback.get("decision")
            }
            update_session_data(session_id, session_updates)
            
            logger.info(f"Session data updated with approval: {session_updates}")
        
        # First, explicitly broadcast that we're starting
        await websocket_manager.send_to_session(session_id, {
            "type": "workflow_event",
            "event": "workflow_started" if not user_feedback else "workflow_resumed",
            "data": {
                "session_id": session_id,
                "message": "Workflow processing started" if not user_feedback else f"Workflow resumed with human decision: {user_feedback.get('decision', 'unknown')}"
            }
        })
        
        async for event in run_resumable_graph(session_id, brd_content, user_feedback):
            # Log all events to help diagnose issues
            logger.info(f"Workflow event: {str(event)[:200]}...")
            
            if isinstance(event, dict):
                # First, broadcast all events to keep the UI updated
                await websocket_manager.send_to_session(session_id, {
                    "type": "workflow_event",
                    "event": "workflow_update",
                    "data": {
                        "session_id": session_id,
                        "event": event
                    }
                })
                
                # Check for interrupt event - NEW FORMAT: {'__interrupt__': ()}
                if '__interrupt__' in event:
                    logger.info(f"Detected interrupt event: {event}")
                    interrupt_detected = True
                    
                    # Since the interrupt doesn't include node info, get it from workflow state
                    from app.services.workflow_service import get_enhanced_workflow
                    enhanced_workflow = await get_enhanced_workflow(session_id)
                    current_state = None
                    try:
                        current_state = enhanced_workflow["graph"].get_state({
                            "configurable": {"thread_id": session_id}
                        })
                        logger.info(f"Retrieved current state with keys: {list(current_state.values.keys())}")
                    except Exception as e:
                        logger.error(f"Error retrieving state: {e}")
                    
                    # Check if workflow is interrupted (paused for human approval)
                    if current_state and hasattr(current_state, 'next') and current_state.next:
                        logger.info(f"Workflow appears to be interrupted: next = {current_state.next}")
                        
                        # Determine approval stage from paused node
                        approval_type = "unknown"
                        paused_at_node = "unknown"
                        
                        # Identify the workflow stage from the paused node
                        next_nodes = str(current_state.next)
                        if "plan" in next_nodes:
                            approval_type = "implementation_plan"
                            paused_at_node = "human_approval_plan_node"
                        elif "design" in next_nodes or "system_design" in next_nodes:
                            approval_type = "system_design"
                            paused_at_node = "human_approval_system_design_node"
                        elif "tech_stack" in next_nodes:
                            approval_type = "tech_stack_recommendation"
                            paused_at_node = "human_approval_tech_stack_node"
                            logger.info(f"Detected tech stack approval needed - will use standardized payload")
                        elif "brd" in next_nodes:
                            approval_type = "brd_analysis"
                            paused_at_node = "human_approval_brd_node"
                        
                        # Create standardized approval payload
                        try:
                            if approval_type != "unknown":
                                approval_payload = await get_approval_payload_for_stage(
                                    approval_type, 
                                    current_state.values
                                )
                                approval_data = approval_payload.data
                                logger.info(f"Created standardized approval payload for {approval_type}")
                            else:
                                # Fallback for unknown cases
                                from app.services.approval_service import extract_brd_analysis_data
                                approval_data = await extract_brd_analysis_data(current_state.values)
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
                            approval_payload = ApprovalPayload(
                                step_name="error",
                                display_name="Error",
                                data=approval_data,
                                instructions="An error occurred while preparing the approval data.",
                                is_revision=False,
                                previous_feedback=None
                            )
                        
                        logger.info(f"WORKFLOW INTERRUPTED at {paused_at_node} for human approval of {approval_type}")
                        
                        # Save step results with the approval payload data
                        if approval_type != "unknown" and approval_payload:
                            await save_step_results(session_id, approval_type, approval_payload.data, current_state.values)
                        
                        # Send standardized approval payload to frontend
                        await websocket_manager.send_to_session(session_id, {
                            "type": "workflow_event",
                            "event": "workflow_paused",
                            "data": {
                                "session_id": session_id,
                                "paused_at": paused_at_node,
                                "approval_type": approval_type,
                                "payload": approval_payload.model_dump()
                            }
                        })
            
        # Check if we reached the end without detecting an interrupt
        if not interrupt_detected:
            logger.warning(f"Workflow completed without detecting any interruption points for session {session_id}")
            
            # Check final state to see why workflow ended
            try:
                from app.services.workflow_service import get_enhanced_workflow
                enhanced_workflow = await get_enhanced_workflow(session_id)
                final_state = enhanced_workflow["graph"].get_state({
                    "configurable": {"thread_id": session_id}
                })
                
                if final_state and final_state.next:
                    logger.info(f"Workflow ended but has remaining nodes: {final_state.next}")
                    # Send a message about the remaining work
                    await websocket_manager.send_to_session(session_id, {
                        "type": "workflow_event",
                        "event": "workflow_incomplete",
                        "data": {
                            "session_id": session_id,
                            "message": f"Workflow completed but has remaining nodes: {final_state.next}",
                            "remaining_nodes": list(final_state.next) if final_state.next else []
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