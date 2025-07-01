#!/usr/bin/env python3
"""
Shared Memory Hub for Multi-AI Development System

This module provides a centralized shared memory system that all agents and tools use
to prevent memory isolation issues that cause empty data models and broken workflows.

CRITICAL: All agents and tools MUST use this shared memory hub instead of creating
their own separate memory instances.
"""

import logging
import threading
from typing import Optional, Any, Dict, List
from functools import lru_cache

# Global shared memory instance (singleton pattern)
_shared_memory_instance = None
_memory_lock = threading.Lock()

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_shared_memory_hub():
    """
    Get the GLOBAL shared memory instance.
    
    This function implements a singleton pattern to ensure ALL agents and tools
    use the SAME memory instance, preventing data isolation issues.
    
    Returns:
        EnhancedSharedProjectMemory: The global shared memory instance
    """
    global _shared_memory_instance
    
    with _memory_lock:
        if _shared_memory_instance is None:
            try:
                from enhanced_memory_manager import create_memory_manager
                
                logger.info("Creating GLOBAL shared memory hub for all agents and tools")
                _shared_memory_instance = create_memory_manager(
                    backend_type="hybrid",
                    persistent_dir="./output/memory",  # Use consistent directory
                    max_memory_mb=200,  # Increased for multi-agent usage
                    enable_monitoring=True
                )
                logger.info("Global shared memory hub initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to create shared memory hub: {e}")
                # Fallback to basic memory if enhanced memory fails
                try:
                    from enhanced_memory_manager import EnhancedSharedProjectMemory
                    _shared_memory_instance = EnhancedSharedProjectMemory(memory_type='persistent')
                    logger.warning("Using fallback basic memory instead of hybrid")
                except Exception as fallback_error:
                    logger.error(f"Even fallback memory failed: {fallback_error}")
                    _shared_memory_instance = None
                    
        return _shared_memory_instance


def store_shared_data(key: str, data: Any, context: str = "shared", source_agent: str = None) -> bool:
    """
    Store data in the shared memory hub with cross-agent accessibility.
    
    Args:
        key: The key to store data under
        data: The data to store
        context: Context/namespace for the data
        source_agent: Name of the agent storing the data (for tracking)
        
    Returns:
        bool: True if storage was successful
    """
    try:
        memory = get_shared_memory_hub()
        if not memory:
            logger.error("No shared memory available for storing data")
            return False
            
        # Store in multiple contexts for cross-agent access
        contexts = [context, "cross_agent", "shared_data"]
        if source_agent:
            contexts.append(f"agent_{source_agent}")
            
        for ctx in contexts:
            memory.store(key, data, context=ctx)
            
        logger.info(f"Stored shared data '{key}' from {source_agent or 'unknown'} in contexts: {contexts}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store shared data '{key}': {e}")
        return False


def retrieve_shared_data(key: str, context: str = "shared", requesting_agent: str = None) -> Optional[Any]:
    """
    Retrieve data from the shared memory hub with cross-agent accessibility.
    
    Args:
        key: The key to retrieve data for
        context: Context/namespace to search in
        requesting_agent: Name of the agent requesting the data (for tracking)
        
    Returns:
        The stored data or None if not found
    """
    try:
        memory = get_shared_memory_hub()
        if not memory:
            logger.error("No shared memory available for retrieving data")
            return None
            
        # Try multiple contexts for cross-agent access
        contexts = [context, "cross_agent", "shared_data", "cross_tool", "design_tools", 
                   "tech_stack_tools", "brd_analysis", "planning_tools"]
        
        for ctx in contexts:
            data = memory.get(key, None, context=ctx)
            if data is not None:
                logger.info(f"Retrieved shared data '{key}' for {requesting_agent or 'unknown'} from context: {ctx}")
                return data
                
        logger.info(f"No shared data found for key '{key}' in any context")
        return None
        
    except Exception as e:
        logger.error(f"Failed to retrieve shared data '{key}': {e}")
        return None


def get_cross_agent_context() -> Dict[str, Any]:
    """
    Get all available cross-agent context data for better decision making.
    
    Returns:
        Dict containing all available cross-agent data
    """
    try:
        memory = get_shared_memory_hub()
        if not memory:
            return {}
            
        context = {}
        
        # Standard keys that agents commonly use
        common_keys = [
            # BRD Analysis outputs
            "brd_analysis", "requirements_summary", "project_requirements",
            "business_requirements", "functional_requirements", "raw_brd_content",
            
            # Tech Stack outputs
            "tech_stack_recommendation", "backend_recommendation", 
            "frontend_recommendation", "database_recommendation", 
            "architecture_recommendation", "tech_evaluations",
            
            # System Design outputs
            "system_design", "design_analysis", "architecture_pattern",
            "system_components", "data_model", "api_design", 
            "security_architecture", "component_designs",
            
            # Planning outputs
            "project_analysis", "timeline_estimation", "risk_assessment",
            "implementation_plan", "development_phases", 
            
            # Cross-cutting data
            "project_domain", "project_name", "project_context"
        ]
        
        # Try to retrieve each key from multiple contexts
        for key in common_keys:
            data = retrieve_shared_data(key, requesting_agent="context_retrieval")
            if data is not None:
                context[key] = data
                
        logger.info(f"Retrieved cross-agent context with {len(context)} keys")
        return context
        
    except Exception as e:
        logger.error(f"Failed to get cross-agent context: {e}")
        return {}


def clear_shared_memory() -> bool:
    """
    Clear all shared memory data (for testing/cleanup).
    
    Returns:
        bool: True if clearing was successful
    """
    global _shared_memory_instance
    
    try:
        with _memory_lock:
            if _shared_memory_instance:
                # Try different clear methods depending on the memory implementation
                if hasattr(_shared_memory_instance, 'clear'):
                    _shared_memory_instance.clear()
                elif hasattr(_shared_memory_instance, 'reset'):
                    _shared_memory_instance.reset()
                elif hasattr(_shared_memory_instance, '_data'):
                    _shared_memory_instance._data.clear()
                else:
                    # Create a new instance to "clear" it
                    _shared_memory_instance = None
                    logger.info("Reset shared memory hub by clearing instance")
                    return True
                    
                logger.info("Cleared shared memory hub")
                return True
            else:
                logger.info("No shared memory to clear")
                return True
                
    except Exception as e:
        logger.error(f"Failed to clear shared memory: {e}")
        return False


def get_memory_stats() -> Dict[str, Any]:
    """
    Get statistics about the shared memory usage.
    
    Returns:
        Dict containing memory statistics
    """
    try:
        memory = get_shared_memory_hub()
        if not memory:
            return {"status": "no_memory", "keys": 0}
            
        # Try to get stats if available
        stats = {
            "status": "active",
            "backend_type": getattr(memory, 'backend_type', 'unknown'),
            "keys": 0,
            "contexts": []
        }
        
        # This is implementation-specific, may need adjustment
        if hasattr(memory, '_data'):
            stats["keys"] = len(memory._data)
        elif hasattr(memory, 'memory'):
            stats["keys"] = len(memory.memory)
            
        logger.info(f"Shared memory stats: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get memory stats: {e}")
        return {"status": "error", "error": str(e)}


# Convenience functions for backward compatibility
def get_enhanced_tool_memory():
    """Backward compatibility function - returns shared memory hub."""
    return get_shared_memory_hub()

def get_enhanced_brd_memory():
    """Backward compatibility function - returns shared memory hub."""
    return get_shared_memory_hub()

def get_enhanced_tech_memory():
    """Backward compatibility function - returns shared memory hub.""" 
    return get_shared_memory_hub()

def get_enhanced_design_memory():
    """Backward compatibility function - returns shared memory hub."""
    return get_shared_memory_hub()

def get_enhanced_planning_memory():
    """Backward compatibility function - returns shared memory hub."""
    return get_shared_memory_hub() 