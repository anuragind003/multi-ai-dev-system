"""
Enhanced, consolidated planning tools to minimize API calls and improve reliability.
"""

import logging
from typing import Dict, Any, Optional
import json

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from models.data_contracts import WorkItemBacklog, ComprehensiveImplementationPlanOutput
from config import get_llm

logger = logging.getLogger(__name__)


class WorkItemBacklogInput(BaseModel):
    """Input schema for the work item backlog generation tool."""
    requirements_analysis: dict = Field(description="The full, structured output from the BRD analysis phase.")
    tech_stack_recommendation: dict = Field(description="The full, structured output from the tech stack recommendation phase.")
    system_design: dict = Field(description="The full, structured output from the system design phase.")


@tool(args_schema=WorkItemBacklogInput)
def generate_comprehensive_work_item_backlog(requirements_analysis: dict, tech_stack_recommendation: dict, system_design: dict) -> WorkItemBacklog:
    """
    Analyzes project context to generate a detailed backlog of work items.
    """
    logger.info("Executing consolidated tool: generate_comprehensive_work_item_backlog")
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are an expert technical project manager and system architect. Your task is to create a detailed, step-by-step implementation plan for a new software project by breaking it down into a granular backlog of 'Work Items'.

Your goal is to create a list of tasks so small and specific that a junior developer could pick any one of them up and complete it without further questions.

The output MUST be a raw JSON object that strictly adheres to the `WorkItemBacklog` schema. Do not add any explanatory text, markdown, or any other characters before or after the JSON object.

```json
{schema_definition_here}
```"""),
        ("human", """Please create a complete work item backlog based on this BRD analysis:
{requirements_analysis_json}

This tech stack:
{tech_stack_json}

And this system design:
{system_design_json}
""")
    ])
    
    json_schema = json.dumps(WorkItemBacklog.model_json_schema(), indent=2)
    
    chain = prompt_template | get_llm(temperature=0.2)

    try:
        # Convert Pydantic models to dictionaries if needed
        if hasattr(requirements_analysis, 'model_dump'):
            requirements_analysis = requirements_analysis.model_dump()
        if hasattr(tech_stack_recommendation, 'model_dump'):
            tech_stack_recommendation = tech_stack_recommendation.model_dump()
        if hasattr(system_design, 'model_dump'):
            system_design = system_design.model_dump()
            
        requirements_analysis_json = json.dumps(requirements_analysis, indent=2)
        tech_stack_json = json.dumps(tech_stack_recommendation, indent=2)
        system_design_json = json.dumps(system_design, indent=2)
        
        response_text = chain.invoke({
            "schema_definition_here": json_schema,
            "requirements_analysis_json": requirements_analysis_json,
            "tech_stack_json": tech_stack_json,
            "system_design_json": system_design_json,
        }).content

        try:
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.rfind('```')
                clean_json_str = response_text[json_start:json_end].strip() if json_end != -1 else response_text[json_start:].strip()
            else:
                json_start_index = response_text.index('{')
                json_end_index = response_text.rindex('}') + 1
                clean_json_str = response_text[json_start_index:json_end_index]
            
            response_json = json.loads(clean_json_str)
        except (ValueError, IndexError):
            raise json.JSONDecodeError("Could not find or parse JSON object in response", response_text, 0)
        
        logger.info("Successfully parsed work item backlog LLM response into JSON.")
        return WorkItemBacklog(**response_json)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from work item backlog LLM response: {e}\\nRaw response: {response_text}", exc_info=True)
        return {"error": "json_decode_error", "details": f"Failed to parse LLM output: {e}"}
    except Exception as e:
        logger.error(f"Failed to generate work item backlog: {e}", exc_info=True)
        return {"error": "tool_execution_error", "details": str(e)} 