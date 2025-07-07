# app/server.py
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from langserve import add_routes
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable
import os
import sys
import uuid
import logging
import time
from fastapi.openapi.utils import get_openapi
from datetime import datetime
import asyncio
from langgraph.types import Command
import json
import signal
from pydantic import BaseModel
from utils.shared_memory_hub import get_shared_memory_hub
from typing import Any, Dict, Optional, List
from rag_manager import RAGManager
from tools.code_execution_tool import CodeExecutionTool
from message_bus import MessageBus
import mimetypes
from agents.brd_analyst_react import BRDAnalystReActAgent
from agents.tech_stack_advisor_simplified import TechStackAdvisorSimplifiedAgent
from agents.system_designer_simplified import SystemDesignerSimplifiedAgent
from agents.planning.plan_compiler_simplified import PlanCompilerSimplifiedAgent
from agents.code_generation.architecture_generator import ArchitectureGeneratorAgent
from agents.code_generation.database_generator import DatabaseGeneratorAgent
from agents.code_generation.backend_orchestrator import BackendOrchestratorAgent
from agents.code_generation.frontend_generator import FrontendGeneratorAgent
from agents.code_generation.integration_generator import IntegrationGeneratorAgent
from agents.code_generation.code_optimizer import CodeOptimizerAgent
from agent_temperatures import get_agent_temperature
from config import get_llm

from models.data_contracts import (
    BRDAnalysisOutput, ComprehensiveTechStackOutput, SystemDesignOutput, 
    ComprehensiveImplementationPlanOutput, WorkItem,
    TechStackComponent, ArchitecturePatternOption, SelectedTechStack 
)
from multi_ai_dev_system.utils.logging_config import setup_logging
from multi_ai_dev_system.app.middleware import add_process_time_header
from multi_ai_dev_system.mcp.langgraph_mcp import LangGraphMultiControlPanel
from multi_ai_dev_system.mcp.agent_integration import wrap_agent_for_mcp
from multi_ai_dev_system.tools.code_execution_tool import execute_python_code, CodeExecutionToolInput
from multi_ai_dev_system.tools.tech_stack_tools_enhanced import generate_comprehensive_tech_stack
from multi_ai_dev_system.tools.brd_analysis_tools_enhanced import analyze_brd_and_extract_requirements
from multi_ai_dev_system.tools.system_design_tools_enhanced import generate_system_design
from multi_ai_dev_system.tools.plan_compiler_tools import compile_detailed_plan
from multi_ai_dev_system.tools.general_tools import log_to_console, read_project_file, write_project_file, get_project_structure
from multi_ai_dev_system.utils.file_utils import get_session_output_path

# Import the websocket schema
from app.websocket_schema import (
    WebSocketMessageBase, 
    AgentEventMessage, 
    WorkflowStatusMessage, 
    WorkflowPausedMessage,
    ErrorMessage,
    HealthCheckMessage
)

# Initialize logger
logger = setup_logging(__name__)
# logging.basicConfig(level=logging.INFO)  # Removed to prevent conflict with uvicorn logging

# Define API version for compatibility checks
API_VERSION = "v1"
SERVER_VERSION = "0.0.1-alpha"

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

# Define required classes early
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

class VersionResponse(BaseModel):
    api_version: str = API_VERSION
    server_version: str = SERVER_VERSION
    compatible: bool = True

# Define session storage
sessions = {}

# Define enhanced memory manager functions early
_enhanced_memory_manager = None
_enhanced_workflow_cache = {}

def get_enhanced_memory_manager():
    """Get or create the global enhanced memory manager"""
    global _enhanced_memory_manager
    if _enhanced_memory_manager is None:
        _enhanced_memory_manager = create_enhanced_memory_with_recovery()
        logger.info("Created enhanced memory manager with recovery capabilities")
    return _enhanced_memory_manager

async def get_enhanced_workflow(session_id: str):
    """Get or create enhanced workflow for session"""
    global _enhanced_workflow_cache
    if session_id not in _enhanced_workflow_cache:
        workflow_components = await initialize_workflow_with_recovery(session_id)
        _enhanced_workflow_cache[session_id] = workflow_components
        logger.info(f"Created enhanced workflow for session: {session_id}")
    return _enhanced_workflow_cache[session_id]

# Import from the project
from serve_chain import create_workflow_runnable
from config import get_system_config, initialize_system_config, AdvancedWorkflowConfig
from .websocket_manager import websocket_manager
from graph import get_workflow
from enhanced_memory_manager_with_recovery import create_enhanced_memory_with_recovery
from enhanced_graph_with_recovery import initialize_workflow_with_recovery
from enhanced_graph_nodes_with_recovery import (
    recover_workflow_from_checkpoint, 
    list_available_checkpoints, 
    get_session_recovery_info
)
from agent_state import StateFields
from async_graph import get_async_workflow
from rag_manager import ProjectRAGManager, set_rag_manager, get_rag_manager
from app.recovery_endpoints import recovery_router
from enhanced_memory_manager_with_recovery import get_enhanced_memory_manager
from advanced_rate_limiting.rate_limit_manager import RateLimitManager
from config import AdvancedWorkflowConfig
from async_graph import create_async_phased_workflow
from enhanced_memory_manager_with_recovery import EnhancedMemoryManagerWithRecovery
from models.human_approval import ApprovalPayload

# --- Global System Config Initialization (Executed once at server startup) ---
try:
    cfg = get_system_config()
except RuntimeError:
    logger.warning("SystemConfig not initialized. Attempting to initialize now for app.server.")
    adv_workflow_cfg = AdvancedWorkflowConfig.load_from_multiple_sources()
    initialize_system_config(adv_workflow_cfg)
    cfg = get_system_config()
# ---

# --- Global Checkpointer Setup ---
# Create a single, reusable checkpointer instance.
# This checkpointer will manage the state of all concurrent workflows.
enhanced_memory = get_enhanced_memory_manager()
# ---

# Initialize FastAPI app with properly enabled OpenAPI schema
app = FastAPI(
    title="Multi-AI Development System API",
    version=API_VERSION,
    description="API for managing and interacting with the Multi-AI Development System workflow.",
    # Enable OpenAPI schema at /openapi.json
    openapi_url="/openapi.json",
    # Explicitly set the docs_url to ensure Swagger UI is available
    docs_url="/docs"
)

# Include recovery endpoints router
app.include_router(recovery_router)

# async def shutdown_server(delay: int):
#     """Waits for a given delay and then gracefully shuts down the server."""
#     await asyncio.sleep(delay)
#     logging.warning(
#         f"No WebSocket client connected for {delay} seconds. Shutting down server to save costs."
#     )
#     # Sending SIGINT to the process triggers Uvicorn's graceful shutdown
#     os.kill(os.getpid(), signal.SIGINT)

@app.on_event("startup")
async def startup_event():
    """Initialize RAG and schedule the initial server shutdown task."""
    global enhanced_memory  # Use the global variable

    # Schedule the server to shut down in 60 seconds if no client connects
    # shutdown_task = asyncio.create_task(shutdown_server(60))
    # app.state.shutdown_task = shutdown_task
    # logging.info("Server startup complete. Scheduled shutdown in 60s if no client connects.")

    # --- FIX: Initialize workflow runnable and add routes at startup ---
    # This ensures that the memory_hub is available from app.state.
    memory_hub = app.state.memory_hub if hasattr(app.state, 'memory_hub') else None
    
    # Initialize enhanced memory manager for the application
    enhanced_memory = get_enhanced_memory_manager()
    app.state.enhanced_memory = enhanced_memory
    
    # --- Initialize shared memory hub for cross-component communication ---
    shared_memory_hub = get_shared_memory_hub()
    app.state.memory_hub = shared_memory_hub
    
    logging.info("Initializing RAG manager...")
    project_root = os.path.dirname(os.path.dirname(__file__))
    rag_manager = ProjectRAGManager(project_root=project_root)
    
    # Check if an index exists, if not, create one
    if not rag_manager.load_existing_index():
        logging.info("No existing RAG index found. Initializing a new one...")
        # Index the project code and WAIT for it to complete.
        await asyncio.to_thread(rag_manager.index_project_code)
    
    set_rag_manager(rag_manager)
    logging.info("RAG manager initialized successfully.")

    # --- CRITICAL FIX: Enhanced ASYNC workflow configuration ---
    logger.info("Initializing enhanced ASYNC workflow with improved interrupt handling")
    graph_builder = await get_async_workflow("phased")
    
    # Compile the ASYNC graph with explicit interrupt configuration
    workflow = graph_builder.compile(
        checkpointer=enhanced_memory,
        # CRITICAL: Be very explicit about ALL interrupt points with correct node names
        interrupt_before=[
            "human_approval_brd_node", 
            "human_approval_tech_stack_node", 
            "human_approval_system_design_node", 
            "human_approval_plan_node", 
            "human_approval_code_node"
        ]
        # REMOVED: state_validation parameter is not supported in this LangGraph version
    )
    
    # Add the ASYNC runnable to the app state
    app.state.workflow_runnable = workflow
    logger.info("Enhanced ASYNC workflow initialized with improved interrupt handling")
    
    # Initialize enhanced memory system on startup
    try:
        # Try to get memory stats if available
        try:
            stats = enhanced_memory.get_memory_stats()
            logger.info(f"Enhanced memory system initialized: {stats}")
        except (AttributeError, Exception) as e:
            logger.warning(f"Memory stats not available: {e}")
            logger.info("Enhanced memory system initialized with basic configuration")
        
        # Create backup on startup if method exists
        try:
            if hasattr(enhanced_memory, '_create_disk_backup'):
                enhanced_memory._create_disk_backup()
                logger.info("Initial backup created on startup")
            else:
                logger.info("Disk backup not available for this memory manager")
        except Exception as e:
            logger.warning(f"Could not create initial backup: {e}")
        
    except Exception as e:
        logger.error(f"Failed to initialize enhanced memory system: {e}")
        # Continue anyway - fallback to basic system

    # Initialize RAG Manager for the session's project directory
    # session_dir = os.path.join("output", "interactive_runs", session_id)
    # session_dir.mkdir(parents=True, exist_ok=True)
    # rag_manager = RAGManager(project_dir=str(session_dir))
    # asyncio.create_task(asyncio.to_thread(rag_manager.get_retriever))
    
    # Create a unique memory hub for this session
    # memory_hub = get_shared_memory_hub()

@app.on_event("shutdown") 
async def shutdown_event():
    """Cleanup enhanced memory system on shutdown"""
    try:
        enhanced_memory = get_enhanced_memory_manager()
        enhanced_memory._create_disk_backup()
        logger.info("Final backup created on shutdown")
    except Exception as e:
        logger.error(f"Failed to create shutdown backup: {e}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory for examples.html
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Custom OpenAPI schema generator that includes temperature strategy information
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Multi-AI Development System API",
        version=API_VERSION,
        description="API for managing and interacting with the Multi-AI Development System workflow.",
        routes=app.routes,
    )
    
    # Add temperature strategy information to OpenAPI schema
    openapi_schema["info"]["x-temperature-strategy"] = {
        "brd_analyst": 0.3,        # Creative analysis
        "tech_stack_advisor": 0.2, # Analytical recommendations
        "system_designer": 0.2,    # Analytical design
        "planning_agent": 0.4,     # Creative planning
        "code_generation": 0.1,    # Deterministic code
        "test_case_generator": 0.2,# Analytical test design
        "code_quality": 0.1,       # Deterministic analysis
        "test_validation": 0.1     # Deterministic validation
    }
    
    # Add paths for LangServe routes manually to avoid schema generation issues
    if "/api/workflow" not in openapi_schema["paths"]:
        openapi_schema["paths"]["/api/workflow"] = {
            "post": {
                "summary": "Process BRD with Multi-AI Agent System",
                "description": "Takes a Business Requirements Document and processes it through the complete AI agent workflow",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "brd_content": {
                                        "type": "string",
                                        "description": "Content of the Business Requirements Document"
                                    },
                                    "workflow_type": {
                                        "type": "string",
                                        "description": "Type of workflow (phased or iterative)",
                                        "default": "phased"
                                    },
                                    "temperature_strategy": {
                                        "type": "object",
                                        "description": "Custom temperature settings for specialized agents"
                                    }
                                },
                                "required": ["brd_content"]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Successful response with generated software artifacts",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object"
                                }
                            }
                        }
                    }
                }
            }
        }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Set the custom OpenAPI function
app.openapi = custom_openapi

@app.get("/")
def read_root():
    """Root endpoint providing API information and navigation."""
    return {
        "message": "Multi-AI Development System API",
        "documentation": "/docs",
        "examples": "/static/examples.html",
        "api": "/api/workflow",
        "temperature_strategy": {
            "brd_analyst": 0.3,        # Creative analysis
            "tech_stack_advisor": 0.2, # Analytical recommendations
            "system_designer": 0.2,    # Analytical design
            "planning_agent": 0.4,     # Creative planning
            "code_generation": 0.1,    # Deterministic code
            "test_case_generator": 0.2,# Analytical test design
            "code_quality": 0.1,       # Deterministic analysis
            "test_validation": 0.1     # Deterministic validation
        }
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
async def health_check():
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
    # A client has connected, so cancel any scheduled shutdown
    # if hasattr(app.state, "shutdown_task") and app.state.shutdown_task and not app.state.shutdown_task.done():
    #     app.state.shutdown_task.cancel()
    #     logging.info("Client connected. Server shutdown cancelled.")

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
        enhanced_memory = get_enhanced_memory_manager()
        active_sessions = sessions.keys()
        
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
                            
                            paused_sessions[session_id] = {
                                "session_id": session_id,
                                "paused_at": paused_at_nodes,
                                "approval_type": approval_type,
                                "approval_data": approval_data,
                                "payload": approval_payload.model_dump()
                            }
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
        
        # If it was the last client, schedule a new shutdown task
        # if not websocket_manager.has_active_connections():
        #     shutdown_task = asyncio.create_task(shutdown_server(60))
        #     app.state.shutdown_task = shutdown_task
        #     logging.warning("Last client disconnected. Scheduling server shutdown in 60 seconds.")
    except Exception as e:
        logging.error(f"WebSocket error for client {connection_id}: {e}")
        await websocket_manager.disconnect(connection_id)

# Add result extraction and saving functions
async def extract_brd_analysis_data(state_values: dict) -> dict:
    """Extract BRD analysis data from the workflow state."""
    brd_analysis = state_values.get("requirements_analysis", {})
    if not brd_analysis:
        brd_analysis = state_values.get("brd_analysis_output", {})
    
    # Extract requirements with proper formatting
    requirements = brd_analysis.get("requirements", [])
    functional_requirements = brd_analysis.get("functional_requirements", [])
    non_functional_requirements = brd_analysis.get("non_functional_requirements", [])
    
    # If requirements is a list of objects, extract the text
    def extract_requirement_text(req_list):
        if isinstance(req_list, list):
            result = []
            for req in req_list:
                if isinstance(req, dict):
                    # Try different possible field names
                    text = req.get('requirement') or req.get('description') or req.get('text') or req.get('content') or str(req)
                    result.append(text)
                else:
                    result.append(str(req))
            return result
        return req_list
    
    # Process and clean up requirements
    processed_requirements = extract_requirement_text(requirements)
    processed_functional = extract_requirement_text(functional_requirements)
    processed_non_functional = extract_requirement_text(non_functional_requirements)
    
    # Create a combined requirements list in the format the frontend expects
    combined_requirements = []
    
    # Add functional requirements
    for i, req in enumerate(processed_functional):
        combined_requirements.append({
            "id": f"FR-{i+1}",
            "title": f"Functional Requirement {i+1}",
            "description": req,
            "type": "functional",
            "acceptance_criteria": []
        })
    
    # Add non-functional requirements
    for i, req in enumerate(processed_non_functional):
        combined_requirements.append({
            "id": f"NFR-{i+1}",
            "title": f"Non-Functional Requirement {i+1}",
            "description": req,
            "type": "non_functional",
            "acceptance_criteria": []
        })
    
    # If we have any requirements in the original requirements field, add them too
    for i, req in enumerate(processed_requirements):
        if req not in [r["description"] for r in combined_requirements]:  # Avoid duplicates
            combined_requirements.append({
                "id": f"REQ-{i+1}",
                "title": f"Requirement {i+1}",
                "description": req,
                "type": "general",
                "acceptance_criteria": []
            })
    
    extracted_data = {
        "type": "brd_analysis",
        "timestamp": time.time(),
        "project_name": brd_analysis.get("project_name", "Unknown Project"),
        "project_summary": brd_analysis.get("project_summary", ""),
        "requirements": combined_requirements,  # Combined list for frontend
        "functional_requirements": processed_functional,  # Keep originals for compatibility
        "non_functional_requirements": processed_non_functional,
        "stakeholders": brd_analysis.get("stakeholders", []),
        "constraints": brd_analysis.get("constraints", []),
        "success_criteria": brd_analysis.get("success_criteria", []),
        "raw_analysis": brd_analysis,
        # Also provide extracted_requirements field that frontend checks
        "extracted_requirements": combined_requirements
    }
    
    # Log the extracted data for debugging
    logger.info(f"Extracted BRD analysis data with {len(combined_requirements)} total requirements ({len(processed_functional)} functional, {len(processed_non_functional)} non-functional)")
    if processed_functional:
        logger.info(f"First functional requirement: {processed_functional[0][:100]}...")
    
    return extracted_data

async def extract_tech_stack_frontend_data(extracted_data: dict) -> dict:
    """Extract only the frontend-compatible data for TechStackReview component."""
    frontend_data = {}
    
    # Only include keys that are arrays (for Vue v-for iteration)
    array_keys = ["frontend", "backend", "database", "cloud", "architecture", "tools", "risks"]
    
    for key in array_keys:
        if key in extracted_data and isinstance(extracted_data[key], list) and extracted_data[key]:
            frontend_data[key] = extracted_data[key]
    
    # If no arrays found, create basic structure from the extracted string fields
    if not frontend_data:
        if extracted_data.get("frontend_framework"):
            frontend_data["frontend"] = [{"name": extracted_data["frontend_framework"], "reason": "Selected frontend framework"}]
        if extracted_data.get("backend_framework"):
            frontend_data["backend"] = [{"name": extracted_data["backend_framework"], "reason": "Selected backend framework"}]
        if extracted_data.get("database"):
            frontend_data["database"] = [{"name": extracted_data["database"], "reason": "Selected database"}]
        if extracted_data.get("cloud_platform"):
            frontend_data["cloud"] = [{"name": extracted_data["cloud_platform"], "reason": "Selected cloud platform"}]
    
    # Log what we're sending to frontend
    logger.info(f"🎯 Frontend tech stack data contains keys: {list(frontend_data.keys())}")
    for key, value in frontend_data.items():
        logger.info(f"🎯 {key}: {len(value) if isinstance(value, list) else type(value)} items")
    
    return frontend_data

async def extract_tech_stack_data(state_values: dict, user_feedback: Optional[Dict[str, Any]] = None) -> dict:
    """Extract tech stack recommendation data from the workflow state, handling multiple options and user selections."""
    tech_stack_output_raw = state_values.get("tech_stack_recommendation", {})
    logger.info(f"🔍 Extracting tech stack data. Received structure with keys: {list(tech_stack_output_raw.keys())}")

    # Attempt to parse into the Pydantic model for robust access
    try:
        tech_stack_output = ComprehensiveTechStackOutput(**tech_stack_output_raw)
    except Exception as e:
        logger.error(f"Failed to parse tech_stack_recommendation into ComprehensiveTechStackOutput: {e}", exc_info=True)
        # Fallback to a minimal, empty output if parsing fails
        tech_stack_output = ComprehensiveTechStackOutput()

    extracted_data = {
        "type": "tech_stack",
        "timestamp": time.time(),
        "raw_recommendation": tech_stack_output.model_dump(),
        "frontend_options": [],
        "backend_options": [],
        "database_options": [],
        "cloud_options": [],
        "architecture_options": [],
        "tool_options": [],
        "risks": [],
        "synthesis": tech_stack_output.synthesis.model_dump() if tech_stack_output.synthesis else {},
        "selected_stack": tech_stack_output.selected_stack.model_dump() if tech_stack_output.selected_stack else {}
    }

    # Helper to process options and mark selections
    def process_options(options: List[Any], feedback_key: str, default_name_key: str = 'name') -> List[dict]:
        processed = []
        selected_name = user_feedback.get(feedback_key) if user_feedback else None
        has_selection = False

        for i, option_raw in enumerate(options):
            # Ensure option is a dictionary, convert Pydantic models
            option_dict = option_raw.model_dump() if hasattr(option_raw, 'model_dump') else option_raw

            # Mark 'selected' based on user feedback or as the first option if no feedback
            is_selected = False
            if selected_name:
                if option_dict.get(default_name_key) == selected_name:
                    is_selected = True
                    has_selection = True
            elif i == 0 and not has_selection: # Default select the first if no user feedback for this category
                is_selected = True
                has_selection = True

            option_dict["selected"] = is_selected
            processed.append(option_dict)
        return processed

    extracted_data["frontend_options"] = process_options(tech_stack_output.frontend_options, "frontend_selection")
    extracted_data["backend_options"] = process_options(tech_stack_output.backend_options, "backend_selection")
    extracted_data["database_options"] = process_options(tech_stack_output.database_options, "database_selection")
    extracted_data["cloud_options"] = process_options(tech_stack_output.cloud_options, "cloud_selection")
    extracted_data["architecture_options"] = process_options(tech_stack_output.architecture_options, "architecture_selection", default_name_key='pattern')
    extracted_data["tool_options"] = process_options(tech_stack_output.tool_options, "tool_selection")
    
    # Risks are just a list of TechRisk objects, no 'selected' field needed
    extracted_data["risks"] = [risk.model_dump() for risk in tech_stack_output.risks]

    logger.info(f"Extracted tech stack data (after processing options): {list(extracted_data.keys())}")
    return extracted_data

async def extract_system_design_data(state_values: dict) -> dict:
    """Extract system design data from the workflow state."""
    system_design = state_values.get("system_design", {})
    
    return {
        "type": "system_design",
        "timestamp": time.time(),
        "architecture_overview": system_design.get("architecture", {}).get("pattern", ""),
        "components": system_design.get("components", []),
        "data_flow": system_design.get("data_flow", ""),
        "security_considerations": [m.get("implementation", "") for m in system_design.get("security", {}).get("security_measures", [])],
        "scalability_plan": system_design.get("scalability_and_performance", {}).get("summary", ""),
        "deployment_strategy": system_design.get("deployment_strategy", {}).get("summary", ""),
        "raw_design": system_design
    }

async def extract_plan_data(state_values: dict) -> dict:
    """Extract implementation plan data from the workflow state."""
    # Get the ComprehensiveImplementationPlanOutput object (as a dict)
    plan_output = state_values.get("implementation_plan", {})
    
    # The actual ImplementationPlan is nested under the 'plan' key
    # Check if plan_output is a Pydantic model and access 'plan' directly
    if hasattr(plan_output, 'plan'):
        implementation_plan = plan_output.plan
    else:
        # Fallback for older structures or if it's already a dict
        implementation_plan = plan_output.get("plan", {})
    
    return {
        "type": "implementation_plan",
        "timestamp": time.time(),
        "project_overview": implementation_plan.project_summary.get("description", "") if isinstance(implementation_plan.project_summary, dict) else (implementation_plan.project_summary.description if hasattr(implementation_plan.project_summary, 'description') else ""),
        "development_phases": [phase.model_dump() if hasattr(phase, 'model_dump') else phase for phase in implementation_plan.phases] if hasattr(implementation_plan, 'phases') else [],
        "timeline_estimation": implementation_plan.timeline.model_dump() if hasattr(implementation_plan.timeline, 'model_dump') else implementation_plan.timeline,
        "risk_assessment": implementation_plan.risks_and_mitigations if hasattr(implementation_plan, 'risks_and_mitigations') else [],
        "resource_requirements": implementation_plan.resource_allocation if hasattr(implementation_plan, 'resource_allocation') else [],
        "deliverables": [item for phase in implementation_plan.phases for item in phase.get("deliverables", [])] if hasattr(implementation_plan, 'phases') else [],
        "dependencies": [], # Dependencies are usually at work item level, not direct plan level
        "raw_plan": plan_output # Keep the entire output for raw inspection
    }

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
        
        # Store in memory for frontend access
        if not hasattr(cfg, 'session_results'):
            cfg.session_results = {}
        if session_id not in cfg.session_results:
            cfg.session_results[session_id] = {}
        
        cfg.session_results[session_id][approval_type] = {
            "data": approval_data,
            "timestamp": timestamp,
            "filepath": filepath
        }
        
        logging.info(f"Saved {approval_type} results for session {session_id} to {filepath}")
        
    except Exception as e:
        logging.error(f"Failed to save step results for {approval_type} in session {session_id}: {e}")

async def stream_workflow_events(graph, inputs: Any, config: dict, session_id: str):
    """Stream workflow events from the graph to websocket clients."""
    try:
        event_stream = graph.stream(inputs, config)
        event_count = 0
        
        async for event in event_stream:
            event_count += 1
            # Log the event type for debugging
            if isinstance(event, dict) and 'type' in event:
                logging.info(f"Stream event type: {event['type']}")
            
            # Broadcast event to websocket clients
            await websocket_manager.broadcast(event)
        
        logging.info(f"Workflow session {session_id} event stream ended with {event_count} total events.")
        
        # After the stream ends, check if it was due to an interruption or completion.
        current_state = graph.get_state(config)
        if not current_state.next:
            # No next node, so the workflow has truly completed.
            logging.info(f"Workflow {session_id} has completed.")
            await websocket_manager.broadcast({
                "type": "workflow_event",  # Add explicit type field
                "event": "workflow_completed",
                "data": {"session_id": session_id, "final_state": current_state.values},
            })
        else:
            # The workflow is paused at an interruption point.
            paused_at_nodes = current_state.next
            logging.info(f"Workflow {session_id} is paused at node(s): {paused_at_nodes}")
            
            # Determine which type of approval is needed and extract appropriate data
            paused_at_node = paused_at_nodes[0] if paused_at_nodes else "unknown"
            
            approval_data = {}
            approval_type = "unknown"
            save_data = None
            
            # Map paused nodes to approval types for standardized payload creation
            node_to_stage_map = {
                "brd": "brd_analysis",
                "tech_stack": "tech_stack_recommendation", 
                "system_design": "system_design",
                "design": "system_design",
                "plan": "implementation_plan"
            }
            
            # Determine approval type from paused node
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
                    logger.info(f"✅ Created standardized approval payload for {approval_type} in monitoring")
                else:
                    # Fallback to extract_brd_analysis_data for unknown cases
                    approval_data = await extract_brd_analysis_data(current_state.values)
                    logger.warning(f"⚠️ Unknown node {paused_at_node}, using fallback BRD extraction")
                    # Create a basic payload for unknown cases
                    approval_payload = ApprovalPayload(
                        step_name="unknown",
                        display_name="Unknown Stage", 
                        data=approval_data,
                        instructions="Please review the workflow state.",
                        is_revision=False,
                        previous_feedback=None
                    )
                    
            except Exception as e:
                logger.error(f"❌ Error creating approval payload in monitoring: {e}")
                approval_data = {"error": str(e)}
                # Create error payload
                approval_payload = ApprovalPayload(
                    step_name="error",
                    display_name="Error",
                    data=approval_data,
                    instructions="An error occurred while preparing the approval data.",
                    is_revision=False,
                    previous_feedback=None
                )
            
            # Use save_data if available (for tech stack full data), otherwise use approval_data
            data_to_save = save_data if save_data is not None else approval_data
            await save_step_results(session_id, approval_type, data_to_save, current_state.values)
            
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
    except Exception as e:
        logging.error(f"Error in workflow session {session_id}: {e}", exc_info=True)
        await websocket_manager.broadcast({
            "event": "error",
            "data": {"session_id": session_id, "error": str(e)},
        })
    finally:
        logging.info(f"Completed processing for session_id: {session_id}")

async def run_resumable_graph(session_id: str, brd_content: str, user_feedback: dict = None):
    """Run workflow with enhanced recovery capabilities"""
    enhanced_memory = None  # Initialize to avoid UnboundLocalError
    try:
        # Get enhanced workflow components
        workflow_components = await get_enhanced_workflow(session_id)
        graph = workflow_components["graph"]
        config = {"configurable": {"thread_id": session_id}}

        if user_feedback:
            logger.info(f"Resuming workflow {session_id} with user feedback: {user_feedback}")

            # Create a generic state update for resumption.
            # The specific routing is now handled by the graph's internal logic.
            
            # Determine the current approval stage from session data
            session_data = sessions.get(session_id, {})
            current_stage = session_data.get("current_approved_stage", "brd_analysis")
            
            state_update = {
                "human_decision": user_feedback.get("decision", "end"),
                "revision_feedback": user_feedback.get("feedback", {}),
                "resume_from_approval": True, # This flag tells the approval node to skip interrupting.
                # CRITICAL: Set the current approval stage for proper routing
                "current_approval_stage": current_stage
            }
            
            logger.info(f"Updating state for resumption: {state_update}")
            
            # CRITICAL FIX: Update the state in the checkpointer and then resume
            await asyncio.to_thread(graph.update_state, config, state_update)
            logger.info("State updated successfully. Resuming workflow.")
            
            inputs = None # Pass None to resume from the interrupt point.

            # Store decision in session data for recovery logging
            if session_id in sessions:
                sessions[session_id]["last_human_decision"] = user_feedback.get("decision", "end")
                sessions[session_id]["last_approved_stage"] = "brd_analysis"
        else:
            # This is a new run, so the input is the BRD content.
            inputs = {
                "brd_content": brd_content,
                "session_id": session_id,
                "workflow_start_time": datetime.now().isoformat(),
                "enhanced_recovery_enabled": True
            }

        # Run the enhanced graph
        logger.info(f"Executing graph for session: {session_id}.")
        
        # Track interruptions
        interruption_detected = False
        
        async for event in graph.astream(inputs, config):
            # Handle workflow events with enhanced logging
            if isinstance(event, dict):
                logger.info(f"Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
                
                # Check for interruption events
                if "__interrupt__" in event:
                    interruption_detected = True
                    logger.info(f"Workflow interrupted")
                    
                # Log node completions
                for node_name in ["brd_analysis_node", "tech_stack_recommendation_node", 
                                 "system_design_node", "human_approval_brd_node"]:
                    if node_name in event:
                        result = event[node_name]
                        logger.info(f"Node {node_name} completed with keys: {list(result.keys()) if isinstance(result, dict) else 'non-dict'}")
                        # Create checkpoint after important nodes
                        if enhanced_memory and hasattr(enhanced_memory, 'create_checkpoint'):
                            checkpoint_id = await asyncio.to_thread(enhanced_memory.create_checkpoint, session_id)
                            logger.info(f"{node_name} checkpoint created: {checkpoint_id}")
            
            yield event
            
    except Exception as e:
        logger.error(f"Enhanced workflow execution failed for session {session_id}: {e}", exc_info=True)
        # Try to recover from checkpoint if available
        if enhanced_memory:
            try:
                checkpoints = list_available_checkpoints(session_id, enhanced_memory)
                if checkpoints:
                    logger.info(f"Recovery options available: {len(checkpoints)} checkpoints found")
            except Exception as recovery_e:
                logger.error(f"Error checking recovery options: {recovery_e}")
        raise

@app.post("/api/workflow/resume/{session_id}")
async def resume_interactive_workflow(session_id: str, request: Request, background_tasks: BackgroundTasks):
    """Resume an interactive workflow."""
    body = await request.json()
    decision = body.get("decision")
    
    if not decision:
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

    # Retrieve the original BRD content from the session storage.
    # This is critical to prevent the brd_content from being overwritten by the feedback payload.
    session_data = sessions.get(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    original_brd_content = session_data.get("brd_content")
    if not original_brd_content:
        raise HTTPException(status_code=404, detail=f"BRD content for session {session_id} not found")

    feedback_payload = body
    
    logger.info(f"Resuming workflow for session {session_id} with decision: {decision}")
    
    # Pass the original BRD content and the feedback payload to the consumer.
    background_tasks.add_task(run_workflow_consumer, session_id, original_brd_content, feedback_payload)
    
    return {"status": "resumed", "session_id": session_id}

@app.post("/api/workflow/run_interactive")
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
        
        # Store session info for later retrieval
        sessions[session_id] = {
            "start_time": datetime.now().isoformat(),
            "status": "running",
            "brd_content": brd_content
        }
        
        # CRITICAL FIX: Use background_tasks instead of not awaiting the coroutine
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
llm = get_llm()

# Create a prompt template
prompt_template = PromptTemplate.from_template("You are a helpful assistant. {question}")

# Create a runnable sequence (modern approach, replacing LLMChain)
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

# Add endpoint to retrieve available agents and their temperature settings
@app.get("/api/temperature-strategy")
async def get_temperature_strategy():
    """Get the temperature strategy for all agents."""
    return {
        "agent_temperatures": {
            "brd_analyst": 0.3,
            "tech_stack_advisor": 0.2,
            "system_designer": 0.2,
            "planning_agent": 0.4,
            "code_generation": 0.1,
            "test_case_generator": 0.2,
            "code_quality": 0.1,
            "test_validation": 0.1
        },
        "temperature_categories": {
            "analytical": [0.1, 0.2],
            "creative": [0.3, 0.4]
        },
        "recommended_values": {
            "code_generation": 0.1,
            "analysis": 0.2,
            "planning": 0.4
        }
    }

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

@app.get("/api/workflow/results/{session_id}")
async def get_workflow_results(session_id: str):
    """Get all saved workflow results for a session."""
    try:
        results = {}
        
        # Get from memory first
        if hasattr(cfg, 'session_results') and session_id in cfg.session_results:
            results = cfg.session_results[session_id]
        
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



@app.get("/api/workflow/status/{session_id}")
async def get_workflow_status(session_id: str):
    """Get the current status of a workflow session."""
    try:
        # Get results to see which steps have been completed
        results = {}
        if hasattr(cfg, 'session_results') and session_id in cfg.session_results:
            results = cfg.session_results[session_id]
        
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

@app.post("/api/workflow/create", response_model=WorkflowResponse)
async def create_workflow_session(request: WorkflowRequest):
    """Create a new workflow session with enhanced recovery capabilities"""
    try:
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        # Initialize enhanced workflow with recovery
        workflow_components = await get_enhanced_workflow(session_id)
        enhanced_memory = get_enhanced_memory_manager()
        
        # Store session information
        sessions[session_id] = {
            "session_id": session_id,
            "created_at": datetime.now(),
            "status": "created",
            "brd_content": request.brd_content,
            "enhanced_memory": enhanced_memory,
            "workflow_components": workflow_components
        }
        
        logger.info(f"Created enhanced workflow session: {session_id}")
        
        return WorkflowResponse(
            session_id=session_id,
            status="created",
            message="Enhanced workflow session created with recovery capabilities"
        )
        
    except Exception as e:
        logger.error(f"Failed to create enhanced workflow session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/api/workflow/stream/{session_id}")
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


# Add time import for timestamp functions
import time

# Wrapper function to properly consume the async generator in the background task
async def run_workflow_consumer(session_id: str, brd_content: str, user_feedback: dict = None):
    """Consumer wrapper for run_resumable_graph to ensure the generator is properly iterated"""
    try:
        logger.info(f"🔄 Starting workflow consumer for session: {session_id}")
        interrupt_detected = False

        # CRITICAL FIX: Save the original BRD content to avoid starting over
        if session_id not in sessions:
            sessions[session_id] = {}

        if "brd_content" not in sessions[session_id]:
            sessions[session_id]["brd_content"] = brd_content

        # CRITICAL FIX: Enhanced logging for user feedback
        if user_feedback:
            decision = user_feedback.get("decision", "unknown")
            logger.info(f"[PROCESSING HUMAN FEEDBACK] Decision: {decision} for session {session_id}")
            
        # If we have user feedback indicating an approval, explicitly log it
        if user_feedback and user_feedback.get("decision") in ["proceed", "continue"]:
            logger.info(f"[STAR] Explicit approval received for session {session_id}. "
                        f"Will ensure continuation to next step.")
            
            # CRITICAL FIX: Set a marker in sessions to indicate this session should move forward
            sessions[session_id]["approved_for_next_step"] = True
            # Determine the current stage from the session's approval history or default to brd_analysis
            current_stage = sessions[session_id].get("last_approval_type", "brd_analysis")
            sessions[session_id]["current_approved_stage"] = current_stage
            sessions[session_id]["next_stage"] = get_next_stage_name(current_stage)
            sessions[session_id]["human_decision"] = user_feedback.get("decision")
            
            logger.info(f"Session data updated with approval: {sessions[session_id]}")
        
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
            # DEBUG: Log all events to help diagnose issues
            logger.info(f"📝 Workflow event: {str(event)[:200]}...")
            
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
                    logger.info(f"⚠️ Detected interrupt event: {event}")
                    interrupt_detected = True
                    
                    # Since the interrupt doesn't include node info, get it from workflow state
                    enhanced_workflow = await get_enhanced_workflow(session_id)
                    current_state = None
                    try:
                        current_state = enhanced_workflow["graph"].get_state({
                            "configurable": {"thread_id": session_id}
                        })
                        logger.info(f"📊 Retrieved current state with keys: {list(current_state.values.keys())}")
                    except Exception as e:
                        logger.error(f"❌ Error retrieving state: {e}")
                    
                    # Check if workflow is interrupted (paused for human approval)
                    if current_state and hasattr(current_state, 'next') and current_state.next:
                        logger.info(f"🔍 Workflow appears to be interrupted: next = {current_state.next}")
                        
                        # Determine approval stage from paused node
                        paused_at_node = "unknown"
                        approval_type = "unknown"
                        save_data = None  # For storing full data to save (different from approval_data for display)
                        
                        # Identify the workflow stage from the paused node
                        if "plan" in str(current_state.next):
                            approval_type = "implementation_plan"
                            paused_at_node = "human_approval_plan_node"
                        elif "design" in str(current_state.next) or "system_design" in str(current_state.next):
                            approval_type = "system_design"
                            paused_at_node = "human_approval_system_design_node"
                        elif "tech_stack" in str(current_state.next):
                            approval_type = "tech_stack_recommendation"
                            paused_at_node = "human_approval_tech_stack_node"
                            logger.info(f"✅ Detected tech stack approval needed - will use standardized payload")
                        elif "brd" in str(current_state.next):
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
                                logger.info(f"✅ Created standardized approval payload for {approval_type} in monitoring")
                            else:
                                # Fallback for unknown cases
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
                        
                        logger.info(f"⚠️ WORKFLOW INTERRUPTED at {paused_at_node} for human approval of {approval_type}")
                        
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
            logger.warning("⚠️ Workflow completed without detecting any interruption points")
            
    except Exception as e:
        logger.error(f"❌ Workflow consumer error: {str(e)}", exc_info=True)
        await websocket_manager.send_error(
            session_id,
            f"Workflow execution error: {str(e)}"
        )

def create_enhanced_workflow(session_id: str) -> Runnable:
    """Creates the enhanced workflow with recovery mechanisms."""
    # The async workflow is designed for recovery and human-in-the-loop.
    phased_workflow = create_async_phased_workflow()
    logger.info(f"Created enhanced ASYNC workflow for session: {session_id}")
    return phased_workflow

async def _get_workflow_state(session_id: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}

@app.get("/api/session-files/{session_id}")
async def get_session_files(session_id: str):
    """
    Get the file tree for a specific session's generated output.
    """
    session_output_dir = os.path.join("output", "interactive_runs", session_id, "generated_code")
    
    if not os.path.exists(session_output_dir):
        raise HTTPException(status_code=404, detail=f"Session output directory not found for {session_id}")

    def _get_file_tree(base_path: str, current_path: str):
        tree = []
        for item in os.listdir(current_path):
            item_path = os.path.join(current_path, item)
            relative_path = os.path.relpath(item_path, base_path)
            if os.path.isdir(item_path):
                tree.append({
                    "name": item,
                    "type": "directory",
                    "path": relative_path.replace("\\", "/"), # Use forward slashes for consistency
                    "children": _get_file_tree(base_path, item_path)
                })
            else:
                tree.append({
                    "name": item,
                    "type": "file",
                    "path": relative_path.replace("\\", "/"), # Use forward slashes
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
    """
    base_dir = os.path.join("output", "interactive_runs", session_id, "generated_code")
    
    # Sanitize file_path to prevent directory traversal
    abs_file_path = os.path.abspath(os.path.join(base_dir, file_path))
    
    if not abs_file_path.startswith(os.path.abspath(base_dir)):
        raise HTTPException(status_code=403, detail="Access denied: Invalid file path.")

    if not os.path.exists(abs_file_path) or not os.path.isfile(abs_file_path):
        raise HTTPException(status_code=404, detail="File not found.")

    try:
        with open(abs_file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Determine mimetype for frontend
        mime_type, _ = mimetypes.guess_type(abs_file_path)
        
        return {
            "session_id": session_id,
            "file_path": file_path,
            "content": content,
            "mime_type": mime_type or "text/plain"
        }
    except Exception as e:
        logger.error(f"Error reading file {file_path} for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

# === Modular Human Approval Functions ===

async def create_brd_approval_payload(state_values: dict, user_feedback: Optional[Dict[str, Any]] = None) -> ApprovalPayload:
    """Create standardized approval payload for BRD analysis stage."""
    extracted_data = await extract_brd_analysis_data(state_values)
    
    return ApprovalPayload(
        step_name="brd_analysis",
        display_name="Business Requirements Analysis",
        data=extracted_data,
        instructions="Please review the extracted requirements and project analysis. Verify that all functional and non-functional requirements are correctly identified and categorized.",
        is_revision=user_feedback is not None,
        previous_feedback=user_feedback.get("feedback") if user_feedback else None
    )

async def create_tech_stack_approval_payload(state_values: dict, user_feedback: Optional[Dict[str, Any]] = None) -> ApprovalPayload:
    """Create standardized approval payload for technology stack recommendation stage."""
    extracted_data = await extract_tech_stack_data(state_values, user_feedback)
    
    return ApprovalPayload(
        step_name="tech_stack_recommendation",
        display_name="Technology Stack Recommendation",
        data=extracted_data,
        instructions="Please review the recommended technology stack. You can approve the selections, request revisions with specific feedback, or choose different options from the provided alternatives.",
        is_revision=user_feedback is not None,
        previous_feedback=user_feedback.get("feedback") if user_feedback else None
    )

async def create_system_design_approval_payload(state_values: dict, user_feedback: Optional[Dict[str, Any]] = None) -> ApprovalPayload:
    """Create standardized approval payload for system design stage."""
    extracted_data = await extract_system_design_data(state_values)
    
    return ApprovalPayload(
        step_name="system_design",
        display_name="System Architecture Design",
        data=extracted_data,
        instructions="Please review the system architecture design including components, data flow, security considerations, and scalability plan. Ensure the design aligns with your requirements and technical constraints.",
        is_revision=user_feedback is not None,
        previous_feedback=user_feedback.get("feedback") if user_feedback else None
    )

async def create_implementation_plan_approval_payload(state_values: dict, user_feedback: Optional[Dict[str, Any]] = None) -> ApprovalPayload:
    """Create standardized approval payload for implementation plan stage."""
    extracted_data = await extract_plan_data(state_values)
    
    return ApprovalPayload(
        step_name="implementation_plan",
        display_name="Implementation Plan",
        data=extracted_data,
        instructions="Please review the detailed implementation plan including development phases, timeline, resource allocation, and risk assessment. Verify that the plan is realistic and aligns with your project goals.",
        is_revision=user_feedback is not None,
        previous_feedback=user_feedback.get("feedback") if user_feedback else None
    )

async def get_approval_payload_for_stage(stage: str, state_values: dict, user_feedback: Optional[Dict[str, Any]] = None) -> ApprovalPayload:
    """
    Factory function to get the appropriate approval payload for any workflow stage.
    This centralizes approval payload creation and makes it easy to add new stages.
    
    Args:
        stage: The workflow stage name (e.g., 'brd_analysis', 'tech_stack_recommendation')
        state_values: Current workflow state values
        user_feedback: Optional user feedback for revision scenarios
        
    Returns:
        ApprovalPayload: Standardized approval payload for the stage
        
    Raises:
        ValueError: If the stage is not supported
    """
    stage_creators = {
        "brd_analysis": create_brd_approval_payload,
        "tech_stack_recommendation": create_tech_stack_approval_payload,
        "system_design": create_system_design_approval_payload,
        "implementation_plan": create_implementation_plan_approval_payload,
    }
    
    if stage not in stage_creators:
        raise ValueError(f"Unsupported approval stage: {stage}. Supported stages: {list(stage_creators.keys())}")
    
    return await stage_creators[stage](state_values, user_feedback)

# === End Approval Functions ===

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)