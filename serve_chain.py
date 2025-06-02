"""
LangServe integration for Multi-AI Development System.
Creates a runnable API endpoint for the complete development workflow.
"""

from typing import Dict, Any, List, Optional
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda
from config import get_system_config, get_llm
from agent_state import create_initial_agent_state, AgentState
from graph import create_phased_workflow, create_iterative_workflow
import os
import json
import asyncio
from contextlib import asynccontextmanager

def create_workflow_runnable() -> Runnable:
    """
    Create a runnable for the Multi-AI Development System workflow.
    This preserves the temperature-optimized agent strategy (0.1-0.4).
    """
    cfg = get_system_config()
    
    async def execute_workflow(inputs: Dict[str, Any], config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
        """Execute the workflow asynchronously with temperature strategy."""
        try:
            # Extract BRD content and configuration
            brd_content = inputs.get("brd_content", "")
            
            # Use phased workflow by default (or allow override from inputs)
            workflow_type = inputs.get("workflow_type", "phased")
            
            # Create the workflow
            if workflow_type == "iterative":
                workflow = create_iterative_workflow()
            else:
                workflow = create_phased_workflow()
                
            # Apply temperature strategy from input if provided
            temperature_strategy = inputs.get("temperature_strategy", {
                "brd_analyst": 0.3,
                "tech_stack_advisor": 0.2,
                "system_designer": 0.2,
                "planning_agent": 0.4,
                "code_generation": 0.1,
                "test_case_generator": 0.2,
                "code_quality": 0.1,
                "test_validation": 0.1
            })
            
            # Update system config with custom temperature strategy if provided
            if temperature_strategy:
                cfg.agent_temperatures.update(temperature_strategy)
            
            # Create initial state
            initial_state = create_initial_agent_state(brd_content, cfg.workflow_config)
            
            # Execute the workflow
            final_state = workflow.invoke(initial_state)
            
            # Return selected outputs from the final state with temperature metadata
            return {
                "requirements_analysis": final_state.get("requirements_analysis", {}),
                "tech_stack": final_state.get("tech_stack_recommendation", {}),
                "system_design": final_state.get("system_design", {}),
                "code_generation_result": final_state.get("code_generation_result", {}),
                "quality_analysis": final_state.get("quality_analysis", {}),
                "test_validation": final_state.get("test_validation_result", {}),
                "execution_metrics": {
                    "total_time": final_state.get("agent_execution_times", {}),
                    "quality_score": final_state.get("overall_quality_score", 0),
                    "test_success_rate": final_state.get("test_success_rate", 0),
                    "code_coverage": final_state.get("code_coverage_percentage", 0)
                },
                "temperature_strategy": temperature_strategy
            }
        except Exception as e:
            return {"error": str(e), "status": "failed"}
    
    # Support batch processing of multiple BRDs
    async def batch_execute_workflows(batch_inputs: Dict[str, Any], config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
        """Execute multiple BRDs in a batch."""
        if "batch" not in batch_inputs:
            # If not a batch request, process as a single workflow
            return await execute_workflow(batch_inputs, config)
        
        batch = batch_inputs["batch"]
        results = []
        
        # Process each BRD in the batch concurrently
        tasks = [execute_workflow(input_item, config) for input_item in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results, handling any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "batch_index": i,
                    "error": str(result),
                    "status": "failed"
                })
            else:
                result["batch_index"] = i
                processed_results.append(result)
                
        return {"batch_results": processed_results}
    
    # Create the runnable
    return RunnableLambda(batch_execute_workflows)