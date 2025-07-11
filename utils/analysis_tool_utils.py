"""
Shared utilities for BRD and Tech Stack analysis tools.
Provides standardized JSON parsing, error handling, and data transformation functions.
"""

import logging
import json
import re
from typing import Dict, Any, Optional, List, Union, Type
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class AnalysisToolError(Exception):
    """Custom exception for analysis tool errors."""
    pass

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
        
        # Fix common null/boolean value issues
        json_str = re.sub(r'\bNone\b', 'null', json_str)
        json_str = re.sub(r'\bTrue\b', 'true', json_str)
        json_str = re.sub(r'\bFalse\b', 'false', json_str)
        
        return json_str
    
    # Main parsing logic
    try:
        # Step 1: Extract JSON from the response text
        json_string = extract_json_from_text(response_text)
        logger.debug(f"Extracted JSON string (first 200 chars): {json_string[:200]}")
        
        # Step 2: Clean the JSON
        clean_json = clean_json_string(json_string)
        
        # Step 3: Parse the final JSON
        result = json.loads(clean_json)
        logger.info("Successfully parsed JSON from LLM response")
        return result
        
    except (ValueError, json.JSONDecodeError) as e:
        logger.error(f"Robust JSON parsing failed: {e}")
        logger.error(f"Original response (first 1000 chars): {response_text[:1000]}")
        raise json.JSONDecodeError(f"Could not parse JSON after all attempts: {e}", response_text, 0)

def standardized_llm_invoke(
    llm: BaseChatModel,
    prompt_template: ChatPromptTemplate,
    inputs: Dict[str, Any],
    operation_name: str = "analysis"
) -> str:
    """
    Standardized LLM invocation with consistent error handling.
    
    Args:
        llm: The language model instance
        prompt_template: The prompt template to use
        inputs: Input variables for the prompt
        operation_name: Name of the operation for logging
        
    Returns:
        Raw text response from LLM
        
    Raises:
        AnalysisToolError: If LLM invocation fails
    """
    try:
        logger.info(f"Starting {operation_name} with LLM")
        chain = prompt_template | llm
        response = chain.invoke(inputs)
        
        response_text = response.content
        logger.info(f"LLM {operation_name} completed successfully")
        logger.debug(f"Raw LLM response (first 500 chars): {response_text[:500]}")
        
        return response_text
        
    except Exception as e:
        logger.error(f"LLM {operation_name} failed: {e}", exc_info=True)
        raise AnalysisToolError(f"Failed to execute {operation_name}: {str(e)}")

def validate_and_convert_to_model(
    data: Dict[str, Any],
    model_class: Type[BaseModel],
    apply_field_fixes: bool = True
) -> Union[Dict[str, Any], BaseModel]:
    """
    Validate data against a Pydantic model with optional field fixing.
    
    Args:
        data: The data to validate
        model_class: The Pydantic model class
        apply_field_fixes: Whether to apply field mapping fixes
        
    Returns:
        Either the validated model instance converted to dict, or the original data
    """
    try:
        if apply_field_fixes:
            # Apply any model-specific field fixes
            if hasattr(model_class, '__name__'):
                model_name = model_class.__name__
                if 'TechStack' in model_name:
                    data = fix_tech_stack_field_mappings(data)
                elif 'BRD' in model_name:
                    data = fix_brd_field_mappings(data)
        
        # Validate against the model
        validated_instance = model_class(**data)
        logger.info(f"Successfully validated data against {model_class.__name__}")
        
        # Return as dict for consistency
        return validated_instance.model_dump()
        
    except Exception as e:
        logger.warning(f"Model validation failed for {model_class.__name__}: {e}")
        logger.info("Returning raw data without validation")
        return data

def fix_tech_stack_field_mappings(data: Dict[str, Any]) -> Dict[str, Any]:
    """Fix common field mapping issues in tech stack analysis data."""
    
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
            score_defaults = {
                'scalability_score': 7.0,
                'maintainability_score': 7.0,
                'development_speed_score': 5.0,
                'overall_score': 6.0
            }
            for score_field, default_value in score_defaults.items():
                if score_field not in item:
                    item[score_field] = default_value
                    
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
            risk_defaults = {
                'category': 'General Risk',
                'description': 'No description provided.',
                'severity': 'Medium',
                'likelihood': 'Medium',
                'mitigation': 'Monitor and address as needed.'
            }
            for field, default_value in risk_defaults.items():
                if field not in item:
                    item[field] = default_value
        return item

    # Apply fixes to different categories
    for category in ['tool_options', 'frontend_options', 'backend_options', 'database_options', 'cloud_options']:
        if category in data and isinstance(data[category], list):
            data[category] = [fix_tech_component(item) for item in data[category]]
    
    if 'architecture_options' in data and isinstance(data['architecture_options'], list):
        data['architecture_options'] = [fix_architecture_option(item) for item in data['architecture_options']]

    if 'risks' in data and isinstance(data['risks'], list):
        data['risks'] = [fix_tech_risk(item) for item in data['risks']]

    # Ensure synthesis field is present and properly formatted
    if 'synthesis' not in data or data['synthesis'] is None:
        data['synthesis'] = create_default_synthesis(data)

    return data

def fix_brd_field_mappings(data: Dict[str, Any]) -> Dict[str, Any]:
    """Fix common field mapping issues in BRD analysis data."""
    
    # Ensure all required fields are present with defaults
    brd_defaults = {
        'project_name': 'Unnamed Project',
        'project_summary': 'No summary provided.',
        'project_goals': [],
        'target_audience': [],
        'business_context': 'No business context provided.',
        'requirements': [],
        'functional_requirements': [],
        'non_functional_requirements': [],
        'stakeholders': [],
        'success_criteria': [],
        'constraints': [],
        'assumptions': [],
        'risks': [],
        'domain_specific_details': {},
        'quality_assessment': {
            'completeness_score': 5,
            'clarity_score': 5,
            'consistency_score': 5,
            'recommendations': []
        },
        'gap_analysis': {
            'identified_gaps': [],
            'recommendations_for_completion': []
        }
    }
    
    for field, default_value in brd_defaults.items():
        if field not in data:
            data[field] = default_value
    
    # Fix requirements format if needed
    if 'requirements' in data and isinstance(data['requirements'], list):
        for i, req in enumerate(data['requirements']):
            if isinstance(req, str):
                # Convert string requirements to proper format
                data['requirements'][i] = {
                    'id': f'REQ-{i+1:03d}',
                    'description': req,
                    'category': 'functional',
                    'priority': 1
                }
            elif isinstance(req, dict):
                # Ensure required fields are present
                if 'id' not in req:
                    req['id'] = f'REQ-{i+1:03d}'
                if 'category' not in req:
                    req['category'] = 'functional'
                if 'priority' not in req:
                    req['priority'] = 1
    
    return data

def create_default_synthesis(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a default synthesis object from tech stack data."""
    synthesis = {
        "backend": {},
        "frontend": {},
        "database": {},
        "architecture_pattern": "Microservices Architecture",
        "deployment_environment": {"platform": "Cloud", "reasoning": "Scalable and flexible deployment"},
        "key_libraries_tools": [],
        "estimated_complexity": "Medium"
    }
    
    # Extract from first options if available
    for category, key in [('backend_options', 'backend'), ('frontend_options', 'frontend'), ('database_options', 'database')]:
        if category in data and data[category]:
            first_option = data[category][0]
            if category == 'database_options':
                synthesis[key] = {
                    "technology": first_option.get('name', 'PostgreSQL'),
                    "justification": first_option.get('reasoning', f'Recommended {key} choice')
                }
            else:
                lang = first_option.get('language', 'JavaScript' if key == 'frontend' else 'Python')
                name = first_option.get('name', 'React' if key == 'frontend' else 'FastAPI')
                synthesis[key] = {
                    "technology": f"{lang} with {name}",
                    "justification": first_option.get('reasoning', f'Recommended {key} choice')
                }
    
    if 'architecture_options' in data and data['architecture_options']:
        first_arch = data['architecture_options'][0]
        synthesis["architecture_pattern"] = first_arch.get('pattern', 'Microservices Architecture')
    
    if 'tool_options' in data and data['tool_options']:
        synthesis["key_libraries_tools"] = [
            {
                "name": tool.get('name', 'Tool'),
                "purpose": tool.get('reasoning', 'Development tool')
            }
            for tool in data['tool_options'][:3]  # Limit to first 3 tools
        ]
    else:
        # Provide default tools if none specified
        synthesis["key_libraries_tools"] = [
            {"name": "Git", "purpose": "Version control and collaboration"},
            {"name": "Docker", "purpose": "Containerization and deployment"},
            {"name": "CI/CD", "purpose": "Automated testing and deployment"}
        ]
    
    return synthesis

def create_error_response(error_type: str, details: str, operation_name: str = "analysis") -> Dict[str, Any]:
    """Create a standardized error response."""
    return {
        "error": error_type,
        "operation": operation_name,
        "details": details,
        "timestamp": logger.handlers[0].formatter.formatTime(logger.makeRecord(
            logger.name, logging.ERROR, __file__, 0, "", (), None
        )) if logger.handlers else "unknown"
    }

def log_tool_start(operation_name: str, details: str = ""):
    """Standardized logging for the start of tool execution."""
    logger.info(f" {operation_name} starting... {details}")

def log_tool_execution(operation_name: str, success: bool, details: str = "", execution_time: float = 0.0):
    """Standardized logging for tool execution completion."""
    if success:
        logger.info(f" {operation_name} completed successfully in {execution_time:.2f}s")
        if details:
            logger.debug(f"Details: {details}")
    else:
        logger.error(f" {operation_name} failed: {details}") 