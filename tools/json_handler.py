"""
Centralized JSON handling tools for all agents in the multi-AI system.
Provides robust parsing, cleaning, and error recovery for LLM JSON outputs.
"""
import logging
import re
import copy
import json
import os
import traceback
from typing import Dict, Any, List, Optional, Union, Tuple
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.runnables import Runnable

# Initialize module-level logger
logger = logging.getLogger(__name__)

class JsonHandler:
    """Provides robust JSON handling capabilities for all agents."""
    
    @staticmethod
    def create_strict_json_template(stage_name: str, instructions: str, example_json: str) -> List:
        """
        Create a template with ultra-strict JSON formatting instructions.
        
        Args:
            stage_name: Name of the processing stage (for context)
            instructions: Specific instructions for the LLM
            example_json: Example JSON structure to guide the LLM
            
        Returns:
            List of message objects for the LLM
        """
        system_content = f"""You are an AI expert in software development specializing in generating ONLY valid JSON for {stage_name}.
        
        CRITICAL INSTRUCTIONS (MANDATORY COMPLIANCE):
        1. Your ENTIRE response must be ONLY a raw, valid JSON object
        2. Start your response with '{{' and end with '}}' - NOTHING else
        3. NO explanations, NO markdown formatting, NO backticks
        4. NO text before or after the JSON object
        5. Always use DOUBLE QUOTES for keys and string values
        6. Never use single quotes in JSON
        7. Never include ```json or ``` markers
        8. Ensure all JSON syntax is correct with proper commas and no trailing commas
        
        FAILURE TO FOLLOW THESE INSTRUCTIONS WILL CAUSE SYSTEM FAILURE"""

        human_content = f"""{instructions}
        
        YOUR RESPONSE MUST BE RAW JSON. NO OTHER TEXT. Start with '{{' and end with '}}'.
        
        EXAMPLE FORMAT (follow this precise structure):
        {example_json}
        
        Remember:
        - Start with '{{', end with '}}'
        - Use double quotes for keys and string values
        - Return ONLY the JSON, absolutely no other text or formatting
        - NO explanations before or after
        - NO code block markers
        - VALID JSON SYNTAX ONLY
        """

        return [
            SystemMessage(content=system_content),
            HumanMessage(content=human_content)
        ]
    
    @staticmethod
    def create_strict_json_llm(
        llm: BaseLanguageModel,
        json_schema: Dict[str, Any],
        system_prompt: str,
        max_tokens: int = 8192
    ) -> Runnable:
        """Create a chain that returns a JSON object matching the given schema."""
        try:
            # DEPRECATED: TrackedChatModel is no longer used.
            # The base LLM is now expected to have tracking/rate-limiting wrappers applied.
            # from config import TrackedChatModel
            
            # Check if the LLM is a tracked model
            # if not isinstance(llm, TrackedChatModel):
            #     logger.warning("LLM is not a TrackedChatModel, creating a new one.")
            
            # Use the provided model or the default
            base_model = llm
            
            # Import necessary classes
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            # Detect if it's a Gemini model
            is_gemini = (isinstance(base_model, ChatGoogleGenerativeAI) or 
                         'gemini' in getattr(base_model, 'model_name', '').lower())
            
            # Log detailed model information for debugging
            model_info = f"Model: {getattr(base_model, 'model_name', type(base_model).__name__)}"
            logger.info(f"Creating strict JSON LLM for {model_info}")
            
            # Prepare binding arguments based on model type with enhanced Gemini support
            if is_gemini:
                # For Gemini models, use generation_config with enhanced JSON parameters
                binding_args = {
                    "temperature": 0.0,  # Zero temperature for deterministic output
                    "top_p": 0.95,       # More focused sampling
                    "generation_config": {
                        "max_output_tokens": max_tokens,
                        "temperature": 0.0,
                        "top_p": 0.95,
                        "response_mime_type": "application/json",  # Native JSON mode
                    }
                }
                
                logger.info(f"Using Gemini JSON mode with generation_config")
            else:
                # For other models that may use max_tokens directly
                binding_args = {
                    "temperature": 0.0,
                    "max_tokens": max_tokens
                }
            
            # Bind parameters to create the JSON-optimized model
            json_llm = base_model.bind(**binding_args)
            
            return json_llm
            
        except Exception as e:
            logger.warning(f"Error creating strict JSON LLM: {e}", exc_info=True)
            return llm  # Return the original LLM as fallback
    
    @staticmethod
    def _detect_model_provider(llm):
        """
        Detect the model provider from the LLM instance.
        
        Args:
            llm: Language model instance
            
        Returns:
            String identifier of the model provider
        """
        llm_class_name = llm.__class__.__name__.lower()
        llm_module = getattr(llm, "__module__", "").lower()
        model_name = getattr(llm, "model_name", "").lower()
        
        # Enhanced detection with more specific provider checks
        if "openai" in llm_class_name or "openai" in llm_module:
            return "openai"
        elif "google" in llm_class_name or "google" in llm_module or "gemini" in llm_class_name or "gemini" in model_name:
            return "gemini"
        elif "anthropic" in llm_class_name or "claude" in llm_class_name or "anthropic" in llm_module:
            return "anthropic"
        elif "mistral" in llm_class_name or "mistral" in llm_module or "mistral" in model_name:
            return "mistral"
        elif "cohere" in llm_class_name or "cohere" in llm_module or "cohere" in model_name:
            return "cohere"
        else:
            # For unknown models, assume they don't support response_format
            return "unknown"
    
    @staticmethod
    def _extract_text_content(response) -> str:
        """
        Extract text content from various response types including AIMessage objects.
        
        Args:
            response: Response object from LLM (AIMessage, string, dict, etc.)
            
        Returns:
            Extracted text string
        """
        try:
            # If response is None, return empty string
            if response is None:
                return ""
            
            # Handle AIMessage objects (most common case)
            if hasattr(response, 'content'):
                content = response.content
                # Handle string content
                if isinstance(content, str):
                    return content
                # Handle list or dict content (multimodal responses)
                elif isinstance(content, list):
                    text_parts = []
                    for item in content:
                        if isinstance(item, str):
                            text_parts.append(item)
                        elif isinstance(item, dict) and item.get('type') == 'text':
                            text_parts.append(item.get('text', ''))
                    return ' '.join(text_parts)
                # If content is some other type, convert to string
                return str(content)
                
            # Handle standard types
            if isinstance(response, str):
                return response
            elif isinstance(response, dict):
                return json.dumps(response)
            elif isinstance(response, list):
                return json.dumps(response)
                
            # Try to extract from common attributes
            for attr in ['text', 'message', 'result', 'response', 'output']:
                if hasattr(response, attr):
                    attr_value = getattr(response, attr)
                    if isinstance(attr_value, str):
                        return attr_value
            
            # Last resort: try string conversion
            return str(response)
        except Exception as e:
            logger.warning(f"Error extracting text content: {str(e)}")
            return ""
    
    @staticmethod
    def _preprocess_json_text(text: str) -> str:
        """
        Apply targeted preprocessing for common response issues.
        
        Args:
            text: Text to preprocess
            
        Returns:
            Preprocessed text
        """
        if not text:
            return "{}"
            
        # First, scan character by character to find the first valid JSON start
        valid_start_idx = -1
        for i, char in enumerate(text):
            if char == '{' or char == '[':
                valid_start_idx = i
                break
        
        # If found valid start, trim everything before it
        if valid_start_idx >= 0:
            text = text[valid_start_idx:]
        
        # Find the matching closing brace/bracket
        if text.startswith('{'):
            # Track opening and closing braces
            open_count = 0
            close_idx = -1
            
            for i, char in enumerate(text):
                if char == '{':
                    open_count += 1
                elif char == '}':
                    open_count -= 1
                    if open_count == 0:
                        close_idx = i
                        break
                        
            if close_idx > 0:
                text = text[:close_idx + 1]
        
        elif text.startswith('['):
            # Track opening and closing brackets
            open_count = 0
            close_idx = -1
            
            for i, char in enumerate(text):
                if char == '[':
                    open_count += 1
                elif char == ']':
                    open_count -= 1
                    if open_count == 0:
                        close_idx = i
                        break
                        
            if close_idx > 0:
                text = text[:close_idx + 1]
        
        # Handle line issues by normalizing all whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove all non-printable and control characters
        text = re.sub(r'[^\x20-\x7E\s]', '', text)
        
        # Fix inconsistent quote styles
        text = re.sub(r'(?<![\\])\'([^\']*?)(?<![\\])\'', r'"\1"', text)
        
        # Fix malformed numbers
        text = re.sub(r'(\d),(\d)', r'\1\2', text)
        
        # Fix trailing commas
        text = re.sub(r',(\s*[}\]])', r'\1', text)
        
        return text
    
    @staticmethod
    def _extract_json_character_by_character(text: str) -> str:
        """
        Extract JSON by parsing character-by-character with bracket balancing.
        
        Args:
            text: Text potentially containing JSON
            
        Returns:
            Extracted JSON string or empty string if no valid JSON found
        """
        result = ""
        in_json = False
        brace_count = 0
        bracket_count = 0
        in_string = False
        escape_next = False
        
        # First find the starting position of JSON
        start_pos = -1
        for i, char in enumerate(text):
            if char == '{' or char == '[':
                start_pos = i
                break
        
        # If no JSON start found, return empty string
        if start_pos == -1:
            return ""
            
        # Extract JSON character by character
        for i, char in enumerate(text[start_pos:], start=start_pos):
            # Start tracking once we find a JSON opening character
            if not in_json and (char == '{' or char == '['):
                in_json = True
                
            if in_json:
                result += char
                
                # Handle string state
                if char == '"' and not escape_next:
                    in_string = not in_string
                
                # Track nested structures (only when not in a string)
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0 and bracket_count == 0:
                            # Closed top-level JSON object
                            break
                    elif char == '[':
                        bracket_count += 1
                    elif char == ']':
                        bracket_count -= 1
                        if brace_count == 0 and bracket_count == 0:
                            # Closed top-level JSON array
                            break
        
        return result
    
    @staticmethod
    def _thoroughly_clean_json(text: str) -> str:
        """
        Aggressively clean text to extract valid JSON.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text that should be valid JSON
        """
        try:
            if not text:
                logger.warning("Empty text received in _thoroughly_clean_json")
                return "{}"
            
            # Remove any leading/trailing whitespace
            text = text.strip()
            
            # Remove markdown code blocks first
            text = re.sub(r'```(?:json)?\s*', '', text)
            text = re.sub(r'```\s*$', '', text)
            
            # Check if this looks like a simple string rather than JSON
            if not ('{' in text or '[' in text):
                # This might be a simple string input, try to create a minimal JSON structure
                logger.info(f"Input appears to be a plain string rather than JSON: {text[:100]}...")
                # If it looks like a requirements summary, wrap it appropriately
                if any(keyword in text.lower() for keyword in ['requirement', 'should', 'need', 'must', 'system', 'application', 'web', 'api']):
                    return json.dumps({"requirements_summary": text})
                else:
                    # For other content, put it in a general structure
                    return json.dumps({"content": text})
            
            # Declare variables BEFORE using them
            open_braces = 0
            open_brackets = 0
            
            # Remove any comments
            text = re.sub(r'//.*?$', '', text, flags=re.MULTILINE)
            text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
            
            # Extract everything between first { and last }
            if '{' in text and '}' in text:
                start = text.find('{')
                end = text.rfind('}') + 1
                if start >= 0 and end > start:
                    text = text[start:end]
                    
                    # Calculate brace counts AFTER extraction
                    open_braces = text.count('{') - text.count('}')
                    open_brackets = text.count('[') - text.count(']')
                else:
                    raise ValueError(f"Invalid brace positions: start={start}, end={end}")
            elif '[' in text and ']' in text:
                # Handle array root objects
                start = text.find('[')
                end = text.rfind(']') + 1
                if start >= 0 and end > start:
                    text = text[start:end]
                    
                    # Calculate bracket counts AFTER extraction
                    open_braces = text.count('{') - text.count('}')
                    open_brackets = text.count('[') - text.count(']')
                else:
                    raise ValueError(f"Invalid bracket positions: start={start}, end={end}")
            else:
                # IMPROVED: More descriptive error message with better fallback
                logger.warning(f"No JSON object delimiters found in text (length: {len(text)})")
                # Try to extract key-value pairs from the text as a last resort
                extracted_data = JsonHandler._extract_structured_content(text)
                if extracted_data:
                    return json.dumps(extracted_data)
                else:
                    # Create a minimal structure with the text as content
                    return json.dumps({"requirements_summary": text if text else "No requirements specified"})
            
            # NEW: Fix unterminated strings by scanning line by line
            lines = text.split('\n')
            for i, line in enumerate(lines):
                # Check for lines with odd number of quotes (unescaped)
                quote_positions = [m.start() for m in re.finditer(r'(?<!\\)"', line)]
                if len(quote_positions) % 2 == 1:
                    # If odd number of quotes, add closing quote at end
                    logger.warning(f"Found unterminated string on line {i+1}, fixing by adding quote")
                    lines[i] = line + '"'
                
            # Rejoin the fixed lines
            text = '\n'.join(lines)
            
            # Fix trailing commas
            text = re.sub(r',\s*}', '}', text)
            text = re.sub(r',\s*]', ']', text)
            
            # Fix unquoted property names
            text = re.sub(r'([{,]\s*)([a-zA-Z0-9_]+)(\s*:)', r'\1"\2"\3', text)
            
            # Fix single quotes to double quotes
            text = re.sub(r'(?<![\\])\'([^\']*?)(?<![\\])\'', r'"\1"', text)
            
            # Balance braces and brackets if needed
            if open_braces > 0:
                text += '}' * open_braces
                logger.info(f"Added {open_braces} closing braces to balance JSON")
            if open_brackets > 0:
                text += ']' * open_brackets
                logger.info(f"Added {open_brackets} closing brackets to balance JSON")
            
            # Try parsing
            try:
                json.loads(text)
                return text
            except json.JSONDecodeError as e:
                # If still invalid, check for common issues with truncation
                if '"impact":' in text and not text.endswith('}'):
                    # The common case: truncated in the middle of a field
                    text = re.sub(r'"impact"\s*:(?:\s*"[^"]*)?$', '"impact": "Truncated"}]}', text)
                    logger.info("Fixed truncated 'impact' field in recommendations")
                    
                # Try one more time after fixing
                try:
                    json.loads(text)
                    return text
                except json.JSONDecodeError:
                    logger.warning(f"JSON still invalid after cleaning: {e}")
                    # Return a minimal valid structure
                    return json.dumps({"requirements_summary": "Failed to parse requirements"})
            
            return text
                
        except Exception as e:
            # IMPROVED: Don't swallow the original error, provide better fallback
            logger.warning(f"JSON cleaning error in _thoroughly_clean_json: {e}")
            # Try to preserve the original text if it looks like requirements
            if text and any(keyword in text.lower() for keyword in ['requirement', 'should', 'need', 'must', 'system']):
                return json.dumps({"requirements_summary": text})
            else:
                return json.dumps({"requirements_summary": "Error processing requirements"})  # Better than empty object
    
    @classmethod
    def _extract_structured_content(cls, text: str) -> Dict[str, Any]:
        """
        Extract structured content from unstructured text when JSON parsing fails.
        
        Args:
            text: Text to extract structured content from
            
        Returns:
            Dictionary with extracted key-value pairs
        """
        result = {}
        
        try:
            # Try to extract key-value pairs from text
            technology_patterns = {
                "backend": r'(?:backend|server)[^:]*?:\s*(?:is|should be)?\s*([^,\.\n]+)',
                "frontend": r'(?:frontend|client|ui)[^:]*?:\s*(?:is|should be)?\s*([^,\.\n]+)',
                "database": r'(?:database|data store)[^:]*?:\s*(?:is|should be)?\s*([^,\.\n]+)',
                "architecture": r'(?:architecture|pattern)[^:]*?:\s*(?:is|should be)?\s*([^,\.\n]+)'
            }
            
            # Extract technologies
            for tech_key, pattern in technology_patterns.items():
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result[tech_key] = match.group(1).strip()
            
            # Extract additional structured information
            # Look for lists
            list_patterns = {
                "requirements": r'(?:requirements|features)(?:[^:]*?):\s*(?:\n|-)+((?:[\s\-•*]*[^•\n][^\n]+\n)+)',
                "constraints": r'(?:constraints|limitations)(?:[^:]*?):\s*(?:\n|-)+((?:[\s\-•*]*[^•\n][^\n]+\n)+)',
                "components": r'(?:components|modules)(?:[^:]*?):\s*(?:\n|-)+((?:[\s\-•*]*[^•\n][^\n]+\n)+)',
            }
            
            for key, pattern in list_patterns.items():
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    # Extract list items from bullet points or numbered lists
                    item_text = match.group(1)
                    items = []
                    
                    # Extract individual items
                    for line in item_text.split('\n'):
                        # Remove bullet points and leading whitespace
                        cleaned = re.sub(r'^[\s\-•*\d.]+', '', line).strip()
                        if cleaned:
                            items.append(cleaned)
                    
                    if items:
                        result[key] = items
            
            # If we found at least one technology, add a note
            if result:
                result["_note"] = "Extracted from unstructured text as fallback"
                logger.info(f"Extracted {len(result)-1} key-values from unstructured text")
                
            return result
            
        except Exception as e:
            logger.warning(f"Failed to extract structured content: {str(e)}")
            return {}
    
    @staticmethod
    def _parse_model_specific_json(response_text, model_provider, default_response=None, agent_instance=None):
        """
        Parse JSON with model-specific handling.
        
        Args:
            response_text: Text response from the model
            model_provider: Identifier string for the model provider
            default_response: Default response if parsing fails
            agent_instance: Optional reference to the agent for logging
            
        Returns:
            Parsed JSON object or default response
        """
        if model_provider == "gemini":
            return JsonHandler._parse_gemini_json_response(
                response_text, 
                default_response,
                agent_instance
            )
        elif model_provider == "anthropic":
            # Claude-specific JSON handling
            try:
                # Claude tends to have well-formed JSON but sometimes with markdown wrappers
                if "```json" in response_text:
                    # Extract JSON from markdown code block
                    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response_text)
                    if match:
                        text = match.group(1).strip()
                        return json.loads(text)
                
                # If not in code block, try direct parsing
                return json.loads(response_text.strip())
            except json.JSONDecodeError:
                # Fall back to standard parsing
                return JsonHandler._parse_json_with_robust_fallbacks(
                    response_text, 
                    default_response,
                    agent_instance
                )
        else:
            return JsonHandler._parse_json_with_robust_fallbacks(
                response_text, 
                default_response,
                agent_instance
            )
    
    @staticmethod
    def _parse_gemini_json_response(response_text: str, default_response=None, agent_instance=None):
        """
        Parse JSON from Gemini with specialized handling for common errors.
        
        Args:
            response_text: Text response from Gemini
            default_response: Default response if parsing fails
            agent_instance: Optional reference to agent for logging
            
        Returns:
            Parsed JSON object or default response
        """
        try:
            # 1. Initial preprocessing
            text = JsonHandler._preprocess_json_text(response_text)
            
            # 2. Try direct parsing of preprocessed text
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                # Continue to more intensive methods
                pass
                
            # 3. Try extracting JSON with character-by-character parsing
            extracted = JsonHandler._extract_json_character_by_character(text)
            if extracted:
                try:
                    return json.loads(extracted)
                except json.JSONDecodeError:
                    # Continue to more fallbacks
                    pass
            
            # 4. Try thorough cleaning
            try:
                cleaned_text = JsonHandler._thoroughly_clean_json(text)
                return json.loads(cleaned_text)
            except json.JSONDecodeError:
                # Continue to more fallbacks
                pass
                
            # 5. Final fallback: extract key values with regex
            result = JsonHandler._extract_structured_content(text)
            return result if result else (default_response or {})
                
        except Exception as e:
            if agent_instance and hasattr(agent_instance, "log_warning"):
                agent_instance.log_warning(f"Gemini JSON parsing failed: {e}")
            else:
                logger.warning(f"Gemini JSON parsing failed: {e}")
            return default_response if default_response is not None else {}
    
    @staticmethod
    def _parse_json_with_robust_fallbacks(response_text: str, default_response=None, agent_instance=None):
        """
        Parse JSON with multiple fallback strategies and template variable detection.
        
        Args:
            response_text: Text to parse into JSON
            default_response: Default response if parsing fails
            agent_instance: Optional reference to agent for logging
            
        Returns:
            Parsed JSON object or default response
        """
        try:
            # Check for empty or None response
            if not response_text:
                if agent_instance and hasattr(agent_instance, "log_warning"):
                    agent_instance.log_warning("Empty response received for JSON parsing")
                else:
                    logger.warning("Empty response received for JSON parsing")
                return default_response if default_response is not None else {}
            
            # ADDED: Check for template variables in response (common error)
            template_variable_patterns = [
                r'\{extracted_requirement', 
                r'\{backend_evaluation',
                r'\{frontend_evaluation',
                r'\{database_evaluation',
                r'\{architecture_evaluation',
                r'\{tech_stack_recommendation',
                r'\{system_design'
            ]
            
            for pattern in template_variable_patterns:
                if re.search(pattern, response_text, re.IGNORECASE):
                    if agent_instance and hasattr(agent_instance, "log_warning"):
                        agent_instance.log_warning(f"Detected template variable pattern '{pattern}' in response - rejecting")
                    else:
                        logger.warning(f"Detected template variable pattern '{pattern}' in response - rejecting")
                    return default_response if default_response is not None else {}
            
            # Also check for general template-like patterns (anything within braces that's not proper JSON)
            if '{' in response_text and not (response_text.strip().startswith('{') or response_text.strip().startswith('[')):
                suspicious_template_patterns = re.findall(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}', response_text)
                if suspicious_template_patterns:
                    if agent_instance and hasattr(agent_instance, "log_warning"):
                        agent_instance.log_warning(f"Detected suspicious template patterns: {suspicious_template_patterns} - rejecting")
                    else:
                        logger.warning(f"Detected suspicious template patterns: {suspicious_template_patterns} - rejecting")
                    return default_response if default_response is not None else {}
            
            # Try direct JSON parsing first
            try:
                cleaned_text = response_text.strip()

                # Extract from markdown code block if present
                if cleaned_text.startswith("```"):
                    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned_text)
                    if match:
                        cleaned_text = match.group(1).strip()

                return json.loads(cleaned_text)

            except json.JSONDecodeError as e:
                if agent_instance and hasattr(agent_instance, "log_warning"):
                    agent_instance.log_warning(f"Initial JSON parsing failed at position {e.pos}: {e}")
                else:
                    logger.warning(f"Initial JSON parsing failed at position {e.pos}: {e}")
                
                # ADDED: Check if JSON error might be due to template variables
                error_context = ""
                if e.pos > 0 and e.pos < len(response_text):
                    start = max(0, e.pos - 30)
                    end = min(len(response_text), e.pos + 30)
                    error_context = response_text[start:end].replace('\n', '\\n')
                    if agent_instance and hasattr(agent_instance, "log_warning"):
                        agent_instance.log_warning(f"JSON context around position {e.pos}: '...{error_context}...'")
                    else:
                        logger.warning(f"JSON context around position {e.pos}: '...{error_context}...'")
                        
                    # Check if the error context contains template-like patterns
                    if '{' in error_context and '}' in error_context:
                        template_matches = re.findall(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}', error_context)
                        if template_matches:
                            if agent_instance and hasattr(agent_instance, "log_warning"):
                                agent_instance.log_warning(f"Template variables detected around error position: {template_matches} - rejecting")
                            else:
                                logger.warning(f"Template variables detected around error position: {template_matches} - rejecting")
                            return default_response if default_response is not None else {}

                # Try aggressive cleaning
                try:
                    cleaned_text = JsonHandler._thoroughly_clean_json(response_text)
                    parsed_json = json.loads(cleaned_text)
                    
                    if agent_instance and hasattr(agent_instance, "log_info"):
                        agent_instance.log_info("Successfully parsed JSON after thorough cleaning")
                    else:
                        logger.info("Successfully parsed JSON after thorough cleaning")
                        
                    return parsed_json

                except json.JSONDecodeError:
                    # Try character-by-character extraction as last resort
                    extracted = JsonHandler._extract_json_character_by_character(response_text)
                    if extracted:
                        try:
                            return json.loads(extracted)
                        except json.JSONDecodeError:
                            pass
                    
                    # Final fallback to extract structured content
                    result = JsonHandler._extract_structured_content(response_text)
                    return result if result else (default_response or {})
        
        except Exception as e:
            if agent_instance and hasattr(agent_instance, "log_warning"):
                agent_instance.log_warning(f"Error in JSON parsing: {str(e)}")
            else:
                logger.warning(f"Error in JSON parsing: {str(e)}")
        
            return default_response if default_response is not None else {}
    
    @classmethod
    def parse_json_with_error_tracking(cls, response, agent_instance=None, pydantic_model=None, default_response=None):
        """
        Parse JSON from LLM response with enhanced validation, structured error tracking, and repair strategies.
        
        Args:
            response: Raw response from LLM (string, AIMessage, or other response object)
            agent_instance: Optional reference to the calling agent for context-aware processing
            pydantic_model: Optional Pydantic model to validate and structure the output
            default_response: Default response to use if parsing fails
            
        Returns:
            Dict/List: Successfully parsed JSON object or default response on failure
        """
        # Track parsing stages for better diagnostics
        parsing_stages = []
        
        try:
            # Extract text content first
            extracted_text = cls._extract_text_content(response)
            parsing_stages.append(("text_extraction", bool(extracted_text)))
            
            # Log raw input for diagnostics if an agent instance is provided
            if agent_instance and hasattr(agent_instance, "log_info"):
                input_preview = extracted_text[:100] + "..." if len(extracted_text) > 100 else extracted_text
                agent_instance.log_info(f"Parsing JSON from input ({len(extracted_text)} chars): {input_preview}")
            
            # Check for empty response and try model escalation if possible
            if not extracted_text or extracted_text.strip() == "":
                logger.warning("Empty response received, cannot parse JSON")
                parsing_stages.append(("empty_check", False))
                
                if agent_instance and hasattr(agent_instance, "last_json_prompt"):
                    parsing_stages.append(("escalation_attempt", True))
                    logger.info("Attempting model escalation for empty response")
                    current_model = getattr(agent_instance.llm, 'model_name', None)
                    
                    escalation_result = cls.auto_escalate_model_for_json(
                        default_response if default_response is not None else {}, 
                        agent_instance.llm,
                        agent_instance.last_json_prompt,
                        current_model
                    )
                    
                    if escalation_result and isinstance(escalation_result, dict) and len(escalation_result) > 0:
                        parsing_stages.append(("escalation_success", True))
                        # Log success if agent instance is provided
                        if agent_instance and hasattr(agent_instance, "log_success"):
                            agent_instance.log_success("Model escalation produced valid JSON response")
                        return escalation_result
                    
                    parsing_stages.append(("escalation_success", False))
                
                # Log failure details if agent instance is provided
                if agent_instance and hasattr(agent_instance, "log_warning"):
                    agent_instance.log_warning("Failed to parse empty response, using default")
                
                return default_response if default_response is not None else {}
            
            # Check for template variables before attempting to parse
            has_templates, template_vars = cls.check_template_variables(extracted_text)
            parsing_stages.append(("template_check", not has_templates))
            
            if has_templates:
                # Log template variables in the response
                if agent_instance and hasattr(agent_instance, "log_warning"):
                    agent_instance.log_warning(f"Template variables detected in response: {template_vars}")
                else:
                    logger.warning(f"Template variables detected in response: {template_vars}")
                
                # Try to sanitize template variables before giving up
                sanitized_text = extracted_text
                for var in template_vars:
                    # Replace template variables with dummy values based on variable name
                    if "id" in var.lower():
                        sanitized_text = re.sub(r'\{\s*' + var + r'\s*\}', '"id-placeholder"', sanitized_text)
                    elif "name" in var.lower():
                        sanitized_text = re.sub(r'\{\s*' + var + r'\s*\}', '"name-placeholder"', sanitized_text)
                    else:
                        sanitized_text = re.sub(r'\{\s*' + var + r'\s*\}', '"placeholder"', sanitized_text)
                
                # Try parsing with sanitized text
                try:
                    parsed_json = json.loads(sanitized_text)
                    if agent_instance and hasattr(agent_instance, "log_info"):
                        agent_instance.log_info("Successfully parsed JSON after template variable sanitization")
                    
                    # Add warning about sanitization
                    if isinstance(parsed_json, dict):
                        parsed_json["_sanitized_templates"] = template_vars
                        
                    parsing_stages.append(("sanitization_success", True))
                    return parsed_json
                except json.JSONDecodeError:
                    parsing_stages.append(("sanitization_success", False))
                    # Continue to normal parsing as fallback
            
            # For non-empty responses, detect model provider and use appropriate parser
            try:
                # Detect model provider if agent instance is available
                model_provider = "unknown"
                if agent_instance and hasattr(agent_instance, "llm"):
                    model_provider = cls._detect_model_provider(agent_instance.llm)
                
                parsing_stages.append(("model_detection", bool(model_provider != "unknown")))
                
                # Use BRD-specific repair for BRD Analyst
                if agent_instance and getattr(agent_instance, "agent_name", "") == "BRD Analyst Agent":
                    try:
                        repaired_json = cls.repair_brd_analyst_json(extracted_text)
                        if repaired_json and isinstance(repaired_json, dict):
                            parsing_stages.append(("brd_specific_repair", True))
                            if agent_instance and hasattr(agent_instance, "log_info"):
                                agent_instance.log_info("Used BRD-specific JSON repair successfully")
                            
                            # Validate against Pydantic model if provided
                            if pydantic_model and repaired_json:
                                try:
                                    validated = pydantic_model(**repaired_json)
                                    parsing_stages.append(("pydantic_validation", True))
                                    return validated.dict()
                                except Exception as e:
                                    parsing_stages.append(("pydantic_validation", False))
                                    if agent_instance and hasattr(agent_instance, "log_warning"):
                                        agent_instance.log_warning(f"Pydantic validation failed after BRD repair: {e}")
                            
                            return repaired_json
                    except Exception as repair_error:
                        parsing_stages.append(("brd_specific_repair", False))
                        if agent_instance and hasattr(agent_instance, "log_warning"):
                            agent_instance.log_warning(f"BRD-specific repair failed: {repair_error}")
                
                # Parse response based on detected model provider
                result = cls._parse_model_specific_json(
                    extracted_text, 
                    model_provider, 
                    default_response=default_response,
                    agent_instance=agent_instance
                )
                
                parsing_stages.append(("model_specific_parsing", bool(result)))
                
                # Apply agent-specific fixes if possible
                if result and isinstance(result, dict) and agent_instance:
                    agent_name = getattr(agent_instance, "agent_name", "")
                    if agent_name:
                        fixed_result = cls.fix_common_agent_json_issues(agent_name, result)
                        parsing_stages.append(("agent_specific_fixes", True))
                        result = fixed_result
            
                # Validate against pydantic model if provided
                if pydantic_model and result:
                    try:
                        # For Pydantic v1
                        if hasattr(pydantic_model, 'parse_obj'):
                            validated = pydantic_model.parse_obj(result)
                            parsing_stages.append(("pydantic_validation", True))
                            if agent_instance and hasattr(agent_instance, "log_info"):
                                agent_instance.log_info("Successfully validated with Pydantic model")
                            return validated.dict()
                        # For Pydantic v2
                        else:
                            validated = pydantic_model.model_validate(result) 
                            parsing_stages.append(("pydantic_validation", True))
                            if agent_instance and hasattr(agent_instance, "log_info"):
                                agent_instance.log_info("Successfully validated with Pydantic v2 model")
                            return validated.model_dump()
                    except Exception as pydantic_error:
                        parsing_stages.append(("pydantic_validation", False))
                        
                        # Provide detailed validation error information
                        error_details = str(pydantic_error)
                        validation_errors = {}
                        
                        # Extract specific field errors for better debugging
                        if hasattr(pydantic_error, 'errors'):
                            try:
                                for error in pydantic_error.errors():
                                    loc = '.'.join(str(x) for x in error.get('loc', []))
                                    validation_errors[loc] = error.get('msg', '')
                            except Exception:
                                pass
                        
                        if agent_instance and hasattr(agent_instance, "log_warning"):
                            agent_instance.log_warning(f"Pydantic validation failed: {error_details}")
                            if validation_errors:
                                agent_instance.log_warning(f"Field errors: {validation_errors}")
                        else:
                            logger.warning(f"Pydantic validation failed: {error_details}")
                            if validation_errors:
                                logger.warning(f"Field errors: {validation_errors}")
                        
                        # Add validation info to result if it's a dict
                        if isinstance(result, dict):
                            result["_validation_errors"] = validation_errors
                            result["_validation_status"] = "failed"
                
                # Log parsing success if agent instance is provided
                if result and agent_instance and hasattr(agent_instance, "log_info"):
                    result_type = f"{type(result).__name__} with {len(result)} items" if isinstance(result, (dict, list)) else type(result).__name__
                    agent_instance.log_info(f"JSON parsing completed successfully: {result_type}")
                
                return result
    
            except Exception as e:
                # Comprehensive error handling
                parsing_stages.append(("exception", True))
                error_message = f"Error in JSON parsing: {str(e)}"
                
                if agent_instance and hasattr(agent_instance, "log_warning"):
                    agent_instance.log_warning(error_message)
                    # Log parsing stages for debugging
                    agent_instance.log_warning(f"JSON parsing stages: {parsing_stages}")
                else:
                    logger.warning(error_message)
                    logger.warning(f"JSON parsing stages: {parsing_stages}")
            
                # Try one final extraction approach for robustness
                try:
                    structured_result = cls._extract_structured_content(extracted_text)
                    if structured_result:
                        if agent_instance and hasattr(agent_instance, "log_info"):
                            agent_instance.log_info("Fell back to structured content extraction")
                        return structured_result
                except Exception:
                    pass
            
                # Return default response with error details
                if isinstance(default_response, dict):
                    error_response = default_response.copy()
                    error_response["_parsing_error"] = str(e)
                    error_response["_parsing_stages"] = parsing_stages
                    return error_response
                
                return default_response if default_response is not None else {}
        
        except Exception as e:
            # Global exception handler for the entire method
            logger.error(f"Critical error in parse_json_with_error_tracking: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Return default response with error details
            if isinstance(default_response, dict):
                error_response = default_response.copy()
                error_response["_critical_error"] = str(e)
                return error_response
                
            return default_response if default_response is not None else {}
    
    @classmethod
    def _extract_structured_data(cls, text):
        """
        Extract structured data from unstructured text using regex patterns.
        
        Args:
            text: Text to extract data from
            
        Returns:
            Dictionary with extracted data
        """
        result = {}
        
        # Match key-value patterns like "key: value" or "key = value"
        kv_patterns = [
            r'["\']?([\w\s]+)["\']?\s*:\s*["\']?([\w\s\.\-]+)["\']?',  # "key": "value" or key: value
            r'["\']?([\w\s]+)["\']?\s*=\s*["\']?([\w\s\.\-]+)["\']?',  # "key" = "value" or key = value
        ]
        
        for pattern in kv_patterns:
            matches = re.findall(pattern, text)
            for key, value in matches:
                key = key.strip()
                value = value.strip()
                if key and value and key not in result:
                    result[key] = value
        
        # Try to extract arrays/lists
        list_pattern = r'["\']?([\w\s]+)["\']?\s*:\s*\[([\w\s",\.\-\']+)\]'
        list_matches = re.findall(list_pattern, text)
        for key, value_list in list_matches:
            key = key.strip()
            if key and key not in result:
                # Split the list by commas and clean up items
                items = [item.strip(' "\'') for item in value_list.split(',')]
                result[key] = [item for item in items if item]
        
        # Try to parse nested structures (simplified)
        nested_pattern = r'["\']?([\w\s]+)["\']?\s*:\s*\{([^\}]+)\}'
        nested_matches = re.findall(nested_pattern, text)
        for key, nested_content in nested_matches:
            key = key.strip()
            if key and key not in result:
                # Recursively extract from nested content
                nested_result = cls._extract_structured_data(nested_content)
                if nested_result:
                    result[key] = nested_result
        
        return result
    
    @staticmethod
    def _parse_timeline_json(response_text: str, default_response=None):
        """
        Parse JSON from timeline synthesis responses with enhanced heuristics.
        
        Args:
            response_text: Text response from LLM
            default_response: Default response if parsing fails
            
        Returns:
            Parsed JSON object or default response
        """
        try:
            # 1. Initial preprocessing
            text = JsonHandler._preprocess_json_text(response_text)
            
            # 2. Try direct parsing of preprocessed text
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                # Continue to more intensive methods
                pass
                
            # 3. Try extracting JSON with character-by-character parsing
            extracted = JsonHandler._extract_json_character_by_character(text)
            if extracted:
                try:
                    return json.loads(extracted)
                except json.JSONDecodeError:
                    # Continue to more fallbacks
                    pass
            
            # 4. Try thorough cleaning
            try:
                cleaned_text = JsonHandler._thoroughly_clean_json(text)
                return json.loads(cleaned_text)
            except json.JSONDecodeError:
                # Continue to more fallbacks
                pass
                
            # 5. Final fallback: extract key values with regex
            result = JsonHandler._extract_structured_content(text)
            return result if result else (default_response or {})
                
        except Exception as e:
            logger.warning(f"Timeline JSON parsing failed: {e}")
            return default_response if default_response is not None else {}
    
    @staticmethod
    def _attempt_json_repair(text: str) -> Optional[str]:
        """
        Attempt to repair common JSON issues in the text with enhanced Gemini handling.
        
        Args:
            text: Text to repair
            
        Returns:
            Repaired text or None if repair failed
        """
        try:
            if not text or not isinstance(text, str):
                return None
                
            # 1. Check if the first non-whitespace character is '{'
            text = text.strip()
            if not text.startswith('{') and not text.startswith('['):
                # Try to find a JSON object or array
                match = re.search(r'(\{|\[)', text)
                if match:
                    # Skip everything before the first { or [
                    text = text[match.start():]
                else:
                    # No JSON structure found
                    return None
                    
            # 2. Fix unquoted property names - Enhanced precision for position 1 errors
            # This comprehensive regex specifically targets property names without quotes
            # It handles both object start (position 1) and after commas
            text = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', text)
            
            # 3. Fix trailing commas
            text = re.sub(r',\s*}', '}', text)
            text = re.sub(r',\s*]', ']', text)
            
            # 4. Fix single quotes to double quotes for property values
            text = re.sub(r':\s*\'([^\']*?)\'', r': "\1"', text)
            
            # 5. Fix unquoted property values that should be strings
            text = re.sub(r':\s*(true|false|null|[0-9]+|[0-9]+\.[0-9]+)\s*([,}])', r': \1\2', text)
            text = re.sub(r':\s*([^"{}\[\],\s][^,}\]]*?)([,}\]])', r': "\1"\2', text)
            
            # 6. Balance braces and brackets
            open_braces = text.count('{')
            close_braces = text.count('}')
            if open_braces > close_braces:
                text += '}' * (open_braces - close_braces)
                
            open_brackets = text.count('[')
            close_brackets = text.count(']')
            if open_brackets > close_brackets:
                text += ']' * (open_brackets - close_brackets)
        
            # 7. Verify the JSON is valid before returning
            try:
                json.loads(text)
                return text
            except json.JSONDecodeError:
                # If still invalid, return None
                return None
        except Exception as e:
            logger.warning(f"Error repairing JSON: {e}")
            return None
    
    @staticmethod
    def _log_warning(message: str):
        """
        Log a warning message, can be overridden in agent instance.
        
        Args:
            message: Message to log
        """
        logger.warning(message)
    
    @staticmethod
    def _log_info(message: str):
        """
        Log an info message, can be overridden in agent instance.
        
        Args:
            message: Message to log
        """
        logger.info(message)
    
    @staticmethod
    def validate_json_against_schema(json_data: Dict[str, Any], expected_fields: List[str], 
                                    optional_fields: List[str] = None) -> Dict[str, Any]:
        """
        Validate JSON against expected field structure.
        
        Args:
            json_data: The JSON data to validate
            expected_fields: List of fields that must be present
            optional_fields: List of optional fields
            
        Returns:
            Dict: The validated JSON or a default structure with missing fields
        """
        try:
            if not json_data or not isinstance(json_data, dict):
                logger.warning("Invalid JSON structure: not a dictionary")
                return {}
                
            # Check for expected fields
            for field in expected_fields:
                if field not in json_data:
                    logger.warning(f"Missing expected field: {field}")
                    json_data[field] = None  # Add missing field with null value
            
            # Remove unexpected fields if strict validation
            if optional_fields is not None:
                for key in list(json_data.keys()):
                    if key not in expected_fields and key not in optional_fields:
                        logger.warning(f"Removing unexpected field: {key}")
                        del json_data[key]
            
            return json_data
                
        except Exception as e:
            logger.warning(f"JSON schema validation error: {e}")
            return {}

    @staticmethod
    def transform_json_structure(json_data: Dict[str, Any], 
                             mapping: Dict[str, str] = None,
                             default_structure: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Transform JSON from one structure to another using field mapping.
        
        Args:
            json_data: Source JSON to transform
            mapping: Dictionary mapping source fields to target fields
            default_structure: Default structure to use if transformation fails
            
        Returns:
            Dict: Transformed JSON structure
        """
        try:
            if not json_data:
                return default_structure or {}
                
            if not mapping:
                return json_data
                
            result = {}
            # Apply mapping
            for source_field, target_field in mapping.items():
                if source_field in json_data:
                    result[target_field] = json_data[source_field]
                    
            return result
                
        except Exception as e:
            logger.warning(f"JSON transformation error: {e}")
            return default_structure or {}

    @staticmethod
    def merge_json_objects(primary, secondary, override_conflicts=True, depth=0, max_depth=50):
        """
        Merge two JSON objects with conflict resolution and recursion protection.
        
        Args:
            primary: Primary JSON object
            secondary: Secondary JSON object to merge in
            override_conflicts: Whether to override conflicts with secondary values
            depth: Current recursion depth (internal use)
            max_depth: Maximum recursion depth allowed
            
        Returns:
            Dict: Merged JSON object
        """
        # Add recursion depth protection
        if depth >= max_depth:
            logger.warning(f"Maximum recursion depth {max_depth} reached in merge_json_objects")
            return primary
        
        try:
            if not primary:
                return secondary or {}
                
            if not secondary:
                return primary
                
            result = primary.copy()
            
            # Merge secondary into primary
            for key, value in secondary.items():
                # If both have the key and both values are dictionaries, recursive merge
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = JsonHandler.merge_json_objects(result[key], value, override_conflicts, depth+1, max_depth)
                # Handle list values - append or override
                elif key in result and isinstance(result[key], list) and isinstance(value, list):
                    if override_conflicts:
                        result[key] = value
                    else:
                        # Append items not already in the list (avoid duplicates)
                        for item in value:
                            if item not in result[key]:
                                result[key].append(item)
                # Override or skip based on flag
                elif key not in result or override_conflicts:
                    result[key] = value
                
            return result
                
        except Exception as e:
            logger.warning(f"JSON merge error: {e}")
            return primary

    @staticmethod
    def fix_common_agent_json_issues(agent_name: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply agent-specific fixes for common JSON issues.
        
        Args:
            agent_name: The name of the agent to apply specific fixes for
            json_data: The JSON data to fix
            
        Returns:
            Dict: Fixed JSON object
        """
        try:
            if not json_data:
                return {}
                
            # Clone the input to avoid modifying the original
            fixed_data = json_data.copy()
            
            # Apply agent-specific fixes
            if agent_name.lower() == "tech_stack_advisor_agent" or agent_name.lower() == "tech_stack_advisor":
                # Fix common tech stack advisor issues
                if "backend" in fixed_data and not isinstance(fixed_data["backend"], dict):
                    # Convert string to proper structure
                    if isinstance(fixed_data["backend"], str):
                        fixed_data["backend"] = {"language": fixed_data["backend"]}
                        
                # Fix missing recommendation field
                if "backend_options" in fixed_data and "recommendation" not in fixed_data:
                    if fixed_data["backend_options"] and len(fixed_data["backend_options"]) > 0:
                        fixed_data["recommendation"] = fixed_data["backend_options"][0]
                        
            elif agent_name.lower() == "system_designer_agent" or agent_name.lower() == "system_designer":
                # Fix common system designer issues
                if "architecture_pattern" in fixed_data and isinstance(fixed_data["architecture_pattern"], dict):
                    # Extract pattern from object if needed
                    if "pattern" in fixed_data["architecture_pattern"]:
                        fixed_data["architecture_pattern"] = fixed_data["architecture_pattern"]["pattern"]
                        
                # Fix missing security measures
                if "security_architecture" in fixed_data and isinstance(fixed_data["security_architecture"], dict) and "security_measures" not in fixed_data["security_architecture"]:
                    fixed_data["security_architecture"]["security_measures"] = [
                        {"category": "Default", "implementation": "Basic security measures"}
                    ]
                    
            elif agent_name.lower() == "brd_analyst_agent" or agent_name.lower() == "brd_analyst":
                # Fix common BRD analyst issues
                if "requirements" in fixed_data and isinstance(fixed_data["requirements"], list):
                    # Ensure each requirement has an ID
                    for i, req in enumerate(fixed_data["requirements"]):
                        if isinstance(req, dict) and "id" not in req:
                            req["id"] = f"REQ-{i+1:03d}"
                
            # Return the fixed data
            return fixed_data
                
        except Exception as e:
            logger.warning(f"Error fixing agent-specific JSON issues: {e}")
            return json_data
    
    @staticmethod
    def repair_system_designer_json(json_text: str) -> dict:
        """
        Special JSON repair focused on common System Designer outputs.
        
        Args:
            json_text: Text to repair
            
        Returns:
            Dict: Repaired JSON object
        """
        try:
            # First try normal repair
            repaired = JsonHandler._attempt_json_repair(json_text)
            if repaired:
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError:
                    pass  # Continue to specialized repairs
            
            # Check for malformed module structure - a common issue
            if '"modules"' in json_text:
                # Extract the modules array even if malformed
                modules_match = re.search(r'"modules"\s*:\s*\[(.*?)\]', json_text, re.DOTALL)
                if modules_match:
                    modules_text = modules_match.group(1)
                    # Try to extract individual module objects
                    module_objects = []
                    depth = 0
                    current_obj = ""
                    
                    for char in modules_text:
                        if char == '{':
                            depth += 1
                            current_obj += char
                        elif char == '}':
                            depth -= 1
                            current_obj += char
                            if depth == 0:
                                # Try to parse and fix this module object
                                try:
                                    fixed_obj = "{" + current_obj.split("{", 1)[1]
                                    json.loads(fixed_obj)  # Just to validate
                                    module_objects.append(fixed_obj)
                                except:
                                    pass  # Skip invalid modules
                            current_obj = ""
                        elif depth > 0:
                            current_obj += char
                    
                    # If we extracted valid modules, create a basic structure
                    if module_objects:
                        return {
                            "modules": [json.loads(obj) for obj in module_objects],
                            "_extraction_note": "Recovered modules from malformed JSON"
                        }
            
            # Fall back to structured extraction if all else fails
            return JsonHandler._extract_structured_content(json_text)
        except Exception as e:
            logger.warning(f"System designer JSON repair failed: {e}")
            return JsonHandler._extract_structured_content(json_text)
    
    @classmethod
    def _extract_json_from_markdown(cls, text: str) -> str:
        """
        Extract JSON content from markdown code blocks.
    
        Args:
            text: Text potentially containing markdown code blocks
        
        Returns:
            Extracted JSON string or empty string if no JSON found
        """
        try:
            # Try to extract from JSON code block
            json_block_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
            matches = re.findall(json_block_pattern, text)
            if matches:
                return matches[0].strip()
            
            # Try to extract any code block that might contain JSON
            code_block_pattern = r"```\s*([\s\S]*?)\s*```"
            matches = re.findall(code_block_pattern, text)
            if matches:
                for match in matches:
                    # Check if this block might be JSON (starts with { or [)
                    cleaned = match.strip()
                    if cleaned and (cleaned.startswith('{') or cleaned.startswith('[')):
                        return cleaned
                    
            # If no code blocks found, look for JSON-like structures
            json_pattern = r"(\{[\s\S]*\}|\[[\s\S]*\])"
            matches = re.search(json_pattern, text)
            if matches:
                return matches.group(1)
                
            return ""
        except Exception as e:
            cls._log_warning(f"Error extracting JSON from markdown: {e}")
            return ""
    
    @staticmethod
    def auto_escalate_model_for_json(initial_result, llm, json_prompt, current_model_name=None):
        """
        Automatically escalate to a more powerful model when JSON parsing fails.
        
        Args:
            initial_result: Initial result that triggered escalation
            llm: Base language model
            json_prompt: Prompt that failed to generate valid JSON
            current_model_name: Name of current model (optional)
            
        Returns:
            Fixed JSON result or initial result if escalation fails
        """
        try:
            # Define escalation path (from lighter to heavier models)
            escalation_path = [
                "gemini-2.0-flash-lite",
                "gemini-2.5-flash-preview", 
                "gemini-1.5-pro-latest"
            ]
            
            # Get current model's position in escalation path
            current_name = current_model_name or getattr(llm, 'model_name', '')
            current_index = None
            for i, model in enumerate(escalation_path):
                if model in current_name:
                    current_index = i
                    break
            
            # If not found or already at the end of escalation path, return the initial result
            if current_index is None or current_index >= len(escalation_path) - 1:
                return initial_result
            
            # Try the next model in the escalation path
            next_model = escalation_path[current_index + 1]
            logger.info(f"Auto-escalating from {current_name} to {next_model} after JSON parsing failure")
            
            # Import get_llm function and try with a more powerful model
            try:
                from config import get_llm
                escalated_llm = get_llm(model_name=next_model, temperature=0.0)
                json_llm = JsonHandler.create_strict_json_llm(escalated_llm)
                response = json_llm.invoke(json_prompt)
                
                # Try to parse the result
                response_text = response.content if hasattr(response, 'content') else str(response)
                parsed_json = json.loads(response_text)
                logger.info(f"Successfully parsed JSON after escalation to {next_model}")
                return parsed_json
            except Exception as e:
                logger.warning(f"Model escalation failed: {e}")
                return initial_result
                
        except Exception as e:
            logger.warning(f"Auto-escalation error: {e}")
            return initial_result
    
    @classmethod
    def extract_json_from_text(cls, text: Any) -> Any:
        """
        Extract JSON from text using multiple parsing strategies.
        
        Args:
            text: Text potentially containing JSON or already parsed dict/list
        
        Returns:
            Dict/List/None: Extracted JSON object or None if extraction fails
        """
        # If text is already a dict or list, return it directly
        if isinstance(text, (dict, list)):
            return text
        
        if not text or (isinstance(text, str) and not text.strip()):
            logger.warning("Empty or whitespace-only text received in extract_json_from_text")
            return {"requirements_summary": "No content provided"}
            
        # Convert to string if needed
        if not isinstance(text, str):
            text = str(text)
            
        text = text.strip()
        
        # Check if text looks like JSON at all
        if not ('{' in text or '[' in text):
            logger.info("Text does not contain JSON delimiters, treating as plain text")
            # If it looks like requirements or technical content, wrap appropriately
            if any(keyword in text.lower() for keyword in ['requirement', 'should', 'need', 'must', 'system', 'application', 'web', 'api', 'backend', 'frontend', 'database']):
                return {"requirements_summary": text}
            else:
                return {"content": text}
            
        try:
            # First try to parse the entire text as JSON
            try:
                result = json.loads(text)
                logger.info("Successfully parsed entire text as JSON")
                return result
            except json.JSONDecodeError as e:
                logger.debug(f"Direct JSON parsing failed: {e}")
                
            # Extract JSON from markdown if present
            json_text = cls._extract_json_from_markdown(text)
            if json_text:
                try:
                    result = json.loads(json_text.strip())
                    logger.info("Successfully extracted JSON from markdown")
                    return result
                except json.JSONDecodeError:
                    logger.debug("Markdown-extracted JSON parsing failed")
                    
            # Try preprocessing then parsing
            preprocessed_text = cls._preprocess_json_text(text)
            try:
                result = json.loads(preprocessed_text)
                logger.info("Successfully parsed after preprocessing")
                return result
            except json.JSONDecodeError:
                logger.debug("Preprocessed JSON parsing failed")
                
            # Try character by character extraction
            extracted_text = cls._extract_json_character_by_character(text)
            if extracted_text:
                try:
                    result = json.loads(extracted_text)
                    logger.info("Successfully parsed after character-by-character extraction")
                    return result
                except json.JSONDecodeError:
                    logger.debug("Character-by-character extracted JSON parsing failed")
            
            # Try thorough cleaning
            cleaned_text = cls._thoroughly_clean_json(text)
            try:
                result = json.loads(cleaned_text)
                logger.info("Successfully parsed after thorough cleaning")
                return result
            except json.JSONDecodeError:
                logger.debug("Thoroughly cleaned JSON parsing failed")
                
            # Last resort: attempt repair
            repaired_text = cls._attempt_json_repair(text)
            if repaired_text:
                try:
                    result = json.loads(repaired_text)
                    logger.info("Successfully parsed after JSON repair")
                    return result
                except json.JSONDecodeError:
                    logger.debug("Repaired JSON parsing failed")
            
            # If all parsing attempts fail, try to extract structured content
            logger.info("All JSON parsing attempts failed, attempting structured content extraction")
            structured_content = cls._extract_structured_content(text)
            if structured_content:
                logger.info("Successfully extracted structured content")
                return structured_content
            else:
                # Final fallback - wrap the text as content
                logger.warning("All extraction methods failed, wrapping text as content")
                return {"requirements_summary": text}
            
        except Exception as e:
            logger.warning(f"JSON extraction failed with exception: {e}")
            # Final safety net - return the text wrapped in a structure
            if isinstance(text, str) and text.strip():
                return {"requirements_summary": text}
            else:
                return {"requirements_summary": "Error processing input"}
    
    @classmethod
    def check_template_variables(cls, text: str) -> Tuple[bool, List[str]]:
        """
        Check for template variables in text that could cause JSON parsing issues.
        
        Args:
            text: Text to check for template variables
            
        Returns:
            Tuple of (has_templates, template_variable_names)
        """
        if not text:
            return False, []
            
        # Common template variable patterns
        template_patterns = [
            r'\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}',  # {variable_name}
            r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}',        # {variable_name} without spaces
            r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}',  # {{variable_name}}
            r'\{%\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*%\}'   # {% variable_name %}
        ]
        
        found_variables = set()
        for pattern in template_patterns:
            matches = re.findall(pattern, text)
            found_variables.update(matches)
        
        # Filter out common JSON field names that might match the pattern
        common_json_fields = {'id', 'name', 'type', 'value', 'key', 'data', 'items', 'properties', 'result'}
        template_vars = [var for var in found_variables if var.lower() not in common_json_fields]
        
        # Check for known template variable names
        known_template_vars = [
            'backend_evaluation', 'frontend_evaluation', 'database_evaluation',
            'extracted_requirement', 'tech_stack_recommendation', 'system_design',
            'architecture_evaluation', 'implementation_plan'
        ]
        
        for known_var in known_template_vars:
            if f'{{{known_var}}}' in text:
                template_vars.append(known_var)
        
        # Return results
        return len(template_vars) > 0, template_vars
    
    @staticmethod
    def repair_brd_analyst_json(text: str) -> dict:
        """
        Special JSON repair focused on BRD Analyst outputs.
        
        Args:
            text: Text to repair
            
        Returns:
            Dict: Repaired JSON object
        """
        try:
            # First try normal repair
            repaired = JsonHandler._attempt_json_repair(text)
            if repaired:
                try:
                    parsed_json = json.loads(repaired)
                    # Verify it has the expected structure
                    if "project_name" in parsed_json and "requirements" in parsed_json:
                        return parsed_json
                except json.JSONDecodeError:
                    pass  # Continue to specialized repairs
            
            # Check for malformed requirements structure - a common issue
            requirements_match = re.search(r'"requirements"\s*:\s*\[(.*?)\]', text, re.DOTALL)
            if requirements_match:
                requirements_text = requirements_match.group(1)
                # Try to extract individual requirement objects
                requirement_objects = []
                depth = 0
                current_obj = ""
                
                for char in requirements_text:
                    if char == '{':
                        depth += 1
                        current_obj += char
                    elif char == '}':
                        depth -= 1
                        current_obj += char
                        if depth == 0:
                            # Try to parse and fix this requirement object
                            try:
                                fixed_obj = "{" + current_obj.split("{", 1)[1]
                                json.loads(fixed_obj)  # Just to validate
                                requirement_objects.append(fixed_obj)
                            except:
                                pass  # Skip invalid requirements
                            current_obj = ""
                    elif depth > 0:
                        current_obj += char
                
                # If we extracted valid requirements, create a basic structure
                if requirement_objects:
                    # Extract project name if present
                    project_name = "Untitled Project"
                    project_match = re.search(r'"project_name"\s*:\s*"([^"]+)"', text)
                    if project_match:
                        project_name = project_match.group(1)
                    
                    # Extract project summary if present
                    project_summary = "No summary available"
                    summary_match = re.search(r'"project_summary"\s*:\s*"([^"]+)"', text)
                    if summary_match:
                        project_summary = summary_match.group(1)
                    
                    return {
                        "project_name": project_name,
                        "project_summary": project_summary,
                        "requirements": [json.loads(obj) for obj in requirement_objects],
                        "_extraction_note": "Recovered requirements from malformed JSON"
                    }
            
            # Fall back to structured extraction if all else fails
            structured_data = JsonHandler._extract_structured_content(text)
            
            # If we have minimal structured data, create a basic BRD structure
            if structured_data:
                result = {
                    "project_name": structured_data.get("project_name", "Untitled Project"),
                    "project_summary": structured_data.get("project_summary", "No summary available"),
                    "requirements": structured_data.get("requirements", []),
                    "_extraction_note": "Recovered from structured content extraction"
                }
                
                # Convert string requirements to objects if needed
                if isinstance(result["requirements"], list) and all(isinstance(item, str) for item in result["requirements"]):
                    result["requirements"] = [{"id": f"REQ-{i+1:03d}", "title": item, "description": item, "category": "functional", "priority": "medium"} 
                                           for i, item in enumerate(result["requirements"])]
                
                return result
            
            # If all else fails, return a minimal structure
            return {
                "project_name": "Untitled Project",
                "project_summary": "No summary available - extraction failed",
                "requirements": [],
                "_extraction_error": "Could not extract valid BRD data"
            }
            
        except Exception as e:
            logger.warning(f"BRD analyst JSON repair failed: {e}")
            return {
                "project_name": "Untitled Project",
                "project_summary": "No summary available - repair exception",
                "requirements": [],
                "_extraction_error": f"Repair exception: {str(e)}"
            }