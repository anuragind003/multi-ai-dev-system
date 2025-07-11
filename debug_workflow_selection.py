#!/usr/bin/env python3
"""
Test script to verify which workflow is being used and why async iterator is being called.
"""

import asyncio
import logging
from agent_state import AgentState, StateFields

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

async def test_workflow_selection():
    """Test which workflow is actually being used."""
    
    logger.info("=== WORKFLOW SELECTION TEST ===")
    
    # Test 1: Check which workflow get_async_workflow returns for "phased"
    from async_graph import get_async_workflow
    
    workflow = await get_async_workflow("phased")
    logger.info(f"get_async_workflow('phased') returned: {type(workflow)}")
    
    # Test 2: Examine the compiled graph nodes
    compiled_graph = workflow.compile()
    node_names = list(compiled_graph.get_graph().nodes.keys())
    logger.info(f"Workflow nodes: {node_names}")
    
    # Test 3: Check what specific function is bound to work_item_iterator_node
    work_item_node = compiled_graph.get_graph().nodes.get("work_item_iterator_node")
    if work_item_node:
        logger.info(f"work_item_iterator_node bound to: {work_item_node}")
        if hasattr(work_item_node, 'func'):
            logger.info(f"work_item_iterator_node function: {work_item_node.func}")
    
    # Test 4: Check async_graph_simple directly
    logger.info("=== TESTING async_graph_simple DIRECTLY ===")
    from async_graph_simple import create_simple_sequential_workflow
    simple_workflow = await create_simple_sequential_workflow()
    simple_compiled = simple_workflow.compile()
    simple_nodes = list(simple_compiled.get_graph().nodes.keys())
    logger.info(f"Simple workflow nodes: {simple_nodes}")
    
    simple_work_item_node = simple_compiled.get_graph().nodes.get("work_item_iterator_node")
    if simple_work_item_node:
        logger.info(f"Simple work_item_iterator_node bound to: {simple_work_item_node}")
    
    # Test 5: Check imports in async_graph_simple
    logger.info("=== CHECKING IMPORTS ===")
    from graph_nodes import work_item_iterator_node as sync_version
    from async_graph_nodes import async_work_item_iterator_node as async_version
    
    logger.info(f"Sync version function: {sync_version}")
    logger.info(f"Async version function: {async_version}")
    
    # Test if they're the same (shouldn't be)
    logger.info(f"Are they the same function? {sync_version is async_version}")

if __name__ == "__main__":
    asyncio.run(test_workflow_selection())
