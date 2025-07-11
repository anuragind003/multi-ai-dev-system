"""
Workflow Service Module

This module handles all workflow execution logic, including:
- Workflow creation and management
- Session management
- State tracking
- Recovery mechanisms
"""

import asyncio
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, List
import json

from agent_state import StateFields
from enhanced_memory_manager_with_recovery import get_enhanced_memory_manager
from models.human_approval import ApprovalPayload

logger = logging.getLogger(__name__)

# Global session storage
sessions = {}

# Global workflow cache
_enhanced_workflow_cache = {}

async def get_enhanced_workflow(session_id: str):
    """Get or create enhanced workflow for session"""
    global _enhanced_workflow_cache
    if session_id not in _enhanced_workflow_cache:
        from unified_workflow import get_unified_workflow
        from enhanced_memory_manager_with_recovery import get_enhanced_memory_manager
        
        enhanced_memory = get_enhanced_memory_manager()
        graph_builder = await get_unified_workflow()
        
        # Compile the ASYNC graph with explicit interrupt configuration
        # This list defines which nodes should trigger a pause for human feedback.
        # We remove 'human_approval_code_node' as the new simple workflow automates
        # the implementation loop without mid-loop human approval, fixing state issues.
        interrupt_nodes = [
            "human_approval_brd_node",
            "human_approval_tech_stack_node",
            "human_approval_system_design_node",
            "human_approval_plan_node"
        ]

        # Compile the graph with the checkpointer and interrupt points
        workflow = graph_builder.compile(
            checkpointer=enhanced_memory,
            interrupt_before=interrupt_nodes
        )
        
        _enhanced_workflow_cache[session_id] = {"graph": workflow}
        logger.info(f"Created enhanced workflow for session: {session_id}")
    return _enhanced_workflow_cache[session_id]

def get_next_stage_name(current_stage: str) -> str:
    """Get the next stage name based on the current stage."""
    stage_progression = {
        "brd_analysis": "tech_stack_recommendation",
        "tech_stack_recommendation": "system_design",
        "system_design": "planning",
        "implementation_plan": "code_generation",
        "code_generation": "completed"
    }
    return stage_progression.get(current_stage, "unknown")

async def create_workflow_session(session_id: str, brd_content: str) -> dict:
    """Create a new workflow session with enhanced recovery capabilities"""
    try:
        # Initialize enhanced workflow with recovery
        workflow_components = await get_enhanced_workflow(session_id)
        enhanced_memory = get_enhanced_memory_manager()
        
        # Store session information
        sessions[session_id] = {
            "session_id": session_id,
            "created_at": datetime.now(),
            "status": "created",
            "brd_content": brd_content,
            "enhanced_memory": enhanced_memory,
            "workflow_components": workflow_components
        }
        
        logger.info(f"Created enhanced workflow session: {session_id}")
        
        return {
            "session_id": session_id,
            "status": "created",
            "message": "Enhanced workflow session created with recovery capabilities"
        }
        
    except Exception as e:
        logger.error(f"Failed to create enhanced workflow session: {e}")
        raise

async def run_resumable_graph(session_id: str, brd_content: str, user_feedback: dict = None):
    """Run workflow with enhanced recovery capabilities"""
    try:
        # Get enhanced workflow components
        workflow_components = await get_enhanced_workflow(session_id)
        graph = workflow_components["graph"]
        config = {
            "configurable": {"thread_id": session_id},
            "recursion_limit": 100  # Increase recursion limit to handle complex workflows
        }

        if user_feedback:
            logger.info(f"Resuming workflow {session_id} with user feedback: {user_feedback}")

            # Extract the decision from user feedback
            decision = user_feedback.get("decision", "end")
            logger.info(f"Human decision extracted: {decision}")

            # Create a proper state update for resumption that matches what the graph expects
            session_data = sessions.get(session_id, {})
            current_stage = session_data.get("current_approved_stage", "brd_analysis")
            
            state_update = {
                "human_decision": decision,  # This is what async_decide_after_human looks for
                "decision": decision,  # Also set this as a backup
                "revision_feedback": user_feedback.get("feedback", user_feedback.get("feedback_message", "")),
                "resume_from_approval": True,
                "user_feedback": user_feedback,  # Store the full feedback object
            }
            
            # Also store any selected stack options for tech stack decisions
            if "selected_stack" in user_feedback:
                state_update["selected_stack"] = user_feedback["selected_stack"]
            
            logger.info(f"State update for resumption: {state_update}")
            
            # Determine which approval node should receive the update based on current stage
            stage_to_approval_node = {
                "brd_analysis": "human_approval_brd_node",
                "tech_stack_recommendation": "human_approval_tech_stack_node",
                "system_design": "human_approval_system_design_node",
                "implementation_plan": "human_approval_plan_node",
                "code_generation": "human_approval_code_node"
            }
            
            # Get the current workflow state to determine which node we're resuming from
            current_state = graph.get_state(config)
            as_node = None
            
            if current_state and current_state.next:
                # If we have next nodes, check if any are human approval nodes
                for next_node in current_state.next:
                    if next_node in stage_to_approval_node.values():
                        as_node = next_node
                        break
            
            # Fallback to using the current stage mapping if we can't determine from state
            if not as_node:
                as_node = stage_to_approval_node.get(current_stage, "human_approval_plan_node")
            
            logger.info(f"Updating workflow state as node: {as_node}")
            
            # Update the state in the checkpointer and then resume
            logger.info("Updating workflow state with human decision...")
            await asyncio.to_thread(graph.update_state, config, state_update, as_node=as_node)
            logger.info("State updated successfully. Resuming workflow from checkpoint.")
            
            # For resuming, inputs should be None - the graph will continue from where it left off
            inputs = None
            
            # Store decision in session data for recovery logging
            if session_id in sessions:
                sessions[session_id]["last_human_decision"] = decision
                sessions[session_id]["last_approved_stage"] = current_stage
                sessions[session_id]["workflow_resumed"] = True
                sessions[session_id]["last_feedback"] = user_feedback
        else:
            # This is a new run, so the input is the BRD content
            inputs = {
                "brd_content": brd_content,
                "session_id": session_id,
                "workflow_start_time": datetime.now().isoformat(),
                "enhanced_recovery_enabled": True
            }
            logger.info(f"Starting new workflow for session: {session_id}")

        # Run the enhanced graph
        logger.info(f"Executing graph for session: {session_id}.")
        
        event_count = 0
        async for event in graph.astream(inputs, config):
            event_count += 1
            # Handle workflow events with enhanced logging
            if isinstance(event, dict):
                logger.info(f"Event #{event_count} keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
                
                # Check for interruption events
                if "__interrupt__" in event:
                    logger.info(f"Workflow interrupted after {event_count} events")
                    
                # Log node completions
                for node_name in ["brd_analysis_node", "tech_stack_recommendation_node", 
                                 "system_design_node", "implementation_plan_node", "human_approval_brd_node",
                                 "human_approval_tech_stack_node", "human_approval_system_design_node", 
                                 "human_approval_plan_node"]:
                    if node_name in event:
                        result = event[node_name]
                        logger.info(f"Node {node_name} completed with keys: {list(result.keys()) if isinstance(result, dict) else 'non-dict'}")
            
            yield event
        
        # Check final state after all events
        final_state = graph.get_state(config)
        if final_state and final_state.next:
            logger.info(f"Workflow completed {event_count} events but still has next nodes: {final_state.next}")
        else:
            logger.info(f"Workflow completed after {event_count} events with no remaining nodes")
            
    except Exception as e:
        logger.error(f"Enhanced workflow execution failed for session {session_id}: {e}", exc_info=True)
        raise

def get_session_data(session_id: str) -> Optional[dict]:
    """Get session data by session ID"""
    return sessions.get(session_id)

def update_session_data(session_id: str, data: dict):
    """Update session data"""
    if session_id in sessions:
        sessions[session_id].update(data)
    else:
        sessions[session_id] = data

def get_all_sessions() -> dict:
    """Get all session data"""
    return sessions

async def save_step_results(session_id: str, approval_type: str, approval_data: dict, full_state: dict):
    """Save the results of each approval step to both file and memory for persistence."""
    try:
        # Create output directory structure
        output_dir = os.path.join("output", "interactive_runs", session_id, "approval_results")
        os.makedirs(output_dir, exist_ok=True)
        
        # Create timestamped filename
        timestamp = int(time.time())
        filename = f"{approval_type}_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        # Prepare comprehensive data to save
        save_data = {
            "session_id": session_id,
            "approval_type": approval_type,
            "timestamp": timestamp,
            "approval_data": approval_data,
            "workflow_state_snapshot": {
                key: value for key, value in full_state.items() 
                if key in ["requirements_analysis", "tech_stack_recommendation", "system_design", "implementation_plan"]
            }
        }
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False, default=str)
        
        # Also save a "latest" version for easy access
        latest_filepath = os.path.join(output_dir, f"{approval_type}_latest.json")
        with open(latest_filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Saved {approval_type} results for session {session_id} to {filepath}")
        
    except Exception as e:
        logger.error(f"Failed to save step results for {approval_type} in session {session_id}: {e}") 