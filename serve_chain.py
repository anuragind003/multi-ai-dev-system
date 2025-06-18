"""
LangServe integration for Multi-AI Development System.
Creates a runnable API endpoint for the complete development workflow.
"""

from typing import Dict, Any, List, Optional
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda
from config import get_system_config, get_llm, get_embedding_model, initialize_system_config
from agent_state import create_initial_agent_state, AgentState
from graph import create_phased_workflow, create_iterative_workflow, get_workflow
import os
import json
import asyncio
import traceback
import uuid
from datetime import datetime

# Import components from their correct locations
from shared_memory import SharedProjectMemory
from message_bus import MessageBus
from checkpoint_manager import CheckpointManager
from tools.code_execution_tool import CodeExecutionTool
from rag_manager import ProjectRAGManager
from config import AdvancedWorkflowConfig
from langchain_google_genai import HarmCategory, HarmBlockThreshold

# Define project root for file operations
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# --- Global Components Initialization (Executed once at server startup) ---
# Ensure system config is loaded
try:
    cfg = get_system_config()
except RuntimeError:
    print("WARNING: SystemConfig not initialized. Attempting to initialize now for serve_chain.")
    # Attempt to load a default configuration
    adv_workflow_cfg = AdvancedWorkflowConfig.load_from_multiple_sources()
    initialize_system_config(adv_workflow_cfg)
    cfg = get_system_config()

print("Initializing global components for serve_chain...")

# Generate a single run ID for the server instance
SERVER_INSTANCE_ID = str(uuid.uuid4())
SERVER_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
# API output directory for server-level shared resources
API_OUTPUT_BASE_DIR = os.path.join(PROJECT_ROOT, "output", "api_server_runs")
os.makedirs(API_OUTPUT_BASE_DIR, exist_ok=True)

# Initialize global components once
GLOBAL_LLM = get_llm()
GLOBAL_EMBEDDING_MODEL = get_embedding_model()

# Shared components - initialized once
GLOBAL_MESSAGE_BUS = MessageBus()
GLOBAL_SHARED_MEMORY = SharedProjectMemory(run_dir=os.path.join(API_OUTPUT_BASE_DIR, "shared_memory_global"))
GLOBAL_CHECKPOINT_MANAGER = CheckpointManager(output_dir=os.path.join(API_OUTPUT_BASE_DIR, "checkpoints_global"))
GLOBAL_CODE_EXECUTION_TOOL = CodeExecutionTool(output_dir=os.path.join(API_OUTPUT_BASE_DIR, "code_execution_global"))

# Initialize and index RAG once
GLOBAL_RAG_MANAGER = ProjectRAGManager(
    project_root=PROJECT_ROOT,
    embeddings=GLOBAL_EMBEDDING_MODEL,
    environment=cfg.workflow.environment
)
print("Indexing project code for RAG (once at server startup)...")
GLOBAL_RAG_MANAGER.index_project_code()
print("RAG indexing complete.")

# Global LLM-specific kwargs based on provider
GLOBAL_LLM_SPECIFIC_KWARGS = {}
if cfg.llm_provider == "google":
    GLOBAL_LLM_SPECIFIC_KWARGS = {
        "safety_settings": {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        },
        "generation_config": {
            "top_k": 40,
            "top_p": 0.95,
            "max_output_tokens": 8192
        }
    }
elif cfg.llm_provider == "anthropic":
    GLOBAL_LLM_SPECIFIC_KWARGS = {
        "max_tokens": 4096
    }
# --- End of Global Components Initialization ---


def create_workflow_runnable() -> Runnable:
    """
    Create a runnable for the Multi-AI Development System workflow.
    This preserves the temperature-optimized agent strategy (0.1-0.4).
    """
    # Define temperature strategy for logging, API responses, and LangSmith trace categorization.
    # NOTE: This dictionary doesn't directly control actual LLM temperature settings.
    # The actual temperature binding happens in graph_nodes.py via get_agent_temperature().
    temperature_strategy = {
        "BRD Analyst Agent": 0.3,        # Creative task for requirements extraction
        "Tech Stack Advisor Agent": 0.2,  # Analytical for technology selection
        "System Designer Agent": 0.2,     # Analytical for architecture design
        "Project Analyzer Agent": 0.4,    # More creative for project analysis
        "Timeline Estimator Agent": 0.3,  # Balance for timeline estimates
        "Risk Assessor Agent": 0.2,       # Analytical for risk identification
        "Plan Compiler Agent": 0.3,       # Balance for implementation planning
        "Architecture Generator Agent": 0.1, # Deterministic for architecture code
        "Database Generator Agent": 0.1,   # Deterministic for database schemas
        "Backend Generator Agent": 0.1,    # Deterministic for backend code
        "Frontend Generator Agent": 0.2,   # Slightly creative for UI components
        "Integration Generator Agent": 0.1, # Deterministic for integration code
        "Code Optimizer Agent": 0.1,       # Analytical for optimizations
        "Test Case Generator Agent": 0.2,  # Balanced for test coverage
        "Code Quality Agent": 0.1,         # Analytical for quality assessment
        "Test Validation Agent": 0.1       # Analytical for test validation
    }

    async def execute_workflow(inputs: Dict[str, Any], config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
        """Execute the workflow asynchronously with temperature strategy."""
        global cfg  # Use global instead of nonlocal
        try:
            brd_content = inputs.get("brd_content", "")
            if not brd_content:
                return {"error": "brd_content is required", "status": "failed"}

            # Create run-specific identifier and output directory
            run_id = str(uuid.uuid4())
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_output_dir = os.path.join(API_OUTPUT_BASE_DIR, "runs", f"run_{timestamp}_{run_id[:8]}")
            os.makedirs(run_output_dir, exist_ok=True)

            # Create run-specific components that need isolation
            memory_for_run = SharedProjectMemory(run_dir=run_output_dir)
            checkpoint_manager_for_run = CheckpointManager(output_dir=run_output_dir)
            code_execution_tool_for_run = CodeExecutionTool(output_dir=run_output_dir)

            # Create configurable components dictionary
            configurable_components = {
                "llm": GLOBAL_LLM,
                "memory": memory_for_run,
                "rag_manager": GLOBAL_RAG_MANAGER,
                "code_execution_tool": code_execution_tool_for_run,
                "run_output_dir": run_output_dir,
                "message_bus": GLOBAL_MESSAGE_BUS,
                "checkpoint_manager": checkpoint_manager_for_run,
                "workflow_id": run_id,
                "global_llm_specific_kwargs": GLOBAL_LLM_SPECIFIC_KWARGS,
                "temperature_strategy": temperature_strategy
            }

            # Set up workflow based on input type
            workflow_type = inputs.get("workflow_type", "phased")
            workflow = get_workflow(workflow_type)

            # Create initial state
            initial_state = create_initial_agent_state(brd_content, cfg.workflow)
            initial_state["workflow_id"] = run_id
            initial_state["temperature_strategy"] = temperature_strategy

            # Execute workflow
            final_state = await workflow.ainvoke(
                initial_state,
                config={"configurable": configurable_components}
            )

            # Clean up run-specific resources
            if hasattr(memory_for_run, 'aclose'):
                await memory_for_run.aclose()
            elif hasattr(memory_for_run, 'close'):
                await asyncio.to_thread(memory_for_run.close)

            # Return results
            return {
                "requirements_analysis": final_state.get("requirements_analysis", {}),
                "tech_stack": final_state.get("tech_stack_recommendation", {}),
                "system_design": final_state.get("system_design", {}),
                "code_generation_result": final_state.get("code_generation_result", {}),
                "quality_analysis": final_state.get("quality_analysis", {}),
                "test_validation": final_state.get("test_validation_result", {}),
                "execution_metrics": {
                    "agent_execution_times": final_state.get("agent_execution_times", {}),
                    "total_time": final_state.get("workflow_summary", {}).get("total_execution_time"),
                    "quality_score": final_state.get("overall_quality_score", 0),
                    "test_success_rate": final_state.get("test_success_rate", 0),
                    "code_coverage": final_state.get("code_coverage_percentage", 0)
                },
                "temperature_strategy": temperature_strategy,
                "run_id": run_id,
                "output_dir": run_output_dir,
                "status": "completed_successfully"
            }
        except Exception as e:
            # Log the error properly
            error_trace = traceback.format_exc()
            print(f"Error in execute_workflow: {e}\n{error_trace}")
            return {"error": str(e), "status": "failed", "trace": error_trace}

    async def batch_execute_workflows(batch_inputs: Dict[str, Any], config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
        """Execute multiple BRDs in a batch."""
        if "batch" not in batch_inputs or not isinstance(batch_inputs["batch"], list):
            return await execute_workflow(batch_inputs, config)

        batch = batch_inputs["batch"]
        if not batch:
            return {"error": "Batch is empty", "status": "failed"}

        tasks = []
        for i, input_item in enumerate(batch):
            if not isinstance(input_item, dict):
                tasks.append(asyncio.create_task(
                     asyncio.to_thread(lambda idx=i: {"batch_index": idx, "error": "Invalid item in batch", "status": "failed"})
                ))
            else:
                tasks.append(asyncio.create_task(execute_workflow(input_item, config)))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "batch_index": i,
                    "error": str(result),
                    "status": "failed",
                    "trace": ''.join(traceback.format_exception(type(result), result, result.__traceback__)) if hasattr(result, "__traceback__") else "No traceback"
                })
            else:
                # Ensure result is a dict before trying to set batch_index
                if isinstance(result, dict):
                    result["batch_index"] = i
                    processed_results.append(result)
                else:
                    processed_results.append({
                        "batch_index": i,
                        "error": "Non-dict result from execute_workflow",
                        "status": "failed",
                        "actual_result": str(result)
                    })
        return {"batch_results": processed_results}

    return RunnableLambda(batch_execute_workflows)