"""
Enhanced, consolidated BRD analysis tool using shared utilities for consistency.
"""
import logging
import json
from typing import Dict, Any

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.language_models.chat_models import BaseChatModel

from config import get_llm
from models.data_contracts import BRDRequirementsAnalysis
from utils.analysis_tool_utils import (
    robust_json_parser,
    standardized_llm_invoke,
    validate_and_convert_to_model,
    create_error_response,
    log_tool_execution,
    log_tool_start,
    AnalysisToolError
)

logger = logging.getLogger(__name__)

class ComprehensiveBRDInput(BaseModel):
    raw_brd_content: str = Field(description="The full, raw text content of the Business Requirements Document (BRD).")
    llm: BaseChatModel = Field(None, description="The language model to use for the analysis.")

@tool(args_schema=ComprehensiveBRDInput)
def generate_comprehensive_brd_analysis(raw_brd_content: str, llm: BaseChatModel = None) -> Dict[str, Any]:
    """
    Analyzes raw BRD text and generates a comprehensive, structured analysis in a single step.
    This includes requirements, goals, constraints, performs a quality assessment,
    and identifies any gaps in the provided Business Requirements Document.

    The output is a structured JSON object conforming to the BRDRequirementsAnalysis model.
    """
    operation_name = "BRD comprehensive analysis"
    start_time = logger.handlers[0].formatter.formatTime(logger.makeRecord(
        logger.name, logging.INFO, __file__, 0, "", (), None
    )) if logger.handlers else 0
    
    log_tool_start(operation_name, "Starting analysis")
    
    try:
        # Use the provided LLM or get a default one
        llm_instance = llm or get_llm(temperature=0.2)
        
        # Create the prompt template for BRD analysis
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
        
        # Use standardized LLM invocation
        response_text = standardized_llm_invoke(
            llm=llm_instance,
            prompt_template=prompt_template,
            inputs={"brd_content": raw_brd_content},
            operation_name=operation_name
        )
        
        # Use robust JSON parser
        response_json = robust_json_parser(response_text)
        
        # Validate and convert using shared utilities
        result = validate_and_convert_to_model(
            data=response_json,
            model_class=BRDRequirementsAnalysis,
            apply_field_fixes=True
        )
        
        log_tool_execution(operation_name, True, f"Analysis completed with {len(result.get('requirements', []))} requirements")
        return result

    except AnalysisToolError as e:
        # Tool-specific errors (LLM invocation failed)
        error_response = create_error_response("tool_execution_error", str(e), operation_name)
        log_tool_execution(operation_name, False, str(e))
        return error_response
        
    except json.JSONDecodeError as e:
        # JSON parsing errors
        error_response = create_error_response("json_decode_error", f"Failed to parse LLM output: {e}", operation_name)
        log_tool_execution(operation_name, False, f"JSON parsing failed: {e}")
        return error_response
        
    except Exception as e:
        # Any other unexpected errors
        error_response = create_error_response("unexpected_error", str(e), operation_name)
        log_tool_execution(operation_name, False, f"Unexpected error: {e}")
        return error_response 