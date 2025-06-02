# app/server.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langserve import add_routes
from langchain_core.prompts import PromptTemplate
import os
import sys
from fastapi.openapi.utils import get_openapi

# Add the parent directory to sys.path to allow imports from the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import from the project
from serve_chain import create_workflow_runnable
from config import get_llm

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)