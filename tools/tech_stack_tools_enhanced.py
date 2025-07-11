"""
Enhanced, consolidated tech stack generation tools using shared utilities for consistency.
"""

import logging
import json
from typing import Dict, Any, Optional, Type
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, validator
from langchain_core.language_models.chat_models import BaseChatModel

from config import get_llm
from models.data_contracts import ComprehensiveTechStackOutput
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

class ComprehensiveTechStackInput(BaseModel):
    """Input schema for the comprehensive tech stack generation tool."""
    brd_analysis: dict = Field(description="The full, structured output from the BRD analysis phase.")
    llm: Optional[BaseChatModel] = Field(None, description="The language model to use for the analysis.")
    
    @validator('brd_analysis', pre=True)
    def parse_brd_analysis(cls, v):
        """Parse brd_analysis if it's a JSON string."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("brd_analysis must be a valid JSON string or dictionary")
        return v

@tool(args_schema=ComprehensiveTechStackInput)
def generate_comprehensive_tech_stack(brd_analysis: dict, llm: Optional[BaseChatModel] = None) -> Dict[str, Any]:
    """
    Analyzes the BRD analysis output and generates a comprehensive, structured tech stack recommendation.

    This tool provides recommendations for frontend, backend, database, cloud services,
    and architectural patterns with MULTIPLE OPTIONS for user selection.
    The output is a structured JSON object conforming to the ComprehensiveTechStackOutput model.
    """
    operation_name = "Tech stack comprehensive analysis"
    log_tool_start(operation_name, "Starting analysis")
    
    try:
        # Use the provided LLM or get a default one
        llm_instance = llm or get_llm(temperature=0.2)

        # Get the schema and escape curly braces to avoid LangChain template variable conflicts
        schema_json = json.dumps(ComprehensiveTechStackOutput.model_json_schema(), indent=2)
        escaped_schema = schema_json.replace("{", "{{").replace("}", "}}")
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", f"""You are a world-class CTO AI. Your task is to analyze the provided BRD analysis and recommend a complete technology stack with MULTIPLE OPTIONS for user selection.

IMPORTANT: You must provide EXACTLY 3 options for each technology category:
- frontend_options: 3 different frontend frameworks/technologies
- backend_options: 3 different backend frameworks/technologies  
- database_options: 3 different database technologies
- cloud_options: 3 different cloud platforms
- architecture_options: 3 different architecture patterns
- tool_options: 3-6 different development/deployment tools

Each option should have detailed reasoning for why it fits the project requirements. The user will select one option from each category.

You must also provide a "synthesis" object that contains an overall technology stack recommendation, summarizing the first/recommended option from each category with justification for the overall architecture approach.

You MUST return ONLY a valid JSON object that follows the schema provided below. No explanations, no markdown, no additional text - just the JSON object.

**Schema:**
```json
{escaped_schema}
```

CRITICAL: Your response must be ONLY this JSON object. Start with {{{{ and end with }}}}. No other text."""),
            ("human", "Analyze this BRD analysis and recommend a technology stack with 3 options for each category:\n\n{brd_analysis_str}")
        ])
        
        # Convert the brd_analysis dict to a string for the prompt
        brd_analysis_str = json.dumps(brd_analysis, indent=2)
        
        # Use standardized LLM invocation
        response_text = standardized_llm_invoke(
            llm=llm_instance,
            prompt_template=prompt_template,
            inputs={"brd_analysis_str": brd_analysis_str},
            operation_name=operation_name
        )
        
        # Use robust JSON parser
        response_json = robust_json_parser(response_text)
        
        # Validate and convert using shared utilities
        result = validate_and_convert_to_model(
            data=response_json,
            model_class=ComprehensiveTechStackOutput,
            apply_field_fixes=True
        )
        
        log_tool_execution(operation_name, True, f"Analysis completed with tech stack recommendations")
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

# Keep the legacy function for backward compatibility, but make it a simple wrapper
def fix_field_mappings(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Legacy function for backward compatibility.
    Use utils.analysis_tool_utils.fix_tech_stack_field_mappings instead.
    """
    from utils.analysis_tool_utils import fix_tech_stack_field_mappings
    return fix_tech_stack_field_mappings(data) 