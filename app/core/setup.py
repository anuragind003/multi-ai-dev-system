"""
Application Setup Module

This module handles FastAPI application configuration and startup logic.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi

from config import get_system_config, initialize_system_config, AdvancedWorkflowConfig
from enhanced_memory_manager_with_recovery import get_enhanced_memory_manager
from async_graph import get_async_workflow
from rag_manager import ProjectRAGManager, set_rag_manager
from utils.shared_memory_hub import get_shared_memory_hub
from utils.windows_logging_fix import setup_windows_compatible_logging

# Initialize logger
logger = setup_windows_compatible_logging()

# Define API version for compatibility checks
API_VERSION = "v1"
SERVER_VERSION = "0.0.1-alpha"

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    # Initialize system config
    try:
        cfg = get_system_config()
    except RuntimeError:
        logger.warning("SystemConfig not initialized. Attempting to initialize now for app.server.")
        adv_workflow_cfg = AdvancedWorkflowConfig.load_from_multiple_sources()
        initialize_system_config(adv_workflow_cfg)
        cfg = get_system_config()

    # Initialize FastAPI app with properly enabled OpenAPI schema
    app = FastAPI(
        title="Multi-AI Development System API",
        version=API_VERSION,
        description="API for managing and interacting with the Multi-AI Development System workflow.",
        openapi_url="/openapi.json",
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

    # Mount static files directory
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    os.makedirs(static_dir, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    return app

def setup_openapi_schema(app: FastAPI):
    """Setup custom OpenAPI schema with temperature strategy information."""
    
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
            "brd_analyst": 0.3,
            "tech_stack_advisor": 0.2,
            "system_designer": 0.2,
            "planning_agent": 0.4,
            "code_generation": 0.1,
            "test_case_generator": 0.2,
            "code_quality": 0.1,
            "test_validation": 0.1
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

async def setup_startup_tasks(app: FastAPI):
    """Setup application startup tasks."""
    
    # Initialize shared memory hub for cross-component communication
    shared_memory_hub = get_shared_memory_hub()
    app.state.memory_hub = shared_memory_hub
    
    # Initialize enhanced memory manager for the application
    enhanced_memory = get_enhanced_memory_manager()
    app.state.enhanced_memory = enhanced_memory
    
    # Initialize RAG manager
    logging.info("Initializing RAG manager...")
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    rag_manager = ProjectRAGManager(project_root=project_root)
    
    # Check if an index exists, if not, create one
    if not rag_manager.load_existing_index():
        logging.info("No existing RAG index found. Initializing a new one...")
        # Index the project code and WAIT for it to complete
        await asyncio.to_thread(rag_manager.index_project_code)
    
    set_rag_manager(rag_manager)
    logging.info("RAG manager initialized successfully.")

    # Initialize enhanced ASYNC workflow configuration
    logger.info("Initializing enhanced ASYNC workflow with improved interrupt handling")
    graph_builder = await get_async_workflow("phased")
    
    # Compile the ASYNC graph with explicit interrupt configuration
    workflow = graph_builder.compile(
        checkpointer=enhanced_memory,
        interrupt_before=[
            "human_approval_brd_node", 
            "human_approval_tech_stack_node", 
            "human_approval_system_design_node", 
            "human_approval_plan_node", 
            "human_approval_code_node"
        ]
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

async def setup_shutdown_tasks(app: FastAPI):
    """Setup application shutdown tasks."""
    try:
        enhanced_memory = get_enhanced_memory_manager()
        enhanced_memory._create_disk_backup()
        logger.info("Final backup created on shutdown")
    except Exception as e:
        logger.error(f"Failed to create shutdown backup: {e}")

def get_temperature_strategy():
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