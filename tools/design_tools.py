"""
Design tools for the ReAct-based SystemDesignerAgent.
Each tool is focused on a single, specific design task.
"""

import json
import os
import re
import logging
import traceback
from typing import Dict, Any, List, Optional, Union
from typing import Dict, Any, List, Optional, Union
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from datetime import datetime
from langchain_core.output_parsers import PydanticOutputParser
from .json_handler import JsonHandler
import json
import logging

# Enhanced Memory Management imports
from enhanced_memory_manager import create_memory_manager, EnhancedSharedProjectMemory

# Enhanced Memory Management imports
from enhanced_memory_manager import create_memory_manager, EnhancedSharedProjectMemory

# Configure logger
logger = logging.getLogger(__name__)

# Enhanced memory and RAG helper functions
def get_enhanced_tool_memory():
    """Get SHARED enhanced memory manager instance for design tools."""
    try:
        from utils.shared_memory_hub import get_shared_memory_hub
        # Use the GLOBAL shared memory hub to prevent data isolation
        return get_shared_memory_hub()
    except Exception as e:
        logger.warning(f"Shared memory hub not available, using fallback: {e}")
        return None

def get_design_rag_context(query_type: str, domain: str = None, **kwargs):
    """Get RAG context for design-related queries."""
    try:
        from rag_manager import get_rag_manager
        rag_manager = get_rag_manager()
        if not rag_manager:
            return ""
            
        # Generate domain and type-specific RAG queries
        queries = _get_design_specific_rag_queries(query_type, domain, **kwargs)
        
        context_parts = []
        for query in queries:
            try:
                docs = rag_manager.similarity_search(query, k=3)
                if docs:
                    context_parts.extend([doc.page_content for doc in docs])
            except Exception as e:
                logger.warning(f"RAG query failed for '{query}': {e}")
                
        return "\n\n".join(context_parts[:1000])  # Limit context size
    except Exception as e:
        logger.warning(f"RAG context retrieval failed: {e}")
        return ""

def _get_design_specific_rag_queries(query_type: str, domain: str = None, **kwargs):
    """Generate specific RAG queries based on design type and domain."""
    queries = []
    
    if query_type == "architecture_pattern":
        base_queries = [
            "software architecture patterns best practices",
            "microservices vs monolithic architecture",
            "layered architecture design principles"
        ]
        
        if domain:
            domain_lower = domain.lower()
            if "healthcare" in domain_lower or "medical" in domain_lower:
                queries.extend([
                    "healthcare software architecture HIPAA compliance",
                    "medical records system architecture patterns",
                    "healthcare data security architecture"
                ])
            elif "financial" in domain_lower or "fintech" in domain_lower:
                queries.extend([
                    "financial services architecture patterns",
                    "PCI DSS compliant architecture design",
                    "fraud detection system architecture"
                ])
            elif "iot" in domain_lower or "device" in domain_lower:
                queries.extend([
                    "IoT architecture patterns edge computing",
                    "device management system architecture",
                    "real-time telemetry processing architecture"
                ])
            elif "ecommerce" in domain_lower or "shopping" in domain_lower:
                queries.extend([
                    "ecommerce platform architecture scalability",
                    "high traffic website architecture patterns",
                    "payment processing system architecture"
                ])
            else:
                queries.extend(base_queries)
        else:
            queries.extend(base_queries)
            
    elif query_type == "security_architecture":
        base_queries = [
            "software security architecture best practices",
            "authentication authorization patterns",
            "data encryption architecture design"
        ]
        
        if domain:
            domain_lower = domain.lower()
            if "healthcare" in domain_lower:
                queries.extend([
                    "HIPAA security architecture requirements",
                    "healthcare data security patterns",
                    "medical records access control"
                ])
            elif "financial" in domain_lower:
                queries.extend([
                    "PCI DSS security architecture",
                    "financial data protection patterns",
                    "banking system security design"
                ])
            else:
                queries.extend(base_queries)
        else:
            queries.extend(base_queries)
            
    elif query_type == "data_model":
        db_tech = kwargs.get("database_technology", "").lower()
        queries = [
            f"{db_tech} database design patterns" if db_tech else "database design patterns",
            "data modeling best practices",
            "database schema design principles"
        ]
        
        if domain:
            domain_lower = domain.lower()
            if "healthcare" in domain_lower:
                queries.append("healthcare database schema design")
            elif "financial" in domain_lower:
                queries.append("financial data model patterns")
            elif "ecommerce" in domain_lower:
                queries.append("ecommerce database design patterns")
                
    elif query_type == "api_design":
        queries = [
            "REST API design best practices",
            "API endpoint naming conventions",
            "API security patterns authentication"
        ]
        
        if domain:
            domain_lower = domain.lower()
            if "healthcare" in domain_lower:
                queries.append("healthcare API design FHIR standards")
            elif "financial" in domain_lower:
                queries.append("financial services API security patterns")
                
    return queries

def store_design_data(key: str, data: Any, context: str = "design_tools"):
    """Store design data in enhanced memory with multiple contexts for cross-tool access."""
    try:
        enhanced_memory = get_enhanced_tool_memory()
        if enhanced_memory:
            # Store in multiple contexts for better cross-tool access
            contexts = [context, "cross_tool", "system_design"]
            for ctx in contexts:
                enhanced_memory.store(key, data, context=ctx)
                
            logger.info(f"Stored design data with key '{key}' in contexts: {contexts}")
            return True
    except Exception as e:
        logger.error(f"Failed to store design data: {e}")
    return False

def retrieve_design_data(key: str, context: str = "design_tools"):
    """Retrieve design data from enhanced memory with fallback contexts."""
    try:
        enhanced_memory = get_enhanced_tool_memory()
        if enhanced_memory:
            # Try multiple contexts for better data retrieval
            contexts = [context, "cross_tool", "system_design", "agent_results"]
            for ctx in contexts:
                data = enhanced_memory.get(key, None, context=ctx)
                if data:
                    logger.info(f"Retrieved design data with key '{key}' from context: {ctx}")
                    return data
                    
            logger.info(f"No design data found for key '{key}' in any context")
    except Exception as e:
        logger.error(f"Failed to retrieve design data: {e}")
    return None

def get_design_context_from_memory():
    """Get project context from enhanced memory for better design decisions."""
    try:
        enhanced_memory = get_enhanced_tool_memory()
        if not enhanced_memory:
            return {}
            
        context = {}
        
        # Try to get various pieces of project context
        keys_to_try = [
            "requirements_summary", "project_requirements", "brd_analysis",
            "tech_stack_recommendation", "architecture_pattern", "system_components",
            "project_context", "domain_info"
        ]
        
        for key in keys_to_try:
            # Try multiple contexts
            for ctx in ["cross_tool", "design_tools", "agent_results", "planning_tools"]:
                data = enhanced_memory.get(key, None, context=ctx)
                if data:
                    context[key] = data
                    break
                    
        logger.info(f"Retrieved design context with {len(context)} items from memory")
        return context
        
    except Exception as e:
        logger.error(f"Failed to get design context from memory: {e}")
        return {}

# Import Pydantic models from centralized data contracts
from models.data_contracts import (
    # Input models
    ProjectRequirementsSummaryInput,
    ArchitecturePatternSelectionInput,
    SystemComponentsIdentificationInput,
    ComponentStructureDesignInput,
    DataModelDesignInput,
    ApiEndpointsDesignInput,
    SecurityArchitectureDesignInput,
    SystemDesignSynthesisInput,
    DesignQualityEvaluationInput,
    MultipleComponentStructuresDesignInput,
    
    # Output models
    ProjectRequirementsSummaryOutput,
    ArchitecturePatternOutput,
    SystemComponentsOutput,
    SystemComponentOutput,
    ComponentDesignOutput,
    DataModelOutput,
    ApiEndpointsOutput,
    SecurityArchitectureOutput,
    SecurityMeasure,
    SystemDesignOutput,
    DesignQualityOutput,
    MultipleComponentStructuresOutput
)

# Add the import at the top near other imports
from utils.react_tool_wrapper import smart_react_tool, react_compatible_tool

# Enhanced Memory Management for Design Tools
_shared_memory_instance = None

def get_enhanced_tool_memory() -> EnhancedSharedProjectMemory:
    """
    Get or create a SHARED enhanced memory instance for design tools.
    Uses singleton pattern to ensure all design tools share the same memory.
    Uses hybrid backend for optimal performance.
    """
    global _shared_memory_instance
    
    if _shared_memory_instance is None:
        try:
            from utils.shared_memory_hub import get_shared_memory_hub
            # Use the GLOBAL shared memory hub to prevent data isolation
            _shared_memory_instance = get_shared_memory_hub()
            logger.info("Using GLOBAL shared memory hub for design tools")
        except Exception as e:
            logger.warning(f"Failed to get shared memory hub, falling back to basic: {e}")
            _shared_memory_instance = EnhancedSharedProjectMemory(run_dir="./output/memory")
            
    return _shared_memory_instance

def store_design_data(key: str, data: Any, context: str = "design_tools") -> bool:
    """
    Store design data in enhanced memory with multi-context support.
    
    Args:
        key: Storage key
        data: Data to store
        context: Storage context (default: design_tools)
    
    Returns:
        bool: Success status
    """
    try:
        memory = get_enhanced_tool_memory()
        
        # Store in multiple contexts for cross-tool access
        contexts = [context, "cross_tool", "agent_results"]
        
        for ctx in contexts:
            success = memory.set(key, data, context=ctx)
            if not success:
                logger.warning(f"Failed to store {key} in context {ctx}")
                
        logger.info(f"Successfully stored design data: {key} in {len(contexts)} contexts")
        return True
        
    except Exception as e:
        logger.error(f"Error storing design data {key}: {e}")
        return False

def retrieve_design_data(key: str, default=None, context: str = "design_tools") -> Any:
    """
    Retrieve design data from enhanced memory with fallback support.
    
    Args:
        key: Storage key
        default: Default value if not found
        context: Primary context to search
    
    Returns:
        Stored data or default value
    """
    try:
        memory = get_enhanced_tool_memory()
        
        # Try multiple contexts in order of preference - including shared contexts
        contexts = [context, "cross_tool", "agent_results", "planning_tools", "enhanced_brd_analysis_tools",
                   "shared", "cross_agent", "shared_data"]
        
        for ctx in contexts:
            data = memory.get(key, None, context=ctx)
            if data is not None:
                logger.info(f"Retrieved design data: {key} from context {ctx}")
                return data
                
        logger.warning(f"Design data {key} not found in any context")
        return default
        
    except Exception as e:
        logger.error(f"Error retrieving design data {key}: {e}")
        return default

def get_design_context_from_memory() -> Dict[str, Any]:
    """
    Get comprehensive design context from enhanced memory.
    
    Returns:
        Dict containing all relevant design context data
    """
    try:
        memory = get_enhanced_tool_memory()
        
        # Keys to retrieve for design context
        context_keys = [
            "brd_analysis", "requirements_summary", "tech_stack_recommendation",
            "architecture_pattern", "system_components", "data_model",
            "api_design", "security_architecture", "design_patterns",
            "project_domain", "project_scale", "compliance_requirements"
        ]
        
        context = {}
        for key in context_keys:
            data = retrieve_design_data(key)
            if data is not None:
                context[key] = data
                
        logger.info(f"Retrieved design context with {len(context)} elements")
        return context
        
    except Exception as e:
        logger.error(f"Error getting design context: {e}")
        return {}

def _get_design_rag_context(domain: str = None, requirements: str = None) -> str:
    """
    Get domain-specific RAG context for design tools.
    
    Args:
        domain: Application domain (healthcare, fintech, etc.)
        requirements: Project requirements for domain detection
    
    Returns:
        RAG context string for enhanced design decisions
    """
    try:
        # Try to get RAG manager
        from rag_manager import get_rag_manager
        rag_manager = get_rag_manager()
        
        if not rag_manager:
            logger.info("No RAG manager available, using memory-based context")
            return _get_design_memory_context()
        
        # Detect domain if not provided
        if not domain and requirements:
            req_lower = requirements.lower()
            if any(keyword in req_lower for keyword in ['healthcare', 'medical', 'patient', 'hipaa']):
                domain = 'healthcare'
            elif any(keyword in req_lower for keyword in ['financial', 'fintech', 'banking', 'payment']):
                domain = 'financial'
            elif any(keyword in req_lower for keyword in ['iot', 'device', 'sensor', 'embedded']):
                domain = 'iot'
            elif any(keyword in req_lower for keyword in ['ecommerce', 'shopping', 'retail']):
                domain = 'ecommerce'
            elif any(keyword in req_lower for keyword in ['enterprise', 'workflow', 'crm', 'erp']):
                domain = 'enterprise'
            elif any(keyword in req_lower for keyword in ['gaming', 'game', 'multiplayer']):
                domain = 'gaming'
        
        # Get domain-specific design queries
        queries = _get_domain_specific_design_queries(domain or 'general')
        
        # Retrieve context from RAG
        rag_context = ""
        for query in queries:
            try:
                retriever = rag_manager.get_retriever(search_kwargs={"k": 3})
                docs = retriever.get_relevant_documents(query)
                
                for doc in docs:
                    rag_context += f"\n--- {query} ---\n"
                    rag_context += doc.page_content[:500] + "\n"
                    
            except Exception as e:
                logger.warning(f"Failed to retrieve RAG context for query '{query}': {e}")
        
        # Combine with memory context
        memory_context = _get_design_memory_context()
        
        combined_context = f"""
RAG KNOWLEDGE BASE CONTEXT:
{rag_context}

MEMORY CONTEXT:
{memory_context}
"""
        
        logger.info(f"Retrieved design RAG context: {len(rag_context)} chars from RAG, {len(memory_context)} chars from memory")
        return combined_context
        
    except Exception as e:
        logger.error(f"Error getting design RAG context: {e}")
        return _get_design_memory_context()

def _get_domain_specific_design_queries(domain: str) -> List[str]:
    """
    Get domain-specific queries for RAG retrieval in design context.
    
    Args:
        domain: Application domain
    
    Returns:
        List of relevant queries for the domain
    """
    domain_queries = {
        'healthcare': [
            "HIPAA compliant system architecture patterns",
            "healthcare data security design patterns",
            "medical records API design best practices",
            "patient privacy system design",
            "healthcare audit trail implementation",
            "medical device integration patterns"
        ],
        'financial': [
            "PCI DSS compliant architecture design",
            "financial transaction processing patterns",
            "fraud detection system architecture",
            "banking API security design",
            "financial data encryption patterns",
            "payment gateway integration design"
        ],
        'iot': [
            "IoT device management architecture",
            "real-time data processing design patterns",
            "telemetry handling system design",
            "IoT security architecture patterns",
            "edge computing design principles",
            "device authentication patterns"
        ],
        'ecommerce': [
            "ecommerce platform architecture patterns",
            "product catalog system design",
            "shopping cart implementation patterns",
            "inventory management system design",
            "payment processing architecture",
            "order management system patterns"
        ],
        'enterprise': [
            "enterprise integration patterns",
            "workflow management system design",
            "role-based access control patterns",
            "enterprise API design patterns",
            "business process automation design",
            "enterprise data architecture"
        ],
        'gaming': [
            "game backend architecture patterns",
            "real-time multiplayer design",
            "game session management patterns",
            "leaderboard system architecture",
            "game state synchronization design",
            "gaming analytics architecture"
        ],
        'general': [
            "scalable system architecture patterns",
            "microservices design principles",
            "API design best practices",
            "database design patterns",
            "security architecture patterns",
            "system integration patterns"
        ]
    }
    
    return domain_queries.get(domain, domain_queries['general'])

def _get_design_memory_context() -> str:
    """
    Get design-specific context from enhanced memory.
    
    Returns:
        Memory context string for design decisions
    """
    try:
        context_data = get_design_context_from_memory()
        
        if not context_data:
            return "No design context available in memory."
        
        context_parts = []
        
        if 'brd_analysis' in context_data:
            context_parts.append(f"BRD Analysis: {str(context_data['brd_analysis'])[:200]}...")
        
        if 'tech_stack_recommendation' in context_data:
            context_parts.append(f"Tech Stack: {str(context_data['tech_stack_recommendation'])[:200]}...")
        
        if 'architecture_pattern' in context_data:
            context_parts.append(f"Architecture Pattern: {context_data['architecture_pattern']}")
        
        if 'project_domain' in context_data:
            context_parts.append(f"Project Domain: {context_data['project_domain']}")
        
        if 'design_patterns' in context_data:
            context_parts.append(f"Design Patterns: {str(context_data['design_patterns'])[:200]}...")
        
        return "\n".join(context_parts)
        
    except Exception as e:
        logger.error(f"Error getting design memory context: {e}")
        return "Error retrieving design context from memory."

def _store_design_patterns(patterns: Dict[str, Any], domain: str = None) -> bool:
    """
    Store design patterns in enhanced memory for future reference.
    
    Args:
        patterns: Design patterns to store
        domain: Optional domain for pattern categorization
    
    Returns:
        bool: Success status
    """
    try:
        memory = get_enhanced_tool_memory()
        
        # Store patterns with timestamp and domain
        pattern_data = {
            "patterns": patterns,
            "domain": domain,
            "timestamp": datetime.now().isoformat(),
            "source": "design_tools"
        }
        
        # Store in multiple contexts
        success = True
        success &= memory.set("design_patterns", pattern_data, context="design_tools")
        success &= memory.set("design_patterns", pattern_data, context="cross_tool")
        
        if domain:
            domain_key = f"design_patterns_{domain}"
            success &= memory.set(domain_key, pattern_data, context="design_tools")
        
        logger.info(f"Stored design patterns for domain: {domain or 'general'}")
        return success
        
    except Exception as e:
        logger.error(f"Error storing design patterns: {e}")
        return False

# Helper to get a configured LLM for tools
def get_tool_llm(temperature=0.0):
    """
    Gets a pre-configured LLM instance suitable for use within a tool.
    This simplifies tool logic and centralizes LLM creation.
    """
    from config import get_llm
    # The get_llm function from config.py should handle all the setup.
    # We just request an LLM with the desired temperature.
    return get_llm(temperature=temperature)

@tool("Analyze and summarize project requirements from BRD analysis")
def summarize_project_requirements(brd_analysis_json: Union[str, dict, None] = None):
    """
    Analyzes the full requirements analysis JSON and returns a concise summary
    of the project's main goal.
    
    Args:
        brd_analysis_json: Either a JSON string or dict containing BRD analysis data (can be empty - will try shared memory)
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'summarize_project_requirements' called")
    logger.info(f"Parameter received - brd_analysis_json type: {type(brd_analysis_json)}")
    
    try:
        # Try to get from enhanced memory if not provided
        if brd_analysis_json is None or (isinstance(brd_analysis_json, str) and not brd_analysis_json.strip()):
            logger.info("No BRD analysis provided, checking enhanced memory")
            stored_brd = retrieve_design_data("brd_analysis")
            if stored_brd:
                brd_analysis_json = stored_brd
                logger.info("Successfully retrieved BRD analysis from enhanced memory")
            else:
                logger.warning("No BRD analysis found in enhanced memory")
        
        # Handle ReAct agent inputs that may be nested JSON with escaped quotes
        if isinstance(brd_analysis_json, str):
            logger.debug(f"Input type: string, length: {len(brd_analysis_json)}")
            logger.debug(f"Input preview (first 100 chars): {brd_analysis_json[:100]}...")
            
            # Handle the problematic escaped quotes pattern from ReAct agent
            # Pattern: "\"{\\"project_name\\": \\"value\\"}\""
            if '\\"' in brd_analysis_json and brd_analysis_json.count('\\') > 0:
                logger.info("Detected escaped quotes pattern - cleaning up")
                try:
                    # Remove outer quotes and unescape inner quotes
                    cleaned = brd_analysis_json.strip()
                    if cleaned.startswith('"') and cleaned.endswith('"'):
                        cleaned = cleaned[1:-1]  # Remove outer quotes
                    # Replace escaped quotes with regular quotes
                    cleaned = cleaned.replace('\\"', '"')
                    # Replace escaped newlines
                    cleaned = cleaned.replace('\\n', '')
                    brd_analysis_json = cleaned
                    logger.info("Successfully cleaned escaped quotes from input")
                except Exception as clean_error:
                    logger.warning(f"Failed to clean escaped quotes: {str(clean_error)}")
                    
            # Check if this is a nested JSON structure from ReAct agent
            if isinstance(brd_analysis_json, str) and brd_analysis_json.strip().startswith('{'):
                logger.info("Detected possible JSON structure - attempting to parse")
                try:
                    # Parse the outer JSON to get the actual requirements data
                    outer_json = json.loads(brd_analysis_json)
                    
                    # Check for various parameter names that the ReAct agent might use
                    brd_keys = ['brd_analysis_json', 'requirements_analysis', 'brd_data', 'project_data', 'requirements_summary']
                    
                    for key in brd_keys:
                        if key in outer_json and outer_json[key]:
                            brd_analysis_json = outer_json[key]
                            logger.info(f"Found BRD data under key: {key}")
                            break
                            
                    # If no direct BRD key found, check if this might be a project_name parameter
                    if 'project_name' in outer_json:
                        logger.info(f"Found project_name parameter, constructing BRD")
                        brd_analysis_json = {
                            "project_name": outer_json['project_name'],
                            "project_summary": f"Project: {outer_json['project_name']}",
                            "requirements": []
                        }
                        
                except Exception as nested_error:
                    logger.warning(f"Failed to parse JSON: {str(nested_error)}")
                    # Continue with original string
        
        # If brd_analysis_json is None or empty string, create a default
        if brd_analysis_json is None or (isinstance(brd_analysis_json, str) and not brd_analysis_json.strip()):
            logger.warning("brd_analysis_json is None or empty - using default")
            brd_analysis_json = {
                "project_name": "Unknown Project",
                "project_summary": "No specific requirements provided",
                "requirements": []
            }
            
        # If brd_analysis_json is a string but not JSON, treat it as a project name
        if isinstance(brd_analysis_json, str) and not brd_analysis_json.strip().startswith('{'):
            logger.info(f"Using non-JSON string as project name: {brd_analysis_json}")
            brd_analysis_json = {
                "project_name": brd_analysis_json,
                "project_summary": f"Project: {brd_analysis_json}",
                "requirements": []
            }
            
        # Ensure brd_analysis_json is a dictionary for the next steps
        if isinstance(brd_analysis_json, str):
            try:
                brd_analysis_json = json.loads(brd_analysis_json)
                logger.info("Successfully parsed brd_analysis_json string to dict")
            except json.JSONDecodeError:
                logger.warning("Failed to parse brd_analysis_json as JSON, using as project name")
                brd_analysis_json = {
                    "project_name": brd_analysis_json,
                    "project_summary": f"Project: {brd_analysis_json}",
                    "requirements": []
                }
        
        # Get RAG context for enhanced requirements analysis
        rag_context = _get_design_rag_context(
            requirements=brd_analysis_json.get("project_summary", "") if isinstance(brd_analysis_json, dict) else ""
        )
        
        # Create a Pydantic output parser
        parser = PydanticOutputParser(pydantic_object=ProjectRequirementsSummaryOutput)

        # Create an enhanced prompt with RAG context
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert requirements analyst with access to industry knowledge and patterns."),
            ("human", 
             "Extract the key project information and requirements from this data:\n\n"
             "Project: {project_name}\n\n"
             "Summary: {project_summary}\n\n"
             "Requirements: \n{requirements}\n\n"
             "RELEVANT KNOWLEDGE CONTEXT:\n{rag_context}\n\n"
             "Provide a concise, well-organized summary focusing on technical aspects and leveraging relevant patterns from the knowledge base:\n"
             "{format_instructions}")
        ])

        # Format the prompt with the parsed data and get response
        chain = prompt | get_tool_llm(temperature=0.1) | parser
        
        # Ensure brd_analysis_json is a dictionary
        if not isinstance(brd_analysis_json, dict):
            brd_analysis_json = {"project_name": "Unknown Project", "project_summary": "No data available", "requirements": []}
        
        result = chain.invoke({
            "project_name": brd_analysis_json.get("project_name", "N/A"),
            "project_summary": brd_analysis_json.get("project_summary", "N/A"),
            "requirements": json.dumps(brd_analysis_json.get("requirements", []), indent=2),
            "rag_context": rag_context,
            "format_instructions": parser.get_format_instructions()
        })
        
        # Store result in enhanced memory for cross-tool access
        store_design_data("requirements_summary", result.dict())
        
        # Extract and store domain information
        domain = None
        if result.summary:
            summary_lower = result.summary.lower()
            if any(keyword in summary_lower for keyword in ['healthcare', 'medical', 'patient']):
                domain = 'healthcare'
            elif any(keyword in summary_lower for keyword in ['financial', 'fintech', 'banking']):
                domain = 'financial'
            elif any(keyword in summary_lower for keyword in ['iot', 'device', 'sensor']):
                domain = 'iot'
            elif any(keyword in summary_lower for keyword in ['ecommerce', 'shopping', 'retail']):
                domain = 'ecommerce'
            elif any(keyword in summary_lower for keyword in ['enterprise', 'workflow']):
                domain = 'enterprise'
            elif any(keyword in summary_lower for keyword in ['gaming', 'game']):
                domain = 'gaming'
        
        if domain:
            # Store the domain information for later use
            store_design_data("project_domain", domain)
        
        return result

    except Exception as e:
        logger.error(f"Error in summarize_project_requirements: {e}", exc_info=True)
        return ProjectRequirementsSummaryOutput(
            project_name="Error",
            summary=f"Error extracting project requirements: {str(e)}",
            technical_requirements=["Error occurred during extraction"],
            functional_requirements=["Error occurred during extraction"]
        )

@tool(args_schema=ArchitecturePatternSelectionInput)
def select_architecture_pattern(requirements_summary: str, tech_stack_json: Optional[Union[str, dict]] = "{}") -> ArchitecturePatternOutput:
    """
    Selects the optimal architecture pattern based on requirements summary and optional tech stack.
    
    Args:
        requirements_summary: A summary of the project's technical requirements
        tech_stack_json: JSON string or dict containing the recommended technology stack (optional, defaults to empty)
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'select_architecture_pattern' called")
    
    try:
        logger.info(f"Selecting architecture pattern with requirements: {requirements_summary[:50]}...")
        
        # Parse the tech stack JSON if provided - handle both string and dict inputs
        tech_stack = None
        if tech_stack_json and tech_stack_json != "{}":
            if isinstance(tech_stack_json, dict):
                logger.info("Tech stack input is already a dictionary, using directly")
                tech_stack = tech_stack_json
            elif isinstance(tech_stack_json, str):
                logger.info("Tech stack input is a string, attempting to parse as JSON")
                try:
                    tech_stack = json.loads(tech_stack_json)
                    logger.info("Successfully parsed tech stack JSON string")
                except json.JSONDecodeError as e:
                    logger.warning(f"Tech stack JSON parsing failed: {str(e)}")
                    tech_stack = {"note": "Could not parse tech stack", "raw_input": tech_stack_json}
            else:
                logger.warning(f"Unexpected tech stack input type: {type(tech_stack_json)}")
                tech_stack = {"note": "Unexpected input type", "raw_input": str(tech_stack_json)}
        else:
            tech_stack = {}
            
        logger.info(f"Tech stack data available: {bool(tech_stack)}")

        # Get enhanced memory context and RAG information
        memory_context = get_design_context_from_memory()
        domain = memory_context.get("project_domain", "")
        
        # Get RAG context for architecture patterns
        rag_context = get_design_rag_context("architecture_pattern", domain, 
                                           requirements=requirements_summary, 
                                           tech_stack=tech_stack)

        # Create a Pydantic output parser
        parser = PydanticOutputParser(pydantic_object=ArchitecturePatternOutput)        # Create a clean prompt with domain and scale awareness
        prompt = ChatPromptTemplate.from_messages([
            ("system", 
             "You are an expert Software Architect who selects appropriate architecture patterns "
             "based on domain requirements, scale, and compliance needs. Consider:"
             "\n- Healthcare: Prioritize HIPAA compliance, audit trails, security"
             "\n- Financial: Emphasize security, PCI compliance, transaction integrity" 
             "\n- IoT: Focus on resource constraints, real-time processing, edge computing"
             "\n- E-commerce: Consider high availability, scalability, payment processing"
             "\n- Enterprise: Emphasize integration, workflow management, role-based access"
             "\n- Startups: Balance simplicity with growth potential, cost-effectiveness"
             "\n- Real-time: Prioritize event-driven architecture, low latency"
             "\n- Large-scale: Focus on microservices, distributed systems, data partitioning"),
            ("human", 
             "Select the most appropriate architecture pattern for this project based on these requirements and technology stack.\n\n"
             "REQUIREMENTS: {requirements}\n\n"
             "TECHNOLOGY STACK: {tech_stack}\n\n"
             "DOMAIN CONTEXT: {domain}\n\n"
             "RAG KNOWLEDGE BASE:\n{rag_context}\n\n"
             "Analyze the domain (healthcare, financial, IoT, etc.), scale requirements, and compliance needs "
             "before selecting the pattern. Use the knowledge base information to inform your decision. "
             "Provide your recommendation with detailed justification:\n"
             "{format_instructions}")
        ])

        # Get LLM, create chain, and execute it
        chain = prompt | get_tool_llm(temperature=0.0) | parser
        
        result = chain.invoke({
            "requirements": requirements_summary,
            "tech_stack": json.dumps(tech_stack, indent=2),
            "domain": domain or "General purpose application",
            "rag_context": rag_context or "No additional context available",
            "format_instructions": parser.get_format_instructions()
        })        
        
        # Store the architecture pattern result for other tools to use
        if result and hasattr(result, 'pattern'):
            store_design_data("architecture_pattern", result.pattern)
            store_design_data("architecture_justification", result.justification)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in select_architecture_pattern: {e}", exc_info=True)
        # Determine appropriate fallback based on available context
        fallback_pattern = "Layered Architecture"
        fallback_reason = "Error occurred during pattern selection"
        
        # Try to infer a better fallback from requirements if available
        if requirements_summary:
            req_lower = requirements_summary.lower()
            if any(keyword in req_lower for keyword in ['microservice', 'distributed', 'scalable']):
                fallback_pattern = "Microservices"
                fallback_reason = "Inferred from scalability requirements"
            elif any(keyword in req_lower for keyword in ['real-time', 'event', 'streaming']):
                fallback_pattern = "Event-Driven Architecture"
                fallback_reason = "Inferred from real-time requirements"
            elif any(keyword in req_lower for keyword in ['api', 'rest', 'web service']):
                fallback_pattern = "Service-Oriented Architecture"
                fallback_reason = "Inferred from API-centric requirements"
        
        return ArchitecturePatternOutput(
            pattern=fallback_pattern,
            justification=f"{fallback_reason}: {str(e)}. Selected {fallback_pattern} as it provides good separation of concerns and is widely applicable.",
            key_benefits=["Clear separation of concerns", "Well-established pattern", "Flexible and maintainable"],
            potential_drawbacks=["May not be optimal for this specific use case without further analysis"]
        )

@tool(args_schema=SystemComponentsIdentificationInput)
def identify_system_components(requirements_summary: str, architecture_pattern: Optional[str] = "") -> SystemComponentsOutput:
    """
    Identifies the main system components/modules needed based on requirements and architecture.
    
    Args:
        requirements_summary: Summary of technical requirements that influence system components
        architecture_pattern: The selected architecture pattern (optional)
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'identify_system_components' called")
    
    try:        # Validate and clean inputs
        if not requirements_summary:
            logger.info("requirements_summary is empty - using contextual default")
            requirements_summary = "A system requiring modular components with standard architecture patterns"
            
        if not architecture_pattern:
            architecture_pattern = "Not specified, will infer from requirements"
        
        logger.info(f"Identifying system components with requirements: {requirements_summary[:50]}...")
        logger.info(f"Architecture pattern: {architecture_pattern}")
          # Create prompt template with domain awareness
        prompt = ChatPromptTemplate.from_messages([
            ("system", 
             "You are a system designer who identifies core system components based on domain requirements. "
             "Consider domain-specific components:"
             "\n- Healthcare: Patient Management, Medical Records, Compliance Module, Audit System"
             "\n- Financial: Transaction Processing, Account Management, Fraud Detection, Compliance Engine"
             "\n- IoT: Device Management, Data Collection, Real-time Processing, Device Gateway"
             "\n- E-commerce: Product Catalog, Shopping Cart, Payment Processing, Order Management"
             "\n- Enterprise: User Management, Workflow Engine, Integration Layer, Reporting System"
             "\n- Real-time: Event Processing, Stream Analytics, Message Broker, State Management"
             "\nAlways respond with a valid JSON array of meaningful component names."),
            ("human", 
             "Based on these project requirements and architecture pattern, "
             "identify the main system components/modules needed:\n\n"
             "REQUIREMENTS: {requirements}\n\n"
             "ARCHITECTURE PATTERN: {architecture}\n\n"
             "First analyze the domain from the requirements, then identify components that are "
             "specific and meaningful for that domain. Avoid generic names like 'Frontend' or 'Backend'. "
             "Return ONLY a JSON array of component names. For example: [\"User Authentication Service\", \"Patient Records Manager\"]")
        ])
        
        # Format the prompt with the variables
        formatted_prompt = prompt.format_prompt(
            requirements=requirements_summary,
            architecture=architecture_pattern
        )
        
        # Use strict JSON mode for reliable parsing
        from tools.json_handler import JsonHandler
        json_llm = JsonHandler.create_strict_json_llm(get_tool_llm(temperature=0.0))
        
        # Invoke LLM with the formatted prompt
        logger.debug(f"Invoking LLM for component identification with temp=0.0")
        response = json_llm.invoke(formatted_prompt)
        
        # Process response - handle different response types
        components = None  # Initialize components variable
        if isinstance(response, list):
            components = response
        else:
            content = response.content if hasattr(response, 'content') else str(response)
            # Try explicit JSON extraction as fallback
            try:
                components = JsonHandler.extract_json_from_text(content)
            except Exception as json_error:
                logger.warning(f"JSON extraction failed: {str(json_error)}")
                components = None
                
            if not isinstance(components, list):
                logger.warning(f"Could not extract valid component list, using domain-aware default")
                # Create domain-aware defaults based on requirements
                req_lower = requirements_summary.lower()
                if any(keyword in req_lower for keyword in ['healthcare', 'medical', 'patient']):
                    components = ["Patient Management Service", "Medical Records System", "Compliance Module"]
                elif any(keyword in req_lower for keyword in ['financial', 'fintech', 'payment', 'banking']):
                    components = ["Account Management Service", "Transaction Processing Engine", "Fraud Detection System"]
                elif any(keyword in req_lower for keyword in ['iot', 'device', 'sensor']):
                    components = ["Device Management Gateway", "Data Collection Service", "Real-time Analytics Engine"]
                elif any(keyword in req_lower for keyword in ['ecommerce', 'e-commerce', 'shopping', 'cart']):
                    components = ["Product Catalog Service", "Shopping Cart Manager", "Order Processing System"]
                else:
                    components = ["Authentication Service", "Business Logic Layer", "Data Access Layer"]
                
        # Convert components to SystemComponentOutput objects
        system_components = []
        for comp_name in components:
            system_components.append(SystemComponentOutput(
                name=comp_name,
                description=f"System component: {comp_name}"
            ))
        
        # Store the system components in shared memory for other tools to access
        result = SystemComponentsOutput(components=system_components)
        store_design_data("system_components", [comp.dict() for comp in system_components])
        logger.info(f"Stored {len(system_components)} system components in shared memory")
            
        return result

    except Exception as e:
        logger.error(f"Error in identify_system_components: {str(e)}", exc_info=True)
        # Return domain-aware fallback output on error
        req_lower = requirements_summary.lower() if requirements_summary else ""
        if any(keyword in req_lower for keyword in ['healthcare', 'medical', 'patient']):
            fallback_components = [
                SystemComponentOutput(name="Patient Management Service", description="Manages patient information and records"),
                SystemComponentOutput(name="Medical Records System", description="Stores and retrieves medical data"),
                SystemComponentOutput(name="Compliance Module", description="Ensures HIPAA and regulatory compliance")
            ]
        elif any(keyword in req_lower for keyword in ['financial', 'fintech', 'payment']):
            fallback_components = [
                SystemComponentOutput(name="Account Management Service", description="Manages user accounts and profiles"),
                SystemComponentOutput(name="Transaction Processing Engine", description="Handles financial transactions"),
                SystemComponentOutput(name="Compliance Module", description="Ensures PCI-DSS and regulatory compliance")
            ]
        elif any(keyword in req_lower for keyword in ['iot', 'device', 'sensor']):
            fallback_components = [
                SystemComponentOutput(name="Device Gateway", description="Manages IoT device connections"),
                SystemComponentOutput(name="Data Collection Service", description="Collects and processes sensor data"),
                SystemComponentOutput(name="Analytics Engine", description="Processes real-time device data")
            ]
        else:
            fallback_components = [
                SystemComponentOutput(name="Authentication Service", description="Handles user authentication and authorization"),
                SystemComponentOutput(name="Business Logic Layer", description="Core application logic and processing"),
                SystemComponentOutput(name="Data Access Layer", description="Database and data storage interface")
            ]
        
        # Store fallback components in shared memory as well
        result = SystemComponentsOutput(components=fallback_components)
        store_design_data("system_components", [comp.dict() for comp in fallback_components])
        logger.info(f"Stored {len(fallback_components)} fallback system components in shared memory")
        return result

@tool(args_schema=ComponentStructureDesignInput)
def design_component_structure(component_name: Union[str, dict], requirements_summary: Optional[str] = None) -> ComponentDesignOutput:
    """
    Designs the detailed structure for a specific system component.
    
    Args:
        component_name: Either the component name (str) or a dict/JSON string containing both component_name and requirements_summary
        requirements_summary: A summary of the project's technical requirements (optional if component_name is a dict)
    """    # Import the model at the function level to avoid circular imports
    from models.data_contracts import ComponentDesignOutput, InternalSubComponent
    
    logger = logging.getLogger(__name__)
    logger.info(f"Tool 'design_component_structure' called")
    
    try:
        # Handle ReAct agent inputs that may be nested JSON with escaped quotes
        if isinstance(component_name, str) and component_name.startswith('{'):
            try:
                # Try to parse as JSON string first
                parsed_input = json.loads(component_name)
                if isinstance(parsed_input, dict):
                    actual_component_name = parsed_input.get('component_name', 'Unknown Component')
                    actual_requirements_summary = parsed_input.get('requirements_summary', 'No specific requirements provided')
                else:
                    actual_component_name = component_name
                    actual_requirements_summary = requirements_summary or 'No specific requirements provided'
            except json.JSONDecodeError:
                actual_component_name = component_name
                actual_requirements_summary = requirements_summary or 'No specific requirements provided'
        elif isinstance(component_name, dict):
            # Direct dict input
            actual_component_name = component_name.get('component_name', 'Unknown Component')
            actual_requirements_summary = component_name.get('requirements_summary', 'No specific requirements provided')
        else:
            # Normal string input
            actual_component_name = component_name
            actual_requirements_summary = requirements_summary or 'No specific requirements provided'
        
        # Validate and clean inputs
        if not actual_component_name:
            logger.warning("component_name is empty - using default")
            actual_component_name = "Unknown Component"
            
        if not actual_requirements_summary:
            logger.warning("requirements_summary is empty - using default")
            actual_requirements_summary = "No specific requirements provided"
        
        logger.info(f"Designing structure for component: {actual_component_name}")
        
        # Create a clean prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert Component Designer who always responds in valid JSON. "
                      "The dependencies field must be a list of strings (component names), not objects. "
                      "The internal_components field must be a list of objects, each with 'name' and 'responsibility' fields."),
            ("human", 
             "Design the detailed structure for this system component:\n\n"
             "COMPONENT NAME: {component}\n\n"
             "PROJECT REQUIREMENTS: {requirements}\n\n"
             "Provide a detailed structure in JSON format including:\n"
             "- The component name\n"
             "- A list of internal sub-components with their name and responsibilities\n"
             "- Dependencies on other components (as strings of component names)\n"
             "- Applicable design patterns\n\n"
             "IMPORTANT: Dependencies must be a list of strings, not objects.")
        ])

        # Format the prompt with the data
        formatted_prompt = prompt.format_prompt(
            component=actual_component_name,
            requirements=actual_requirements_summary
        )
        
        # Invoke the LLM with JSON handling
        from tools.json_handler import JsonHandler
        json_llm = JsonHandler.create_strict_json_llm(get_tool_llm(temperature=0.0))
        response = json_llm.invoke(formatted_prompt)
        
        # Process the response
        component_design = None
        if isinstance(response, dict):
            component_design = response
        else:
            content = response.content if hasattr(response, 'content') else str(response)
            component_design = JsonHandler.extract_json_from_text(content)
            
        # Ensure we have a dict
        if not isinstance(component_design, dict):
            logger.warning(f"Failed to get valid JSON response for component {actual_component_name}, using fallback")
            component_design = {
                "name": actual_component_name,
                "responsibilities": ["Main functionality of the component"],
                "internal_components": [
                    {"name": "Core Logic", "responsibility": "Main functionality of the component"}
                ],
                "dependencies": [],
                "design_patterns": ["Repository", "Factory"]
            }
        
        # Ensure the name field is present
        if "name" not in component_design:
            logger.warning(f"Adding missing name field to component design: {actual_component_name}")
            component_design["name"] = actual_component_name
            
        # Ensure we have the required fields with correct types
        if "responsibilities" not in component_design:
            component_design["responsibilities"] = ["Main functionality of the component"]
            
        # Fix dependencies to ensure they're strings
        if "dependencies" in component_design:
            fixed_dependencies = []
            for dep in component_design["dependencies"]:
                if isinstance(dep, dict) and "name" in dep:
                    fixed_dependencies.append(dep["name"])
                elif isinstance(dep, str):
                    fixed_dependencies.append(dep)
            component_design["dependencies"] = fixed_dependencies
        else:
            component_design["dependencies"] = []
            
        # Fix internal_components to ensure proper structure
        if "internal_components" in component_design:
            fixed_components = []
            for comp in component_design["internal_components"]:
                if isinstance(comp, dict):
                    # Ensure it has both required fields
                    if "name" in comp and "responsibility" in comp:
                        fixed_components.append({
                            "name": comp["name"],
                            "responsibility": comp["responsibility"]
                        })
            component_design["internal_components"] = fixed_components
        else:
            component_design["internal_components"] = [
                {"name": "Core Logic", "responsibility": "Main functionality of the component"}
            ]
            
        # Ensure design_patterns is a list of strings
        if "design_patterns" not in component_design or not component_design["design_patterns"]:
            component_design["design_patterns"] = ["Repository", "Factory"]
        
        # Create and validate with Pydantic model
        try:
            valid_model = ComponentDesignOutput(**component_design)
            return valid_model
        except Exception as validation_error:
            logger.error(f"Validation error for component {actual_component_name}: {validation_error}")
            logger.debug(f"Failed component data: {component_design}")
            # Create a minimal valid object
            return ComponentDesignOutput(
                name=actual_component_name,
                responsibilities=["Main functionality of the component"],
                internal_components=[
                    InternalSubComponent(name="Core Logic", responsibility="Main functionality of the component")
                ],
                dependencies=[],
                design_patterns=["Repository", "Factory"]
            )

    except Exception as e:
        logger.error(f"Error in design_component_structure: {e}", exc_info=True)        # Return a valid Pydantic model - import here in case the earlier import failed
        from models.data_contracts import ComponentDesignOutput, InternalSubComponent
        
        # Extract component name from input for fallback
        fallback_name = "Unknown Component"
        if isinstance(component_name, str) and not component_name.startswith('{'):
            fallback_name = component_name
        elif isinstance(component_name, dict):
            fallback_name = component_name.get('component_name', 'Unknown Component')
        elif isinstance(component_name, str):
            try:
                parsed = json.loads(component_name)
                fallback_name = parsed.get('component_name', 'Unknown Component')
            except:
                fallback_name = "Unknown Component"
                
        return ComponentDesignOutput(
            name=fallback_name,
            responsibilities=["Main functionality of the component"],
            internal_components=[
                InternalSubComponent(name="Core Logic", responsibility="Main functionality of the component")
            ],
            dependencies=[],
            design_patterns=["Repository", "Factory"]
        )

@tool(args_schema=DataModelDesignInput)
def design_data_model(requirements_summary: Union[str, dict], components: Optional[Union[str, List[str]]] = None, database_technology: Optional[str] = None) -> DataModelOutput:
    """
    Designs a complete data model for the system including entities, relationships and schema.
    
    Args:
        requirements_summary: A summary of the project's technical requirements
        components: JSON string containing system components or a list of component names
        database_technology: The selected database technology (e.g., 'PostgreSQL', 'MongoDB')
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'design_data_model' called")
    
    try:        # Handle ReAct agent inputs that may be nested JSON with escaped quotes
        if isinstance(requirements_summary, str) and requirements_summary.startswith('{'):
            try:
                # Try to parse as JSON string first
                parsed_input = json.loads(requirements_summary)
                if isinstance(parsed_input, dict):
                    actual_requirements_summary = parsed_input.get('requirements_summary', 'A system requiring data storage and management')
                    actual_components = parsed_input.get('components', ["Database", "API Layer", "Frontend"])
                    actual_database_technology = parsed_input.get('database_technology', None)
                else:
                    actual_requirements_summary = requirements_summary
                    actual_components = components or ["Database", "API Layer", "Frontend"]
                    actual_database_technology = database_technology
            except json.JSONDecodeError:
                actual_requirements_summary = requirements_summary
                actual_components = components or ["Database", "API Layer", "Frontend"]
                actual_database_technology = database_technology
        elif isinstance(requirements_summary, dict):
            # Direct dict input
            actual_requirements_summary = requirements_summary.get('requirements_summary', 'A system requiring data storage and management')
            actual_components = requirements_summary.get('components', ["Database", "API Layer", "Frontend"])
            actual_database_technology = requirements_summary.get('database_technology', None)
        else:
            # Normal individual parameters input
            actual_requirements_summary = requirements_summary or 'A system requiring data storage and management'
            actual_components = components or ["Database", "API Layer", "Frontend"]
            actual_database_technology = database_technology
        
        # Infer database technology from requirements if not provided
        if not actual_database_technology:
            req_lower = actual_requirements_summary.lower()
            if any(keyword in req_lower for keyword in ['document', 'json', 'flexible schema', 'nosql']):
                actual_database_technology = "MongoDB"
                logger.info("Inferred database technology: MongoDB (document-based requirements)")
            elif any(keyword in req_lower for keyword in ['graph', 'relationship', 'network', 'social']):
                actual_database_technology = "Neo4j"
                logger.info("Inferred database technology: Neo4j (graph-based requirements)")
            elif any(keyword in req_lower for keyword in ['time series', 'metrics', 'analytics', 'iot']):
                actual_database_technology = "InfluxDB"
                logger.info("Inferred database technology: InfluxDB (time-series requirements)")
            elif any(keyword in req_lower for keyword in ['cache', 'session', 'real-time', 'redis']):
                actual_database_technology = "Redis"
                logger.info("Inferred database technology: Redis (caching/real-time requirements)")
            elif any(keyword in req_lower for keyword in ['relational', 'acid', 'transaction']):
                actual_database_technology = "PostgreSQL"
                logger.info("Inferred database technology: PostgreSQL (relational requirements)")
            else:
                # Default based on scale and domain
                if any(keyword in req_lower for keyword in ['large scale', 'millions', 'enterprise']):
                    actual_database_technology = "PostgreSQL"
                    logger.info("Defaulted to PostgreSQL for large-scale requirements")
                else:
                    actual_database_technology = "SQLite"
                    logger.info("Defaulted to SQLite for simple/startup requirements")
        
        # Log detailed information about the processed input
        logger.info(f"Designing data model with database technology: {actual_database_technology}")
        logger.info(f"Requirements summary length: {len(actual_requirements_summary) if actual_requirements_summary else 0} chars")
        logger.info(f"Components format: {type(actual_components)}")
        
        # Get enhanced memory context and RAG information
        memory_context = get_design_context_from_memory()
        domain = memory_context.get("project_domain", "")
        
        # Try to get components from memory if none provided
        if not actual_components or actual_components == ["Database", "API Layer", "Frontend"]:
            if "system_components" in memory_context:
                logger.info("Retrieved system components from shared memory for data model design")
                actual_components = memory_context["system_components"]
                if isinstance(actual_components, list) and actual_components:
                    # Extract component names if they're objects
                    component_names = []
                    for comp in actual_components:
                        if isinstance(comp, dict) and "name" in comp:
                            component_names.append(comp["name"])
                        elif isinstance(comp, str):
                            component_names.append(comp)
                    if component_names:
                        actual_components = component_names
                        logger.info(f"Using {len(component_names)} components from memory for data modeling")
        
        # Get RAG context for data model design
        rag_context = get_design_rag_context("data_model", domain, 
                                           database_technology=actual_database_technology,
                                           requirements=actual_requirements_summary)
          
        # Validate inputs are not empty and provide defaults if needed
        if not actual_requirements_summary:
            logger.warning("requirements_summary is empty - using default")
            actual_requirements_summary = "A system requiring data storage and management"
            
        if not actual_components:
            logger.warning("components is empty - using default")
            actual_components = ["Database", "API Layer", "Frontend"]
          # Safely handle components which could be a string or list
        components_data = actual_components
        if isinstance(actual_components, str):
            try:
                components_data = json.loads(actual_components)
                logger.info(f"Successfully parsed components JSON: {len(components_data)} components")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse components JSON: {e}. Using as single component.")
                components_data = [actual_components]
        
        if not isinstance(components_data, list):
            logger.warning(f"Components is not a list. Type: {type(components_data)}. Converting to list.")
            if isinstance(components_data, dict):
                if "component_names" in components_data:
                    components_data = components_data["component_names"]
                else:
                    components_data = [str(components_data)]
            else:
                components_data = [str(components_data)]
                  # Create a domain and technology-aware prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", 
             "You are an expert Database Designer who adapts data models to specific domains and technologies. "
             "Consider domain-specific requirements:"
             "\n- Healthcare: HIPAA compliance, audit trails, patient privacy, data retention"
             "\n- Financial: PCI compliance, transaction integrity, fraud detection, regulatory reporting"
             "\n- IoT: Time-series data, device management, telemetry, edge constraints"
             "\n- E-commerce: Product catalogs, inventory, orders, customer data, analytics"
             "\n- Enterprise: User management, roles, workflows, integration capabilities"
             "\n- Real-time: Event sourcing, streaming data, low-latency access patterns"
             "\nAlways respond in valid JSON with appropriate schema design for the target database."),
            ("human", 
             "Design a complete data model based on these requirements and components:\n\n"
             "REQUIREMENTS: {requirements}\n\n"
             "COMPONENTS: {components}\n\n"
             "DATABASE TECHNOLOGY: {database}\n\n"
             "DOMAIN CONTEXT: {domain}\n\n"
             "DATA MODELING KNOWLEDGE BASE:\n{rag_context}\n\n"
             "Analyze the domain (healthcare, financial, IoT, etc.) and compliance requirements first.\n"
             "Use the data modeling knowledge base to inform your schema design decisions.\n"
             "For SQL databases, include tables, fields, data types, primary/foreign keys, and relationships.\n"
             "For NoSQL databases, include collections, document structures, indexes, and relationships.\n"
             "For graph databases, include nodes, edges, and properties.\n"
             "For time-series databases, include measurements, tags, and retention policies.\n\n"
             "Return a JSON object with schema_type and appropriate structures for {database}.")
        ])
        
        formatted_prompt = prompt.format_prompt(
            requirements=actual_requirements_summary,
            components=json.dumps(components_data),
            database=actual_database_technology,
            domain=domain or "General purpose application",
            rag_context=rag_context or "No additional data modeling context available"
        )
        
        # Invoke the LLM with JSON handling
        from tools.json_handler import JsonHandler
        json_llm = JsonHandler.create_strict_json_llm(get_tool_llm(temperature=0.0))
          # Invoke LLM with the formatted prompt
        logger.debug(f"Invoking LLM for data model design with temp=0.0")
        response = json_llm.invoke(formatted_prompt)
        
        # Process response - handle different response types
        data_model = None
        if isinstance(response, dict):
            data_model = response
        else:
            content = response.content if hasattr(response, 'content') else str(response)
            # Try to extract JSON object
            data_model = JsonHandler.extract_json_from_text(content)        
        if not isinstance(data_model, dict):
            logger.warning(f"Using fallback data model for {actual_database_technology}")
            data_model = {
                "schema_type": actual_database_technology,
                "tables": [
                    {
                        "name": "users",
                        "purpose": "Stores user information",
                        "fields": [
                            {"name": "id", "type": "int", "constraints": ["primary key", "auto-increment"]},
                            {"name": "username", "type": "varchar(50)", "constraints": ["not null", "unique"]}
                        ],
                        "relationships": []
                    }
                ]
            }
        
        # Create a proper DataModelOutput object
        schema_type = data_model.get("schema_type", actual_database_technology)
          # Extract tables/collections
        tables = []
        if "tables" in data_model:
            tables = data_model["tables"]
        elif "collections" in data_model:
            tables = data_model["collections"]
        
        # Convert tables to the proper format if needed
        formatted_tables = []
        for table in tables:
            if isinstance(table, dict):
                # Map field names from LLM output to Pydantic model fields
                formatted_table = {
                    "name": table.get("name") or table.get("table_name", "unknown_table"),
                    "purpose": table.get("purpose") or table.get("description", "Table purpose"),
                    "fields": [],
                    "relationships": table.get("relationships", [])
                }
                
                # Handle fields with proper field name mapping
                table_fields = table.get("fields", [])
                for field in table_fields:
                    if isinstance(field, dict):
                        formatted_field = {
                            "name": field.get("name") or field.get("field_name", "unknown_field"),
                            "type": field.get("type") or field.get("data_type", "varchar"),
                            "constraints": field.get("constraints", [])
                        }
                        formatted_table["fields"].append(formatted_field)
                
                formatted_tables.append(formatted_table)
                
        # Create and return the output model
        result = DataModelOutput(
            schema_type=schema_type,
            tables=formatted_tables,
            description=f"Data model for {actual_database_technology}"
        )
        
        # Store data model for other tools to use
        store_design_data("data_model", {
            "schema_type": result.schema_type,
            "tables": [table.dict() for table in result.tables]
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in design_data_model: {e}", exc_info=True)        # Create a fallback DataModelOutput
        fallback_db_tech = "SQL"
        if 'actual_database_technology' in locals():
            fallback_db_tech = actual_database_technology
        elif database_technology:
            fallback_db_tech = database_technology
            
        return DataModelOutput(
            schema_type=fallback_db_tech,
            tables=[
                {
                    "name": "users",
                    "purpose": "Stores user information",
                    "fields": [
                        {"name": "id", "type": "int", "constraints": ["primary key"]},
                        {"name": "username", "type": "varchar(50)", "constraints": ["not null"]}
                    ],
                    "relationships": []
                }
            ]
        )

@tool(args_schema=ApiEndpointsDesignInput)
def design_api_endpoints(requirements_summary: Union[str, dict], components: Optional[str] = None) -> ApiEndpointsOutput:
    """
    Designs the API endpoints for the system.
    
    Args:
        requirements_summary: A summary of the project's technical requirements OR a JSON string/dict containing both requirements_summary and components
        components: JSON string containing system components (optional)
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'design_api_endpoints' called")
    
    try:
        # Handle ReAct agent inputs that may be nested JSON with escaped quotes
        if isinstance(requirements_summary, str) and requirements_summary.startswith('{'):
            logger.info("Received JSON string input from ReAct agent - parsing for requirements_summary and components")
            try:
                # Try to parse as JSON string first
                parsed_input = json.loads(requirements_summary)
                if isinstance(parsed_input, dict):
                    actual_requirements_summary = parsed_input.get('requirements_summary', 'A web application with REST API endpoints')
                    actual_components = parsed_input.get('components', '["Web Service", "API Layer", "Database Service"]')
                    logger.info("Successfully extracted requirements_summary and components from JSON input")
                else:
                    actual_requirements_summary = requirements_summary
                    actual_components = components or '["Web Service", "API Layer", "Database Service"]'
            except json.JSONDecodeError as e:
                # Check if this is an "Extra data" error (concatenated JSON)
                if "Extra data" in str(e):
                    logger.warning(f"Detected 'Extra data' error - attempting to extract first JSON object: {str(e)}")
                    try:
                        # Extract just the first complete JSON object
                        start_idx = requirements_summary.find('{')
                        if start_idx != -1:
                            brace_count = 0
                            for i in range(start_idx, len(requirements_summary)):
                                if requirements_summary[i] == '{':
                                    brace_count += 1
                                elif requirements_summary[i] == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        json_part = requirements_summary[start_idx:i+1]
                                        parsed_data = json.loads(json_part)
                                        actual_requirements_summary = parsed_data.get('requirements_summary', 'A web application with REST API endpoints')
                                        actual_components = parsed_data.get('components', '["Web Service", "API Layer", "Database Service"]')
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
                            from .json_handler import JsonHandler
                            parsed_data = JsonHandler.extract_json_from_text(requirements_summary)
                            
                            if isinstance(parsed_data, dict):
                                actual_requirements_summary = parsed_data.get('requirements_summary', 'A web application with REST API endpoints')
                                actual_components = parsed_data.get('components', '["Web Service", "API Layer", "Database Service"]')
                                logger.info("Successfully parsed with JsonHandler")
                            else:
                                raise ValueError("JsonHandler did not return a valid dictionary")
                                
                        except Exception as handler_error:
                            logger.error(f"JsonHandler also failed: {str(handler_error)} - using fallback")
                            actual_requirements_summary = requirements_summary[:500]  # Use truncated string
                            actual_components = '["Web Service", "API Layer", "Database Service"]'
                            logger.info("Created fallback input using truncated requirements string")
                else:
                    logger.warning(f"Standard JSON parsing failed: {str(e)} - trying JsonHandler for robust parsing")
                    
                    # JsonHandler fallback for standard JSON parsing failures
                    try:
                        from .json_handler import JsonHandler
                        parsed_data = JsonHandler.extract_json_from_text(requirements_summary)
                        
                        if isinstance(parsed_data, dict):
                            actual_requirements_summary = parsed_data.get('requirements_summary', 'A web application with REST API endpoints')
                            actual_components = parsed_data.get('components', '["Web Service", "API Layer", "Database Service"]')
                            logger.info("Successfully parsed with JsonHandler")
                        else:
                            raise ValueError("JsonHandler did not return a valid dictionary")
                            
                    except Exception as handler_error:
                        logger.error(f"JsonHandler also failed: {str(handler_error)} - using fallback")
                        actual_requirements_summary = requirements_summary[:500]  # Use truncated string
                        actual_components = '["Web Service", "API Layer", "Database Service"]'
                        logger.info("Created fallback input using truncated requirements string")
        elif isinstance(requirements_summary, dict):
            logger.info("Received dict input, extracting requirements_summary and components")
            actual_requirements_summary = requirements_summary.get('requirements_summary', 'A web application with REST API endpoints')
            actual_components = requirements_summary.get('components', '["Web Service", "API Layer", "Database Service"]')
        else:
            # Normal individual parameters input
            actual_requirements_summary = requirements_summary
            actual_components = components
              # Handle missing components parameter
        if actual_components is None:
            logger.info("No components provided after parsing - this is expected for single-string ReAct agent inputs")
            actual_components = '["Web Service", "API Layer", "Database Service"]'
        logger.info(f"Designing API endpoints with requirements summary length: {len(actual_requirements_summary) if actual_requirements_summary else 0} chars")        
        # Parse components if it's a string
        component_list = []
        if isinstance(actual_components, str):
            try:
                component_list = json.loads(actual_components)
                logger.info(f"Successfully parsed components JSON: {len(component_list)} components")
            except Exception as comp_error:
                logger.warning(f"Failed to parse components string as JSON: {str(comp_error)}")
                component_list = []
        elif isinstance(actual_components, list):
            component_list = actual_components
        else:
            logger.warning(f"Components is not a string or list. Type: {type(actual_components)}")
            component_list = []
            
        # Validate inputs are not empty and provide defaults if needed
        if not actual_requirements_summary:
            logger.warning("requirements_summary is empty - using default")
            actual_requirements_summary = "A web application with REST API endpoints"
            
        if not actual_components:
            logger.warning("components is empty - using default")
            actual_components = json.dumps(["User Management", "Data Management", "Authentication"])
            
        logger.info(f"Using parameters: " +
                  f"requirements_summary: {actual_requirements_summary[:30] if actual_requirements_summary else 'None'}..., " +
                  f"components: {actual_components}")
        
        # Create a clean prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert API Designer who always responds in valid JSON."),
            ("human", 
             "Design the API endpoints for this system based on these requirements and components:\n\n"
             "REQUIREMENTS: {requirements}\n\n"
             "COMPONENTS: {components}\n\n"
             "Return a JSON object describing the API including style (REST/GraphQL), base URL, authentication method, "
             "and a list of endpoints with their methods, paths, parameters, and response types.")        ])
        
        formatted_prompt = prompt.format_prompt(
            requirements=actual_requirements_summary,
            components=actual_components
        )
        
        # Invoke the LLM with JSON handling
        from tools.json_handler import JsonHandler
        json_llm = JsonHandler.create_strict_json_llm(get_tool_llm(temperature=0.0))
        response = json_llm.invoke(formatted_prompt)
        
        # Log the API call parameters
        logger.debug(f"Calling API endpoint design LLM with requirements: {len(actual_requirements_summary)} chars, components: {actual_components[:100] if isinstance(actual_components, str) else str(actual_components)[:100]}")
        
        # Process and return the content
        if isinstance(response, dict):
            logger.info("Received API design as dictionary directly")
            # Convert to ApiEndpointsOutput
            return _create_api_endpoints_output(response)
            
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Try to extract JSON object
        api_design = JsonHandler.extract_json_from_text(content)
        if isinstance(api_design, dict):
            logger.info("Successfully extracted API design from response text")
            return _create_api_endpoints_output(api_design)
            
        # Fallback with better error logging
        logger.warning(f"Failed to get valid API design, using fallback template. Response type: {type(response)}")
        
        # Create a sensible fallback based on the components
        endpoints = []        # Parse components string to get component names
        try:
            component_list = json.loads(actual_components) if isinstance(actual_components, str) else actual_components
            component_names = component_list if isinstance(component_list, list) else ["Resource"]
        except Exception:
            component_names = ["Resource"]
        
        # Generate basic CRUD endpoints for each component/resource
        for component in component_names:
            resource = component.replace(" ", "").lower()
            if "api" in resource.lower() or "service" in resource.lower() or "backend" in resource.lower():
                continue
                
            endpoints.append({
                "method": "GET",
                "path": f"/{resource}s",
                "purpose": f"List all {resource}s",
                "parameters": [],
                "response": {"type": f"array of {resource}s"},
                "authentication_required": True
            })
            
            endpoints.append({
                "method": "GET",
                "path": f"/{resource}s/{{id}}",
                "purpose": f"Get a single {resource} by ID",
                "parameters": [{"name": "id", "type": "path", "required": True}],
                "response": {"type": f"{resource} object"},
                "authentication_required": True
            })
            
            endpoints.append({
                "method": "POST",
                "path": f"/{resource}s",
                "purpose": f"Create a new {resource}",
                "parameters": [{"name": "body", "type": "body", "required": True}],
                "response": {"type": f"created {resource} object"},
                "authentication_required": True
            })
        
        # If no endpoints were generated, add a default one
        if not endpoints:
            endpoints = [{
                "method": "GET",
                "path": "/resources",
                "purpose": "List all resources",
                "parameters": [],
                "response": {"type": "array of resources"},
                "authentication_required": True
            }]
            
        fallback = {
            "style": "REST",
            "base_url": "/api/v1",
            "authentication": "JWT",
            "endpoints": endpoints
        }
        
        logger.info(f"Returning fallback API design with {len(endpoints)} endpoints")
        return _create_api_endpoints_output(fallback)

    except Exception as e:
        logger.error(f"Error in design_api_endpoints: {e}", exc_info=True)
        fallback = {
            "style": "REST",
            "base_url": "/api/v1",
            "authentication": "JWT",
            "endpoints": [
                {
                    "method": "GET",
                    "path": "/users",
                    "purpose": "List all users"
                }
            ],
            "error": f"Unexpected error: {e}"
        }
        return _create_api_endpoints_output(fallback)

@tool(args_schema=SecurityArchitectureDesignInput)
def design_security_architecture(requirements_summary: str, architecture_pattern: Optional[str] = None) -> SecurityArchitectureOutput:
    """
    Designs the security architecture for the system.
    
    Args:
        requirements_summary: A summary of the project's technical requirements
        architecture_pattern: The chosen architecture pattern (optional)
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'design_security_architecture' called")
    
    try:
        # Validate and clean inputs
        if not requirements_summary:
            logger.warning("requirements_summary is empty - using default")
            requirements_summary = "A system requiring security architecture"
            
        if not architecture_pattern:
            logger.info("architecture_pattern is empty - using generic approach for security design")
            # Don't attempt to infer - just use a generic default for security purposes
            architecture_pattern = "Generic Architecture"
        
        logger.info(f"Designing security architecture for pattern: {architecture_pattern}")
        
        # Get enhanced memory context and RAG information
        memory_context = get_design_context_from_memory()
        domain = memory_context.get("project_domain", "")
        
        # Get RAG context for security architecture patterns
        rag_context = get_design_rag_context("security_architecture", domain, 
                                           requirements=requirements_summary, 
                                           architecture_pattern=architecture_pattern)
          # Create a domain-aware security prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", 
             "You are an expert Security Architect who designs security based on domain requirements and compliance. "
             "Consider domain-specific security needs:"
             "\n- Healthcare: HIPAA compliance, PHI protection, audit trails, access logging, data encryption"
             "\n- Financial: PCI-DSS compliance, SOX requirements, fraud detection, transaction security, multi-factor auth"
             "\n- Government: FISMA compliance, data classification, access controls, encryption standards"
             "\n- E-commerce: PCI compliance, customer data protection, payment security, fraud prevention"
             "\n- IoT: Device authentication, secure communications, certificate management, edge security"
             "\n- Enterprise: SSO integration, role-based access, directory services, identity management"
             "\n- Startups: Cost-effective security, OAuth integration, basic compliance, scalable solutions"
             "\nAlways respond in valid JSON with security architecture appropriate for the domain and architecture pattern."),
            ("human", 
             "Design a comprehensive security architecture based on these requirements and architecture pattern:\n\n"
             "REQUIREMENTS: {requirements}\n\n"
             "ARCHITECTURE PATTERN: {architecture}\n\n"
             "DOMAIN CONTEXT: {domain}\n\n"
             "SECURITY KNOWLEDGE BASE:\n{rag_context}\n\n"
             "First analyze the domain (healthcare, financial, IoT, etc.) and compliance requirements.\n"
             "Use the security knowledge base to inform your design decisions.\n"
             "Then design appropriate security measures including:\n"
             "- Authentication methods suitable for the domain\n"
             "- Authorization strategies (RBAC, ABAC, etc.)\n"
             "- Data encryption (in-transit and at-rest)\n"
             "- Security measures and controls\n"
             "- Compliance considerations\n\n"
             "Return a JSON object with detailed security architecture.")
        ])
        # Format the prompt with the data
        formatted_prompt = prompt.format_prompt(
            requirements=requirements_summary,
            architecture=architecture_pattern,
            domain=domain or "General purpose application",
            rag_context=rag_context or "No additional security context available"
        )
        
        # Invoke the LLM with JSON handling
        from tools.json_handler import JsonHandler
        json_llm = JsonHandler.create_strict_json_llm(get_tool_llm(temperature=0.0))
        response = json_llm.invoke(formatted_prompt)
        
        # Process the response
        security_architecture = None
        if isinstance(response, dict):
            security_architecture = response
        else:
            content = response.content if hasattr(response, 'content') else str(response)
            # Try to extract JSON object
            security_architecture = JsonHandler.extract_json_from_text(content)
            
        if not isinstance(security_architecture, dict):
            logger.warning("Failed to get valid JSON response, using domain-aware fallback")
            
            # Create domain-aware fallback security architecture
            req_lower = requirements_summary.lower()
            if any(keyword in req_lower for keyword in ['healthcare', 'hipaa', 'medical', 'patient']):
                security_architecture = {
                    "authentication_method": "SAML 2.0 with Multi-Factor Authentication",
                    "authorization_strategy": "Role-based access control with audit trails",
                    "data_encryption": {
                        "in_transit": "TLS 1.3 with certificate pinning",
                        "at_rest": "AES-256 with key rotation"
                    },
                    "compliance_framework": "HIPAA",
                    "security_measures": [
                        {"category": "Access Control", "implementation": "Strong authentication", "mitigation": "Prevents unauthorized access"},
                        {"category": "Audit Logging", "implementation": "Complete audit trail", "mitigation": "Compliance and forensics"},
                        {"category": "Data Protection", "implementation": "End-to-end encryption", "mitigation": "Protects PHI"}
                    ]
                }
            elif any(keyword in req_lower for keyword in ['financial', 'fintech', 'payment', 'banking', 'pci']):
                security_architecture = {
                    "authentication_method": "OAuth 2.0 with PKI certificates",
                    "authorization_strategy": "Attribute-based access control",
                    "data_encryption": {
                        "in_transit": "TLS 1.3 with mutual authentication",
                        "at_rest": "AES-256 with HSM key management"
                    },
                    "compliance_framework": "PCI-DSS",
                    "security_measures": [
                        {"category": "Transaction Security", "implementation": "Digital signatures", "mitigation": "Prevents fraud"},
                        {"category": "Data Tokenization", "implementation": "PCI tokenization", "mitigation": "Protects sensitive data"},
                        {"category": "Fraud Detection", "implementation": "ML-based monitoring", "mitigation": "Real-time threat detection"}
                    ]
                }
            elif any(keyword in req_lower for keyword in ['iot', 'device', 'sensor', 'embedded']):
                security_architecture = {
                    "authentication_method": "X.509 certificates with device attestation",
                    "authorization_strategy": "Device-based access control",
                    "data_encryption": {
                        "in_transit": "DTLS 1.3 for constrained devices",
                        "at_rest": "Lightweight encryption (ChaCha20)"
                    },
                    "security_measures": [
                        {"category": "Device Identity", "implementation": "Hardware-based keys", "mitigation": "Prevents device spoofing"},
                        {"category": "Secure Boot", "implementation": "Verified boot process", "mitigation": "Prevents malware"},
                        {"category": "OTA Security", "implementation": "Signed firmware updates", "mitigation": "Secure device management"}
                    ]
                }
            else:
                # Generic fallback for other domains
                security_architecture = {
                    "authentication_method": "OAuth 2.0 with JWT tokens",
                    "authorization_strategy": "Role-based access control",
                    "data_encryption": {
                        "in_transit": "TLS 1.3",
                        "at_rest": "AES-256"
                    },
                    "security_measures": [
                        {"category": "Input Validation", "implementation": "Server-side validation", "mitigation": "Prevents injection attacks"},
                        {"category": "Session Management", "implementation": "Secure session handling", "mitigation": "Prevents session hijacking"},
                        {"category": "API Security", "implementation": "Rate limiting and authentication", "mitigation": "Prevents API abuse"}
                    ]                }
        
        # Create a proper SecurityArchitectureOutput object
        security_measures = []
        if "security_measures" in security_architecture and isinstance(security_architecture["security_measures"], list):
            for measure in security_architecture["security_measures"]:
                if isinstance(measure, dict):
                    security_measures.append(SecurityMeasure(
                        category=measure.get("category", "General Security"),
                        implementation=measure.get("implementation", "Not specified"),
                        mitigation=measure.get("mitigation", "")
                    ))
        
        # Ensure data_encryption is a dictionary
        data_encryption = security_architecture.get("data_encryption", {})
        if not isinstance(data_encryption, dict):
            data_encryption = {"general": str(data_encryption)}
        
        result = SecurityArchitectureOutput(
            authentication_method=security_architecture.get("authentication_method", "JWT with OAuth2"),
            authorization_strategy=security_architecture.get("authorization_strategy", "Role-based access control"),
            data_encryption=data_encryption,
            security_measures=security_measures
        )
        
        # Store security architecture for other tools to use
        store_design_data("security_architecture", {
            "authentication_method": result.authentication_method,
            "authorization_strategy": result.authorization_strategy,
            "data_encryption": result.data_encryption,
            "security_measures": [sm.dict() for sm in result.security_measures]
        })
        
        return result
    except Exception as e:
        logger.error(f"Error in design_security_architecture: {e}", exc_info=True)
        # Return a properly structured SecurityArchitectureOutput with fallback values
        return SecurityArchitectureOutput(
            authentication_method="JWT",
            authorization_strategy="RBAC",
            data_encryption={"in_transit": "TLS", "at_rest": "AES-256"},
            security_measures=[
                SecurityMeasure(
                    category="Input validation", 
                    implementation="Server-side validation",
                    mitigation=f"Fallback due to error: {str(e)}"
                )
            ]
        )

@tool
def synthesize_system_design(
    architecture_pattern: str,
    components: Optional[str] = "[]",
    data_model: Optional[str] = "{}",
    api_design: Optional[str] = "",
    security_architecture: Optional[str] = ""
) -> SystemDesignOutput:
    """
    Synthesizes all design components into a comprehensive system design.
    
    Args:
        architecture_pattern: The selected architecture pattern for the system
        components: JSON string or list containing the system components (optional, defaults to empty list)
        data_model: JSON string or dict containing the data model design (optional, defaults to empty dict)
        api_design: JSON string or dict containing the API endpoints design (optional)
        security_architecture: JSON string or dict containing the security architecture (optional)
    """
    logger = logging.getLogger(__name__)
    logger.info("Tool 'synthesize_system_design' called")
    
    try:
        logger.info(f"Synthesizing system design with architecture: {architecture_pattern}")
        
        # Handle None values and try to retrieve from shared memory if empty
        components = components or "[]"
        data_model = data_model or "{}"
        api_design = api_design or ""
        security_architecture = security_architecture or ""
        
        # If any parameter is empty/default, try to retrieve from shared memory
        memory_context = get_design_context_from_memory()
        
        if components == "[]" and "system_components" in memory_context:
            logger.info("Retrieved components from shared memory")
            components = json.dumps(memory_context["system_components"])
            
        if data_model == "{}" and "data_model" in memory_context:
            logger.info("Retrieved data model from shared memory")
            data_model = json.dumps(memory_context["data_model"])
            
        if not api_design and "api_design" in memory_context:
            logger.info("Retrieved API design from shared memory")
            api_design = json.dumps(memory_context["api_design"])
            
        if not security_architecture and "security_architecture" in memory_context:
            logger.info("Retrieved security architecture from shared memory")
            security_architecture = json.dumps(memory_context["security_architecture"])
        
        logger.info(f"Final synthesis inputs: components={bool(components != '[]')}, data_model={bool(data_model != '{}')}, api_design={bool(api_design)}, security_architecture={bool(security_architecture)}")
        
        # Parse inputs with robust handling for different data types
        components_data = _parse_design_component(components, "components", logger)
        data_model_data = _parse_design_component(data_model, "data_model", logger) 
        api_design_data = _parse_design_component(api_design, "api_design", logger)
        security_architecture_data = _parse_design_component(security_architecture, "security_architecture", logger)
        
        # Create the prompt with explicit JSON formatting instructions
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert system architect who ALWAYS responds with valid JSON only. Never include explanations, markdown, or text outside the JSON object."),
            ("human", 
             """Synthesize the following design components into a comprehensive system design and return ONLY a valid JSON object:
             
             ARCHITECTURE PATTERN: {architecture_pattern}
             
             COMPONENTS: {components}
             
             DATA MODEL: {data_model}
             
             API ENDPOINTS: {api_design}
             
             SECURITY ARCHITECTURE: {security_architecture}
             
             Return ONLY a JSON object with these fields:
             - architecture_overview: object with pattern and description
             - modules: array of module objects with name and description
             - data_model: object with entities array
             - api_endpoints: array of endpoint objects
             - security_measures: array of security measure objects
             - deployment_architecture: object with deployment info
             - metadata: object with additional info
             
             IMPORTANT: Return ONLY the JSON object, no other text, no markdown, no explanations.""")
        ])
        
        # Use JsonHandler for more robust JSON parsing
        from tools.json_handler import JsonHandler
        llm = JsonHandler.create_strict_json_llm(get_tool_llm(temperature=0.0))        
        
        # Format the prompt with the data
        formatted_prompt = prompt.format_prompt(
            architecture_pattern=architecture_pattern,
            components=json.dumps(components_data) if isinstance(components_data, list) else components,
            data_model=json.dumps(data_model_data) if isinstance(data_model_data, dict) else data_model,
            api_design=json.dumps(api_design_data) if isinstance(api_design_data, dict) else api_design,
            security_architecture=json.dumps(security_architecture_data) if isinstance(security_architecture_data, dict) else security_architecture
        )
        
        # Execute the LLM call with JSON handling
        response = llm.invoke(formatted_prompt)
        
        # Process the response to get the system design data
        design_data = None
        if isinstance(response, dict):
            design_data = response
        else:
            content = response.content if hasattr(response, 'content') else str(response)
            # Use JsonHandler for robust JSON extraction
            design_data = JsonHandler.extract_json_from_text(content)
            
        if not isinstance(design_data, dict):
            logger.warning("Failed to get valid JSON response, using fallback")
            design_data = {
                "architecture_overview": {
                    "pattern": architecture_pattern,
                    "description": f"System design based on {architecture_pattern} architecture"
                },
                "modules": [{"name": "Core Module", "description": "Main application module"}],
                "data_model": {"entities": []},
                "api_endpoints": [],
                "security_measures": [],
                "deployment_architecture": {"pattern": architecture_pattern},
                "metadata": {"generated_from": "synthesis_tool"}
            }
        
        # Create and return the SystemDesignOutput object
        return SystemDesignOutput(
            architecture_overview=design_data.get("architecture_overview", {
                "pattern": architecture_pattern,
                "description": f"System design based on {architecture_pattern} architecture"
            }),
            modules=design_data.get("modules", [{"name": "Core Module", "description": "Main application module"}]),
            data_model=design_data.get("data_model", {"entities": []}),
            api_endpoints=design_data.get("api_endpoints", []),
            security_measures=design_data.get("security_measures", []),
            deployment_architecture=design_data.get("deployment_architecture", {"pattern": architecture_pattern}),
            metadata=design_data.get("metadata", {"generated_from": "synthesis_tool"})
        )
        
    except Exception as e:
        logger.error(f"Error in synthesize_system_design: {str(e)}", exc_info=True)
        # Return a valid Pydantic object even in case of error
        return SystemDesignOutput(
            architecture_overview={
                "pattern": "Error Recovery Architecture",
                "description": f"Error occurred while synthesizing system design: {str(e)}"
            },
            modules=[{"name": "Error Module", "description": "Generated due to error in system design synthesis"}],
            data_model={"entities": []},
            api_endpoints=[],
            security_measures=[],
            deployment_architecture={},
            metadata={"error": True, "error_message": str(e)}
        )

@tool(args_schema=DesignQualityEvaluationInput)
def evaluate_design_quality(system_design: str) -> DesignQualityOutput:
    """
    Evaluates the quality of the system design and identifies improvement areas.
    
    Args:
        system_design: JSON string containing the complete system design    """
    # Import needed model class for output
    from models.data_contracts import DesignQualityDimensionScore
    
    logger = logging.getLogger(__name__)
    logger.info("Tool 'evaluate_design_quality' called")
    
    try:
        # The system_design parameter should already be a string from the schema
        if not system_design:
            logger.warning("system_design is empty")
            return DesignQualityOutput(
                overall_score=0.0,
                dimension_scores={"empty_input": DesignQualityDimensionScore(
                    score=0.0, 
                    justification="No system design provided"
                )},
                strengths=[],
                improvement_opportunities=[{"suggestion": "Provide a valid system design for evaluation"}]
            )
        
        # Parse the system design
        design_data = None
        if isinstance(system_design, dict):
            design_data = system_design
        else:
            try:
                design_data = json.loads(system_design)
            except json.JSONDecodeError:
                from tools.json_handler import JsonHandler
                design_data = JsonHandler.extract_json_from_text(system_design)
                if not design_data:
                    return DesignQualityOutput(
                        overall_score=0.0,
                        dimension_scores={"parsing": DesignQualityDimensionScore(
                            score=0.0, 
                            justification="Failed to parse input"
                        )},
                        strengths=[],
                        improvement_opportunities=[{"suggestion": "Could not parse system design JSON"}]
                    )        # Create a clean prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert Architecture Reviewer who always responds in valid JSON."),
            ("human", 
             "Evaluate the quality of this system design and identify areas for improvement:\n\n"
             "{design}\n\n"
             "Return a JSON object with an overall score, dimension scores (modularity, scalability, "
             "security, maintainability), strengths, and improvement opportunities.")
        ])

        # Format the prompt
        formatted_prompt = prompt.format_prompt(design=json.dumps(design_data, indent=2))
        
        # Invoke the LLM with JSON handling
        from tools.json_handler import JsonHandler
        json_llm = JsonHandler.create_strict_json_llm(get_tool_llm(temperature=0.1))
        response = json_llm.invoke(formatted_prompt)
        
        # Process the response
        evaluation = None
        if isinstance(response, dict):
            evaluation = response
        else:
            content = response.content if hasattr(response, 'content') else str(response)
            # Try to extract JSON object
            evaluation = JsonHandler.extract_json_from_text(content)
        
        # Fallback if we couldn't get valid JSON
        if not isinstance(evaluation, dict):
            logger.warning("Failed to get valid JSON response, using fallback")
            evaluation = {
                "overall_score": 7.5,
                "dimension_scores": {
                    "modularity": 7,
                    "scalability": 8,
                    "security": 7,
                    "maintainability": 8
                },
                "strengths": ["Clear separation of concerns", "Good security measures"],
                "improvement_opportunities": [
                    "Implement more comprehensive error handling"
                ]
            }
        
        # Convert to proper DesignQualityOutput format
        dimension_scores = {}
        if "dimension_scores" in evaluation and isinstance(evaluation["dimension_scores"], dict):
            for dimension, value in evaluation["dimension_scores"].items():
                if isinstance(value, (int, float)):
                    dimension_scores[dimension] = DesignQualityDimensionScore(
                        score=float(value),
                        justification=f"Score for {dimension}"
                    )
                elif isinstance(value, dict) and "score" in value:
                    dimension_scores[dimension] = DesignQualityDimensionScore(
                        score=float(value["score"]),
                        justification=value.get("justification", f"Score for {dimension}")
                    )
        
        # Extract opportunities from either format they might be in
        opportunities = []
        if "improvement_opportunities" in evaluation:
            opps = evaluation["improvement_opportunities"]
            if isinstance(opps, list):
                for opp in opps:
                    if isinstance(opp, str):
                        opportunities.append(opp)
                    elif isinstance(opp, dict) and "suggestion" in opp:
                        opportunities.append(opp["suggestion"])
        
        return DesignQualityOutput(
            overall_score=float(evaluation.get("overall_score", 7.0)),
            dimension_scores=dimension_scores,
            strengths=evaluation.get("strengths", []),
            improvement_opportunities=[{"suggestion": opp} for opp in opportunities]
        )

    except Exception as e:
        logger.error(f"Error in evaluate_design_quality: {e}", exc_info=True)
        # Return a properly structured output even in case of error
        return DesignQualityOutput(
            overall_score=5.0,
            dimension_scores={
                "error_handling": DesignQualityDimensionScore(
                    score=5.0,
                    justification=f"Error occurred during evaluation: {str(e)}"
                )
            },
            strengths=["Unable to determine strengths due to error"],
            improvement_opportunities=[{"suggestion": "Fix the error in the design evaluation tool"}]
        )

from models.data_contracts import MultipleComponentStructuresDesignInput, MultipleComponentStructuresOutput, ComponentDesignOutput # Add ComponentDesignOutput

@tool(args_schema=MultipleComponentStructuresDesignInput)
def design_multiple_component_structures(component_names: Union[List[str], str, Dict[str, Any]], requirements_summary: Optional[str] = None) -> MultipleComponentStructuresOutput:
    """
    Designs the detailed structure for multiple system components in a single batch operation.
    Use this to efficiently design several components at once rather than one by one.
    
    Args:
        component_names: List of component names to design or a JSON string that contains component names
        requirements_summary: A summary of the project's technical requirements (optional)
        
    Returns:
        A Pydantic object containing a list of component designs.    """
    # Import necessary models at the function level
    from models.data_contracts import ComponentDesignOutput, InternalSubComponent, MultipleComponentStructuresOutput
    logger = logging.getLogger(__name__)
    logger.info(f"design_multiple_component_structures called with component_names type: {type(component_names)}")
    
    try:        # Validate and clean inputs
        if not component_names:
            logger.error("No component names provided")
            return MultipleComponentStructuresOutput(designed_components=[])
            
        if requirements_summary is None:
            logger.warning("requirements_summary is None - attempting to retrieve from shared memory")
            # Try to get requirements from shared memory if available
            try:
                from enhanced_memory_manager import EnhancedSharedProjectMemory as SharedProjectMemory
                # Use a persistent memory instance rather than in-memory
                memory = SharedProjectMemory()
                
                # Try to get from different possible keys in order of preference
                stored_requirements = (
                    memory.get("requirements_summary") or 
                    memory.get("project_requirements") or 
                    memory.get("technical_requirements") or
                    memory.get("brd_analysis") or 
                    memory.get("tech_stack_recommendation") or
                    memory.get("system_requirements") or
                    memory.get("functional_requirements")
                )
                
                if stored_requirements:
                    if isinstance(stored_requirements, dict):
                        # Extract summary from different possible formats
                        requirements_summary = (
                            stored_requirements.get("summary", "") or
                            stored_requirements.get("project_summary", "") or
                            stored_requirements.get("technical_requirements", "") or
                            stored_requirements.get("functional_requirements", "") or
                            stored_requirements.get("requirements_summary", "") or
                            stored_requirements.get("description", "") or
                            str(stored_requirements)[:500]  # Limit length for safety
                        )
                        logger.info("Successfully retrieved requirements from shared memory (dict format)")
                    elif isinstance(stored_requirements, str):
                        requirements_summary = stored_requirements[:1000]  # Limit length for safety
                        logger.info("Successfully retrieved requirements from shared memory (string format)")
                    else:
                        requirements_summary = str(stored_requirements)[:500]
                        logger.info("Successfully retrieved requirements from shared memory (converted to string)")
                else:
                    logger.warning("No requirements found in shared memory")
                    requirements_summary = "System components requiring detailed design structure with standard web application patterns"
            except Exception as memory_error:
                logger.warning(f"Error accessing shared memory: {memory_error}")
                requirements_summary = "System components requiring detailed design structure with standard web application patterns"
        else:
            logger.info("Using provided requirements_summary parameter")
          # Ensure component_names is a list
        if isinstance(component_names, str):
            logger.info(f"Processing string component_names: {component_names[:200]}...")
            
            # Handle escaped quotes from ReAct agent
            if '\\"' in component_names:
                logger.info("Detected escaped quotes - cleaning up")
                component_names = component_names.replace('\\"', '"')
                if component_names.startswith('"') and component_names.endswith('"'):
                    component_names = component_names[1:-1]  # Remove outer quotes
              # Handle JSON string that contains an array of component objects
            if component_names.strip().startswith('[') and component_names.strip().endswith(']'):
                try:
                    parsed_list = json.loads(component_names)
                    # Extract component names from objects if needed
                    if parsed_list and isinstance(parsed_list[0], dict):
                        component_names = [comp.get('component_name', str(comp)) for comp in parsed_list]
                        logger.info(f"Successfully extracted component names from JSON objects: {component_names}")
                    elif parsed_list and isinstance(parsed_list[0], str):
                        component_names = parsed_list
                        logger.info(f"Successfully used component names from JSON string array: {component_names}")
                    else:
                        logger.warning(f"Unexpected array format: {parsed_list}")
                        component_names = [str(item) for item in parsed_list]
                        logger.info(f"Converted unexpected format to strings: {component_names}")
                except json.JSONDecodeError as e:
                    # Check if this is an "Extra data" error (concatenated JSON)
                    if "Extra data" in str(e):
                        logger.warning(f"Detected 'Extra data' error - attempting to extract first JSON array: {str(e)}")
                        try:
                            # Extract just the first complete JSON array
                            start_idx = component_names.find('[')
                            if start_idx != -1:
                                bracket_count = 0
                                for i in range(start_idx, len(component_names)):
                                    if component_names[i] == '[':
                                        bracket_count += 1
                                    elif component_names[i] == ']':
                                        bracket_count -= 1
                                        if bracket_count == 0:
                                            json_part = component_names[start_idx:i+1]
                                            parsed_list = json.loads(json_part)
                                            # Extract component names from the parsed array
                                            if parsed_list and isinstance(parsed_list[0], dict):
                                                component_names = [comp.get('component_name', str(comp)) for comp in parsed_list]
                                                logger.info(f"Successfully extracted component names from concatenated JSON: {component_names}")
                                            else:
                                                component_names = [str(item) for item in parsed_list]
                                            break
                                else:
                                    raise ValueError("Could not find complete JSON array")
                            else:
                                raise ValueError("No JSON array found")
                        except Exception as extract_error:
                            logger.warning(f"JSON extraction failed: {str(extract_error)} - falling back to JsonHandler")
                            # Fall back to JsonHandler for robust parsing
                            try:
                                from .json_handler import JsonHandler
                                parsed_data = JsonHandler.extract_json_from_text(component_names)
                                if isinstance(parsed_data, list):
                                    component_names = [str(item) for item in parsed_data]
                                    logger.info("Successfully parsed with JsonHandler - got list")
                                elif isinstance(parsed_data, dict) and 'components' in parsed_data:
                                    component_names = [str(item) for item in parsed_data['components']]
                                    logger.info("Successfully parsed with JsonHandler - extracted from components field")
                                else:
                                    raise ValueError("JsonHandler did not return expected format")
                            except Exception as handler_error:
                                logger.error(f"JsonHandler also failed: {str(handler_error)} - using regex fallback")
                                # Fall through to regex extraction below
                    else:
                        logger.warning(f"Failed to parse JSON array: {e}")
                    
                    # Try to extract component names manually from malformed JSON
                    import re
                    name_pattern = r'"component_name":\s*"([^"]+)"'
                    matches = re.findall(name_pattern, component_names)
                    if matches:
                        component_names = matches
                        logger.info(f"Extracted component names using regex: {component_names}")
                    else:
                        # Fall back to comma-separated parsing
                        component_names = [name.strip() for name in component_names.split(',')]
            # Handle comma-separated string
            elif ',' in component_names:
                component_names = [name.strip() for name in component_names.split(',')]
                logger.info(f"Parsed comma-separated components: {component_names}")
            # Single component
            else:
                component_names = [component_names.strip()]
                logger.info(f"Single component: {component_names}")
        
        logger.info(f"Designing components: {component_names}")
        logger.info(f"Requirements summary available: {requirements_summary is not None}")
        
        all_designs = []
        
        # Loop through each component name and design it
        for component_name in component_names:
            logger.info(f"Designing component: {component_name}")
            
            # Ensure component_name is a string
            component_name_str = str(component_name)
            
            try:                # Create a prompt for designing this component
                prompt = ChatPromptTemplate.from_messages([
                    ("system", "You are an expert Component Designer who always responds in valid JSON. "
                              "The dependencies field must be a list of strings (component names), not objects. "
                              "The internal_components field must be a list of objects, each with 'name' and 'responsibility' fields."),
                    ("human", 
                     "Design the detailed structure for this system component:\n\n"
                     "COMPONENT NAME: {component}\n\n"
                     "PROJECT REQUIREMENTS: {requirements}\n\n"
                     "Provide a detailed structure in JSON format including:\n"
                     "- The component name\n"
                     "- A list of internal sub-components with their name and responsibilities\n"
                     "- Dependencies on other components (as strings of component names)\n"
                     "- Applicable design patterns\n\n"
                     "IMPORTANT: Dependencies must be a list of strings, not objects.")
                ])

                # Format the prompt with the data
                formatted_prompt = prompt.format_prompt(
                    component=component_name_str,
                    requirements=requirements_summary
                )
                
                # Invoke the LLM with JSON handling
                from tools.json_handler import JsonHandler
                json_llm = JsonHandler.create_strict_json_llm(get_tool_llm(temperature=0.0))
                response = json_llm.invoke(formatted_prompt)
                
                # Process the response
                component_design = None
                if isinstance(response, dict):
                    component_design = response
                else:
                    content = response.content if hasattr(response, 'content') else str(response)
                    component_design = JsonHandler.extract_json_from_text(content)
                
                # Ensure we have a valid dict
                if not isinstance(component_design, dict):
                    logger.warning(f"Failed to get valid JSON response for component {component_name_str}, using fallback")
                    component_design = {
                        "name": component_name_str,
                        "responsibilities": ["Main functionality of the component"],
                        "internal_components": [
                            {"name": "Core Logic", "responsibility": "Main functionality of the component"}
                        ],
                        "dependencies": [],
                        "design_patterns": ["Repository", "Factory"]
                    }
                
                # Ensure the name field is present
                if "name" not in component_design:
                    component_design["name"] = component_name_str
                    
                # Ensure all required fields exist with correct types
                if "responsibilities" not in component_design:
                    component_design["responsibilities"] = ["Main functionality of the component"]
                    
                if "dependencies" not in component_design:
                    component_design["dependencies"] = []
                    
                if "internal_components" not in component_design:
                    component_design["internal_components"] = [
                        {"name": "Core Logic", "responsibility": "Main functionality of the component"}
                    ]
                    
                if "design_patterns" not in component_design:
                    component_design["design_patterns"] = ["Repository", "Factory"]
                
                # Create a ComponentDesignOutput model
                component_design_output = ComponentDesignOutput(**component_design)
                all_designs.append(component_design_output)
                
            except Exception as comp_error:
                logger.warning(f"Error designing component {component_name_str}: {str(comp_error)}")
                # Add a fallback component design
                fallback_component = ComponentDesignOutput(
                    name=component_name_str,
                    responsibilities=["Main functionality of the component"],
                    internal_components=[
                        InternalSubComponent(name="Core Logic", responsibility="Main functionality of the component")
                    ],
                    dependencies=[],
                    design_patterns=["Repository", "Factory"]                )
                all_designs.append(fallback_component)
        
        logger.info(f"Successfully designed {len(all_designs)} components in batch mode")
        return MultipleComponentStructuresOutput(designed_components=all_designs)
        
    except Exception as e:
        logger.error(f"Unexpected error in design_multiple_component_structures: {str(e)}", exc_info=True)
        # Return a minimal but valid Pydantic object even on error
        fallback_component = ComponentDesignOutput(
            name="Error Component",
            responsibilities=["Main functionality of the component"],
            internal_components=[
                InternalSubComponent(name="Core Logic", responsibility=f"Error occurred: {str(e)}")
            ],
            dependencies=[],
            design_patterns=["Repository", "Factory"]
        )
        return MultipleComponentStructuresOutput(designed_components=[fallback_component])

def _create_api_endpoints_output(api_design: dict) -> ApiEndpointsOutput:
    """
    Helper function to create ApiEndpointsOutput from a dictionary.
    
    Args:
        api_design: Dictionary containing API design data
        
    Returns:
        ApiEndpointsOutput object    """
    from models.data_contracts import ApiEndpoint
    
    # Extract basic information with defaults
    style = api_design.get("style", "REST")
    base_url = api_design.get("base_url", "/api/v1")
    authentication = api_design.get("authentication", "JWT")
      # Process endpoints
    endpoints = []
    raw_endpoints = api_design.get("endpoints", [])
    
    for endpoint_data in raw_endpoints:
        if isinstance(endpoint_data, dict):
            # Process parameters to ensure all values are strings
            processed_parameters = []
            raw_parameters = endpoint_data.get("parameters", [])
            for param in raw_parameters:
                if isinstance(param, dict):
                    # Convert all values to strings
                    processed_param = {}
                    for key, value in param.items():
                        processed_param[key] = str(value)
                    processed_parameters.append(processed_param)
                else:
                    # If it's not a dict, convert to a simple parameter
                    processed_parameters.append({"name": str(param), "type": "string"})
            
            endpoint = ApiEndpoint(
                method=endpoint_data.get("method", "GET"),
                path=endpoint_data.get("path", "/"),
                purpose=endpoint_data.get("purpose", "API endpoint"),
                parameters=processed_parameters,
                response=endpoint_data.get("response", {}),
                authentication_required=endpoint_data.get("authentication_required", True)
            )
            endpoints.append(endpoint)
    
    return ApiEndpointsOutput(
        style=style,
        base_url=base_url,
        authentication=authentication,
        endpoints=endpoints
    )

def _parse_design_component(component_data, component_type: str, logger):
    """
    Helper function to parse design component data with robust error handling.
    
    Args:
        component_data: The data to parse (string, dict, list, etc.)
        component_type: Type of component for logging
        logger: Logger instance
    
    Returns:
        Parsed and cleaned component data
    """
    import re
    
    if not component_data:
        if component_type == "components":
            return []
        else:
            return {}
    
    # If it's already a dict or list, return as-is
    if isinstance(component_data, dict):
        return component_data
    elif isinstance(component_data, list):
        return component_data
    
    # Handle string inputs
    if isinstance(component_data, str):
        # Try JSON parsing first
        try:
            parsed = json.loads(component_data)
            return parsed
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse {component_type} JSON, attempting regex extraction from: {component_data[:100]}...")
            
            # Extract meaningful data using regex based on component type
            if component_type == "components":
                names = re.findall(r"'name': '([^']+)'", component_data)
                if not names:
                    names = re.findall(r'"name": "([^"]+)"', component_data)
                if names:
                    return [{"name": name, "description": f"Component: {name}"} for name in names]
                else:
                    return [{"name": "Extracted Component", "description": "Component extracted from text"}]
            
            elif component_type == "data_model":
                table_names = re.findall(r"'name': '([^']+)'", component_data)
                if not table_names:
                    table_names = re.findall(r'"name": "([^"]+)"', component_data)
                if table_names:
                    entities = [{"name": name, "fields": []} for name in table_names]
                    return {"entities": entities}
                else:
                    return {"entities": [], "raw_text": str(component_data)[:200]}
            
            elif component_type == "api_design":
                methods = re.findall(r"'method': '([^']+)'", component_data)
                paths = re.findall(r"'path': '([^']+)'", component_data)
                if not methods:
                    methods = re.findall(r'"method": "([^"]+)"', component_data)
                    paths = re.findall(r'"path": "([^"]+)"', component_data)
                
                if methods:
                    endpoints = []
                    for i, method in enumerate(methods):
                        path = paths[i] if i < len(paths) else "/api"
                        endpoints.append({"method": method, "path": path, "description": f"{method} {path}"})
                    return {"endpoints": endpoints}
                else:
                    return {"endpoints": [], "raw_text": str(component_data)[:200]}
            
            elif component_type == "security_architecture":
                auth_methods = re.findall(r"authentication_method='([^']+)'", component_data)
                auth_strategies = re.findall(r"authorization_strategy='([^']+)'", component_data)
                if auth_methods or auth_strategies:
                    return {
                        "authentication": auth_methods[0] if auth_methods else "JWT",
                        "authorization": auth_strategies[0] if auth_strategies else "Role-based",
                        "raw_text": str(component_data)[:200]
                    }
                else:
                    return {"raw_text": str(component_data)[:200]}
            
            # Fallback for unknown types
            return {"raw_text": str(component_data)[:200]}
    
    # Fallback for any other type
    if component_type == "components":
        return []
    else:
        return {}