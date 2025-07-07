"""
Enhanced, consolidated BRD analysis tool to minimize API calls and improve reliability.
"""
import logging
import json
import re
from typing import Dict, Any, List

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from config import get_llm
from models.data_contracts import (
    Requirement,
    QualityAssessment,
    GapAnalysis,
    BRDRequirementsAnalysis
)

logger = logging.getLogger(__name__)

# --- The New, Consolidated Tool ---

class ComprehensiveBRDInput(BaseModel):
    raw_brd_content: str = Field(description="The full, raw text content of the Business Requirements Document (BRD).")

@tool(args_schema=ComprehensiveBRDInput)
def generate_comprehensive_brd_analysis(raw_brd_content: str) -> BRDRequirementsAnalysis:
    """
    Analyzes raw BRD text and generates a comprehensive, structured analysis in a single step.
    This includes requirements, quality assessment, and gap analysis.

    This tool extracts requirements, goals, constraints, performs a quality assessment,
    and identifies any gaps in the provided Business Requirements Document.
    The output is a structured JSON object conforming to the BRDRequirementsAnalysis model.
    """
    logger.info("Executing consolidated tool: generate_comprehensive_brd_analysis")
    
    # The prompt now includes instructions to output raw JSON.
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are a world-class business analyst AI. Your task is to analyze the provided Business Requirements Document (BRD) and convert it into a structured JSON object.

You MUST return ONLY a valid JSON object that follows this exact structure. No explanations, no markdown, no additional text - just the JSON object:

{{
  "project_name": "string - extracted project name",
  "project_summary": "string - brief summary of the project",
  "project_goals": ["list of project goals"],
  "target_audience": ["list of target users"],
  "business_context": "string - business background",
  "requirements": [
    {{
      "id": "REQ-001",
      "description": "requirement description",
      "category": "functional|non_functional",
      "priority": 1
    }}
  ],
  "functional_requirements": ["list of functional requirements as strings"],
  "non_functional_requirements": ["list of non-functional requirements as strings"],
  "stakeholders": ["list of stakeholders"],
  "success_criteria": ["list of success criteria"],
  "constraints": ["list of constraints"],
  "assumptions": ["list of assumptions"],
  "risks": ["list of risks"],
  "domain_specific_details": {{}},
  "quality_assessment": {{
    "completeness_score": 8,
    "clarity_score": 7,
    "consistency_score": 8,
    "recommendations": ["list of improvement recommendations"]
  }},
  "gap_analysis": {{
    "identified_gaps": ["list of gaps"],
    "recommendations_for_completion": ["list of completion recommendations"]
  }}
}}

CRITICAL: Your response must be ONLY this JSON object. Start with {{ and end with }}. No other text."""),
        ("human", "Analyze this BRD and extract all requirements and details:\n\n{brd_content}")
    ])
    
    # The Pydantic model is now used to generate a JSON schema for the prompt.
    json_schema = json.dumps(BRDRequirementsAnalysis.model_json_schema(), indent=2)
    
    # The parser is removed from the chain.
    chain = prompt_template | get_llm(temperature=0.2)

    try:
        # The chain now outputs raw text.
        response_text = chain.invoke({
            "brd_content": raw_brd_content
        }).content

        # Log the raw response for debugging
        logger.info(f"Raw LLM response (first 500 chars): {response_text[:500]}")

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
                    clean_json_str = response_text[json_start_index:json_end_index]
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
            
            # Clean up any trailing commas
            clean_json_str = re.sub(r',\s*([}\]])', r'\1', clean_json_str)
            
            response_json = json.loads(clean_json_str)
        except ValueError:
            # This handles cases where the '{' or '}' are not found.
            raise json.JSONDecodeError("Could not find JSON object in response", response_text, 0)
        
        logger.info("Successfully parsed LLM response into JSON.")
        logger.info(f"Parsed JSON keys: {list(response_json.keys())}")
        
        # Convert the response JSON to a BRDRequirementsAnalysis instance
        try:
            analysis_instance = BRDRequirementsAnalysis(**response_json)
            result = analysis_instance.model_dump()
            logger.info(f"BRDRequirementsAnalysis instance created successfully. Result keys: {list(result.keys())}")
            # Return the dict representation to maintain compatibility with the workflow
            return result
        except Exception as e:
            logger.error(f"Failed to create BRDRequirementsAnalysis instance: {e}")
            logger.info(f"Returning raw JSON with keys: {list(response_json.keys())}")
            # Return the raw JSON if model creation fails
            return response_json

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from LLM response: {e}\nRaw response: {response_text}", exc_info=True)
        return {"error": "json_decode_error", "details": f"Failed to parse LLM output: {e}"}
    except Exception as e:
        logger.error(f"Failed to generate comprehensive BRD analysis: {e}", exc_info=True)
        return {"error": "tool_execution_error", "details": str(e)} 