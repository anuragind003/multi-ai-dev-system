"""
Enhanced, consolidated system design generation tool to minimize API calls and improve reliability.
"""

import logging
from typing import Dict, Any, List
import json
import re

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from config import get_llm
from models.data_contracts import (
    SystemDesignOutput, 
    SystemComponentOutput, 
    ApiEndpoint, 
    DatabaseSchema,
    ComprehensiveSystemDesignOutput
)

logger = logging.getLogger(__name__)

# --- Pydantic Model for the Consolidated Tool Output ---

class ComprehensiveSystemDesignInput(BaseModel):
    """Input schema for the comprehensive system design generation tool."""
    requirements_analysis: dict = Field(description="The full, structured output from the BRD analysis phase.")
    tech_stack_recommendation: dict = Field(description="The full, structured output from the tech stack recommendation phase.")

# --- The New, Consolidated Tool ---

@tool(args_schema=ComprehensiveSystemDesignInput)
def generate_comprehensive_system_design(requirements_analysis: dict, tech_stack_recommendation: dict) -> ComprehensiveSystemDesignOutput:
    """
    Analyzes requirements and tech stack to generate a complete, well-reasoned system design
    in a single, efficient operation.

    This tool covers architectural components, data flows, API designs, database schemas,
    security, deployment, monitoring, and scalability strategies.

    Args:
        requirements_analysis: The full JSON output from the BRD analysis agent.
        tech_stack_recommendation: The full JSON output from the tech stack recommendation agent.

    Returns:
        A dictionary containing the full, structured system design.
    """
    logger.info("Executing consolidated tool: generate_comprehensive_system_design")

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are a world-class System Architect. Your task is to analyze the provided BRD analysis and tech stack recommendation, and produce a complete, structured system design as a JSON object.

The output MUST be a raw JSON object that strictly adheres to the following Pydantic model structure. Do not add any explanatory text, markdown, or any other characters before or after the JSON object.

Specifically, ensure the 'data_flow' field provides a clear description of how data moves through the system.

```json
{schema_definition_here}
```"""),
        ("human", "Please create a system design based on this BRD analysis and tech stack recommendation:\n\nBRD Analysis:\n{brd_analysis_json}\n\nTech Stack Recommendation:\n{tech_stack_recommendation_json}\n\nIMPORTANT: If the tech stack recommendation contains a 'selected_stack' field with user selections, you MUST use those specific technologies in your system design. The selected_stack represents the final user choices and should override any other recommendations.")
    ])
    
    json_schema = json.dumps(ComprehensiveSystemDesignOutput.model_json_schema(), indent=2)
    
    chain = prompt_template | get_llm(temperature=0.2)

    try:
        # Convert Pydantic models to dictionaries if needed
        if hasattr(requirements_analysis, 'model_dump'):
            requirements_analysis = requirements_analysis.model_dump()
        if hasattr(tech_stack_recommendation, 'model_dump'):
            tech_stack_recommendation = tech_stack_recommendation.model_dump()
            
        brd_analysis_json = json.dumps(requirements_analysis, indent=2)
        tech_stack_recommendation_json = json.dumps(tech_stack_recommendation, indent=2)
        
        response_text = chain.invoke({
            "schema_definition_here": json_schema,
            "brd_analysis_json": brd_analysis_json,
            "tech_stack_recommendation_json": tech_stack_recommendation_json
        }).content

        # The model sometimes wraps the JSON in markdown, so we extract the raw JSON string.
        try:
            # Handle markdown code blocks and extract JSON
            if '```json' in response_text:
                # Extract JSON from markdown code block
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                if json_end != -1:
                    clean_json_str = response_text[json_start:json_end].strip()
                else:
                    # Fallback to finding the JSON object
                    json_start_index = response_text.index('{')
                    json_end_index = response_text.rindex('}') + 1
                    clean_json_str = response_text[json_start:json_end_index]
            elif '```' in response_text and '{' in response_text:
                # Handle generic code blocks
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                clean_json_str = response_text[json_start:json_end]
            else:
                # Standard JSON extraction
                json_start_index = response_text.index('{')
                json_end_index = response_text.rindex('}') + 1
                clean_json_str = response_text[json_start_index:json_end_index]
            
            # Use a more robust method to clean up the JSON string
            # Remove trailing commas from objects and arrays
            clean_json_str = re.sub(r',\s*([}\]])', r'\1', clean_json_str)
            
            # Fix missing commas between JSON objects/arrays - common LLM error
            clean_json_str = re.sub(r'"\s*\n\s*"', '",\n    "', clean_json_str)
            clean_json_str = re.sub(r'}\s*\n\s*"', '},\n    "', clean_json_str)
            clean_json_str = re.sub(r']\s*\n\s*"', '],\n    "', clean_json_str)
            
            # Try to parse the cleaned JSON
            response_json = json.loads(clean_json_str)
        except ValueError:
            raise json.JSONDecodeError("Could not find JSON object in response", response_text, 0)
        
        logger.info("Successfully parsed system design LLM response into JSON.")
        return response_json

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from system design LLM response: {e}\\nRaw response: {response_text}", exc_info=True)
        return {"error": "json_decode_error", "details": f"Failed to parse LLM output: {e}"}
    except Exception as e:
        logger.error(f"Failed to generate comprehensive system design: {e}", exc_info=True)
        return {"error": "tool_execution_error", "details": str(e)} 