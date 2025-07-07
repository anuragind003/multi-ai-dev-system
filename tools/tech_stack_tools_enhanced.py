"""
Enhanced, consolidated tech stack generation tools to minimize API calls and improve reliability.
"""

import logging
from typing import Dict, Any, Optional, List
import json
import re

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, validator

from config import get_llm
from models.data_contracts import (
    TechStackComponent,
    ArchitecturePatternOption,
    TechRisk,
    TechStackSynthesisOutput,
    SelectedTechStack,
    ComprehensiveTechStackOutput
)

logger = logging.getLogger(__name__)

def robust_json_parser(response_text: str) -> Dict[str, Any]:
    """
    Robust JSON parser that handles various LLM output formats and common JSON errors.
    
    Args:
        response_text: Raw text response from LLM that should contain JSON
        
    Returns:
        Parsed JSON dictionary
        
    Raises:
        json.JSONDecodeError: If JSON cannot be extracted or parsed after all attempts
    """
    
    def extract_json_from_text(text: str) -> str:
        """Extract JSON from various text formats (markdown, code blocks, etc.)"""
        
        # Method 1: Extract from markdown code blocks
        json_patterns = [
            r'```json\s*\n(.*?)\n```',  # ```json ... ```
            r'```\s*\n(.*?)\n```',      # ``` ... ```
            r'`(.*?)`',                 # `...`
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                potential_json = match.group(1).strip()
                if potential_json.startswith('{') and potential_json.endswith('}'):
                    return potential_json
        
        # Method 2: Find JSON object boundaries
        start_idx = text.find('{')
        if start_idx != -1:
            end_idx = text.rfind('}')
            if end_idx != -1 and end_idx > start_idx:
                return text[start_idx:end_idx + 1]
        
        # Method 3: Return the text as-is if it looks like JSON
        stripped_text = text.strip()
        if stripped_text.startswith('{') and stripped_text.endswith('}'):
            return stripped_text
            
        raise ValueError("No JSON object found in text")
    
    def clean_json_string(json_str: str) -> str:
        """Clean common JSON formatting issues from LLM outputs"""
        
        # Remove extra whitespace and normalize line endings
        json_str = re.sub(r'\r\n', '\n', json_str)
        json_str = re.sub(r'\r', '\n', json_str)
        
        # Fix trailing commas (common LLM error)
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # Fix missing commas between JSON elements
        patterns_to_fix = [
            (r'"\s*\n\s*"', '",\n    "'),           # Missing comma between strings
            (r'}\s*\n\s*"', '},\n    "'),           # Missing comma after object before string
            (r']\s*\n\s*"', '],\n    "'),           # Missing comma after array before string
            (r'}\s*\n\s*\{', '},\n    {'),          # Missing comma between objects
            (r']\s*\n\s*\[', '],\n    ['),          # Missing comma between arrays
            (r'"\s*\n\s*\{', '",\n    {'),          # Missing comma before object
            (r'"\s*\n\s*\[', '",\n    ['),          # Missing comma before array
        ]
        
        for pattern, replacement in patterns_to_fix:
            json_str = re.sub(pattern, replacement, json_str)
        
        # Fix common quote issues
        json_str = re.sub(r'([^\\])"([^",:}\]\s])', r'\1"\2', json_str)  # Fix unescaped quotes
        
        # Fix null values that might be written incorrectly
        json_str = re.sub(r'\bNone\b', 'null', json_str)
        json_str = re.sub(r'\bTrue\b', 'true', json_str)
        json_str = re.sub(r'\bFalse\b', 'false', json_str)
        
        return json_str
    
    def validate_and_fix_json(json_str: str) -> str:
        """Validate JSON and attempt to fix common structural issues"""
        
        try:
            # First attempt: try parsing as-is
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError as e:
            logger.warning(f"Initial JSON parse failed: {e}")
            
            # Attempt to fix the specific error
            if "Expecting ',' delimiter" in str(e):
                # Try to add missing commas around the error position
                pos = getattr(e, 'pos', 0)
                before = json_str[:pos]
                after = json_str[pos:]
                
                # Look for patterns that need commas
                if after.startswith('\n') and before.rstrip().endswith(('"', '}', ']')):
                    json_str = before.rstrip() + ',' + after
                    try:
                        json.loads(json_str)
                        return json_str
                    except:
                        pass
            
            # If specific fixes don't work, try more aggressive cleaning
            json_str = clean_json_string(json_str)
            
            try:
                json.loads(json_str)
                return json_str
            except json.JSONDecodeError:
                # Last resort: try to reconstruct the JSON
                raise
    
    # Main parsing logic
    try:
        # Step 1: Extract JSON from the response text
        json_string = extract_json_from_text(response_text)
        logger.debug(f"Extracted JSON string (first 200 chars): {json_string[:200]}")
        
        # Step 2: Clean and validate the JSON
        clean_json = validate_and_fix_json(json_string)
        
        # Step 3: Parse the final JSON
        result = json.loads(clean_json)
        logger.info("Successfully parsed JSON from LLM response")
        return result
        
    except (ValueError, json.JSONDecodeError) as e:
        logger.error(f"Robust JSON parsing failed: {e}")
        logger.error(f"Original response (first 1000 chars): {response_text[:1000]}")
        raise json.JSONDecodeError(f"Could not parse JSON after all attempts: {e}", response_text, 0)


def fix_field_mappings(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fix common field mapping issues in the LLM response.
    """
    def fix_tech_component(item: Dict[str, Any]) -> Dict[str, Any]:
        """Fix TechStackComponent field mismatches."""
        if isinstance(item, dict):
            # Map 'purpose' to 'reasoning' if present
            if 'purpose' in item and 'reasoning' not in item:
                item['reasoning'] = item.pop('purpose')
            # Ensure required fields are present
            if 'reasoning' not in item:
                item['reasoning'] = item.get('description', 'No reasoning provided.')
        return item

    def fix_architecture_option(item: Dict[str, Any]) -> Dict[str, Any]:
        """Fix ArchitecturePatternOption field mismatches."""
        if isinstance(item, dict):
            # Map 'justification' to 'reasoning' if present
            if 'justification' in item and 'reasoning' not in item:
                item['reasoning'] = item.pop('justification')
            
            # Add missing score fields with default values
            if 'scalability_score' not in item:
                item['scalability_score'] = 7.0
            if 'maintainability_score' not in item:
                item['maintainability_score'] = 7.0
            if 'development_speed_score' not in item:
                item['development_speed_score'] = 5.0
            if 'overall_score' not in item:
                item['overall_score'] = 6.0
            if 'reasoning' not in item:
                item['reasoning'] = 'Default architecture pattern reasoning.'
        return item

    def fix_tech_risk(item: Dict[str, Any]) -> Dict[str, Any]:
        """Fix TechRisk field mismatches."""
        if isinstance(item, dict):
            # Map 'name' to 'category' if present
            if 'name' in item and 'category' not in item:
                item['category'] = item.pop('name')
            
            # Ensure all required fields are present with defaults
            if 'category' not in item:
                item['category'] = 'General Risk'
            if 'description' not in item:
                item['description'] = item.get('name', 'No description provided.')
            if 'severity' not in item:
                item['severity'] = 'Medium'
            if 'likelihood' not in item:
                item['likelihood'] = 'Medium'
            if 'mitigation' not in item:
                item['mitigation'] = 'Monitor and address as needed.'
        return item

    # Fix different categories
    if 'tool_options' in data and isinstance(data['tool_options'], list):
        data['tool_options'] = [fix_tech_component(item) for item in data['tool_options']]
    
    if 'frontend_options' in data and isinstance(data['frontend_options'], list):
        data['frontend_options'] = [fix_tech_component(item) for item in data['frontend_options']]
    
    if 'backend_options' in data and isinstance(data['backend_options'], list):
        data['backend_options'] = [fix_tech_component(item) for item in data['backend_options']]
    
    if 'database_options' in data and isinstance(data['database_options'], list):
        data['database_options'] = [fix_tech_component(item) for item in data['database_options']]
    
    if 'cloud_options' in data and isinstance(data['cloud_options'], list):
        data['cloud_options'] = [fix_tech_component(item) for item in data['cloud_options']]
    
    if 'architecture_options' in data and isinstance(data['architecture_options'], list):
        data['architecture_options'] = [fix_architecture_option(item) for item in data['architecture_options']]

    if 'risks' in data and isinstance(data['risks'], list):
        data['risks'] = [fix_tech_risk(item) for item in data['risks']]

    return data


class ComprehensiveTechStackInput(BaseModel):
    """Input schema for the comprehensive tech stack generation tool."""
    brd_analysis: dict = Field(description="The full, structured output from the BRD analysis phase.")
    
    @validator('brd_analysis', pre=True)
    def parse_brd_analysis(cls, v):
        """Parse brd_analysis if it's a JSON string."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # If it's not valid JSON, leave it as is and let validation fail normally
                pass
        return v

# --- The New, Consolidated Tool ---

@tool(args_schema=ComprehensiveTechStackInput)
def generate_comprehensive_tech_stack(brd_analysis: dict) -> ComprehensiveTechStackOutput:
    """
    Analyzes technical requirements from a BRD analysis and generates a complete,
    well-reasoned technology stack recommendation in a single, efficient operation.

    This tool evaluates frontend, backend, database, and architectural patterns,
    provides a justification, and assesses risks, all within one consolidated operation
    to minimize API calls and improve efficiency.

    Args:
        brd_analysis: The full JSON output from the BRD analysis agent.

    Returns:
        A dictionary containing the full, structured technology stack recommendation.
    """
    logger.info("Executing consolidated tool: generate_comprehensive_tech_stack")

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are a world-class Solutions Architect. Your task is to analyze the provided BRD analysis and produce a complete, structured technology stack recommendation as a JSON object. Provide a maximum of 3 ranked options for each category (frontend, backend, database, cloud, architecture, tools). 

CRITICAL FIELD NAMING REQUIREMENTS:
- For TechStackComponent objects (frontend_options, backend_options, database_options, cloud_options, tool_options): use "reasoning" NOT "purpose" or "description"
- For ArchitecturePatternOption objects (architecture_options): MUST include all these numeric score fields:
  - scalability_score: float (1-10)
  - maintainability_score: float (1-10) 
  - development_speed_score: float (1-10)
  - overall_score: float (1-10)
  - reasoning: string (NOT "justification")
- For TechRisk objects (risks): MUST include all these fields:
  - category: string (NOT "name")
  - description: string (detailed description of the risk)
  - severity: string ("High", "Medium", or "Low")
  - likelihood: string ("High", "Medium", or "Low")
  - mitigation: string (strategy to address the risk)

For each option, include its name, language (if applicable), reasoning for selection, key libraries, and clearly list pros and cons. Finally, provide a synthesis of the overall recommended stack. Do not include the 'selected_stack' field; that will be populated by human choice later. 

The output MUST be a raw JSON object that strictly adheres to the following Pydantic model structure. Do not add any explanatory text, markdown, or any other characters before or after the JSON object.

{schema_definition_here}"""),
        ("human", "Please create a tech stack recommendation based on this BRD analysis:\n\n{brd_analysis_json}")
    ])
    
    json_schema = json.dumps(ComprehensiveTechStackOutput.model_json_schema(), indent=2)
    
    chain = prompt_template | get_llm(temperature=0.2)

    try:
        brd_analysis_json = json.dumps(brd_analysis, indent=2)
        
        response_text = chain.invoke({
            "schema_definition_here": json_schema,
            "brd_analysis_json": brd_analysis_json
        }).content

        # Use the robust JSON parser
        response_json = robust_json_parser(response_text)
        
        # Fix field mapping issues
        response_json = fix_field_mappings(response_json)
        
        logger.info("Successfully parsed tech stack LLM response into JSON.")
        return response_json

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from tech stack LLM response: {e}", exc_info=True)
        return {"error": "json_decode_error", "details": f"Failed to parse LLM output: {e}"}
    except Exception as e:
        logger.error(f"Failed to generate comprehensive tech stack recommendation: {e}", exc_info=True)
        return {"error": "tool_execution_error", "details": str(e)} 