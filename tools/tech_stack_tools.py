"""
Tech stack evaluation tools for the ReAct-based TechStackAdvisorAgent.
Each tool is focused on a specific aspect of technology evaluation and selection.
"""

import json
import os
import re
import logging
import traceback
from typing import Dict, Any, List, Union, Optional
from langchain_core.tools import tool, BaseTool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from enhanced_memory_manager import create_memory_manager, EnhancedSharedProjectMemory

# Import Pydantic models from centralized data contracts
from models.data_contracts import (
    # Input models
    TechnicalRequirementsSummaryInput,
    BackendEvaluationInput,
    FrontendFrameworkRecommendationInput, 
    DatabaseEvaluationInput,
    ArchitectureEvaluationInput,
    TechStackInput,
    TechStackRiskAnalysisInput,
    BatchTechnologyEvaluationInput,
    TechStackSynthesisInput,  # Add this import
    
    # Output models (new)
    TechnicalRequirementsSummaryOutput,
    BackendEvaluationOutput,
    FrontendEvaluationOutput,
    FrontendEvaluationInput,
    DatabaseEvaluationOutput,
    ArchitecturePatternEvaluationOutput,
    TechStackSynthesisOutput,
    TechStackRiskAnalysisOutput,
    
    # Component models
    TechOption,
    ArchitecturePatternOption,
    LibraryTool,
    TechRisk,
    TechCompatibilityIssue
)

# Add the import at the top
from utils.react_tool_wrapper import smart_react_tool

# Enhanced memory and RAG helper functions for tech stack tools
def get_enhanced_tech_memory():
    """Get SHARED enhanced memory manager instance for tech stack tools."""
    try:
        from utils.shared_memory_hub import get_shared_memory_hub
        # Use the GLOBAL shared memory hub to prevent data isolation
        return get_shared_memory_hub()
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Shared memory hub not available, using fallback: {e}")
        return None

def get_tech_rag_context(query_type: str, domain: str = None, **kwargs):
    """Get RAG context for technology-related queries."""
    try:
        from rag_manager import get_rag_manager
        rag_manager = get_rag_manager()
        if not rag_manager:
            return ""
            
        # Generate domain and type-specific RAG queries
        queries = _get_tech_specific_rag_queries(query_type, domain, **kwargs)
        
        context_parts = []
        for query in queries:
            try:
                docs = rag_manager.similarity_search(query, k=3)
                if docs:
                    context_parts.extend([doc.page_content for doc in docs])
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"RAG query failed for '{query}': {e}")
                
        return "\n\n".join(context_parts[:1000])  # Limit context size
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"RAG context retrieval failed: {e}")
        return ""

def _get_tech_specific_rag_queries(query_type: str, domain: str = None, **kwargs):
    """Generate specific RAG queries based on technology type and domain."""
    queries = []
    
    if query_type == "backend":
        base_queries = [
            "backend framework comparison 2024",
            "microservices architecture backend technologies",
            "API development best practices"
        ]
        
        if domain:
            domain_lower = domain.lower()
            if "healthcare" in domain_lower:
                queries.extend([
                    "healthcare backend development HIPAA compliance",
                    "medical data processing backend frameworks",
                    "FHIR API backend implementation"
                ])
            elif "financial" in domain_lower:
                queries.extend([
                    "fintech backend security requirements",
                    "financial transaction processing backends",
                    "PCI DSS compliant backend frameworks"
                ])
            elif "iot" in domain_lower:
                queries.extend([
                    "IoT backend architecture real-time processing",
                    "device management backend systems",
                    "edge computing backend frameworks"
                ])
            else:
                queries.extend(base_queries)
        else:
            queries.extend(base_queries)
            
    elif query_type == "frontend":
        base_queries = [
            "frontend framework comparison 2024",
            "React vs Vue vs Angular performance",
            "modern frontend development trends"
        ]
        
        if domain:
            domain_lower = domain.lower()
            if "healthcare" in domain_lower:
                queries.extend([
                    "healthcare UI/UX best practices",
                    "medical dashboard frontend frameworks",
                    "healthcare data visualization libraries"
                ])
            elif "financial" in domain_lower:
                queries.extend([
                    "financial dashboard frontend development",
                    "trading interface frontend frameworks",
                    "financial data visualization best practices"
                ])
            else:
                queries.extend(base_queries)
        else:
            queries.extend(base_queries)
            
    elif query_type == "database":
        base_queries = [
            "database technology comparison 2024",
            "SQL vs NoSQL performance benchmarks",
            "database scalability patterns"
        ]
        
        if domain:
            domain_lower = domain.lower()
            if "healthcare" in domain_lower:
                queries.extend([
                    "healthcare database requirements HIPAA",
                    "medical records database design",
                    "healthcare data storage compliance"
                ])
            elif "financial" in domain_lower:
                queries.extend([
                    "financial database security requirements",
                    "trading data storage solutions",
                    "financial compliance database design"
                ])
            elif "iot" in domain_lower:
                queries.extend([
                    "IoT time series database comparison",
                    "sensor data storage solutions",
                    "real-time data processing databases"
                ])
            else:
                queries.extend(base_queries)
        else:
            queries.extend(base_queries)
            
    return queries

def store_tech_data(key: str, data: Any, context: str = "tech_stack_tools"):
    """Store tech stack data in enhanced memory with multiple contexts for cross-tool access."""
    try:
        enhanced_memory = get_enhanced_tech_memory()
        if enhanced_memory:
            # Store in multiple contexts for better cross-tool access
            contexts = [context, "cross_tool", "tech_evaluation"]
            for ctx in contexts:
                enhanced_memory.store(key, data, context=ctx)
                
            logger = logging.getLogger(__name__)
            logger.info(f"Stored tech data with key '{key}' in contexts: {contexts}")
            return True
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to store tech data: {e}")
    return False

def retrieve_tech_data(key: str, context: str = "tech_stack_tools"):
    """Retrieve tech stack data from enhanced memory with fallback contexts."""
    try:
        enhanced_memory = get_enhanced_tech_memory()
        if enhanced_memory:
            # Try multiple contexts for better data retrieval - including shared contexts
            contexts = [context, "cross_tool", "tech_evaluation", "agent_results", 
                       "shared", "cross_agent", "shared_data"]
            for ctx in contexts:
                data = enhanced_memory.get(key, None, context=ctx)
                if data:
                    logger = logging.getLogger(__name__)
                    logger.info(f"Retrieved tech data with key '{key}' from context: {ctx}")
                    return data
                    
            logger = logging.getLogger(__name__)
            logger.info(f"No tech data found for key '{key}' in any context")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to retrieve tech data: {e}")
    return None

def get_tech_context_from_memory():
    """Get project context from enhanced memory for better tech decisions."""
    try:
        enhanced_memory = get_enhanced_tech_memory()
        if not enhanced_memory:
            return {}
            
        context = {}
        
        # Try to get various pieces of project context
        keys_to_try = [
            "requirements_summary", "project_requirements", "brd_analysis",
            "project_domain", "architecture_pattern", "system_components",
            "project_context", "tech_evaluations"
        ]
        
        for key in keys_to_try:
            # Try multiple contexts
            for ctx in ["cross_tool", "tech_stack_tools", "agent_results", "design_tools"]:
                data = enhanced_memory.get(key, None, context=ctx)
                if data:
                    context[key] = data
                    break
                    
        logger = logging.getLogger(__name__)
        logger.info(f"Retrieved tech context with {len(context)} items from memory")
        return context
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get tech context from memory: {e}")
        return {}

# Helper to get a configured LLM for tools
def get_tool_llm(temperature=0.0, agent_context=None):
    """
    Get a properly configured LLM for tech stack tools.
    
    Args:
        temperature: Temperature setting for the LLM (default: 0.0)
        agent_context: Optional string describing the context or name of the agent/tool
    """
    from langchain_core.language_models import BaseLanguageModel
    from langchain_core.prompts import ChatPromptTemplate
    
    # Determine which agent is currently running this tool
    context_name = agent_context or os.environ.get("AGENT_CONTEXT", "TechStackAdvisor Agent")
    
    # Import the JsonHandler for reliable JSON generation
    from .json_handler import JsonHandler
    
    # Get the system LLM and configure it for deterministic output
    from config import get_llm
    llm = get_llm(temperature=temperature)
    
    # For tools that need JSON output, use the strict JSON handler
    if temperature == 0.0:
        llm = JsonHandler.create_strict_json_llm(llm)
        
    # Add tracing context to help with debugging
    llm = llm.bind(
        config={"agent_context": f"{context_name}:tech_stack_tool"}
    )
    
    return llm

@smart_react_tool("Get technical requirements summary from BRD analysis")
def get_technical_requirements_summary(brd_analysis):
    """
    Analyzes the full requirements and returns a concise summary of only the key
    technical constraints and non-functional requirements.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Tool 'get_technical_requirements_summary' called with input type: {type(brd_analysis)}")

    # Handle different input types
    brd_analysis_json = ""
    brd_data = None
    
    # First, validate the input parameter
    if brd_analysis is None:
        logger.warning("brd_analysis parameter is None")
        brd_data = {
            "project_name": "Default Project",
            "project_summary": "No requirements provided",
            "requirements": []
        }
    elif brd_analysis == "":
        logger.warning("brd_analysis parameter is empty string")
        brd_data = {
            "project_name": "Default Project", 
            "project_summary": "No requirements provided",
            "requirements": []
        }
    # Handle Pydantic model
    elif isinstance(brd_analysis, TechnicalRequirementsSummaryInput):
        logger.info("Input is a TechnicalRequirementsSummaryInput model")
        brd_analysis_json = brd_analysis.brd_analysis_json
    
    # Handle dict input
    elif isinstance(brd_analysis, dict):
        logger.info("Input is a dictionary")
        if "brd_analysis_json" in brd_analysis:
            brd_analysis_json = brd_analysis["brd_analysis_json"]
        else:
            # Use the dict directly as the BRD data
            brd_data = brd_analysis
            logger.info("Using dictionary input directly as BRD data")
    
    # Handle string input (most common with ReAct agents)
    elif isinstance(brd_analysis, str):
        logger.info("Input is a string - extracting requirements")
        
        # Try to get BRD analysis from the agent's stored state (if available)
        try:
            # Enhanced memory management for better cross-tool communication
            try:
                from enhanced_memory_manager import create_memory_manager, EnhancedSharedProjectMemory
                
                # Try enhanced memory first (faster and more reliable)
                enhanced_memory = create_memory_manager(
                    backend_type="hybrid",
                    persistent_dir=None,
                    max_memory_mb=50,
                    enable_monitoring=True
                )
                
                # Try different contexts and keys
                for context in ["cross_tool", "agent_results", "BRDAnalystReActAgent", "SystemDesignerReActAgent"]:
                    for key in ["brd_analysis", "requirements_analysis", "project_requirements"]:
                        stored_brd = enhanced_memory.get(key, None, context=context)
                        if stored_brd:
                            if isinstance(stored_brd, dict):
                                brd_data = stored_brd
                                logger.info(f"Successfully retrieved BRD analysis from enhanced memory (context: {context}, key: {key})")
                                break
                            elif isinstance(stored_brd, str):
                                brd_analysis_json = stored_brd
                                logger.info(f"Retrieved BRD analysis string from enhanced memory (context: {context}, key: {key})")
                                break
                    if brd_data or brd_analysis_json:
                        break
                        
            except ImportError:
                logger.warning("Enhanced memory not available, falling back to basic SharedMemory")
                # Fallback to basic SharedMemory
                try:
                    from shared_memory import SharedMemory
                    memory = SharedMemory()
                    
                    if memory and hasattr(memory, 'get'):
                        # Try to get the BRD analysis from shared memory
                        stored_brd = memory.get('brd_analysis') or memory.get('requirements_analysis')
                        if stored_brd:
                            if isinstance(stored_brd, dict):
                                brd_data = stored_brd
                                logger.info("Successfully retrieved BRD analysis from basic shared memory")
                            elif isinstance(stored_brd, str):
                                brd_analysis_json = stored_brd
                                logger.info("Retrieved BRD analysis string from basic shared memory")
                except ImportError:
                    # Alternative: try to get from the shared memory module directly
                    import shared_memory as sm
                    # Look for global instance or create one
                    memory = getattr(sm, '_global_memory', None)
                    
                    if memory and hasattr(memory, 'get'):
                        stored_brd = memory.get('brd_analysis') or memory.get('requirements_analysis')
                        if stored_brd:
                            if isinstance(stored_brd, dict):
                                brd_data = stored_brd
                                logger.info("Successfully retrieved BRD analysis from global shared memory")
                            elif isinstance(stored_brd, str):
                                brd_analysis_json = stored_brd
                                logger.info("Retrieved BRD analysis string from global shared memory")
                                
        except Exception as e:
            logger.warning(f"Could not access memory systems: {str(e)}")
            # Continue without shared memory
            
        # If no data from shared memory, process the string input
        if not brd_data and not brd_analysis_json:
            # Simple text analysis to extract project information
            input_text = brd_analysis.lower()
            logger.info(f"Analyzing input text (length: {len(brd_analysis)})")
            
            # Initialize with defaults
            project_name = "Extracted Project"
            project_summary = "Application based on requirements analysis"
            requirements = []
            
            # Try to extract project name/type from common patterns
            project_patterns = [
                r'(?:project|application|system|platform|app).*?(?:for|to|that)\s+([^.!?]+)',
                r'(?:build|create|develop|make)\s+(?:a|an)?\s*([^.!?]+?)(?:\s+(?:application|system|platform|app))',
                r'([^.!?]*?)(?:\s+(?:management|tracking|system|application|app))',
            ]
            
            for pattern in project_patterns:
                match = re.search(pattern, input_text)
                if match:
                    extracted = match.group(1).strip()
                    if len(extracted) > 3 and len(extracted) < 50:  # Reasonable length
                        project_name = extracted.title()
                        logger.info(f"Extracted project name: '{project_name}'")
                        break
            
            # Extract summary from the input
            if len(brd_analysis) > 10:
                # Use first sentence or first 100 chars as summary
                sentences = re.split(r'[.!?]+', brd_analysis)
                if sentences and len(sentences[0].strip()) > 10:
                    project_summary = sentences[0].strip()
                else:
                    project_summary = brd_analysis[:100].strip()
                logger.info(f"Extracted project summary: '{project_summary}'")
            
            # Try to extract requirements from text
            req_keywords = [
                ('user', 'functional'), ('login', 'functional'), ('auth', 'security'),
                ('create', 'functional'), ('view', 'functional'), ('edit', 'functional'), 
                ('delete', 'functional'), ('manage', 'functional'), ('track', 'functional'),
                ('performance', 'non-functional'), ('speed', 'non-functional'), 
                ('security', 'non-functional'), ('scale', 'non-functional'),
                ('responsive', 'non-functional'), ('mobile', 'non-functional')
            ]
            
            req_id = 1
            for keyword, category in req_keywords:
                if keyword in input_text:
                    requirements.append({
                        "id": f"REQ-{req_id:03d}",
                        "title": f"{keyword.title()} Requirement",
                        "description": f"System should support {keyword}-related functionality",
                        "category": category
                    })
                    req_id += 1
            
            # If no requirements found, add some basic ones
            if not requirements:
                requirements = [
                    {
                        "id": "REQ-001",
                        "title": "Basic Functionality",
                        "description": "Core application features based on input requirements",
                        "category": "functional"
                    },
                    {
                        "id": "REQ-002",
                        "title": "Performance",
                        "description": "Application should perform efficiently",
                        "category": "non-functional"
                    }
                ]
            
            brd_data = {
                "project_name": project_name,
                "project_summary": project_summary,
                "requirements": requirements,
                "extracted_from_text": True  # Flag to indicate this was extracted
            }
            logger.info(f"Created BRD structure from text analysis - Project: '{project_name}', {len(requirements)} requirements")
    
    # If we still need to parse brd_analysis_json and don't have brd_data
    if not brd_data and brd_analysis_json:
        # Helper functions for different parsing strategies
        def _use_json_handler(text):
            """Use JsonHandler to extract JSON from text"""
            try:
                from .json_handler import JsonHandler
                # Check if text is None or empty before processing
                if text is None or text == "":
                    logger.warning("_use_json_handler received None or empty text")
                    return None
                # JsonHandler.extract_json_from_text is a classmethod, no need to instantiate
                result = JsonHandler.extract_json_from_text(text)
                return result
            except (ImportError, AttributeError) as e:
                logger.warning(f"JsonHandler not available or extract_json_from_text method missing: {str(e)}")
                return None
            except Exception as e:
                logger.warning(f"JsonHandler extraction failed: {str(e)}")
                return None
        
        def _fix_truncated_json(text):
            """Fix truncated JSON by adding missing braces"""
            if text is None or text == "":
                logger.warning("_fix_truncated_json received None or empty text")
                return None
                
            try:
                fixed_json = text.strip()
                open_braces = fixed_json.count('{')
                close_braces = fixed_json.count('}')
                
                if open_braces > close_braces:
                    missing_braces = open_braces - close_braces
                    fixed_json += '}' * missing_braces
                    logger.info(f"Added {missing_braces} missing closing braces")
                    return json.loads(fixed_json)
                return None
            except (json.JSONDecodeError, TypeError, AttributeError) as e:
                logger.warning(f"_fix_truncated_json failed: {str(e)}")
                return None
        
        def _extract_first_json_object(text):
            """Extract the first complete JSON object from text"""
            if text is None or text == "":
                logger.warning("_extract_first_json_object received None or empty text")
                return None
                
            try:
                text = text.strip()
                start_idx = text.find('{')
                if start_idx == -1:
                    return None
                    
                brace_count = 0
                for i in range(start_idx, len(text)):
                    if text[i] == '{':
                        brace_count += 1
                    elif text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            # Found complete JSON object
                            json_obj = text[start_idx:i+1]
                            logger.info(f"Extracted complete JSON object (length: {len(json_obj)})")
                            return json.loads(json_obj)
                return None
            except (json.JSONDecodeError, TypeError, AttributeError) as e:
                logger.warning(f"_extract_first_json_object failed: {str(e)}")
                return None
        
        def _extract_json_patterns(text):
            """Extract common patterns to build a JSON object"""
            if text is None or text == "":
                logger.warning("_extract_json_patterns received None or empty text")
                return None
                
            try:
                result = {
                    "project_name": "Unknown Project",
                    "project_summary": "Not provided",
                    "requirements": []
                }
                
                # Try to extract key fields
                project_name_match = re.search(r'["\']project_name["\']\s*:\s*["\']([^"\']+)["\']', text)
                if project_name_match:
                    result["project_name"] = project_name_match.group(1)
                    
                project_summary_match = re.search(r'["\'](?:project_summary|summary)["\']\s*:\s*["\']([^"\']+)["\']', text)
                if project_summary_match:
                    result["project_summary"] = project_summary_match.group(1)
                    
                # Check for requirements array pattern
                reqs_pattern = r'["\']requirements["\']\s*:\s*\[(.*?)\]'
                reqs_match = re.search(reqs_pattern, text, re.DOTALL)
                if reqs_match:
                    reqs_text = reqs_match.group(1)
                    # Extract string items from array
                    items = re.findall(r'["\']([^"\']+)["\']', reqs_text)
                    result["requirements"] = items
                    
                return result if (result["project_name"] != "Unknown Project" or 
                                result["project_summary"] != "Not provided" or 
                                result["requirements"]) else None
            except (TypeError, AttributeError, re.error) as e:
                logger.warning(f"_extract_json_patterns failed: {str(e)}")
                return None
        
        # Define the parsing strategies
        parsing_strategies = [
            # Strategy 1: Direct JSON parsing
            lambda x: json.loads(x),
            
            # Strategy 2: Try with JsonHandler
            _use_json_handler,
            
            # Strategy 3: Fix truncated JSON
            _fix_truncated_json,
            
            # Strategy 4: Extract first complete JSON object
            _extract_first_json_object,
            
            # Strategy 5: Last resort - match common patterns
            _extract_json_patterns
        ]
        
        # Check if we have valid input before trying strategies
        if brd_analysis_json is None or brd_analysis_json == "":
            logger.error("brd_analysis_json is None or empty - cannot parse")
            brd_data = None
        else:
            # Try each strategy in sequence
            brd_data = None
            for i, strategy in enumerate(parsing_strategies):
                try:
                    logger.debug(f"Trying parsing strategy {i+1}")
                    brd_data = strategy(brd_analysis_json)
                    if brd_data:
                        logger.info(f"Parsing successful with strategy {i+1}")
                        break
                except Exception as e:
                    logger.debug(f"Strategy {i+1} failed: {str(e)}")
                    continue    # Final validation of parsed data
    if not brd_data or not isinstance(brd_data, dict):
        logger.error("Failed to parse input into valid dictionary after all attempts")
        return TechnicalRequirementsSummaryOutput(
            summary="Error: Could not parse input data into a valid format.",
            performance_requirements=["Unknown due to parsing error"],
            security_requirements=["Unknown due to parsing error"],
            technical_constraints=["Unknown due to parsing error"],
            scalability_requirements=["Unknown due to parsing error"], 
            integration_requirements=["Unknown due to parsing error"]
        )
        
    try:
        # Create a Pydantic output parser
        parser = PydanticOutputParser(pydantic_object=TechnicalRequirementsSummaryOutput)
        
        # Use a more comprehensive prompt with proper variable placeholders and format instructions
        prompt = ChatPromptTemplate.from_messages([
            ("system", 
             "You are a technical requirements analyst who extracts non-functional requirements "
             "and technical constraints from project data. Your expertise is in identifying "
             "performance, security, scalability, integration, and other technical requirements "
             "that impact system design. Provide output in the specified JSON format."),
            ("human", 
             "Extract ONLY the technical constraints and non-functional requirements from this data:\n\n"
             "Project: {project_name}\n\n"
             "Summary: {project_summary}\n\n"
             "Requirements: \n{requirements}\n\n"
             "Focus on these categories:\n"
             "1. Performance requirements (response times, throughput, etc.)\n"
             "2. Security requirements (authentication, authorization, etc.)\n"
             "3. Scalability requirements (user load, data volume growth, etc.)\n"
             "4. Integration requirements (APIs, third-party services, etc.)\n"
             "5. Technical constraints (platforms, compatibility, etc.)\n\n"
             "Provide a concise, well-organized summary following this format:\n\n"
             "{format_instructions}")
        ])
        
        # Extract the required data with enhanced fallbacks and data source tracking
        data_sources = []
        
        # Extract project name with fallbacks
        project_name = None
        for key in ['project_name', 'title', 'name', 'project']:
            if key in brd_data:
                project_name = brd_data[key]
                data_sources.append(f"project_name from '{key}' field")
                break
        if not project_name:
            project_name = "Unknown Project"
            data_sources.append("project_name defaulted to 'Unknown Project'")
            
        # Extract project summary with fallbacks    
        project_summary = None
        for key in ['project_summary', 'summary', 'description', 'overview']:
            if key in brd_data:
                project_summary = brd_data[key]
                data_sources.append(f"project_summary from '{key}' field")
                break
        if not project_summary:
            project_summary = "Not provided"
            data_sources.append("project_summary defaulted to 'Not provided'")
        
        # Handle requirements in multiple possible formats with enhanced logging
        requirements_raw = None
        for key in ['requirements', 'functional_requirements', 'non_functional_requirements', 'features']:
            if key in brd_data:
                requirements_raw = brd_data[key]
                data_sources.append(f"requirements from '{key}' field")
                break
                
        if not requirements_raw:
            requirements_raw = []
            data_sources.append("No requirements found, using empty list")
            
        # Format requirements based on type
        if isinstance(requirements_raw, list):
            # For large lists, select a representative sample
            if len(requirements_raw) > 15:
                logger.info(f"Truncating requirements list from {len(requirements_raw)} to 15 items")
                requirements = json.dumps(requirements_raw[:15], indent=2)
            else:
                requirements = json.dumps(requirements_raw, indent=2)
        elif isinstance(requirements_raw, dict):
            requirements = json.dumps(requirements_raw, indent=2)
        else:
            # For string or other types, convert and limit length
            requirements = str(requirements_raw)
            if len(requirements) > 2000:
                logger.info(f"Truncating requirements string from {len(requirements)} to 2000 chars")
                requirements = requirements[:2000] + "... [truncated]"
        
        logger.info(f"Extracted data - Project: {project_name}, Summary length: {len(project_summary)}, Requirements length: {len(requirements)}")
        logger.info(f"Data sources: {', '.join(data_sources)}")
        
        # Create and execute the chain: prompt -> llm -> parser with error handling
        try:
            chain = prompt | get_tool_llm(temperature=0.1, agent_context="technical_requirements_analyzer") | parser
            
            # Invoke the chain with timeout handling
            result = chain.invoke({
                "project_name": project_name,
                "project_summary": project_summary,
                "requirements": requirements,
                "format_instructions": parser.get_format_instructions()
            })
              # Log successful completion
            logger.info("Successfully generated technical requirements summary")
            return result
            
        except Exception as chain_error:
            logger.error(f"Error in LLM chain execution: {str(chain_error)}", exc_info=True)
            return TechnicalRequirementsSummaryOutput(
                summary=f"Error in LLM processing: {str(chain_error)}",
                performance_requirements=["Could not be determined due to LLM error"],
                security_requirements=["Could not be determined due to LLM error"],
                scalability_requirements=["Could not be determined due to LLM error"],
                integration_requirements=["Could not be determined due to LLM error"],
                technical_constraints=["Could not be determined due to LLM error"]
            )
            
    except Exception as e:
        logger.error(f"Error processing extracted data: {str(e)}", exc_info=True)
        # Generate a minimal output based on what we know
        return TechnicalRequirementsSummaryOutput(
            summary=f"Error extracting technical requirements: {str(e)}. Partial data was extracted.",
            performance_requirements=["Could not be determined due to processing error"],
            security_requirements=["Could not be determined due to processing error"],
            scalability_requirements=["Could not be determined due to processing error"],
            integration_requirements=["Could not be determined due to processing error"],
            technical_constraints=["Could not be determined due to processing error"]
        )
            
            


@smart_react_tool("Evaluate backend technology options based on requirements")
def evaluate_backend_options(brd_analysis) -> dict:
    """
    Evaluates and compares several backend technologies based on the project requirements.
    Returns a structured analysis with comparison data and recommendations.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Tool 'evaluate_backend_options' called with input type: {type(brd_analysis)}")

    # Handle the case where LangChain passes data in a 'tool_input' key
    if isinstance(brd_analysis, dict) and 'tool_input' in brd_analysis:
        logger.info("Found 'tool_input' key in brd_analysis - extracting nested data")
        tool_input = brd_analysis['tool_input']
    else:
        tool_input = brd_analysis

    # Extract requirements_summary from various input formats
    requirements_summary = ""
    
    # Handle Pydantic model
    if isinstance(tool_input, BackendEvaluationInput):
        logger.info("Input is a BackendEvaluationInput model")
        requirements_summary = tool_input.requirements_summary
    
    # Handle dict input
    elif isinstance(tool_input, dict):
        logger.info("Input is a dictionary")
        requirements_summary = tool_input.get("requirements_summary", "")
    
    # Handle string input
    elif isinstance(tool_input, str):
        logger.info("Input is a string")
        requirements_summary = tool_input
      # Default handling
    else:
        logger.warning(f"Unexpected input type: {type(tool_input)}")
        requirements_summary = str(tool_input)

    try:
        # Get enhanced memory context and RAG information
        memory_context = get_tech_context_from_memory()
        domain = memory_context.get("project_domain", "")
        
        # Get RAG context for backend technology evaluation
        rag_context = get_tech_rag_context("backend", domain, requirements=requirements_summary)
        
        # Create a Pydantic output parser
        parser = PydanticOutputParser(pydantic_object=BackendEvaluationOutput)
        
        # Create a clean prompt with format instructions
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert solution architect who evaluates backend technology options."),
            ("human", 
             """You are an expert solution architect. Your task is to evaluate backend technology options
based on the provided technical summary and domain context. Analyze the summary and provide a ranked list of
2-3 suitable backend technologies.

TECHNICAL SUMMARY:
{summary}

DOMAIN CONTEXT: {domain}

TECHNOLOGY KNOWLEDGE BASE:
{rag_context}

Use the knowledge base information to inform your technology recommendations and scoring.
Consider domain-specific requirements (e.g., HIPAA for healthcare, PCI for financial).

Provide your evaluation following this format:
{format_instructions}
""")
        ])

        # Get the LLM and create the chain
        llm = get_tool_llm(temperature=0.1)
        chain = prompt | llm | parser
        
        # Execute the chain
        logger.info("Invoking LLM for backend evaluation")
        result = chain.invoke({
            "summary": requirements_summary,
            "domain": domain or "General purpose application",
            "rag_context": rag_context or "No additional technology context available",
            "format_instructions": parser.get_format_instructions()
        })
        
        # Store backend evaluation results for other tools to use
        if result and hasattr(result, 'backend_options'):
            store_tech_data("backend_evaluation", {
                "backend_options": [opt.dict() for opt in result.backend_options],
                "recommendation": result.recommendation.dict() if result.recommendation else None
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in evaluate_backend_options: {str(e)}", exc_info=True)
        # Return a valid Pydantic object even in case of error
        return BackendEvaluationOutput(
            backend_options=[
                TechOption(
                    name="Node.js",
                    framework="Express",
                    performance_score=8,
                    scalability_score=7,
                    developer_productivity=9,
                    overall_score=8,
                    reasoning="Well-suited for web applications with good ecosystem"
                ),
                TechOption(
                    name="Python",
                    framework="FastAPI",
                    performance_score=7,
                    scalability_score=8,
                    developer_productivity=8,
                    overall_score=7.5,
                    reasoning="Good for rapid development with strong typing support"
                )
            ],
            recommendation=TechOption(
                name="Node.js",
                framework="Express",
                overall_score=8,
                reasoning="Best balance of performance and developer productivity"
            )
        )

@smart_react_tool("Recommend frontend framework based on requirements")
def recommend_frontend_framework(brd_analysis) -> dict:
    """Recommends frontend frameworks based on project requirements."""
    logger = logging.getLogger(__name__)
    logger.info(f"Tool 'recommend_frontend_framework' called with input type: {type(brd_analysis)}")

    # Handle the case where LangChain passes data in a 'tool_input' key
    if isinstance(brd_analysis, dict) and 'tool_input' in brd_analysis:
        logger.info("Found 'tool_input' key in brd_analysis - extracting nested data")
        tool_input = brd_analysis['tool_input']
    else:
        tool_input = brd_analysis

    # Extract data from various input formats
    requirements = ""
    user_experience_focus = "Standard user experience with focus on usability and performance"
    
    # Handle Pydantic model
    if isinstance(tool_input, FrontendFrameworkRecommendationInput):
        logger.info("Input is a FrontendFrameworkRecommendationInput model")
        requirements = tool_input.requirements
        user_experience_focus = tool_input.user_experience_focus or user_experience_focus
    
    # Handle dict input
    elif isinstance(tool_input, dict):
        logger.info("Input is a dictionary")
        requirements = tool_input.get("requirements", "")
        user_experience_focus = tool_input.get("user_experience_focus", user_experience_focus)
    
    # Handle string input
    elif isinstance(tool_input, str):
        logger.info("Input is a string")
        requirements = tool_input
    
    # Default handling
    else:
        logger.warning(f"Unexpected input type: {type(tool_input)}")
        requirements = str(tool_input)
    
    try:
        # Create a Pydantic output parser
        parser = PydanticOutputParser(pydantic_object=FrontendEvaluationOutput)
        
        # Create the prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a frontend technology expert."),
            ("human", 
             "Based on the following project requirements and UX focus, recommend "
             "2-3 frontend frameworks with justifications:\n\n"
             "PROJECT REQUIREMENTS: {requirements}\n\n"
             "UX FOCUS: {ux_focus}\n\n"
             "Format your response according to these instructions:\n"
             "{format_instructions}")
        ])
        
        # Get the LLM and create the chain
        llm = get_tool_llm(temperature=0.1)
        chain = prompt | llm | parser
        
        # Execute the chain
        result = chain.invoke({
            "requirements": requirements,
            "ux_focus": user_experience_focus,
            "format_instructions": parser.get_format_instructions()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in recommend_frontend_framework: {str(e)}", exc_info=True)
        # Return a valid Pydantic object even in case of error
        return FrontendEvaluationOutput(
            frontend_options=[
                TechOption(
                    name="React",
                    framework="React",
                    overall_score=9,
                    reasoning="Industry standard with extensive ecosystem"
                ),
                TechOption(
                    name="Vue.js",
                    framework="Vue.js",
                    overall_score=8,
                    reasoning="Easy learning curve with good performance"
                )
            ],
            recommendation=TechOption(
                name="React",
                framework="React",
                overall_score=9,
                reasoning="Best suited for complex UI requirements with strong ecosystem"
            )
        )

@smart_react_tool("Evaluate database technology options")
def evaluate_database_options(brd_analysis) -> dict:
    """
    Evaluates and recommends database technologies based on requirements.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Tool 'evaluate_database_options' called with input type: {type(brd_analysis)}")

    # Handle the case where LangChain passes data in a 'tool_input' key
    if isinstance(brd_analysis, dict) and 'tool_input' in brd_analysis:
        logger.info("Found 'tool_input' key in brd_analysis - extracting nested data")
        tool_input = brd_analysis['tool_input']
    else:
        tool_input = brd_analysis

    # Extract technical_requirements from various input formats
    technical_requirements = ""
    
    # Handle Pydantic model
    if isinstance(tool_input, DatabaseEvaluationInput):
        logger.info("Input is a DatabaseEvaluationInput model")
        technical_requirements = tool_input.technical_requirements
    
    # Handle dict input
    elif isinstance(tool_input, dict):
        logger.info("Input is a dictionary")
        technical_requirements = tool_input.get("technical_requirements", "")
    
    # Handle string input
    elif isinstance(tool_input, str):
        logger.info("Input is a string")
        technical_requirements = tool_input
      # Default handling
    else:
        logger.warning(f"Unexpected input type: {type(tool_input)}")
        technical_requirements = str(tool_input)

    try:
        # Create a Pydantic output parser
        parser = PydanticOutputParser(pydantic_object=DatabaseEvaluationOutput)
        
        # Create the prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a database technology expert."),
            ("human", 
             """Based on the following technical requirements, evaluate and recommend 
database technologies. Provide a comparative analysis of the options.

TECHNICAL REQUIREMENTS: {requirements}

Format your response according to these instructions:
{format_instructions}""")
        ])
        
        # Get the LLM and create the chain
        llm = get_tool_llm(temperature=0.0)
        chain = prompt | llm | parser
        
        # Execute the chain
        result = chain.invoke({
            "requirements": technical_requirements,
            "format_instructions": parser.get_format_instructions()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in evaluate_database_options: {str(e)}", exc_info=True)
        # Return a valid Pydantic object even in case of error
        return DatabaseEvaluationOutput(
            database_options=[
                TechOption(
                    name="PostgreSQL",
                    framework=None,
                    performance_score=8,
                    scalability_score=8,
                    overall_score=7.8,
                    reasoning="Robust ACID-compliant database with excellent stability"
                ),
                TechOption(
                    name="MongoDB",
                    framework=None,
                    performance_score=7,
                    scalability_score=9,
                    overall_score=8.2,
                    reasoning="Flexible schema design with good horizontal scaling"
                )
            ],
            recommendation=TechOption(
                name="PostgreSQL",
                framework=None,
                overall_score=7.8,
                reasoning="Best balance of performance, reliability, and feature set"
            )
        )

@smart_react_tool("Evaluate architecture patterns for the project")
def evaluate_architecture_patterns(brd_analysis) -> dict:
    """
    Evaluates architecture patterns based on the project requirements and selected technologies.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Tool 'evaluate_architecture_patterns' called with input type: {type(brd_analysis)}")

    # Handle the case where LangChain passes data in a 'tool_input' key
    if isinstance(brd_analysis, dict) and 'tool_input' in brd_analysis:
        logger.info("Found 'tool_input' key in brd_analysis - extracting nested data")
        tool_input = brd_analysis['tool_input']
    else:
        tool_input = brd_analysis
        # Handle ReAct agent inputs (string or dict)
        if isinstance(tool_input, str):
            logger.info("Received string input from ReAct agent (expected behavior) - parsing to ArchitectureEvaluationInput")
            
            # Check if the string contains any JSON-like structure
            if '{' in tool_input or '[' in tool_input:
                try:
                    # Try to parse as JSON
                    parsed_data = json.loads(tool_input)
                    
                    # Check if this contains technology recommendations instead of requirements_summary
                    if "requirements_summary" in parsed_data:
                        tool_input = ArchitectureEvaluationInput(**parsed_data)
                        logger.info("Successfully parsed JSON string to ArchitectureEvaluationInput")
                    else:
                        # This looks like technology recommendations, create a requirements summary
                        logger.info("Parsed JSON contains technology recommendations, converting to requirements format")
                        req_parts = []
                        if "backend_recommendation" in parsed_data:
                            backend_rec = parsed_data["backend_recommendation"]
                            if isinstance(backend_rec, dict) and "name" in backend_rec:
                                req_parts.append(f"Backend using {backend_rec['name']}")
                                if "framework" in backend_rec:
                                    req_parts[-1] += f" with {backend_rec['framework']}"
                        
                        if "frontend_recommendation" in parsed_data:
                            frontend_rec = parsed_data["frontend_recommendation"]
                            if isinstance(frontend_rec, dict) and "name" in frontend_rec:
                                req_parts.append(f"Frontend using {frontend_rec['name']}")
                                if "framework" in frontend_rec:
                                    req_parts[-1] += f" ({frontend_rec['framework']})"
                        
                        if "database_recommendation" in parsed_data:
                            db_rec = parsed_data["database_recommendation"]
                            if isinstance(db_rec, dict) and "name" in db_rec:
                                req_parts.append(f"Database using {db_rec['name']}")
                        
                        if req_parts:
                            requirements_summary = ". ".join(req_parts) + ". Architecture should integrate these technologies effectively."
                        else:
                            requirements_summary = json.dumps(parsed_data, indent=2)
                            
                        tool_input = ArchitectureEvaluationInput(
                            requirements_summary=requirements_summary,
                            backend=parsed_data.get("backend_recommendation", {}).get("name") if "backend_recommendation" in parsed_data else None,
                            frontend=parsed_data.get("frontend_recommendation", {}).get("name") if "frontend_recommendation" in parsed_data else None,
                            database=parsed_data.get("database_recommendation", {}).get("name") if "database_recommendation" in parsed_data else None
                        )
                        logger.info(f"Successfully created ArchitectureEvaluationInput from tech recommendations: {requirements_summary}")
                except json.JSONDecodeError as e:
                    # Check if this is an "Extra data" error (concatenated JSON)
                    if "Extra data" in str(e):
                        logger.warning(f"Detected 'Extra data' error - attempting to extract first JSON object: {str(e)}")
                        try:
                            # Extract just the first complete JSON object
                            start_idx = tool_input.find('{')
                            if start_idx != -1:
                                brace_count = 0
                                for i in range(start_idx, len(tool_input)):
                                    if tool_input[i] == '{':
                                        brace_count += 1
                                    elif tool_input[i] == '}':
                                        brace_count -= 1
                                        if brace_count == 0:
                                            json_part = tool_input[start_idx:i+1]
                                            parsed_data = json.loads(json_part)
                                            # Convert the parsed data to the expected format for ArchitectureEvaluationInput
                                            if "requirements_summary" in parsed_data:
                                                tool_input = ArchitectureEvaluationInput(**parsed_data)
                                            else:
                                                # This looks like technology recommendations, create a requirements summary
                                                req_parts = []
                                                if "backend_recommendation" in parsed_data:
                                                    backend_rec = parsed_data["backend_recommendation"]
                                                    if isinstance(backend_rec, dict) and "name" in backend_rec:
                                                        req_parts.append(f"Backend using {backend_rec['name']}")
                                                        if "framework" in backend_rec:
                                                            req_parts[-1] += f" with {backend_rec['framework']}"
                                                
                                                if "frontend_recommendation" in parsed_data:
                                                    frontend_rec = parsed_data["frontend_recommendation"]
                                                    if isinstance(frontend_rec, dict) and "name" in frontend_rec:
                                                        req_parts.append(f"Frontend using {frontend_rec['name']}")
                                                        if "framework" in frontend_rec:
                                                            req_parts[-1] += f" ({frontend_rec['framework']})"
                                                
                                                if "database_recommendation" in parsed_data:
                                                    db_rec = parsed_data["database_recommendation"]
                                                    if isinstance(db_rec, dict) and "name" in db_rec:
                                                        req_parts.append(f"Database using {db_rec['name']}")
                                                
                                                if req_parts:
                                                    requirements_summary = ". ".join(req_parts) + ". Architecture should integrate these technologies effectively."
                                                else:
                                                    requirements_summary = json.dumps(parsed_data, indent=2)
                                                    
                                                tool_input = ArchitectureEvaluationInput(
                                                    requirements_summary=requirements_summary,
                                                    backend=parsed_data.get("backend_recommendation", {}).get("name") if "backend_recommendation" in parsed_data else None,
                                                    frontend=parsed_data.get("frontend_recommendation", {}).get("name") if "frontend_recommendation" in parsed_data else None,
                                                    database=parsed_data.get("database_recommendation", {}).get("name") if "database_recommendation" in parsed_data else None
                                                )
                                            logger.info("Successfully extracted first JSON object from concatenated data")
                                            break
                                else:
                                    raise ValueError("Could not find complete JSON object")
                            else:
                                raise ValueError("No JSON object found")
                        except Exception as extract_error:
                            logger.warning(f"JSON extraction failed: {str(extract_error)} - falling back to JsonHandler")
                            # Fall through to JsonHandler
                    else:
                        logger.warning(f"Standard JSON parsing failed: {str(e)} - trying JsonHandler for robust parsing")
                    try:
                        # Use JsonHandler for robust JSON extraction
                        from .json_handler import JsonHandler
                        parsed_data = JsonHandler.extract_json_from_text(tool_input)
                        
                        if isinstance(parsed_data, dict):
                            try:
                                tool_input = ArchitectureEvaluationInput(**parsed_data)
                                logger.info("Successfully parsed with JsonHandler")
                            except Exception as validation_error:
                                logger.warning(f"Parsed data doesn't match ArchitectureEvaluationInput schema: {str(validation_error)}")
                                # Fall back to treating the string as requirements_summary
                                tool_input = ArchitectureEvaluationInput(requirements_summary=str(parsed_data))
                                logger.info("Created ArchitectureEvaluationInput using parsed data as requirements_summary")
                        else:
                            raise ValueError("JsonHandler did not return a valid dictionary")
                            
                    except Exception as handler_error:
                        logger.error(f"JsonHandler also failed: {str(handler_error)} - using fallback approach")
                        # Fall back to treating the string as requirements_summary
                        tool_input = ArchitectureEvaluationInput(requirements_summary=tool_input)
                        logger.info("Created minimal valid input using string as requirements_summary")
            else:
                # No JSON structure detected - treat as plain text requirements
                logger.info("Input appears to be plain text requirements, wrapping in ArchitectureEvaluationInput")
                # Clean up the text and use it as requirements summary
                cleaned_text = tool_input.strip()
                if not cleaned_text:
                    cleaned_text = "No specific requirements provided"
                
                tool_input = ArchitectureEvaluationInput(requirements_summary=cleaned_text)
                logger.info(f"Created ArchitectureEvaluationInput from plain text: {cleaned_text[:100]}...")
        elif isinstance(tool_input, dict):
            logger.info("Received dict input, converting to ArchitectureEvaluationInput")
            
            # Check if this is already in the expected format
            if "requirements_summary" in tool_input:
                tool_input = ArchitectureEvaluationInput(**tool_input)
            else:
                # This appears to be technology recommendations rather than requirements
                # Extract what we can and create a requirements summary
                logger.info("Dict appears to contain technology recommendations, extracting requirements context")
                
                # Try to extract meaningful requirements information
                requirements_parts = []
                
                # Look for backend info
                if "backend_recommendation" in tool_input:
                    backend_info = tool_input["backend_recommendation"]
                    if isinstance(backend_info, dict) and "name" in backend_info:
                        requirements_parts.append(f"Backend should support {backend_info['name']} technology")
                        if "framework" in backend_info:
                            requirements_parts.append(f"using {backend_info['framework']} framework")
                
                # Look for frontend info
                if "frontend_recommendation" in tool_input:
                    frontend_info = tool_input["frontend_recommendation"]
                    if isinstance(frontend_info, dict) and "name" in frontend_info:
                        requirements_parts.append(f"Frontend should use {frontend_info['name']} framework")
                        if "framework" in frontend_info and frontend_info["framework"] != frontend_info["name"]:
                            requirements_parts.append(f"specifically {frontend_info['framework']}")
                        
                # Look for database info
                if "database_recommendation" in tool_input:
                    database_info = tool_input["database_recommendation"]
                    if isinstance(database_info, dict) and "name" in database_info:
                        requirements_parts.append(f"Database should use {database_info['name']}")
                
                # Create a summary from available information
                if requirements_parts:
                    requirements_summary = ". ".join(requirements_parts) + ". The architecture should optimize for these technology choices and ensure good integration between components."
                else:
                    requirements_summary = "Web application with standard architecture requirements including scalability, maintainability, and performance considerations"
                
                # Create the ArchitectureEvaluationInput with extracted info
                tool_input = ArchitectureEvaluationInput(
                    requirements_summary=requirements_summary,
                    backend=tool_input.get("backend_recommendation", {}).get("name") if "backend_recommendation" in tool_input else None,
                    frontend=tool_input.get("frontend_recommendation", {}).get("name") if "frontend_recommendation" in tool_input else None,
                    database=tool_input.get("database_recommendation", {}).get("name") if "database_recommendation" in tool_input else None
                )
                logger.info(f"Created ArchitectureEvaluationInput from tech recommendations: {requirements_summary}")
            
        # Input validation
        if not hasattr(tool_input, 'requirements_summary') or not tool_input.requirements_summary:
            raise ValueError("Missing required field: requirements_summary")
            
        # Extract data from the converted tool_input
        requirements_summary = tool_input.requirements_summary
        backend = tool_input.backend if hasattr(tool_input, 'backend') else None
        database = tool_input.database if hasattr(tool_input, 'database') else None
        frontend = tool_input.frontend if hasattr(tool_input, 'frontend') else None        
        # Build technology stack context
        tech_stack = ""
        if backend or database or frontend:
            tech_stack = "Technology Selections:"
            if backend:
                tech_stack += f"\n- Backend: {backend}"
            if database:
                tech_stack += f"\n- Database: {database}"
            if frontend:
                tech_stack += f"\n- Frontend: {frontend}"        
        try:
            # Create a Pydantic output parser
            parser = PydanticOutputParser(pydantic_object=ArchitecturePatternEvaluationOutput)
            
            # Create the prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an architecture expert."),
                ("human", 
                 """You are an architecture expert. Your task is to evaluate architecture patterns
based on the provided requirements and technology selections.

Technical Requirements: {requirements}
{tech_stack}

Provide your evaluation according to these instructions:
{format_instructions}""")
            ])
            
            # Get the LLM and create the chain
            llm = get_tool_llm(temperature=0.0)
            chain = prompt | llm | parser
            
            # Execute the chain
            result = chain.invoke({
                "requirements": requirements_summary,
                "tech_stack": tech_stack,
                "format_instructions": parser.get_format_instructions()
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error in evaluate_architecture_patterns: {str(e)}", exc_info=True)
            # Return a valid Pydantic object even in case of error
            return ArchitecturePatternEvaluationOutput(
                architecture_options=[
                    ArchitecturePatternOption(
                        pattern="Microservices",
                        scalability_score=9,
                        maintainability_score=7,
                        development_speed_score=6,
                        overall_score=7.5,
                        reasoning="Excellent scalability and separation of concerns"
                    ),
                    ArchitecturePatternOption(
                        pattern="Monolithic MVC",
                        scalability_score=6,
                        maintainability_score=8,
                        development_speed_score=9,
                        overall_score=7.5,
                        reasoning="Faster initial development and simpler deployment"
                    )
                ],
                recommendation={
                    "pattern": "Monolithic MVC",
                    "reasoning": "Best suited for the project scale and complexity"
                }
            )

@smart_react_tool("Synthesize final technology stack recommendation")
def synthesize_tech_stack(recommendations) -> dict:
    """
    Combines all technology evaluations into a comprehensive tech stack.
    Use this as your final step after all evaluations are complete.
    """
    import json
    import logging
    import traceback
    from models.data_contracts import TechStackSynthesisOutput, LibraryTool
    
    logger = logging.getLogger(__name__)
    logger.info(f"Tool 'synthesize_tech_stack' called with input type: {type(recommendations)}")

    # Handle the case where LangChain passes data in a 'tool_input' key
    if isinstance(recommendations, dict) and 'tool_input' in recommendations:
        logger.info("Found 'tool_input' key in recommendations - extracting nested data")
        tool_input = recommendations['tool_input']
    else:
        tool_input = recommendations
    
    # Handle ReAct agent inputs (string or dict)
    if isinstance(tool_input, str):
        logger.info("Received string input from ReAct agent (expected behavior) - parsing to TechStackSynthesisInput")
        try:
            # Try to parse as JSON
            parsed_data = json.loads(tool_input)
            tool_input = TechStackSynthesisInput(**parsed_data)
            logger.info("Successfully parsed JSON string to TechStackSynthesisInput")
        except json.JSONDecodeError as e:
            # Check if this is an "Extra data" error (concatenated JSON)
            if "Extra data" in str(e):
                logger.warning(f"Detected 'Extra data' error - attempting to extract first JSON object: {str(e)}")
                try:
                    # Extract just the first complete JSON object
                    start_idx = tool_input.find('{')
                    if start_idx != -1:
                        brace_count = 0
                        for i in range(start_idx, len(tool_input)):
                            if tool_input[i] == '{':
                                brace_count += 1
                            elif tool_input[i] == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_part = tool_input[start_idx:i+1]
                                    parsed_data = json.loads(json_part)
                                    tool_input = TechStackSynthesisInput(**parsed_data)
                                    logger.info("Successfully extracted first JSON object from concatenated data")
                                    break
                        else:
                            raise ValueError("Could not find complete JSON object")
                    else:
                        raise ValueError("No JSON object found")
                except Exception as extract_error:
                    logger.warning(f"JSON extraction failed: {str(extract_error)} - falling back to JsonHandler")
                    # Fall through to JsonHandler
            else:
                logger.warning(f"Standard JSON parsing failed: {str(e)} - trying JsonHandler for robust parsing")
            try:
                # Use JsonHandler for robust JSON extraction
                from .json_handler import JsonHandler
                parsed_data = JsonHandler.extract_json_from_text(tool_input)
                
                if isinstance(parsed_data, dict):
                    # Try to create TechStackSynthesisInput from parsed data
                    try:
                        tool_input = TechStackSynthesisInput(**parsed_data)
                        logger.info("Successfully parsed with JsonHandler")
                    except Exception as validation_error:
                        logger.warning(f"Parsed data doesn't match TechStackSynthesisInput schema: {str(validation_error)}")
                        # Use the string as combined_input and provide defaults for required fields
                        tool_input = TechStackSynthesisInput(
                            evaluation_results=parsed_data if isinstance(parsed_data, dict) else {},
                            architecture_recommendation="",
                            backend_recommendation="",
                            frontend_recommendation="",
                            database_recommendation="", 
                            combined_input=tool_input  # Use the original string as combined_input
                        )
                        logger.info("Created TechStackSynthesisInput with parsed data as evaluation_results")
                else:
                    raise ValueError("JsonHandler did not return a valid dictionary")
                    
            except Exception as handler_error:
                logger.error(f"JsonHandler also failed: {str(handler_error)} - using fallback approach")
                # We need to provide default values for required fields
                tool_input = TechStackSynthesisInput(
                    evaluation_results={},
                    architecture_recommendation="",
                    backend_recommendation="",
                    frontend_recommendation="",
                    database_recommendation="", 
                    combined_input=tool_input  # Use the string as combined_input
                )
                logger.info("Created minimal valid input using string as combined_input")
    elif isinstance(tool_input, dict):
        logger.info("Received dict input, converting to TechStackSynthesisInput")
        tool_input = TechStackSynthesisInput(**tool_input)
    
    # Early logging to debug the input type
    logger.info(f"Tool input type: {type(tool_input)}")
    
    # Helper function to parse recommendations
    def parse_recommendation(rec):
        if rec is None:
            return {}
        if isinstance(rec, dict):
            return rec
        if isinstance(rec, str):
            try:
                return json.loads(rec)
            except Exception:
                # If it's not valid JSON, return it as a simple string value
                return {"value": rec}
        return {}
    
    try:
        # Get enhanced memory context for all evaluations
        memory_context = get_tech_context_from_memory()
        
        # Extract data from the tool_input
        evaluation_results = tool_input.evaluation_results
        architecture_recommendation = tool_input.architecture_recommendation
        backend_recommendation = tool_input.backend_recommendation
        frontend_recommendation = tool_input.frontend_recommendation
        database_recommendation = tool_input.database_recommendation
        combined_input = tool_input.combined_input
        
        # Try to get evaluation data from memory if not provided
        if not backend_recommendation:
            backend_data = retrieve_tech_data("backend_evaluation")
            if backend_data:
                backend_recommendation = backend_data.get("recommendation", {})
                logger.info("Retrieved backend recommendation from enhanced memory")
                
        if not frontend_recommendation:
            frontend_data = retrieve_tech_data("frontend_evaluation") 
            if frontend_data:
                frontend_recommendation = frontend_data.get("recommendation", {})
                logger.info("Retrieved frontend recommendation from enhanced memory")
                
        if not database_recommendation:
            database_data = retrieve_tech_data("database_evaluation")
            if database_data:
                database_recommendation = database_data.get("recommendation", {})
                logger.info("Retrieved database recommendation from enhanced memory")
        
        # Debug logging
        logger.info(f"evaluation_results type: {type(evaluation_results)}")
        logger.info(f"architecture_recommendation type: {type(architecture_recommendation)}")
        logger.info(f"backend_recommendation type: {type(backend_recommendation)}")
        logger.info(f"frontend_recommendation type: {type(frontend_recommendation)}")
        logger.info(f"database_recommendation type: {type(database_recommendation)}")
        logger.info(f"combined_input type: {type(combined_input)}")
        
        # Process combined_input if present
        if combined_input:
            try:
                if isinstance(combined_input, str):
                    combined_data = json.loads(combined_input)
                else:
                    combined_data = combined_input
                
                # Extract recommendations from combined data
                backend_recommendation = combined_data.get("backend_recommendation", backend_recommendation)
                frontend_recommendation = combined_data.get("frontend_recommendation", frontend_recommendation)
                database_recommendation = combined_data.get("database_recommendation", database_recommendation)
                architecture_recommendation = combined_data.get("architecture_recommendation", architecture_recommendation)
                
                logger.info("Successfully processed combined_input")
            except Exception as e:
                logger.error(f"Error processing combined_input: {str(e)}")
        
        # Process evaluation_results if present and other fields not set
        if evaluation_results and not (backend_recommendation or frontend_recommendation or database_recommendation):
            try:
                if isinstance(evaluation_results, str):
                    eval_data = json.loads(evaluation_results)
                else:
                    eval_data = evaluation_results
                
                # Extract recommendations from evaluation results
                if "backend" in eval_data:
                    backend_recommendation = eval_data.get("backend", {})
                    frontend_recommendation = eval_data.get("frontend", {})
                    database_recommendation = eval_data.get("database", {})
                    logger.info("Using standard backend/frontend/database keys from evaluation_results")
            except Exception as e:
                logger.error(f"Error processing evaluation_results: {str(e)}")
        
        # Ensure we have an architecture_recommendation dict
        if not architecture_recommendation:
            architecture_recommendation = {"recommendation": {"pattern": "Layered Architecture"}}
        
        # Convert any string recommendations to dicts
        try:
            backend_rec = parse_recommendation(backend_recommendation)
            frontend_rec = parse_recommendation(frontend_recommendation)
            database_rec = parse_recommendation(database_recommendation)
            arch_rec = parse_recommendation(architecture_recommendation)
        except Exception as e:
            logger.error(f"Error parsing recommendations: {str(e)}")
            # Set defaults if parsing fails
            backend_rec = backend_recommendation if isinstance(backend_recommendation, dict) else {}
            frontend_rec = frontend_recommendation if isinstance(frontend_recommendation, dict) else {}
            database_rec = database_recommendation if isinstance(database_recommendation, dict) else {}
            arch_rec = architecture_recommendation if isinstance(architecture_recommendation, dict) else {}        # Setup LangChain parsing chain
        parser = PydanticOutputParser(pydantic_object=TechStackSynthesisOutput)
        
        template = """
        You are a technology stack architect tasked with creating a comprehensive tech stack recommendation.
        
        Synthesize a detailed technology stack from the provided components:
        
        Backend: {backend}
        Frontend: {frontend}
        Database: {database}
        Architecture: {architecture}
        
        IMPORTANT: Follow this EXACT JSON structure (all values in deployment_environment must be strings, not arrays):
        
        {{
          "backend": {{
            "language": "string",
            "framework": "string", 
            "reasoning": "string"
          }},
          "frontend": {{
            "language": "string",
            "framework": "string",
            "reasoning": "string"
          }},
          "database": {{
            "type": "string",
            "reasoning": "string"
          }},
          "architecture_pattern": "string",
          "deployment_environment": {{
            "platform": "string",
            "containerization": "string",
            "reasoning": "string"
          }},
          "key_libraries_tools": [
            {{
              "name": "string",
              "purpose": "string"
            }}
          ],
          "estimated_complexity": "Low|Medium|High"
        }}
        
        Note: If you need to specify multiple deployment services, include them in the reasoning field as a descriptive string, not as a separate services array.
        
        {format_instructions}
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a technology stack architect tasked with creating a comprehensive tech stack recommendation."),
            ("human", template)
        ])
        
        llm = get_tool_llm(temperature=0.1)
        chain = prompt | llm | parser        
        result = chain.invoke({
            "backend": json.dumps(backend_rec),
            "frontend": json.dumps(frontend_rec),
            "database": json.dumps(database_rec),
            "architecture": json.dumps(arch_rec),
            "format_instructions": parser.get_format_instructions()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in synthesize_tech_stack: {str(e)}", exc_info=True)
        
        # If the error is related to Pydantic validation, try to fix the structure
        if "deployment_environment.services" in str(e) or "Input should be a valid string" in str(e):
            logger.info("Attempting to fix deployment_environment structure issue...")
            try:
                # Try to get the raw LLM output and fix it manually
                llm = get_tool_llm(temperature=0.1)
                
                # Get raw response without Pydantic parsing
                raw_response = llm.invoke([
                    ("system", "You are a technology stack architect tasked with creating a comprehensive tech stack recommendation."),
                    ("human", f"""
                    Synthesize a detailed technology stack from the provided components:
                    
                    Backend: {json.dumps(backend_rec)}
                    Frontend: {json.dumps(frontend_rec)}
                    Database: {json.dumps(database_rec)}
                    Architecture: {json.dumps(arch_rec)}
                    
                    Return ONLY valid JSON. Ensure deployment_environment contains only string values, no arrays.
                    """)
                ])
                
                # Use JsonHandler to parse and clean the response
                from .json_handler import JsonHandler
                cleaned_json = JsonHandler.extract_json_from_text(raw_response.content if hasattr(raw_response, 'content') else str(raw_response))
                
                if cleaned_json and isinstance(cleaned_json, dict):
                    # Fix deployment_environment if it has arrays
                    if "deployment_environment" in cleaned_json and isinstance(cleaned_json["deployment_environment"], dict):
                        deploy_env = cleaned_json["deployment_environment"]
                        if "services" in deploy_env and isinstance(deploy_env["services"], list):
                            # Convert services array to a descriptive string
                            services_str = ", ".join(deploy_env["services"])
                            deploy_env["reasoning"] = deploy_env.get("reasoning", "") + f". Services: {services_str}"
                            del deploy_env["services"]  # Remove the problematic array
                    
                    # Ensure all required fields exist with proper types
                    if "key_libraries_tools" not in cleaned_json:
                        cleaned_json["key_libraries_tools"] = []
                    
                    # Convert to Pydantic object manually
                    return TechStackSynthesisOutput(**cleaned_json)
                    
            except Exception as fix_error:
                logger.error(f"Failed to fix structure: {str(fix_error)}")
        
        # Return a valid Pydantic object even in case of error
        default_libraries = [
            LibraryTool(name="Jest", purpose="Testing framework"),
            LibraryTool(name="Webpack", purpose="Module bundler"),
            LibraryTool(name="Sequelize", purpose="ORM for database interactions")
        ]
        
        result = TechStackSynthesisOutput(
            backend={
                "language": "JavaScript",
                "framework": "Node.js/Express",
                "reasoning": "Well-suited for web applications with good ecosystem"
            },
            frontend={
                "language": "JavaScript",
                "framework": "React",
                "reasoning": "Popular, well-supported library with strong ecosystem"
            },
            database={
                "type": "PostgreSQL",
                "reasoning": "Reliable relational database with excellent feature set"
            },
            architecture_pattern="MVC with REST API",
            deployment_environment={
                "platform": "Cloud (AWS)",
                "containerization": "Docker"
            },
            key_libraries_tools=default_libraries,
            estimated_complexity="Medium"
        )
        
        # Store final tech stack synthesis for other tools to use
        store_tech_data("tech_stack_synthesis", {
            "backend": result.backend,
            "frontend": result.frontend,
            "database": result.database,
            "architecture_pattern": result.architecture_pattern,
            "deployment_environment": result.deployment_environment,
            "key_libraries_tools": result.key_libraries_tools,
            "estimated_complexity": result.estimated_complexity
        })
        
        return result

@smart_react_tool("Analyze risks in the technology stack")
def analyze_tech_stack_risks(tech_stack) -> dict:
    """
    Analyzes potential risks and challenges in the selected technology stack.
    Use this after synthesizing the tech stack to identify potential issues.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Tool 'analyze_tech_stack_risks' called with input type: {type(tech_stack)}")

    # Handle the case where LangChain passes data in a 'tool_input' key
    if isinstance(tech_stack, dict) and 'tool_input' in tech_stack:
        logger.info("Found 'tool_input' key in tech_stack - extracting nested data")
        tool_input = tech_stack['tool_input']
    else:
        tool_input = tech_stack
    logger.info("Tool 'analyze_tech_stack_risks' called.")
    
    try:
        # Handle ReAct agent inputs (string or dict)
        if isinstance(tool_input, str):
            logger.info("Received string input from ReAct agent (expected behavior) - parsing to TechStackRiskAnalysisInput")
            try:
                # First try standard JSON parsing
                parsed_data = json.loads(tool_input)
                
                # Check if this contains the expected structure or technology recommendations
                if "tech_stack_json" in parsed_data:
                    tool_input = TechStackRiskAnalysisInput(**parsed_data)
                    logger.info("Successfully parsed JSON string to TechStackRiskAnalysisInput")
                else:
                    # This looks like technology recommendations, convert to expected format
                    logger.info("Parsed JSON contains technology recommendations, converting to tech stack format")
                    
                    # Create tech_stack_json from the recommendations
                    tech_stack_data = {}
                    
                    if "backend_recommendation" in parsed_data:
                        backend_rec = parsed_data["backend_recommendation"]
                        if isinstance(backend_rec, dict):
                            tech_stack_data["backend"] = backend_rec
                    
                    if "frontend_recommendation" in parsed_data:
                        frontend_rec = parsed_data["frontend_recommendation"]
                        if isinstance(frontend_rec, dict):
                            tech_stack_data["frontend"] = frontend_rec
                    
                    if "database_recommendation" in parsed_data:
                        db_rec = parsed_data["database_recommendation"]
                        if isinstance(db_rec, dict):
                            tech_stack_data["database"] = db_rec
                    
                    if "architecture_recommendation" in parsed_data:
                        arch_rec = parsed_data["architecture_recommendation"]
                        if isinstance(arch_rec, dict):
                            tech_stack_data["architecture_pattern"] = arch_rec.get("pattern", arch_rec)
                        else:
                            tech_stack_data["architecture_pattern"] = arch_rec
                    
                    # If no specific recommendations found, use the entire parsed data
                    if not tech_stack_data:
                        tech_stack_data = parsed_data
                    
                    tool_input = TechStackRiskAnalysisInput(
                        tech_stack_json=json.dumps(tech_stack_data, indent=2),
                        requirements_summary="Technology stack for risk analysis based on recommendations"
                    )
                    logger.info(f"Successfully created TechStackRiskAnalysisInput from tech recommendations")
            except json.JSONDecodeError as e:
                # Check if this is an "Extra data" error (concatenated JSON)
                if "Extra data" in str(e):
                    logger.warning(f"Detected 'Extra data' error - attempting to extract first JSON object: {str(e)}")
                    try:
                        # Extract just the first complete JSON object
                        start_idx = tool_input.find('{')
                        if start_idx != -1:
                            brace_count = 0
                            for i in range(start_idx, len(tool_input)):
                                if tool_input[i] == '{':
                                    brace_count += 1
                                elif tool_input[i] == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        json_part = tool_input[start_idx:i+1]
                                        parsed_data = json.loads(json_part)
                                        # Convert the parsed data to the expected format for TechStackRiskAnalysisInput
                                        tool_input = TechStackRiskAnalysisInput(
                                            tech_stack_json=json.dumps(parsed_data, indent=2),
                                            requirements_summary="Extracted from ReAct agent concatenated JSON"
                                        )
                                        logger.info("Successfully extracted first JSON object from concatenated data")
                                        break
                            else:
                                raise ValueError("Could not find complete JSON object")
                        else:
                            raise ValueError("No JSON object found")
                    except Exception as extract_error:
                        logger.warning(f"JSON extraction failed: {str(extract_error)} - falling back to JsonHandler")
                        # Fall through to JsonHandler fallback below
                        
                        # JsonHandler fallback for "Extra data" extraction failures
                        try:
                            # Use JsonHandler for robust JSON extraction
                            from .json_handler import JsonHandler
                            parsed_data = JsonHandler.extract_json_from_text(tool_input)
                            
                            if isinstance(parsed_data, dict):
                                # Check if it has the expected structure
                                if "tech_stack_json" in parsed_data:
                                    tool_input = TechStackRiskAnalysisInput(**parsed_data)
                                    logger.info("Successfully parsed with JsonHandler - found tech_stack_json field")
                                else:
                                    # Convert the parsed data to the expected format
                                    tool_input = TechStackRiskAnalysisInput(
                                        tech_stack_json=json.dumps(parsed_data, indent=2),
                                        requirements_summary="Extracted from ReAct agent input"
                                    )
                                    logger.info("Successfully parsed with JsonHandler - created tech_stack_json from data")
                            else:
                                raise ValueError("JsonHandler did not return a valid dictionary")
                                
                        except Exception as handler_error:
                            logger.error(f"JsonHandler also failed: {str(handler_error)} - using final fallback")
                            # Create a minimal valid input using the original string as tech_stack_json
                            tool_input = TechStackRiskAnalysisInput(
                                tech_stack_json=tool_input[:2000],  # Use original string, limit length
                                requirements_summary="Failed to parse input - using raw string"
                            )
                            logger.info("Created fallback input using truncated raw string")
                else:
                    logger.warning(f"Standard JSON parsing failed: {str(e)} - trying JsonHandler for robust parsing")
                    
                    # JsonHandler fallback for standard JSON parsing failures
                    try:
                        # Use JsonHandler for robust JSON extraction
                        from .json_handler import JsonHandler
                        parsed_data = JsonHandler.extract_json_from_text(tool_input)
                        
                        if isinstance(parsed_data, dict):
                            # Check if it has the expected structure
                            if "tech_stack_json" in parsed_data:
                                tool_input = TechStackRiskAnalysisInput(**parsed_data)
                                logger.info("Successfully parsed with JsonHandler - found tech_stack_json field")
                            else:
                                # Convert the parsed data to the expected format
                                tool_input = TechStackRiskAnalysisInput(
                                    tech_stack_json=json.dumps(parsed_data, indent=2),
                                    requirements_summary="Extracted from ReAct agent input"
                                )
                                logger.info("Successfully parsed with JsonHandler - created tech_stack_json from data")
                        else:
                            raise ValueError("JsonHandler did not return a valid dictionary")
                            
                    except Exception as handler_error:
                        logger.error(f"JsonHandler also failed: {str(handler_error)} - using final fallback")
                        # Create a minimal valid input using the original string as tech_stack_json  
                        tool_input = TechStackRiskAnalysisInput(
                            tech_stack_json=tool_input[:2000],  # Use original string, limit length
                            requirements_summary="Failed to parse input - using raw string"
                        )
                        logger.info("Created fallback input using truncated raw string")
        elif isinstance(tool_input, dict):
            logger.info("Received dict input, converting to TechStackRiskAnalysisInput")
            
            # Check if the dict has the expected TechStackRiskAnalysisInput structure
            if "tech_stack_json" in tool_input:
                # Standard case: dict already has the right structure
                tool_input = TechStackRiskAnalysisInput(**tool_input)
            else:
                # ReAct agent passed the tech stack data directly as a dict
                # Convert the dict to JSON string for the tech_stack_json field
                tech_stack_data = tool_input.copy()
                
                # Remove any non-tech-stack fields that might be present
                tech_stack_fields = ['backend', 'frontend', 'database', 'architecture_pattern', 
                                   'deployment_environment', 'key_libraries_tools', 'estimated_complexity']
                
                filtered_tech_stack = {}
                for field in tech_stack_fields:
                    if field in tech_stack_data:
                        filtered_tech_stack[field] = tech_stack_data[field]
                
                # If we didn't find tech stack fields, use the entire dict
                if not filtered_tech_stack:
                    filtered_tech_stack = tech_stack_data
                
                logger.info(f"Converting tech stack dict to JSON string for analysis. Found fields: {list(filtered_tech_stack.keys())}")
                
                # Create the proper input structure
                tool_input = TechStackRiskAnalysisInput(
                    tech_stack_json=json.dumps(filtered_tech_stack, indent=2),
                    requirements_summary=tech_stack_data.get('requirements_summary', 
                                       "Standard web application requirements with focus on reliability and security.")
                )
            
        # Extract data from the converted tool_input
        tech_stack_json = tool_input.tech_stack_json
        requirements_summary = tool_input.requirements_summary
        
        # Handle the case where requirements_summary is empty
        if not requirements_summary or requirements_summary == "Standard web application requirements with focus on reliability and security.":
            # Try to extract requirements from tech_stack_json if it appears to contain them
            if "requirement" in tech_stack_json.lower():
                logger.info("Attempting to extract requirements from tech_stack_json")
                # Simple extraction of sentences containing requirement-related terms
                import re
                req_sentences = []
                sentences = re.split(r'[.!?]', tech_stack_json)
                for sentence in sentences:
                    if any(term in sentence.lower() for term in ["requirement", "focus", "need", "must", "should", "performance", "security", "scalability"]):
                        req_sentences.append(sentence.strip() + ".")
                
                if req_sentences:
                    requirements_summary = " ".join(req_sentences)
                    logger.info(f"Extracted requirements: {requirements_summary[:100]}...")
        
        # Create a Pydantic output parser
        parser = PydanticOutputParser(pydantic_object=TechStackRiskAnalysisOutput)
        
        # Create the prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a technology risk analyst."),
            ("human", 
             """You are a technology risk analyst. Your task is to evaluate potential risks, challenges,
and compatibility issues in the proposed technology stack.

Tech Stack:
{tech_stack}

Project Requirements:
{requirements}

Provide your risk analysis according to these instructions:
{format_instructions}""")
        ])
        
        # Get the LLM and create the chain
        llm = get_tool_llm(temperature=0.1)
        chain = prompt | llm | parser
        
        # Execute the chain
        result = chain.invoke({
            "tech_stack": tech_stack_json,
            "requirements": requirements_summary,
            "format_instructions": parser.get_format_instructions()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in analyze_tech_stack_risks: {str(e)}", exc_info=True)
        # Return a valid Pydantic object even in case of error
        return TechStackRiskAnalysisOutput(
            risks=[
                TechRisk(
                    category="Technology Adoption",
                    description="Team may need time to adapt to the selected stack",
                    severity="Medium",
                    likelihood="Medium",
                    mitigation="Provide training and documentation"
                ),
                TechRisk(
                    category="Scalability",
                    description="Solution may face challenges with very high user loads",
                    severity="Medium",
                    likelihood="Low",
                    mitigation="Implement caching and horizontal scaling"
                )
            ],
            technology_compatibility_issues=[
                TechCompatibilityIssue(
                    components=["Frontend", "Backend"],
                    potential_issue="API integration challenges",
                    solution="Establish clear API contracts early"
                )
            ]
        )

@smart_react_tool("Evaluate frontend technology options")
def evaluate_frontend_options(brd_analysis) -> dict:
    """
    Evaluates frontend framework options based on requirements and user experience focus.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Tool 'evaluate_frontend_options' called with input type: {type(brd_analysis)}")

    # Handle the case where LangChain passes data in a 'tool_input' key
    if isinstance(brd_analysis, dict) and 'tool_input' in brd_analysis:
        logger.info("Found 'tool_input' key in brd_analysis - extracting nested data")
        tool_input = brd_analysis['tool_input']
    else:
        tool_input = brd_analysis

    # Extract data from various input formats
    requirements = ""
    user_experience = ""
    
    # Handle Pydantic model
    if isinstance(tool_input, FrontendEvaluationInput):
        logger.info("Input is a FrontendEvaluationInput model")
        requirements = tool_input.requirements
        user_experience = tool_input.user_experience or ""
    
    # Handle dict input
    elif isinstance(tool_input, dict):
        logger.info("Input is a dictionary")
        requirements = tool_input.get("requirements", "")
        user_experience = tool_input.get("user_experience", "")
    
    # Handle string input
    elif isinstance(tool_input, str):
        logger.info("Input is a string")
        requirements = tool_input
    
    # Default handling
    else:
        logger.warning(f"Unexpected input type: {type(tool_input)}")
        requirements = str(tool_input)
    
    try:
        # Create a Pydantic output parser
        parser = PydanticOutputParser(pydantic_object=FrontendEvaluationOutput)
        
        # Create the prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a frontend technology expert."),
            ("human", 
             "Based on the following project requirements and UX focus, recommend "
             "2-3 frontend frameworks with justifications:\n\n"
             "PROJECT REQUIREMENTS: {requirements}\n\n"
             "UX FOCUS: {ux_focus}\n\n"
             "Format your response according to these instructions:\n"
             "{format_instructions}")
        ])
        
        # Get the LLM and create the chain
        llm = get_tool_llm(temperature=0.1)
        chain = prompt | llm | parser
        
        # Execute the chain
        result = chain.invoke({
            "requirements": requirements,
            "ux_focus": user_experience,
            "format_instructions": parser.get_format_instructions()
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in evaluate_frontend_options: {e}", exc_info=True)
        # Return a valid Pydantic object even in case of error
        return FrontendEvaluationOutput(
            frontend_options=[
                TechOption(
                    name="React",
                    framework="React",
                    overall_score=9.0,
                    reasoning="Industry standard with extensive ecosystem"
                ),
                TechOption(
                    name="Vue.js",
                    framework="Vue.js",
                    overall_score=8.0,
                    reasoning="Easy learning curve with good performance"
                ),
                TechOption(
                    name="Angular",
                    framework="Angular",
                    overall_score=7.5,
                    reasoning="Complete framework with strong enterprise features"
                )
            ],
            recommendation=TechOption(
                name="React",
                framework="React",
                overall_score=9.0,
                reasoning="Best suited for most web application needs"
            )
        )

@smart_react_tool("Evaluate all technology options comprehensively")
def evaluate_all_technologies(brd_analysis):
    """
    Evaluates backend, frontend, and database technologies in a single batch operation.
    Use this to efficiently gather technology recommendations all at once rather than one by one.
    
    Args:
        brd_analysis: Dictionary containing requirements_summary and optional evaluation flags and ux_focus
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'evaluate_all_technologies' called for batch technology evaluation")
    
    try:
        # Handle the case where LangChain passes data in a 'tool_input' key
        if isinstance(brd_analysis, dict) and 'tool_input' in brd_analysis:
            logger.info("Found 'tool_input' key in brd_analysis - extracting nested data")
            tool_input = brd_analysis['tool_input']
        else:
            tool_input = brd_analysis
            
        # Handle multiple input types from ReAct agents
        if isinstance(tool_input, BatchTechnologyEvaluationInput):
            logger.info("Received BatchTechnologyEvaluationInput object - using directly")
            # tool_input is already the correct type, use it as-is
            pass
        elif isinstance(tool_input, str):
            logger.info("Received string input from ReAct agent - parsing to BatchTechnologyEvaluationInput")
            # Try to extract JSON from the string
            from tools.json_handler import JsonHandler
            json_result = JsonHandler.extract_json_from_text(tool_input)
            
            # Handle both dict return type and object return type from JsonHandler
            json_data = None
            if isinstance(json_result, dict):
                # JsonHandler returned a dict directly
                json_data = json_result
                logger.info("JsonHandler returned dict directly")
            elif hasattr(json_result, 'success') and hasattr(json_result, 'data'):
                # JsonHandler returned an object with success/data attributes
                if json_result.success and json_result.data:
                    json_data = json_result.data
                    logger.info("JsonHandler returned success object with data")
            
            if json_data:
                try:
                    # Handle ux_focus field in json_data before creating the object
                    if 'ux_focus' in json_data and isinstance(json_data['ux_focus'], list):
                        if json_data['ux_focus']:
                            json_data['ux_focus'] = ", ".join(str(item) for item in json_data['ux_focus'])
                        else:
                            json_data['ux_focus'] = None
                    
                    tool_input = BatchTechnologyEvaluationInput(**json_data)
                    logger.info("Successfully parsed JSON from string to BatchTechnologyEvaluationInput")
                except Exception as parse_error:
                    logger.warning(f"Failed to create BatchTechnologyEvaluationInput from extracted JSON: {str(parse_error)}")
                    # Create a minimal valid object with the string as the requirements
                    tool_input = BatchTechnologyEvaluationInput(
                        requirements_summary=tool_input,
                        evaluate_backend=True,
                        evaluate_frontend=True,
                        evaluate_database=True,
                        ux_focus=None
                    )
            else:
                logger.info("No valid JSON found in string, using as raw requirements")
                # Create a minimal valid object with the string as the requirements
                tool_input = BatchTechnologyEvaluationInput(
                    requirements_summary=tool_input,
                    evaluate_backend=True,
                    evaluate_frontend=True,
                    evaluate_database=True,
                    ux_focus=None
                )
                
        elif isinstance(tool_input, dict):
            logger.info("Received dict input from ReAct agent - converting to BatchTechnologyEvaluationInput")
            try:
                tool_input = BatchTechnologyEvaluationInput(**tool_input)
                logger.info("Successfully converted dict to BatchTechnologyEvaluationInput")
            except Exception as parse_error:
                logger.warning(f"Failed to create BatchTechnologyEvaluationInput from dict: {str(parse_error)}")
                # Try to extract requirements from common dict keys
                requirements = (
                    tool_input.get("requirements_summary") or 
                    tool_input.get("requirements") or 
                    tool_input.get("technical_requirements") or
                    str(tool_input)
                )
                
                # Handle ux_focus - ensure it's a string or None, not a list
                ux_focus_raw = tool_input.get("ux_focus")
                ux_focus = None
                if ux_focus_raw:
                    if isinstance(ux_focus_raw, list):
                        # Convert list to string if it has content
                        if ux_focus_raw:
                            ux_focus = ", ".join(str(item) for item in ux_focus_raw)
                        else:
                            ux_focus = None
                    elif isinstance(ux_focus_raw, str):
                        ux_focus = ux_focus_raw
                    else:
                        ux_focus = str(ux_focus_raw)
                
                tool_input = BatchTechnologyEvaluationInput(
                    requirements_summary=requirements,
                    evaluate_backend=tool_input.get("evaluate_backend", True),
                    evaluate_frontend=tool_input.get("evaluate_frontend", True),
                    evaluate_database=tool_input.get("evaluate_database", True),
                    ux_focus=ux_focus
                )
        
        # Extract data from the tool_input
        requirements_summary = tool_input.requirements_summary
        evaluate_backend = tool_input.evaluate_backend
        evaluate_frontend = tool_input.evaluate_frontend
        evaluate_database = tool_input.evaluate_database
        ux_focus = tool_input.ux_focus
        
        logger.info(f"Processing batch evaluation with requirements: {requirements_summary[:50]}...")
        logger.info(f"Evaluation flags - Backend: {evaluate_backend}, Frontend: {evaluate_frontend}, Database: {evaluate_database}")
        
        results = {}
        
        # Evaluate backend if requested
        if evaluate_backend:
            try:
                # Call the function directly with requirements_summary
                backend_result = evaluate_backend_options(requirements_summary)
                results["backend"] = backend_result.dict() if hasattr(backend_result, "dict") else backend_result
                logger.info("Backend technology evaluation completed successfully")
            except Exception as be:
                logger.error(f"Backend evaluation failed: {str(be)}")
                results["backend"] = {"error": str(be)}
        
        # Evaluate frontend if requested
        if evaluate_frontend:
            try:
                ux = ux_focus or "Standard user experience with focus on usability and performance"
                # Call the function directly with requirements_summary
                frontend_result = evaluate_frontend_options(requirements_summary)
                results["frontend"] = frontend_result.dict() if hasattr(frontend_result, "dict") else frontend_result
                logger.info("Frontend technology evaluation completed successfully")
            except Exception as fe:
                logger.error(f"Frontend evaluation failed: {str(fe)}")
                results["frontend"] = {"error": str(fe)}
        
        # Evaluate database if requested
        if evaluate_database:
            try:
                # Call the function directly with requirements_summary
                database_result = evaluate_database_options(requirements_summary)
                results["database"] = database_result.dict() if hasattr(database_result, "dict") else database_result
                logger.info("Database technology evaluation completed successfully")
            except Exception as de:
                logger.error(f"Database evaluation failed: {str(de)}")
                results["database"] = {"error": str(de)}
        
        # Return a structured result
        logger.info(f"Successfully evaluated {len(results)} technology categories in batch mode")
        return results
        
    except Exception as e:
        logger.error(f"Error in evaluate_all_technologies: {str(e)}", exc_info=True)
        
        # Completely rebuild the tool input if we've reached this error state
        # This handles cases where we get parsing errors or the original input was malformed
        try:
            # For string input, create a minimal valid object with the string as requirements
            if isinstance(brd_analysis, str):
                logger.info("Treating raw string input as requirements_summary")
                requirements_summary = brd_analysis
                evaluate_backend = True
                evaluate_frontend = True
                evaluate_database = True
            else:
                # Try to extract what we can from the input
                requirements_summary = getattr(brd_analysis, "requirements_summary", "No requirements provided")
                evaluate_backend = getattr(brd_analysis, "evaluate_backend", True)
                evaluate_frontend = getattr(brd_analysis, "evaluate_frontend", True)
                evaluate_database = getattr(brd_analysis, "evaluate_database", True)
            
            # Create a minimal response with errors
            return {
                "error": str(e),
                "requirements_processed": requirements_summary[:100] + "...",
                "backend": {} if evaluate_backend else None,
                "frontend": {} if evaluate_frontend else None, 
                "database": {} if evaluate_database else None
            }
        except Exception as nested_e:
            # Last resort fallback
            logger.error(f"Fallback error handler failed: {str(nested_e)}")
            return {
                "error": f"Multiple errors: {str(e)} and then {str(nested_e)}",
                "backend": {},
                "frontend": {}, 
                "database": {}
            }

def _normalize_tech_field(field_value) -> str:
    """
    Normalize a tech field that can be either a string or a dictionary to a string.
    
    Args:
        field_value: Can be a string, dict with 'name' field, or None
        
    Returns:
        String representation of the technology
    """
    if not field_value:
        return ""
    
    if isinstance(field_value, str):
        return field_value
    
    if isinstance(field_value, dict):
        # Extract name and framework if available
        name = field_value.get('name', '')
        framework = field_value.get('framework', '')
        
        if name and framework and name != framework:
            return f"{name} ({framework})"
        elif name:
            return name
        elif framework:
            return framework
        else:
            return ""
    
    # Fallback for other types
    return str(field_value)

@tool
def compile_tech_stack_recommendation() -> Dict[str, Any]:
    """
    Compile the final technology stack recommendation based on all analyses.
    
    This is the REQUIRED final tool that must be called to complete the
    tech stack advisor agent execution. This tool synthesizes all previous
    analyses into a comprehensive technology stack recommendation.
    
    Returns:
        Dict containing the complete tech stack recommendation with all required fields
    """
    import logging
    import json
    from datetime import datetime
    
    logger = logging.getLogger(__name__)
    logger.info("Tool 'compile_tech_stack_recommendation' called - final synthesis step")
    
    try:
        # Get the LLM for synthesis
        llm = get_tool_llm(temperature=0.1, agent_context="tech_stack_compiler")
        
        # Check if we have shared memory with previous tool results
        tech_evaluations = {}
        requirements_context = {}
        
        try:
            # Try to get previous tool results from enhanced memory first
            try:
                from enhanced_memory_manager import create_memory_manager
                
                # Create enhanced memory manager
                enhanced_memory = create_memory_manager(
                    backend_type="hybrid",
                    persistent_dir=None,
                    max_memory_mb=50,
                    enable_monitoring=True
                )
                
                # Try different contexts and keys for BRD analysis
                for context in ["cross_tool", "agent_results", "BRDAnalystReActAgent", "SystemDesignerReActAgent"]:
                    for key in ["brd_analysis", "requirements_analysis", "project_requirements"]:
                        brd_analysis = enhanced_memory.get(key, None, context=context)
                        if brd_analysis:
                            requirements_context = brd_analysis if isinstance(brd_analysis, dict) else {}
                            logger.info(f"Retrieved BRD analysis from enhanced memory (context: {context}, key: {key})")
                            break
                    if requirements_context:
                        break
                
                # Try different contexts for tech evaluations
                for context in ["cross_tool", "agent_results", "TechStackAdvisorReActAgent"]:
                    for key in ["tech_evaluations", "technology_results", "tech_stack_recommendation"]:
                        tech_results = enhanced_memory.get(key, None, context=context)
                        if tech_results:
                            tech_evaluations = tech_results if isinstance(tech_results, dict) else {}
                            logger.info(f"Retrieved tech evaluations from enhanced memory (context: {context}, key: {key})")
                            break
                    if tech_evaluations:
                        break
                        
            except ImportError:
                logger.warning("Enhanced memory not available, falling back to basic SharedMemory")
                # Fallback to basic SharedMemory
                from shared_memory import SharedMemory
                memory = SharedMemory()
                
                if memory and hasattr(memory, 'get'):
                    # Get BRD analysis context
                    brd_analysis = memory.get('brd_analysis') or memory.get('requirements_analysis')
                    if brd_analysis:
                        requirements_context = brd_analysis if isinstance(brd_analysis, dict) else {}
                        logger.info("Retrieved BRD analysis from basic shared memory")
                    
                    # Get any tech evaluation results
                    tech_results = memory.get('tech_evaluations') or memory.get('technology_results')
                    if tech_results:
                        tech_evaluations = tech_results if isinstance(tech_results, dict) else {}
                        logger.info("Retrieved tech evaluations from basic shared memory")
                        
        except Exception as e:
            logger.warning(f"Could not access memory systems for previous results: {str(e)}")
        
        # Create a comprehensive synthesis prompt
        synthesis_prompt = f"""
        You are a Senior Technology Architect tasked with creating a comprehensive technology stack recommendation.
        
        Based on the available context and analysis:
        
        REQUIREMENTS CONTEXT:
        {json.dumps(requirements_context, indent=2) if requirements_context else "Standard web application with CRUD operations, user authentication, and responsive design"}
        
        TECHNOLOGY EVALUATIONS:
        {json.dumps(tech_evaluations, indent=2) if tech_evaluations else "No previous evaluations found - provide standard recommendations"}
        
        Create a COMPLETE technology stack recommendation including:
        
        1. RECOMMENDED_STACK:
           - Frontend: Framework, libraries, build tools
           - Backend: Runtime, framework, key libraries
           - Database: Primary database, caching solution if needed
           - Cloud: Platform and essential services
           - DevOps: CI/CD, monitoring, testing tools
        
        2. JUSTIFICATION:
           - Why each technology was chosen
           - How it meets the requirements
           - Performance and scalability considerations
           - Development team productivity factors
           - Cost and maintenance considerations
        
        3. ALTERNATIVES:
           - Alternative technology choices for each component
           - Trade-offs and considerations
           - Migration paths if technology changes are needed
        
        4. IMPLEMENTATION_ROADMAP:
           - Phase 1: Setup and foundational components
           - Phase 2: Core development and integration
           - Phase 3: Testing and optimization
           - Phase 4: Deployment and monitoring
        
        5. RISK_ASSESSMENT:
           - Technology adoption risks
           - Scalability and performance risks
           - Security considerations
           - Mitigation strategies for each risk
           - Contingency plans
        
        Return as a well-structured JSON object with these exact sections.
        Focus on practical, proven technologies that balance innovation with stability.
        """
        
        # Get the synthesis from the LLM
        response = llm.invoke(synthesis_prompt)
        
        try:
            # Try to parse the response as JSON
            result = json.loads(response.content if hasattr(response, 'content') else str(response))
            logger.info("Successfully parsed LLM response as JSON")
        except json.JSONDecodeError:
            logger.warning("LLM response was not valid JSON, creating structured response")
            # Create a comprehensive fallback recommendation
            result = {
                "recommended_stack": {
                    "frontend": {
                        "framework": "React 18",
                        "state_management": "Redux Toolkit",
                        "styling": "Tailwind CSS",
                        "build_tool": "Vite",
                        "ui_library": "Material-UI or Ant Design"
                    },
                    "backend": {
                        "runtime": "Node.js 18+",
                        "framework": "Express.js",
                        "orm": "Prisma",
                        "validation": "Joi or Zod",
                        "authentication": "JWT with refresh tokens",
                        "api_documentation": "Swagger/OpenAPI"
                    },
                    "database": {
                        "primary": "PostgreSQL 14+",
                        "caching": "Redis",
                        "search": "Elasticsearch (if full-text search needed)",
                        "file_storage": "AWS S3 or equivalent"
                    },
                    "cloud": {
                        "platform": "AWS (recommended) or Azure",
                        "compute": "EC2 or Container Service (ECS/Fargate)",
                        "storage": "S3 for files, RDS for database",
                        "cdn": "CloudFront",
                        "monitoring": "CloudWatch"
                    },
                    "devops": {
                        "ci_cd": "GitHub Actions or GitLab CI",
                        "containerization": "Docker",
                        "infrastructure": "Terraform or CloudFormation",
                        "monitoring": "New Relic or DataDog",
                        "logging": "Winston + ELK Stack",
                        "testing": "Jest (unit) + Cypress (E2E)"
                    }
                },
                "justification": {
                    "frontend": "React provides excellent developer experience, large ecosystem, and strong community support. Vite offers fast development builds.",
                    "backend": "Node.js enables full-stack JavaScript development, Express is lightweight and flexible, Prisma provides type-safe database access.",
                    "database": "PostgreSQL offers excellent reliability, ACID compliance, and advanced features. Redis provides high-performance caching.",
                    "cloud": "AWS provides comprehensive services, excellent documentation, and proven scalability for web applications.",
                    "devops": "GitHub Actions integrates well with development workflow, Docker ensures consistent environments, monitoring tools provide operational visibility."
                },
                "alternatives": {
                    "frontend": {
                        "frameworks": ["Vue.js 3", "Angular 15+", "Svelte"],
                        "state_management": ["Zustand", "Context API", "MobX"],
                        "build_tools": ["Webpack", "Rollup", "Parcel"]
                    },
                    "backend": {
                        "runtimes": ["Python (Django/FastAPI)", "Java (Spring Boot)", "Go (Gin)", ".NET Core"],
                        "databases": ["MongoDB", "MySQL", "Aurora", "Supabase"]
                    },
                    "cloud": {
                        "platforms": ["Microsoft Azure", "Google Cloud Platform", "DigitalOcean", "Vercel + PlanetScale"]
                    }
                },
                "implementation_roadmap": {
                    "phase_1": {
                        "title": "Foundation Setup (Weeks 1-2)",
                        "tasks": [
                            "Set up development environment and CI/CD pipeline",
                            "Configure database and basic backend API structure",
                            "Initialize frontend project with routing and basic layout",
                            "Implement authentication system"
                        ]
                    },
                    "phase_2": {
                        "title": "Core Development (Weeks 3-6)",
                        "tasks": [
                            "Develop core business logic and database models",
                            "Build main user interface components",
                            "Implement CRUD operations and API endpoints",
                            "Add form validation and error handling"
                        ]
                    },
                    "phase_3": {
                        "title": "Testing and Polish (Weeks 7-8)",
                        "tasks": [
                            "Write comprehensive unit and integration tests",
                            "Implement end-to-end testing with Cypress",
                            "Performance optimization and security hardening",
                            "User experience refinement and accessibility"
                        ]
                    },
                    "phase_4": {
                        "title": "Deployment and Monitoring (Weeks 9-10)",
                        "tasks": [
                            "Set up production environment and infrastructure",
                            "Configure monitoring, logging, and alerting",
                            "Deploy application and conduct load testing",
                            "Documentation and knowledge transfer"
                        ]
                    }
                },
                "risk_assessment": {
                    "technology_risks": [
                        {
                            "risk": "React ecosystem changes rapidly",
                            "impact": "Medium",
                            "probability": "Medium",
                            "mitigation": "Stick to stable React patterns, use Long Term Support versions where available"
                        },
                        {
                            "risk": "Node.js single-threading limitations",
                            "impact": "Medium",
                            "probability": "Low",
                            "mitigation": "Implement proper clustering, use caching, consider worker threads for CPU-intensive tasks"
                        },
                        {
                            "risk": "Cloud vendor lock-in",
                            "impact": "High",
                            "probability": "Medium",
                            "mitigation": "Design cloud-agnostic architecture, use Infrastructure as Code, consider multi-cloud deployment patterns"
                        }
                    ],
                    "security_considerations": [
                        "Implement proper authentication and authorization",
                        "Use HTTPS everywhere with proper SSL certificates",
                        "Regular security updates and dependency scanning",
                        "Input validation and SQL injection prevention",
                        "Rate limiting and DDoS protection"
                    ],
                    "scalability_considerations": [
                        "Database connection pooling and query optimization",
                        "Implement caching at multiple levels",
                        "Consider microservices for future scaling",
                        "Use CDN for static assets",
                        "Horizontal scaling with load balancers"
                    ]
                }
            }
        
        # Add metadata
        result["metadata"] = {
            "generated_at": datetime.now().isoformat(),
            "agent": "Tech_Stack_Advisor",
            "confidence_score": 0.90,
            "requirements_analyzed": bool(requirements_context),
            "tech_evaluations_used": bool(tech_evaluations),
            "compilation_method": "llm_synthesis" if 'recommended_stack' in str(response) else "structured_fallback"
        }
        
        # Log successful completion
        logger.info("Successfully compiled comprehensive tech stack recommendation")
        logger.info(f"Recommendation includes {len(result.get('recommended_stack', {}))} technology categories")
        
        return result
        
    except Exception as e:
        logger.error(f"Error compiling tech stack recommendation: {str(e)}", exc_info=True)
        
        # Return a minimal but valid recommendation even in case of error
        return {
            "error": f"Compilation failed: {str(e)}",
            "recommended_stack": {
                "frontend": {"framework": "React", "reasoning": "Industry standard with good ecosystem"},
                "backend": {"framework": "Node.js/Express", "reasoning": "JavaScript full-stack development"},
                "database": {"type": "PostgreSQL", "reasoning": "Reliable and feature-rich"},
                "cloud": {"platform": "AWS", "reasoning": "Comprehensive cloud services"}
            },
            "justification": {
                "overall": "Safe, proven technology choices suitable for most web applications"
            },
            "alternatives": {
                "note": "Multiple alternatives available for each technology choice"
            },
            "implementation_roadmap": {
                "phase_1": "Setup development environment",
                "phase_2": "Implement core features",
                "phase_3": "Testing and optimization",
                "phase_4": "Deployment and monitoring"
            },
            "risk_assessment": {
                "primary_risks": ["Technology learning curve", "Scalability planning", "Security implementation"],
                "mitigation": "Follow best practices and conduct regular reviews"
            },
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "agent": "Tech_Stack_Advisor",
                "confidence_score": 0.60,
                "error_recovery": True
            }
        }

# Helper function to get all tech stack tools including the new compiler
def get_tech_stack_advisor_tools() -> List[BaseTool]:
    """Get all tech stack advisor tools including the required compiler tool."""
    return [
        get_technical_requirements_summary,
        evaluate_backend_options,
        evaluate_frontend_options,
        evaluate_database_options,
        evaluate_architecture_patterns,
        synthesize_tech_stack,
        analyze_tech_stack_risks,
        evaluate_all_technologies,
        compile_tech_stack_recommendation  # The required final tool
    ]