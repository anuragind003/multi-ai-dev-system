"""
LangGraph Dev Console Registration Module
Handles registration of all workflow types with LangGraph Dev for visualization
"""

import asyncio
import logging
import importlib
import sys
from typing import Dict, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

def check_langgraph_version():
    """Check LangGraph version and return appropriate dev console module"""
    try:
        import langgraph
        version = getattr(langgraph, "__version__", "0.0.0")
        logger.info(f"Detected LangGraph version: {version}")
        
        # Try different import paths based on version
        try:
            from langgraph.dev import dev_console
            logger.info("Successfully imported dev_console from langgraph.dev")
            return dev_console
        except ImportError:
            try:
                from langgraph.graph.vis import dev_console
                logger.info("Successfully imported dev_console from langgraph.graph.vis")
                return dev_console
            except ImportError:
                logger.warning("Could not find dev_console in standard locations")
                return None
    except ImportError:
        logger.error("LangGraph is not installed")
        return None

# Import all workflow creation functions
try:
    from graph import (
        get_workflow,
        create_basic_workflow,
        create_iterative_workflow,
        create_phased_workflow,
        create_modular_workflow,
        create_resumable_workflow,
        create_implementation_workflow
    )

    # Import async workflows if they exist
    try:
        from async_graph import (
            create_async_phased_workflow,
            create_async_iterative_workflow
        )
        has_async = True
    except ImportError:
        has_async = False
        logger.warning("Async workflows not available, skipping registration")
        
except ImportError as e:
    logger.error(f"Failed to import workflow modules: {e}")
    sys.exit(1)

def register_all_workflows(dev_console_module) -> Dict[str, Any]:
    """
    Register all available workflows with LangGraph Dev console.
    
    Returns:
        Dictionary of registered workflow names to workflow objects
    """
    if not dev_console_module:
        logger.error("Dev console module not available - can't register workflows")
        return {}
        
    logger.info("Registering all workflows with LangGraph Dev console")
    
    # Track registered workflows
    registered = {}
    
    # IMPORTANT: Register ALL workflow types
    workflow_types = [
        "basic", 
        "iterative", 
        "phased", 
        "modular", 
        "resumable",
        "implementation"
    ]
    
    # Register synchronous workflows
    for workflow_type in workflow_types:
        try:
            # Handle implementation workflow separately
            if workflow_type == "implementation":
                workflow = create_implementation_workflow()
            else:
                # Use the router function to get consistent workflow creation
                workflow = get_workflow(workflow_type)
                
            dev_console_module.register_workflow(workflow_type, workflow)
            registered[workflow_type] = workflow
            logger.info(f"Registered {workflow_type} workflow with LangGraph Dev")
        except Exception as e:
            logger.warning(f"Failed to register {workflow_type} workflow: {e}")
    
    return registered

async def register_async_workflows(dev_console_module) -> Dict[str, Any]:
    """
    Register all available async workflows with LangGraph Dev console.
    
    Returns:
        Dictionary of registered workflow names to workflow objects
    """
    if not dev_console_module or not has_async:
        logger.error("Dev console module or async workflows not available")
        return {}
        
    logger.info("Registering async workflows with LangGraph Dev console")
    
    # Track registered workflows
    registered = {}
    
    # Register async phased workflow
    try:
        async_phased = await create_async_phased_workflow()
        dev_console_module.register_workflow("async_phased", async_phased)
        registered["async_phased"] = async_phased
        logger.info("Registered async_phased workflow with LangGraph Dev")
    except Exception as e:
        logger.warning(f"Failed to register async_phased workflow: {e}")
    
    # Register async iterative workflow
    try:
        async_iterative = await create_async_iterative_workflow()
        dev_console_module.register_workflow("async_iterative", async_iterative)
        registered["async_iterative"] = async_iterative
        logger.info("Registered async_iterative workflow with LangGraph Dev")
    except Exception as e:
        logger.warning(f"Failed to register async_iterative workflow: {e}")
    
    return registered

def initialize_dev_console(run_async_registration: bool = True) -> Dict[str, Any]:
    """
    Initialize the LangGraph Dev console with all workflows.
    
    Args:
        run_async_registration: Whether to also register async workflows
        
    Returns:
        Dictionary of registered workflow names to workflow objects
    """
    # Configure basic logging if not already configured
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO,
                           format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # First, check if we can access the dev console
    dev_console = check_langgraph_version()
    
    if not dev_console:
        logger.error("LangGraph Dev console not available in your installed version.")
        logger.error("To use this feature, upgrade LangGraph to the latest version.")
        logger.error("Try: pip install --upgrade langgraph")
        return {}
    
    # Register sync workflows
    registered = register_all_workflows(dev_console)
    
    # Optionally register async workflows
    if run_async_registration and has_async:
        try:
            # Run the async registration
            async_registered = asyncio.run(register_async_workflows(dev_console))
            registered.update(async_registered)
        except Exception as e:
            logger.warning(f"Failed to register async workflows: {e}")
    
    logger.info(f"Successfully registered {len(registered)} workflows with LangGraph Dev")
    return registered

# Only run if executed directly
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Register all workflows
    registered_workflows = initialize_dev_console()
    
    if registered_workflows:
        # Print summary
        print(f"\nRegistered {len(registered_workflows)} workflows:")
        for name in registered_workflows.keys():
            print(f"- {name}")
        
        print("\nLangGraph Dev is ready! Access the dashboard to visualize workflows.")
    else:
        print("\nNo workflows were registered. Check the errors above.")
        print("You may need to upgrade LangGraph with:")
        print("$ pip install --upgrade langgraph")