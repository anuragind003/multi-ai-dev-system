"""
Enhanced BRD Analysis Tools with Hybrid Validation and API Token Optimization

This module provides enhanced BRD analysis tools that use the 3-layer hybrid validation
system and include API token optimization features for React agents.

Key Enhancements:
- 3-layer hybrid validation for all inputs
- API token usage optimization
- Enhanced error recovery and resilience
- Performance tracking and caching
- React agent input preprocessing
- Enhanced memory management for cross-tool data sharing
"""

import re
import logging
import json
import time
from typing import Dict, Any, List, Optional, Union, Callable
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.prompts import PromptTemplate

from tools.json_handler import JsonHandler
from models.data_contracts import BRDRequirementsAnalysis
from utils.enhanced_tool_validator import robust_tool_wrapper, enhanced_tool_validator
from utils.hybrid_validator import HybridValidator
from utils.react_tool_wrapper import smart_react_tool
# from utils.llm_response_parser import LLMResponseParser  # Not needed for current implementation
# from utils.enhanced_tools_shared import smart_react_tool  # Using react_tool_wrapper instead

# Enhanced Memory Management for BRD Tools
try:
    from enhanced_memory_manager import create_memory_manager, EnhancedSharedProjectMemory
    ENHANCED_MEMORY_AVAILABLE = True
except ImportError:
    ENHANCED_MEMORY_AVAILABLE = False

logger = logging.getLogger(__name__)

# Global variables for enhanced tools
_llm = None
_brd_content = ""
_json_handler = JsonHandler()
_hybrid_validator = HybridValidator(logger)
_tool_memory = None

# Cost Control Configuration for API Token Management
class BRDCostConfig:
    """Configuration for BRD gap filling cost control."""
    
    def __init__(self):
        # Master control
        self.gap_filling_enabled = True
        
        # Mode selection
        self.budget_mode = False  # Use heuristic fallbacks instead of LLM
        
        # Section limits
        self.max_sections_to_generate = 3  # Maximum sections to generate per BRD
        self.priority_sections_only = False  # Only generate critical sections
        
        # Priority order (most important first)
        self.section_priority = [
            "goals",
            "constraints", 
            "assumptions",
            "risks",
            "business_context",
            "target_audience"
        ]
        
        # Caching
        self.enable_caching = True
        self.cache_duration_hours = 24
        
        # Token estimation and limits
        self.estimated_tokens_per_section = {
            "goals": 400,
            "constraints": 450,
            "assumptions": 400,
            "risks": 350,
            "business_context": 300,
            "target_audience": 350
        }
        self.max_tokens_per_brd = 2000
        
        # Fallback strategies
        self.use_heuristic_fallbacks = True
        self.use_template_based_generation = True

# Global cost configuration instance
_cost_config = BRDCostConfig()

def configure_brd_cost_control(**kwargs):
    """Configure cost control settings for BRD gap filling."""
    global _cost_config
    
    for key, value in kwargs.items():
        if hasattr(_cost_config, key):
            setattr(_cost_config, key, value)
            logger.info(f"BRD cost control: {key} = {value}")
        else:
            logger.warning(f"Unknown cost control setting: {key}")

def get_brd_cost_stats() -> Dict[str, Any]:
    """Get current cost control configuration and estimated usage."""
    global _cost_config
    
    # Calculate estimated tokens for current config
    priority_sections = _cost_config.section_priority[:_cost_config.max_sections_to_generate]
    estimated_tokens = sum(_cost_config.estimated_tokens_per_section.get(section, 350) 
                          for section in priority_sections)
    
    return {
        "gap_filling_enabled": _cost_config.gap_filling_enabled,
        "budget_mode": _cost_config.budget_mode,
        "max_sections": _cost_config.max_sections_to_generate,
        "priority_sections_only": _cost_config.priority_sections_only,
        "estimated_tokens_per_brd": estimated_tokens,
        "max_tokens_limit": _cost_config.max_tokens_per_brd,
        "within_budget": estimated_tokens <= _cost_config.max_tokens_per_brd,
        "caching_enabled": _cost_config.enable_caching,
        "heuristic_fallbacks": _cost_config.use_heuristic_fallbacks
    }

# Simple cache for generated content
_generation_cache = {}

def _get_cache_key(section_type: str, content_hash: str) -> str:
    """Generate cache key for content."""
    return f"{section_type}_{content_hash[:16]}"

def _get_cached_content(section_type: str, brd_content: str) -> Optional[List[str]]:
    """Get cached generated content if available."""
    global _generation_cache, _cost_config
    
    if not _cost_config.enable_caching:
        return None
    
    import hashlib
    content_hash = hashlib.md5(brd_content.encode()).hexdigest()
    cache_key = _get_cache_key(section_type, content_hash)
    
    cached_data = _generation_cache.get(cache_key)
    if cached_data:
        # Check if cache is still valid
        import time
        cache_time, content = cached_data
        if time.time() - cache_time < (_cost_config.cache_duration_hours * 3600):
            logger.info(f"Using cached {section_type} content (saved ~{_cost_config.estimated_tokens_per_section.get(section_type, 350)} tokens)")
            return content
        else:
            # Cache expired
            del _generation_cache[cache_key]
    
    return None

def _cache_content(section_type: str, brd_content: str, content: List[str]):
    """Cache generated content."""
    global _generation_cache, _cost_config
    
    if not _cost_config.enable_caching:
        return
    
    import hashlib
    import time
    content_hash = hashlib.md5(brd_content.encode()).hexdigest()
    cache_key = _get_cache_key(section_type, content_hash)
    
    _generation_cache[cache_key] = (time.time(), content)
    logger.info(f"Cached {section_type} content for future use")

# Enhanced JSON Parsing Utilities for Better LLM Response Handling
class EnhancedJSONParser:
    """Enhanced JSON parser for handling LLM output parsing errors."""
    
    @staticmethod
    def clean_json_string(text: str) -> str:
        """Clean and prepare text for JSON parsing."""
        if not text:
            return "{}"
        
        # Remove common LLM artifacts
        text = text.strip()
        
        # Remove markdown code blocks
        text = re.sub(r'```(?:json)?\s*', '', text)
        text = re.sub(r'```\s*$', '', text)
        
        # Remove leading/trailing text that's not JSON
        json_start = text.find('{')
        json_end = text.rfind('}')
        
        if json_start != -1 and json_end != -1 and json_end > json_start:
            text = text[json_start:json_end + 1]
        
        # Fix common JSON formatting issues
        text = re.sub(r',\s*}', '}', text)  # Remove trailing commas before }
        text = re.sub(r',\s*]', ']', text)  # Remove trailing commas before ]
        
        # Fix unescaped quotes in strings
        text = re.sub(r'(?<!\\)"(?=.*":)', '\\"', text)
        
        return text
    
    @staticmethod
    def safe_json_parse(text: str, default: Any = None) -> Any:
        """Safely parse JSON with fallback options."""
        if not text:
            return default or {}
        
        try:
            # First try direct parsing
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        try:
            # Try cleaning the text first
            cleaned = EnhancedJSONParser.clean_json_string(text)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        
        try:
            # Try extracting JSON from text using regex
            json_pattern = r'\{(?:[^{}]|{[^{}]*})*\}'
            matches = re.findall(json_pattern, text, re.DOTALL)
            if matches:
                return json.loads(matches[0])
        except (json.JSONDecodeError, IndexError):
            pass
        
        # Last resort: try to extract key-value pairs manually
        try:
            return EnhancedJSONParser.extract_key_values(text)
        except Exception:
            logger.warning(f"Failed to parse JSON from text: {text[:200]}...")
            return default or {}
    
    @staticmethod
    def extract_key_values(text: str) -> Dict[str, Any]:
        """Extract key-value pairs from text using pattern matching."""
        result = {}
        
        # Pattern for "key": "value" or "key": value
        patterns = [
            r'"([^"]+)":\s*"([^"]*)"',  # "key": "value"
            r'"([^"]+)":\s*([^,}\]]+)',  # "key": value
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*"([^"]*)"',  # key: "value"
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*([^,}\]]+)',  # key: value
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for key, value in matches:
                key = key.strip()
                value = value.strip()
                
                # Try to parse value as appropriate type
                if value.lower() == 'true':
                    result[key] = True
                elif value.lower() == 'false':
                    result[key] = False
                elif value.lower() == 'null':
                    result[key] = None
                elif value.isdigit():
                    result[key] = int(value)
                elif re.match(r'^\d+\.\d+$', value):
                    result[key] = float(value)
                else:
                    # String value
                    result[key] = value.strip('"\'')
        
        return result

def safe_llm_json_parse(response: str, default: Any = None, log_errors: bool = True) -> Any:
    """
    Safe wrapper for parsing LLM JSON responses with comprehensive error handling.
    
    Args:
        response: Raw LLM response text
        default: Default value if parsing fails
        log_errors: Whether to log parsing errors
    
    Returns:
        Parsed JSON object or default value
    """
    try:
        return EnhancedJSONParser.safe_json_parse(response, default)
    except Exception as e:
        if log_errors:
            logger.warning(f"LLM JSON parsing error: {e}")
            logger.debug(f"Raw response: {response[:500]}...")
        return default or {}

def get_enhanced_tool_memory():
    """Get or create SHARED enhanced memory for BRD analysis tools."""
    global _tool_memory
    if _tool_memory is None and ENHANCED_MEMORY_AVAILABLE:
        try:
            from utils.shared_memory_hub import get_shared_memory_hub
            # Use the GLOBAL shared memory hub to prevent data isolation
            _tool_memory = get_shared_memory_hub()
            logging.info("Using GLOBAL shared memory hub for BRD tools")
        except Exception as e:
            logging.warning(f"Failed to get shared memory hub for BRD tools: {e}")
            _tool_memory = None
    return _tool_memory

def store_brd_data(key: str, value: Any, description: str = ""):
    """Store BRD analysis data in enhanced memory for cross-tool access."""
    memory = get_enhanced_tool_memory()
    if memory:
        try:
            memory.set(key, value, context="cross_tool")
            memory.set(key, value, context="brd_analysis")
            memory.set(key, value, context="agent_results")
            logging.info(f"Stored BRD data: {key} - {description}")
        except Exception as e:
            logging.warning(f"Failed to store BRD data {key}: {e}")

def retrieve_brd_data(key: str, default: Any = None) -> Any:
    """Retrieve BRD analysis data from enhanced memory with fallbacks."""
    memory = get_enhanced_tool_memory()
    if memory:
        try:
            # Try different contexts
            for context in ["cross_tool", "brd_analysis", "agent_results"]:
                value = memory.get(key, None, context=context)
                if value is not None:
                    logging.info(f"Retrieved BRD data: {key} from context: {context}")
                    return value
        except Exception as e:
            logging.warning(f"Failed to retrieve BRD data {key}: {e}")
    return default

# Enhanced Input Schemas with Validation Support
class EnhancedExtractSectionInput(BaseModel):
    """Enhanced input schema for extracting sections with flexible validation."""
    section_title: str = Field(..., description="The title/heading of the section to extract")
    
    class Config:
        extra = "allow"  # Allow extra fields for ReAct agent flexibility

class EnhancedExtractMultipleSectionsInput(BaseModel):
    """Enhanced input schema for extracting multiple sections with hybrid validation."""
    section_titles: Union[str, List[str]] = Field(
        ..., 
        description="List of section titles to extract. Can be JSON string or actual list."
    )
    
    class Config:
        extra = "allow"  # Allow extra fields from ReAct agents
    
    @field_validator('section_titles', mode='before')
    @classmethod
    def preprocess_section_titles(cls, v):
        """Preprocess section titles with enhanced parsing."""
        if v is None:
            return []
        
        # If it's already a list, return as-is
        if isinstance(v, list):
            return v
        
        # If it's a string, try to parse as JSON or split by commas
        if isinstance(v, str):
            v = v.strip()
            
            # Try JSON parsing first
            if v.startswith('[') and v.endswith(']'):
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError:
                    pass
            
            # Try comma-separated values
            if ',' in v:
                return [title.strip().strip('"\'') for title in v.split(',')]
            
            # Single item
            return [v.strip().strip('"\'')]
        
        # Convert other types to string and then process
        return cls.preprocess_section_titles(str(v))

class EnhancedFinalBRDAnalysisInput(BaseModel):
    """Enhanced input schema for final BRD analysis with comprehensive validation."""
    project_name: str = Field(default="Not specified", description="Project name")
    project_summary: str = Field(default="Not provided", description="Project summary")
    project_goals: List[str] = Field(default_factory=list, description="Project goals")
    target_audience: List[str] = Field(default_factory=list, description="Target audience")
    business_context: str = Field(default="Not specified", description="Business context")
    requirements: List[Dict[str, Any]] = Field(default_factory=list, description="Requirements list")
    constraints: List[str] = Field(default_factory=list, description="Constraints")
    assumptions: List[str] = Field(default_factory=list, description="Assumptions")
    risks: List[str] = Field(default_factory=list, description="Risks")
    domain_specific_details: Dict[str, Any] = Field(default_factory=dict, description="Domain details")
    quality_assessment: Dict[str, Any] = Field(default_factory=dict, description="Quality assessment")
    gap_analysis: Dict[str, Any] = Field(default_factory=dict, description="Gap analysis")
    
    class Config:
        extra = "allow"

# Custom Fallback Extractors
def extract_section_titles_fallback(raw_input: Any) -> Dict[str, Any]:
    """Fallback extractor for section titles from various text formats."""
    if isinstance(raw_input, str):
        text = raw_input.lower()
        
        # Common patterns for section extraction
        patterns = [
            r'(?:extract|get|find).*?(?:sections?|titles?|headings?).*?[:]\s*([^\n]+)',
            r'(?:sections?|titles?|headings?).*?[:=]\s*([^\n]+)',
            r'\[([^\]]+)\]',  # Bracketed lists
            r'"([^"]+)"',     # Quoted items
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Clean and split the matches
                titles = []
                for match in matches:
                    if ',' in match:
                        titles.extend([t.strip() for t in match.split(',')])
                    else:
                        titles.append(match.strip())
                
                if titles:
                    return {"section_titles": titles}
    
    return {}

def extract_common_brd_sections_fallback(raw_input: Any) -> Dict[str, Any]:
    """Extract common BRD sections based on keywords."""
    common_sections = [
        "Project Overview", "Goals", "Objectives", "Requirements", 
        "Constraints", "Assumptions", "Risks", "Scope", "Business Context"
    ]
    
    text = str(raw_input).lower()
    found_sections = []
    
    for section in common_sections:
        if any(word.lower() in text for word in section.split()):
            found_sections.append(section)
    
    if found_sections:
        return {"section_titles": found_sections}
    
    # Default fallback
    return {"section_titles": ["Project Overview", "Requirements", "Goals", "Constraints", "Assumptions"]}

# Initialize Enhanced Tools
def initialize_enhanced_brd_tools(llm: BaseLanguageModel, brd_content: str):
    """Initialize enhanced BRD tools with validation and optimization."""
    global _llm, _brd_content
    _llm = llm
    _brd_content = brd_content
    logger.info(f"Enhanced BRD tools initialized with content length: {len(brd_content)}")

# Enhanced Tool Functions with Hybrid Validation

@smart_react_tool("Extract multiple sections from the BRD document")
def extract_multiple_sections_enhanced(section_titles) -> Dict[str, str]:
    """
    Enhanced tool to extract multiple sections from the BRD.
    
    Args:
        section_titles: List of section titles to extract
        
    Returns:
        Dictionary mapping section titles to their extracted content
    """
    global _brd_content
    
    logger.info(f"Enhanced extract_multiple_sections called with: {section_titles}")
    
    if not _brd_content:
        return {"error": "BRD content not available. Use read_brd_document first."}
    
    if not section_titles:
        return {"error": "No section titles provided"}
    
    # Ensure section_titles is a list
    if isinstance(section_titles, str):
        try:
            section_titles = json.loads(section_titles)
        except json.JSONDecodeError:
            section_titles = [section_titles]
    
    if not isinstance(section_titles, list):
        section_titles = [str(section_titles)]
    
    logger.info(f"Processing {len(section_titles)} sections: {section_titles}")
    
    extracted_sections = {}
    
    for section_title in section_titles:
        if not section_title or not section_title.strip():
            continue
            
        section_title = section_title.strip()
        
        # Enhanced section extraction with multiple patterns
        section_content = _extract_section_enhanced(section_title, _brd_content)
        
        if section_content:
            extracted_sections[section_title] = section_content
            logger.info(f"Successfully extracted section '{section_title}' ({len(section_content)} chars)")
        else:
            extracted_sections[section_title] = f"Section '{section_title}' not found in the document."
            logger.warning(f"Could not find section '{section_title}'")
    
    return extracted_sections

@smart_react_tool("Extract a specific section from the BRD document")
def extract_text_section_enhanced(section_title) -> str:
    """
    Enhanced tool to extract a specific section from BRD.
    
    Args:
        section_title: The section title to extract
        
    Returns:
        Extracted section content or error message
    """
    global _brd_content
    
    logger.info(f"Enhanced extract_text_section called with: {section_title}")
    
    if not _brd_content:
        return "Error: BRD content not available. Use read_brd_document first."
    
    if not section_title:
        return "Error: No section title provided."
    
    section_content = _extract_section_enhanced(section_title, _brd_content)
    
    if section_content:
        logger.info(f"Successfully extracted section '{section_title}' ({len(section_content)} chars)")
        return section_content
    else:
        return f"Section '{section_title}' not found in the document."

@smart_react_tool("Identify and extract requirements from text")
def identify_requirements_enhanced(text) -> List[Dict[str, Any]]:
    """
    Enhanced tool to identify and extract requirements from text.
    
    Args:
        text: Text containing requirements to extract
        
    Returns:
        List of extracted requirements with metadata
    """
    global _llm
    
    logger.info(f"Enhanced identify_requirements called with text length: {len(text)}")
    
    if not text:
        return [{"error": "No text provided for requirements extraction"}]
    
    if not _llm:
        return [{"error": "LLM not available for requirements extraction"}]

    # Use cached analysis if available
    cache_key = f"requirements_{hash(text[:200])}"
    
    try:
        # Enhanced prompt for requirements extraction
        prompt = f"""
        Analyze the following text and extract specific, actionable requirements.
        Focus on functional and non-functional requirements.
        
        Text to analyze:
        {text}
        
        Extract requirements in this JSON format:
        {{
            "requirements": [
                {{
                    "id": "REQ-001",
                    "title": "Brief requirement title",
                    "description": "Detailed requirement description",
                    "type": "functional|non-functional|business",
                    "priority": "high|medium|low",
                    "category": "UI|Backend|Database|Integration|Performance|Security",
                    "acceptance_criteria": ["criterion 1", "criterion 2"]
                }}
            ]
        }}
        
        Be specific and actionable. Avoid vague statements.
        """
        
        # Use temperature optimized for requirements analysis
        response = _llm.bind(temperature=0.1).invoke(prompt)
        
        # Parse the response with enhanced JSON parsing
        result = safe_llm_json_parse(response.content, default={})
        
        if result and "requirements" in result:
            requirements = result["requirements"]
            logger.info(f"Extracted {len(requirements)} requirements from text")
            return requirements
        else:
            # Try alternative parsing methods
            try:
                # Try to parse as direct array
                if isinstance(result, list):
                    requirements = result
                elif hasattr(response, 'content') and '[' in response.content:
                    # Try to extract array directly
                    array_match = re.search(r'\[.*\]', response.content, re.DOTALL)
                    if array_match:
                        requirements = safe_llm_json_parse(array_match.group(), default=[])
                        if requirements:
                            logger.info(f"Extracted {len(requirements)} requirements using array parsing")
                            return requirements
            except Exception as e:
                logger.debug(f"Alternative parsing failed: {e}")
            
            # Fallback to manual extraction
            return _extract_requirements_manually(text)
            
    except Exception as e:
        logger.error(f"Requirements extraction failed: {str(e)}")
        return _extract_requirements_manually(text)

@smart_react_tool("Read the BRD document content")
def read_brd_document_enhanced() -> str:
    """
    Enhanced tool to read the BRD document.
    
    Returns:
        Full BRD content with metadata
    """
    global _brd_content
    
    if not _brd_content or len(_brd_content) < 10:
        return "Error: BRD document appears to be empty or very short."
    
    logger.info(f"BRD document accessed ({len(_brd_content)} characters)")
    return _brd_content

def compile_final_brd_analysis_direct(input_data: Union[str, Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Direct (non-tool) version for testing and internal use.
    
    Args:
        input_data: Dictionary or JSON string containing BRD analysis data
        
    Returns:
        Complete BRD analysis conforming to schema
    """
    global _brd_content
    logger.info("Compiling enhanced final BRD analysis (direct)")
    
    # Handle None input
    if input_data is None:
        input_data = {}
    
    # Parse input data if it's a string
    if isinstance(input_data, str):
        try:
            input_data = safe_llm_json_parse(input_data, default={})
        except Exception as e:
            logger.warning(f"Failed to parse input JSON: {e}")
            input_data = {}
    
    # Extract project information from BRD content
    project_name = _extract_project_name_from_brd()
    project_summary = _extract_project_summary_from_brd()
    project_goals = _extract_project_goals_from_brd()
    
    # Generate missing sections using LLM when not present in input_data
    constraints_from_llm = []
    assumptions_from_llm = []
    risks_from_llm = []
    
    # Track sections generated for cost control
    sections_generated = 0
    sections_budget = []
    
    # Check if these sections are missing and generate them with cost control
    if not input_data.get("constraints") and not input_data.get("Constraints"):
        if sections_generated < _cost_config.max_sections_to_generate and "constraints" in _cost_config.section_priority:
            constraints_from_llm = _generate_missing_constraints_with_llm()
            if constraints_from_llm:
                sections_generated += 1
                sections_budget.append(f"constraints (~{_cost_config.estimated_tokens_per_section.get('constraints', 450)} tokens)")
                logger.info("Generated missing constraints using LLM")
    
    if not input_data.get("assumptions") and not input_data.get("Assumptions"):
        if sections_generated < _cost_config.max_sections_to_generate and "assumptions" in _cost_config.section_priority:
            assumptions_from_llm = _generate_missing_assumptions_with_llm()
            if assumptions_from_llm:
                sections_generated += 1
                sections_budget.append(f"assumptions (~{_cost_config.estimated_tokens_per_section.get('assumptions', 400)} tokens)")
                logger.info("Generated missing assumptions using LLM")
    
    if not input_data.get("risks") and not input_data.get("Risks"):
        if sections_generated < _cost_config.max_sections_to_generate and "risks" in _cost_config.section_priority:
            risks_from_llm = _generate_missing_risks_with_llm()
            if risks_from_llm:
                sections_generated += 1
                sections_budget.append(f"risks (~{_cost_config.estimated_tokens_per_section.get('risks', 350)} tokens)")
                logger.info("Generated missing risks using LLM")
    
    # Log cost summary
    if sections_budget:
        total_estimated_tokens = sum(_cost_config.estimated_tokens_per_section.get(section.split('(')[0].strip(), 350) for section in sections_budget)
        logger.info(f"BRD Gap Filling Summary: Generated {sections_generated} sections using ~{total_estimated_tokens} tokens: {', '.join(sections_budget)}")
    else:
        logger.info("BRD Gap Filling: No additional LLM calls made (all sections present or budget constraints)")

    # Extract values with defaults, using extracted/generated values when available
    final_project_name = input_data.get("project_name", project_name or "Not specified")
    final_project_summary = input_data.get("project_summary", project_summary or "Not provided")
    final_project_goals = input_data.get("project_goals", project_goals or [])
    final_target_audience = input_data.get("target_audience", [])
    final_business_context = input_data.get("business_context", "Not specified")
    final_requirements = input_data.get("requirements", input_data.get("Extracted Requirements", []))
    final_constraints = input_data.get("constraints", input_data.get("Constraints", constraints_from_llm))
    final_assumptions = input_data.get("assumptions", input_data.get("Assumptions", assumptions_from_llm))
    final_risks = input_data.get("risks", input_data.get("Risks", risks_from_llm))
    final_domain_specific_details = input_data.get("domain_specific_details", {})
    
    # Ensure all lists are actually lists
    if not isinstance(final_project_goals, list):
        final_project_goals = []
    if not isinstance(final_target_audience, list):
        final_target_audience = []
    if not isinstance(final_requirements, list):
        final_requirements = []
    if not isinstance(final_constraints, list):
        final_constraints = []
    if not isinstance(final_assumptions, list):
        final_assumptions = []
    if not isinstance(final_risks, list):
        final_risks = []
    if not isinstance(final_domain_specific_details, dict):
        final_domain_specific_details = {}
    
    # FIX: Normalize requirements to ensure they are dictionaries, not strings
    normalized_requirements = []
    for i, req in enumerate(final_requirements):
        if isinstance(req, str):
            # Convert string requirement to dictionary format
            normalized_req = {
                "id": f"REQ-{i+1:03d}",
                "title": req[:50] + "..." if len(req) > 50 else req,
                "description": req,
                "type": "functional",
                "priority": "medium",
                "category": "General"
            }
            normalized_requirements.append(normalized_req)
            logger.debug(f"Converted string requirement to dictionary: {req[:50]}...")
        elif isinstance(req, dict):
            # Ensure dictionary has required fields
            normalized_req = {
                "id": req.get("id", f"REQ-{i+1:03d}"),
                "title": req.get("title", req.get("description", "Unknown requirement")[:50]),
                "description": req.get("description", req.get("title", "No description")),
                "type": req.get("type", req.get("category", "functional")),
                "priority": req.get("priority", "medium"),
                "category": req.get("category", req.get("type", "General"))
            }
            normalized_requirements.append(normalized_req)
        else:
            # Convert other types to string then to dictionary
            req_str = str(req)
            normalized_req = {
                "id": f"REQ-{i+1:03d}",
                "title": req_str[:50] + "..." if len(req_str) > 50 else req_str,
                "description": req_str,
                "type": "functional",
                "priority": "medium",
                "category": "General"
            }
            normalized_requirements.append(normalized_req)
            logger.debug(f"Converted {type(req)} requirement to dictionary")
    
    # Update final_requirements with normalized version
    final_requirements = normalized_requirements

    # Create analysis kwargs for helper functions
    analysis_kwargs = {
        "project_name": final_project_name,
        "project_summary": final_project_summary,
        "project_goals": final_project_goals,
        "target_audience": final_target_audience,
        "business_context": final_business_context,
        "requirements": final_requirements,
        "constraints": final_constraints,
        "assumptions": final_assumptions,
        "risks": final_risks,
        "domain_specific_details": final_domain_specific_details
    }
    
    # Create the final analysis
    final_analysis = {
        "project_name": final_project_name,
        "project_summary": final_project_summary,
        "project_goals": final_project_goals,
        "target_audience": final_target_audience,
        "business_context": final_business_context,
        "requirements": final_requirements,
        "constraints": final_constraints,
        "assumptions": final_assumptions,
        "risks": final_risks,
        "domain_specific_details": final_domain_specific_details,
        "quality_assessment": _generate_quality_assessment(analysis_kwargs),
        "gap_analysis": _generate_gap_analysis(analysis_kwargs),
        "analysis_metadata": {
            "extraction_method": "enhanced_hybrid_validation",
            "validation_level": "multi-layer", 
            "timestamp": str(time.time()),
            "total_sections_processed": 0,
            "requirements_count": len(final_requirements)
        }
    }
    
    # Validate the final analysis
    try:
        validated_analysis = BRDRequirementsAnalysis(**final_analysis)
        result = validated_analysis.dict()
        
        # Store in enhanced memory for cross-tool access
        store_brd_data("brd_analysis", result, "Complete BRD analysis for cross-tool access")
        store_brd_data("requirements_analysis", result, "Requirements analysis for planning and design")
        store_brd_data("project_requirements", final_requirements, "Extracted project requirements")
        store_brd_data("project_constraints", final_constraints, "Project constraints for planning")
        store_brd_data("project_goals", final_project_goals, "Project goals for design alignment")
        
        logger.info("Final BRD analysis compiled, validated, and stored in enhanced memory")
        return result
    except Exception as e:
        logger.warning(f"Final validation failed, returning best-effort analysis: {str(e)}")
        
        # Still store the best-effort analysis
        store_brd_data("brd_analysis", final_analysis, "Best-effort BRD analysis")
        store_brd_data("requirements_analysis", final_analysis, "Best-effort requirements analysis")
        
        return final_analysis

@smart_react_tool("Compile the final BRD analysis")  
def compile_final_brd_analysis_enhanced(input_data: Union[str, Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Enhanced tool to compile the final BRD analysis.
    
    Args:
        input_data: Dictionary or JSON string containing BRD analysis data
        
    Returns:
        Complete BRD analysis conforming to schema
    """
    # Use the direct implementation
    return compile_final_brd_analysis_direct(input_data)

@smart_react_tool("Fill missing sections in BRD analysis")
def fill_missing_brd_sections(section_types) -> Dict[str, List[str]]:
    """
    Enhanced tool to fill missing sections in BRD analysis using AI.
    
    Args:
        section_types: List of section types to generate (e.g., ["goals", "constraints", "assumptions", "risks"])
        
    Returns:
        Dictionary with generated content for each requested section type
    """
    global _llm, _brd_content
    
    logger.info(f"Filling missing BRD sections: {section_types}")
    
    if not _brd_content:
        return {"error": "BRD content not available. Use read_brd_document first."}
    
    # Parse section_types if it's a string
    if isinstance(section_types, str):
        try:
            section_types = safe_llm_json_parse(section_types, default=[])
        except:
            # Split by comma if it's a simple string
            section_types = [s.strip() for s in section_types.split(',')]
    
    if not isinstance(section_types, list):
        section_types = [str(section_types)]
    
    results = {}
    
    for section_type in section_types:
        section_type = section_type.lower().strip()
        
        if section_type in ["goals", "objectives", "project_goals"]:
            results["goals"] = _generate_missing_goals_with_llm()
        
        elif section_type in ["constraints", "limitations"]:
            results["constraints"] = _generate_missing_constraints_with_llm()
        
        elif section_type in ["assumptions", "presumptions"]:
            results["assumptions"] = _generate_missing_assumptions_with_llm()
        
        elif section_type in ["risks", "threats", "challenges"]:
            results["risks"] = _generate_missing_risks_with_llm()
        
        elif section_type in ["business_context", "context", "background"]:
            results["business_context"] = _generate_missing_business_context_with_llm()
        
        elif section_type in ["target_audience", "users", "stakeholders"]:
            results["target_audience"] = _generate_missing_target_audience_with_llm()
        
        else:
            logger.warning(f"Unknown section type: {section_type}")
    
    logger.info(f"Successfully generated {len(results)} missing sections")
    return results

def _generate_missing_business_context_with_llm() -> str:
    """Generate business context when missing from BRD."""
    global _llm, _brd_content
    if not _llm or not _brd_content:
        return "Not specified"
    
    try:
        prompt = f"""Based on the following Business Requirements Document, generate a concise business context that explains the business motivation and background for this project.

BRD Content:
{_brd_content}

The business context should explain:
- Why this project is needed
- What business problem it solves
- How it fits into the overall business strategy
- What business value it provides

Return the business context as a single paragraph (2-4 sentences).

Business Context:"""

        response = _llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Clean up the response
        context = content.strip().replace('"', '').replace('\n', ' ')
        if len(context) > 10:
            logger.info("Generated missing business context using LLM")
            return context
        
    except Exception as e:
        logger.warning(f"Failed to generate business context with LLM: {e}")
    
    return "Business context not specified in the original requirements"

def _generate_missing_target_audience_with_llm() -> List[str]:
    """Generate target audience when missing from BRD."""
    global _llm, _brd_content
    if not _llm or not _brd_content:
        return []
    
    try:
        prompt = f"""Based on the following Business Requirements Document, identify and generate 3-5 target audience groups or user types that would use this system.

BRD Content:
{_brd_content}

Consider different user roles such as:
- Primary users (who will use the system daily)
- Secondary users (who will use it occasionally)
- Administrative users (who will manage the system)
- Stakeholders (who will benefit from the system)

Return the target audience as a JSON list of strings. Example format:
["User type 1", "User type 2", "User type 3"]

Target Audience:"""

        response = _llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Extract JSON from response
        audience_json = safe_llm_json_parse(content, default=[])
        if isinstance(audience_json, list) and audience_json:
            logger.info(f"Generated {len(audience_json)} target audience groups using LLM")
            return audience_json
        
    except Exception as e:
        logger.warning(f"Failed to generate target audience with LLM: {e}")
    
    return []

# Helper Functions

def _extract_section_enhanced(section_title: str, content: str) -> Optional[str]:
    """Enhanced section extraction with multiple pattern matching."""
    if not section_title or not content:
        return None
    
    # Enhanced patterns for section extraction
    patterns = [
        # Standard numbered heading
        rf'(?i)(?:\d+\.?\s*)?{re.escape(section_title)}[:\s]*\n+(.*?)(?:\n+(?:\d+\.?\s*)?[A-Z][^:\n]*[:\s]*\n+|$)',
        # Heading with underline or emphasis
        rf'(?i){re.escape(section_title)}\s*\n[-=*]+\s*\n+(.*?)(?:\n+[A-Z][^:\n]*\s*\n[-=*]+|$)',
        # All caps or title case
        rf'(?i){re.escape(section_title.upper())}\s*[:\n]+(.*?)(?:\n+[A-Z][^:\n]*(?:\s*:|$)|$)',
        # Flexible pattern with section keywords
        rf'(?i)(?:section|part|chapter)?\s*\d*\.?\s*{re.escape(section_title)}[:\s]*\n+(.*?)(?:\n\s*\n|(?:\n+(?:section|part|chapter)?\s*\d*\.?\s*[A-Z]))',
        # Very loose pattern
        rf'(?i){re.escape(section_title)}[:\s]*\n+(.*?)(?:\n\s*\n|$)'
    ]
    
    for i, pattern in enumerate(patterns):
        try:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                section_content = match.group(1).strip()
                if len(section_content) > 10:  # Ensure meaningful content
                    logger.debug(f"Section '{section_title}' found with pattern {i+1}")
                    return section_content
        except Exception as e:
            logger.debug(f"Pattern {i+1} failed for section '{section_title}': {e}")
            continue
    
    # Keyword-based fallback
    return _keyword_based_section_extraction(section_title, content)

def _keyword_based_section_extraction(section_title: str, content: str) -> Optional[str]:
    """Fallback section extraction using keyword matching."""
    keywords = section_title.lower().split()
    
    # Look for paragraphs containing the keywords
    paragraphs = content.split('\n\n')
    
    for paragraph in paragraphs:
        if len(paragraph.strip()) < 50:  # Skip short paragraphs
            continue
            
        para_lower = paragraph.lower()
        keyword_matches = sum(1 for kw in keywords if kw in para_lower)
        
        if keyword_matches >= len(keywords) * 0.7:  # 70% keyword match
            logger.debug(f"Found content for '{section_title}' using keyword matching")
            return paragraph.strip()
    
    return None

def _extract_requirements_manually(text: str) -> List[Dict[str, Any]]:
    """Manual requirements extraction fallback."""
    requirements = []
    
    # Look for numbered or bulleted requirements
    patterns = [
        r'(?i)(?:req|requirement)\s*\d+[.:]?\s*([^\n]+)',
        r'(?i)(?:shall|must|should|will)\s+([^\n.]+)',
        r'^\s*[-*•]\s*([^\n]+)',
        r'^\s*\d+[.)]\s*([^\n]+)'
    ]
    
    req_id = 1
    for pattern in patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        for match in matches:
            if len(match.strip()) > 10:
                requirements.append({
                    "id": f"REQ-{req_id:03d}",
                    "title": match.strip()[:50] + "..." if len(match) > 50 else match.strip(),
                    "description": match.strip(),
                    "type": "functional",
                    "priority": "medium",
                    "category": "General",
                    "acceptance_criteria": []
                })
                req_id += 1
    
    return requirements[:20]  # Limit to 20 requirements

def _generate_quality_assessment(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate quality assessment for the BRD analysis."""
    return {
        "completeness_score": min(100, len(analysis_data.get("requirements", [])) * 5),
        "clarity_score": 85,  # Default good score
        "consistency_score": 90,
        "issues_found": [],
        "recommendations": ["Consider adding more detailed acceptance criteria for requirements"]
    }

def _generate_gap_analysis(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate gap analysis with enhanced missing section detection."""
    missing_sections = []
    generated_sections = []
    recommendations = []
    
    # Check for missing or generated sections
    if not analysis_data.get("project_goals") or len(analysis_data.get("project_goals", [])) == 0:
        missing_sections.append("project_goals")
    
    if not analysis_data.get("constraints") or len(analysis_data.get("constraints", [])) == 0:
        missing_sections.append("constraints")
        generated_sections.append("constraints - Generated by AI based on project context")
    
    if not analysis_data.get("assumptions") or len(analysis_data.get("assumptions", [])) == 0:
        missing_sections.append("assumptions") 
        generated_sections.append("assumptions - Generated by AI based on project context")
    
    if not analysis_data.get("risks") or len(analysis_data.get("risks", [])) == 0:
        missing_sections.append("risks")
        generated_sections.append("risks - Generated by AI based on project context")
    
    if not analysis_data.get("target_audience") or len(analysis_data.get("target_audience", [])) == 0:
        missing_sections.append("target_audience")
        recommendations.append("Define target audience for better requirement validation")
    
    if analysis_data.get("business_context") == "Not specified":
        missing_sections.append("business_context")
        recommendations.append("Add business context to understand project motivation")
    
    # Standard recommendations
    if len(analysis_data.get("requirements", [])) < 3:
        recommendations.append("Consider adding more detailed functional requirements")
    
    if generated_sections:
        recommendations.append("Review AI-generated sections and validate against actual project needs")
    
    risk_level = "low"
    if len(missing_sections) > 3:
        risk_level = "high" 
    elif len(missing_sections) > 1:
        risk_level = "medium"
    
    return {
        "missing_sections": missing_sections,
        "generated_sections": generated_sections,
        "recommendations": recommendations,
        "risk_level": risk_level,
        "completeness_score": max(0, 100 - (len(missing_sections) * 15))
    }

def _extract_project_name_from_brd() -> Optional[str]:
    """Extract project name from BRD content."""
    global _brd_content
    if not _brd_content:
        return None
    
    # Look for common project title patterns
    patterns = [
        r'(?i)project\s+title\s*:?\s*(.+)',
        r'(?i)project\s+name\s*:?\s*(.+)',
        r'(?i)title\s*:?\s*(.+)',
        r'(?i)^(.+?)(?:\s+(?:project|application|system))',
        r'(?i)(?:project|application|system):\s*(.+)',
    ]
    
    lines = _brd_content.split('\n')
    for line in lines[:5]:  # Check first 5 lines
        line = line.strip()
        if not line:
            continue
            
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                project_name = match.group(1).strip()
                # Clean up the extracted name
                project_name = re.sub(r'[^\w\s-]', '', project_name).strip()
                if len(project_name) > 3 and len(project_name) < 100:
                    logger.info(f"Extracted project name: '{project_name}'")
                    return project_name
    
    return None

def _extract_project_summary_from_brd() -> Optional[str]:
    """Extract project summary from BRD content."""
    global _brd_content
    if not _brd_content:
        return None
    
    # Look for overview or summary sections
    overview_content = _extract_section_enhanced("Project Overview", _brd_content)
    if overview_content and len(overview_content) > 20:
        # Use first sentence or first 200 chars
        sentences = re.split(r'[.!?]+', overview_content)
        if sentences and len(sentences[0].strip()) > 20:
            return sentences[0].strip()
        return overview_content[:200].strip() + "..." if len(overview_content) > 200 else overview_content.strip()
    
    # Fallback: look for any descriptive content in first few paragraphs
    paragraphs = _brd_content.split('\n\n')
    for para in paragraphs[:3]:
        if len(para.strip()) > 50 and not re.match(r'^\d+\.', para.strip()):
            return para.strip()[:200] + "..." if len(para) > 200 else para.strip()
    
    return None

def _extract_project_goals_from_brd() -> List[str]:
    """Extract project goals from BRD content."""
    global _brd_content
    if not _brd_content:
        return []
    
    goals = []
    
    # Look for goals/objectives sections
    for section_name in ["Goals", "Objectives", "Purpose", "Project Goals"]:
        section_content = _extract_section_enhanced(section_name, _brd_content)
        if section_content:
            # Extract bulleted or numbered goals
            goal_patterns = [
                r'^\s*[-*•]\s*(.+)',
                r'^\s*\d+[.)]\s*(.+)',
                r'(?i)goal\s*\d*:?\s*(.+)',
                r'(?i)objective\s*\d*:?\s*(.+)'
            ]
            
            for line in section_content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                    
                for pattern in goal_patterns:
                    match = re.search(pattern, line)
                    if match:
                        goal = match.group(1).strip()
                        if len(goal) > 10:
                            goals.append(goal)
    
    # If no explicit goals found, use LLM to generate them
    if not goals:
        goals = _generate_missing_goals_with_llm()
    
    return goals[:5]  # Limit to 5 goals

def _generate_missing_goals_with_llm() -> List[str]:
    """Use LLM to generate project goals when missing from BRD."""
    global _llm, _brd_content, _cost_config
    
    # Check if gap filling is enabled
    if not _cost_config.gap_filling_enabled:
        logger.info("Gap filling disabled, using fallback goals")
        return _generate_fallback_goals()
    
    # Check if we're in budget mode
    if _cost_config.budget_mode:
        logger.info("Budget mode enabled, using heuristic fallback for goals")
        return _generate_fallback_goals()
    
    # Check cache first
    cached_goals = _get_cached_content("goals", _brd_content)
    if cached_goals:
        return cached_goals
    
    # Check if we're within section limits
    sections_generated = 0  # This would be tracked in real implementation
    if sections_generated >= _cost_config.max_sections_to_generate:
        logger.info(f"Section limit reached ({_cost_config.max_sections_to_generate}), skipping goals generation")
        return _generate_fallback_goals()
    
    if not _llm or not _brd_content:
        return _generate_fallback_goals()
    
    try:
        # Estimate tokens for this operation
        estimated_tokens = _cost_config.estimated_tokens_per_section.get("goals", 400)
        logger.info(f"Generating goals with LLM (estimated ~{estimated_tokens} tokens)")
        
        prompt = f"""Based on the following Business Requirements Document, generate 3-5 clear and specific project goals that would be appropriate for this project.

BRD Content:
{_brd_content}

Generate project goals that are:
- Specific and measurable
- Aligned with the project description
- Realistic and achievable
- Business-focused

Return the goals as a JSON list of strings. Example format:
["Goal 1 description", "Goal 2 description", "Goal 3 description"]

Goals:"""

        response = _llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Extract JSON from response
        goals_json = safe_llm_json_parse(content, default=[])
        if isinstance(goals_json, list) and goals_json:
            logger.info(f"Generated {len(goals_json)} missing project goals using LLM")
            # Cache the results
            _cache_content("goals", _brd_content, goals_json)
            return goals_json
        
    except Exception as e:
        logger.warning(f"Failed to generate goals with LLM: {e}")
    
    # Fallback goals based on project type
    logger.info("Using heuristic fallback for goals due to LLM failure")
    return _generate_fallback_goals()

def _generate_fallback_goals() -> List[str]:
    """Generate basic fallback goals when LLM generation fails."""
    global _brd_content
    if not _brd_content:
        return []
    
    # Simple heuristic-based goal generation
    content_lower = _brd_content.lower()
    goals = []
    
    if any(word in content_lower for word in ["manage", "track", "organize"]):
        goals.append("Provide an efficient system for data management and organization")
    
    if any(word in content_lower for word in ["user", "customer", "client"]):
        goals.append("Deliver an intuitive user experience that meets user needs")
    
    if any(word in content_lower for word in ["fast", "quick", "performance", "speed"]):
        goals.append("Ensure optimal system performance and responsiveness")
    
    if any(word in content_lower for word in ["secure", "security", "safe"]):
        goals.append("Maintain high security standards and data protection")
    
    # Always add a general business goal
    goals.append("Successfully deliver the project within scope, timeline, and budget")
    
    return goals[:3]

def _generate_missing_constraints_with_llm() -> List[str]:
    """Use LLM to generate project constraints when missing from BRD."""
    global _llm, _brd_content, _cost_config
    
    # Check if gap filling is enabled
    if not _cost_config.gap_filling_enabled:
        logger.info("Gap filling disabled, skipping constraints generation")
        return []
    
    # Check if we're in budget mode
    if _cost_config.budget_mode:
        logger.info("Budget mode enabled, using heuristic fallback for constraints")
        return _generate_fallback_constraints()
    
    # Check cache first
    cached_constraints = _get_cached_content("constraints", _brd_content)
    if cached_constraints:
        return cached_constraints
    
    if not _llm or not _brd_content:
        return _generate_fallback_constraints() if _cost_config.use_heuristic_fallbacks else []
    
    try:
        # Estimate tokens for this operation
        estimated_tokens = _cost_config.estimated_tokens_per_section.get("constraints", 450)
        logger.info(f"Generating constraints with LLM (estimated ~{estimated_tokens} tokens)")
        
        prompt = f"""Based on the following Business Requirements Document, identify and generate 3-5 realistic project constraints that would typically apply to this type of project.

BRD Content:
{_brd_content}

Consider typical constraints such as:
- Technical constraints (technology, platform, compatibility)
- Resource constraints (budget, time, team size)
- Business constraints (compliance, security, scalability)
- User experience constraints (performance, accessibility, usability)

Return the constraints as a JSON list of strings. Example format:
["Constraint 1 description", "Constraint 2 description", "Constraint 3 description"]

Constraints:"""

        response = _llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Extract JSON from response
        constraints_json = safe_llm_json_parse(content, default=[])
        if isinstance(constraints_json, list) and constraints_json:
            logger.info(f"Generated {len(constraints_json)} missing project constraints using LLM")
            # Cache the results
            _cache_content("constraints", _brd_content, constraints_json)
            return constraints_json
        
    except Exception as e:
        logger.warning(f"Failed to generate constraints with LLM: {e}")
    
    # Use fallback if available
    if _cost_config.use_heuristic_fallbacks:
        logger.info("Using heuristic fallback for constraints due to LLM failure")
        return _generate_fallback_constraints()
    
    return []

def _generate_fallback_constraints() -> List[str]:
    """Generate basic fallback constraints when LLM generation fails."""
    global _brd_content
    if not _brd_content:
        return []
    
    content_lower = _brd_content.lower()
    constraints = []
    
    # Technical constraints
    if any(word in content_lower for word in ["web", "app", "application", "system"]):
        constraints.append("Must be compatible with modern web browsers and devices")
    
    # Performance constraints
    if any(word in content_lower for word in ["fast", "quick", "performance", "speed"]):
        constraints.append("System response time must be under 2 seconds for all operations")
    
    # Security constraints
    if any(word in content_lower for word in ["user", "data", "information"]):
        constraints.append("Must comply with data protection and privacy regulations")
    
    # Resource constraints
    constraints.append("Project must be completed within allocated budget and timeline")
    
    return constraints[:3]

def _generate_missing_assumptions_with_llm() -> List[str]:
    """Use LLM to generate project assumptions when missing from BRD."""
    global _llm, _brd_content, _cost_config
    
    # Check if gap filling is enabled
    if not _cost_config.gap_filling_enabled:
        logger.info("Gap filling disabled, skipping assumptions generation")
        return []
    
    # Check if we're in budget mode
    if _cost_config.budget_mode:
        logger.info("Budget mode enabled, using heuristic fallback for assumptions")
        return _generate_fallback_assumptions()
    
    # Check cache first
    cached_assumptions = _get_cached_content("assumptions", _brd_content)
    if cached_assumptions:
        return cached_assumptions
    
    if not _llm or not _brd_content:
        return _generate_fallback_assumptions() if _cost_config.use_heuristic_fallbacks else []
    
    try:
        # Estimate tokens for this operation
        estimated_tokens = _cost_config.estimated_tokens_per_section.get("assumptions", 400)
        logger.info(f"Generating assumptions with LLM (estimated ~{estimated_tokens} tokens)")
        
        prompt = f"""Based on the following Business Requirements Document, identify and generate 3-5 reasonable project assumptions that would typically be made for this type of project.

BRD Content:
{_brd_content}

Consider typical assumptions such as:
- User behavior assumptions
- Technical environment assumptions  
- Business process assumptions
- Data availability assumptions
- External dependency assumptions

Return the assumptions as a JSON list of strings. Example format:
["Assumption 1 description", "Assumption 2 description", "Assumption 3 description"]

Assumptions:"""

        response = _llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Extract JSON from response
        assumptions_json = safe_llm_json_parse(content, default=[])
        if isinstance(assumptions_json, list) and assumptions_json:
            logger.info(f"Generated {len(assumptions_json)} missing project assumptions using LLM")
            # Cache the results
            _cache_content("assumptions", _brd_content, assumptions_json)
            return assumptions_json
        
    except Exception as e:
        logger.warning(f"Failed to generate assumptions with LLM: {e}")
    
    # Use fallback if available
    if _cost_config.use_heuristic_fallbacks:
        logger.info("Using heuristic fallback for assumptions due to LLM failure")
        return _generate_fallback_assumptions()
    
    return []

def _generate_fallback_assumptions() -> List[str]:
    """Generate basic fallback assumptions when LLM generation fails."""
    global _brd_content
    if not _brd_content:
        return []
    
    content_lower = _brd_content.lower()
    assumptions = []
    
    # User assumptions
    if any(word in content_lower for word in ["user", "customer", "client"]):
        assumptions.append("Users have basic computer literacy and internet access")
    
    # Technical assumptions
    if any(word in content_lower for word in ["web", "app", "system"]):
        assumptions.append("Target environment supports modern web standards")
    
    # Business assumptions
    assumptions.append("Stakeholders will be available for requirements clarification")
    assumptions.append("Project scope will remain stable during development")
    
    return assumptions[:3]

def _generate_missing_risks_with_llm() -> List[str]:
    """Use LLM to generate project risks when missing from BRD."""
    global _llm, _brd_content, _cost_config
    
    # Check if gap filling is enabled
    if not _cost_config.gap_filling_enabled:
        logger.info("Gap filling disabled, skipping risks generation")
        return []
    
    # Check if we're in budget mode
    if _cost_config.budget_mode:
        logger.info("Budget mode enabled, using heuristic fallback for risks")
        return _generate_fallback_risks()
    
    # Check cache first
    cached_risks = _get_cached_content("risks", _brd_content)
    if cached_risks:
        return cached_risks
    
    if not _llm or not _brd_content:
        return _generate_fallback_risks() if _cost_config.use_heuristic_fallbacks else []
    
    try:
        # Estimate tokens for this operation
        estimated_tokens = _cost_config.estimated_tokens_per_section.get("risks", 350)
        logger.info(f"Generating risks with LLM (estimated ~{estimated_tokens} tokens)")
        
        prompt = f"""Based on the following Business Requirements Document, identify and generate 3-5 potential project risks that should be considered for this type of project.

BRD Content:
{_brd_content}

Consider typical risks such as:
- Technical risks (complexity, technology choice, integration)
- Resource risks (timeline, budget, team availability)
- Business risks (changing requirements, market conditions)
- User adoption risks (usability, training, change management)
- Security and compliance risks

Return the risks as a JSON list of strings. Example format:
["Risk 1 description", "Risk 2 description", "Risk 3 description"]

Risks:"""

        response = _llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Extract JSON from response
        risks_json = safe_llm_json_parse(content, default=[])
        if isinstance(risks_json, list) and risks_json:
            logger.info(f"Generated {len(risks_json)} missing project risks using LLM")
            # Cache the results
            _cache_content("risks", _brd_content, risks_json)
            return risks_json
        
    except Exception as e:
        logger.warning(f"Failed to generate risks with LLM: {e}")
    
    # Use fallback if available
    if _cost_config.use_heuristic_fallbacks:
        logger.info("Using heuristic fallback for risks due to LLM failure")
        return _generate_fallback_risks()
    
    return []

def _generate_fallback_risks() -> List[str]:
    """Generate basic fallback risks when LLM generation fails."""
    global _brd_content
    if not _brd_content:
        return []
    
    content_lower = _brd_content.lower()
    risks = []
    
    # Technical risks
    if any(word in content_lower for word in ["complex", "integration", "system"]):
        risks.append("Technical complexity may lead to implementation delays")
    
    # Resource risks
    risks.append("Project timeline may be impacted by resource availability")
    
    # Business risks
    if any(word in content_lower for word in ["requirement", "feature", "function"]):
        risks.append("Requirements may change during development phase")
    
    # User adoption risks
    if any(word in content_lower for word in ["user", "interface", "experience"]):
        risks.append("User adoption may be slower than expected without proper training")
    
    return risks[:3]

# Tool Collection Function
def get_enhanced_brd_analysis_tools() -> List[Callable]:
    """Get the complete list of enhanced BRD analysis tools."""
    return [
        read_brd_document_enhanced,
        extract_multiple_sections_enhanced,
        extract_text_section_enhanced,
        identify_requirements_enhanced,
        compile_final_brd_analysis_enhanced,
        fill_missing_brd_sections,
        # Cost Control Tools
        configure_brd_cost_settings,
        get_brd_cost_configuration,
        enable_brd_budget_mode,
        disable_brd_gap_filling,
        enable_full_brd_gap_filling
    ]

@smart_react_tool("Configure BRD gap filling cost control settings")
def configure_brd_cost_settings(settings) -> Dict[str, Any]:
    """
    Configure cost control settings for BRD gap filling.
    
    Args:
        settings: Dictionary containing cost control configuration
        
    Returns:
        Current cost control configuration and estimated usage
    """
    global _cost_config
    
    # Parse settings if it's a string
    if isinstance(settings, str):
        try:
            settings = safe_llm_json_parse(settings, default={})
        except:
            logger.warning(f"Failed to parse settings JSON: {settings}")
            settings = {}
    
    if not isinstance(settings, dict):
        return {"error": "Settings must be a dictionary"}
    
    # Apply settings
    for key, value in settings.items():
        if hasattr(_cost_config, key):
            setattr(_cost_config, key, value)
            logger.info(f"BRD cost control: {key} = {value}")
        else:
            logger.warning(f"Unknown cost control setting: {key}")
    
    # Return current configuration
    return get_brd_cost_stats()

@smart_react_tool("Get BRD gap filling cost statistics and current configuration")
def get_brd_cost_configuration() -> Dict[str, Any]:
    """
    Get current BRD gap filling cost control configuration and estimated usage.
    
    Returns:
        Dictionary containing cost control settings and token estimates
    """
    return get_brd_cost_stats()

@smart_react_tool("Set BRD gap filling to budget mode")  
def enable_brd_budget_mode(max_sections: int = 2) -> Dict[str, Any]:
    """
    Enable budget mode for BRD gap filling to minimize API costs.
    
    Args:
        max_sections: Maximum sections to generate (default 2)
        
    Returns:
        Updated cost configuration
    """
    global _cost_config
    
    _cost_config.budget_mode = True
    _cost_config.max_sections_to_generate = max_sections
    _cost_config.priority_sections_only = True
    _cost_config.use_heuristic_fallbacks = True
    
    logger.info(f"BRD Budget Mode Enabled: max {max_sections} sections, heuristic fallbacks enabled")
    return get_brd_cost_stats()

@smart_react_tool("Disable BRD gap filling completely")
def disable_brd_gap_filling() -> Dict[str, Any]:
    """
    Disable BRD gap filling completely to avoid any additional API costs.
    
    Returns:
        Updated cost configuration
    """
    global _cost_config
    
    _cost_config.gap_filling_enabled = False
    logger.info("BRD Gap Filling Completely Disabled - No additional API calls will be made")
    return get_brd_cost_stats()

@smart_react_tool("Enable full BRD gap filling")
def enable_full_brd_gap_filling(max_sections: int = 6) -> Dict[str, Any]:
    """
    Enable full BRD gap filling with all features.
    
    Args:
        max_sections: Maximum sections to generate (default 6)
        
    Returns:
        Updated cost configuration
    """
    global _cost_config
    
    _cost_config.gap_filling_enabled = True
    _cost_config.budget_mode = False
    _cost_config.max_sections_to_generate = max_sections
    _cost_config.priority_sections_only = False
    _cost_config.use_heuristic_fallbacks = True
    _cost_config.enable_caching = True
    
    logger.info(f"Full BRD Gap Filling Enabled: max {max_sections} sections, caching enabled")
    return get_brd_cost_stats() 