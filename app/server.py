# app/server.py
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langserve import add_routes
from langchain_core.prompts import PromptTemplate
import os
import sys
import uuid
import logging
from fastapi.openapi.utils import get_openapi
from datetime import datetime
import asyncio
from langgraph.types import Command
import json
from fastapi import BackgroundTasks

# Import from the project
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from serve_chain import create_workflow_runnable
from config import get_llm
from .websocket_manager import websocket_manager
from multi_ai_dev_system.graph import get_workflow
from multi_ai_dev_system.enhanced_memory_manager import get_project_memory
from multi_ai_dev_system.enhanced_langgraph_checkpointer import EnhancedMemoryCheckpointer
from multi_ai_dev_system.agent_state import StateFields
from multi_ai_dev_system.async_graph import get_async_workflow

# Initialize FastAPI app with properly enabled OpenAPI schema
app = FastAPI(
    title="Multi-AI Development System API",
    version="1.0",
    description="API for automated software development using specialized AI agents",
    # Enable OpenAPI schema at /openapi.json
    openapi_url="/openapi.json",
    # Explicitly set the docs_url to ensure Swagger UI is available
    docs_url="/docs"
)

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
        version="1.0",
        description="API for automated software development using specialized AI agents",
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

# Create runnable workflow
workflow_runnable = create_workflow_runnable()

# Add routes using the runnable workflow
try:
    add_routes(
        app,
        workflow_runnable,
        path="/api/workflow"
    )
except Exception as e:
    print(f"Warning: Error adding workflow routes: {str(e)}")
    # Add a placeholder route so the API still works
    @app.post("/api/workflow")
    async def manual_workflow_route(request: Request):
        """Manual implementation of workflow route if LangServe route registration fails."""
        json_body = await request.json()
        result = workflow_runnable.invoke(json_body)
        return result

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
    print(f"Warning: Error adding LLM routes: {str(e)}")
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

# WebSocket endpoints for real-time monitoring
@app.websocket("/ws/agent-monitor")
async def websocket_agent_monitor(websocket: WebSocket):
    """WebSocket endpoint for real-time agent monitoring."""
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for any client messages
            data = await websocket.receive_json()
            # NEW: Handle human responses
            if data.get("type") == "human_response":
                session_id = data.get("session_id")
                await websocket_manager.handle_human_response(session_id, data)
            else:
                await websocket.send_text(f"Echo: {json.dumps(data)}")

    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)

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

async def run_resumable_graph(session_id: str, inputs: dict, graph_runner_queue: asyncio.Queue):
    """Function to run in the background for a resumable workflow."""
    
    memory_manager = get_project_memory(f"./output/run_{session_id}")
    checkpointer = EnhancedMemoryCheckpointer(memory_manager=memory_manager, backend_type="hybrid")
    
    # Get the async graph definition
    uncompiled_graph = await get_async_workflow("resumable")
    
    # Compile it with our persistent checkpointer
    resumable_workflow = uncompiled_graph.compile(checkpointer=checkpointer)
    
    config = {"configurable": {"thread_id": session_id}}
    
    # Initial invocation
    await websocket_manager.send_workflow_status(session_id, "started", "Workflow started.")
    result = None
    
    async for event in resumable_workflow.astream(inputs, config, stream_mode="values"):
        result = event
        # This will stream all node outputs to the client
        await websocket_manager.send_agent_event(session_id, "node_update", event)

    while result and result.get('__interrupt__'):
        await websocket_manager.send_workflow_status(session_id, "paused", "Waiting for human input.", result.get('__interrupt__'))
        
        # Wait for user input from the queue
        user_response = await graph_runner_queue.get()
        decision = user_response.get("decision", "reject")
        payload = user_response.get("payload", {})
        
        command = Command(resume=decision, update=payload)
        
        # Resume the graph
        async for event in resumable_workflow.astream(command, config, stream_mode="values"):
             result = event
             await websocket_manager.send_agent_event(session_id, "node_update", event)

    await websocket_manager.send_workflow_status(session_id, "completed", "Workflow finished.", result)
    del websocket_manager.resumable_runs[session_id]

@app.post("/api/workflow/run_interactive")
async def run_interactive_workflow(request: Request, background_tasks: BackgroundTasks):
    """Run an interactive, resumable workflow with WebSocket communication."""
    body = await request.json()
    inputs = body.get("inputs", {})
    session_id = body.get("session_id") or f"session_{uuid.uuid4()}"

    if session_id in websocket_manager.resumable_runs:
        return {"status": "error", "message": "Session already in progress."}

    graph_runner_queue = asyncio.Queue()
    websocket_manager.resumable_runs[session_id] = graph_runner_queue

    background_tasks.add_task(run_resumable_graph, session_id, inputs, graph_runner_queue)
    
    return {"status": "started", "session_id": session_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)