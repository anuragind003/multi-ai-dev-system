#!/usr/bin/env python3
"""
Simple test script to debug the planning tool and plan compiler.
"""

import asyncio
import logging
import sys
import os

# Add the multi-ai-dev-system directory to the path


from tools.planning_tools_enhanced import generate_comprehensive_work_item_backlog
from agents.planning.plan_compiler_simplified import PlanCompilerSimplifiedAgent
from config import get_llm

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

# Sample test data
test_requirements_analysis = {
    "project_name": "E-Commerce Platform",
    "project_summary": "A modern e-commerce platform with user authentication, product catalog, and order processing",
    "functional_requirements": [
        "User registration and authentication",
        "Product catalog with search",
        "Shopping cart functionality",
        "Order processing and payment"
    ],
    "non_functional_requirements": [
        "Support 1000 concurrent users",
        "Response time < 200ms",
        "99.9% uptime"
    ]
}

test_tech_stack = {
    "backend": {"name": "Python", "framework": "FastAPI"},
    "frontend": {"name": "React", "framework": "TypeScript"},
    "database": {"name": "PostgreSQL"},
    "architecture_pattern": "Microservices"
}

test_system_design = {
    "architecture": "Microservices",
    "components": [
        {"name": "user-service", "responsibility": "User management"},
        {"name": "product-service", "responsibility": "Product catalog"},
        {"name": "order-service", "responsibility": "Order processing"}
    ],
    "database_schema": [
        {"table_name": "users", "columns": {"id": "integer", "email": "varchar", "password_hash": "varchar"}},
        {"table_name": "products", "columns": {"id": "integer", "name": "varchar", "price": "decimal"}},
        {"table_name": "orders", "columns": {"id": "integer", "user_id": "integer", "total": "decimal"}}
    ]
}

async def test_planning_tool_directly():
    """Test the planning tool directly."""
    logger.info("=== Testing Planning Tool Directly ===")
    
    try:
        llm = get_llm(temperature=0.2)
        
        result = generate_comprehensive_work_item_backlog.func(
            requirements_analysis=test_requirements_analysis,
            tech_stack_recommendation=test_tech_stack,
            system_design=test_system_design,
            llm=llm
        )
        
        logger.info(f"Planning tool result type: {type(result)}")
        logger.info(f"Planning tool result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        if isinstance(result, dict):
            if 'work_items' in result:
                work_items = result['work_items']
                logger.info(f"Found {len(work_items)} work items")
                
                # Log first few work items
                for i, item in enumerate(work_items[:3]):
                    logger.info(f"Work item {i}: {item}")
            else:
                logger.warning("No 'work_items' key found in result")
                logger.info(f"Available keys: {list(result.keys())}")
        
        return result
        
    except Exception as e:
        logger.error(f"Planning tool test failed: {e}", exc_info=True)
        return None

async def test_plan_compiler():
    """Test the plan compiler agent."""
    logger.info("=== Testing Plan Compiler Agent ===")
    
    try:
        llm = get_llm(temperature=0.2)
        agent = PlanCompilerSimplifiedAgent(llm=llm)
        
        result = agent.run(
            requirements_analysis=test_requirements_analysis,
            tech_stack_recommendation=test_tech_stack,
            system_design=test_system_design
        )
        
        logger.info(f"Plan compiler result type: {type(result)}")
        logger.info(f"Plan compiler result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        if isinstance(result, dict):
            if 'plan_type' in result:
                logger.info(f"Plan type: {result['plan_type']}")
            if 'phases' in result:
                logger.info(f"Number of phases: {len(result['phases'])}")
                for i, phase in enumerate(result['phases']):
                    if isinstance(phase, dict) and 'work_items' in phase:
                        logger.info(f"Phase {i} ({phase.get('name', 'unnamed')}) has {len(phase['work_items'])} work items")
        
        return result
        
    except Exception as e:
        logger.error(f"Plan compiler test failed: {e}", exc_info=True)
        return None

async def main():
    """Main test function."""
    logger.info("Starting planning debug tests...")
    
    # Test planning tool directly
    tool_result = await test_planning_tool_directly()
    
    print("\n" + "="*60 + "\n")
    
    # Test plan compiler
    compiler_result = await test_plan_compiler()
    
    print("\n" + "="*60 + "\n")
    
    # Summary
    logger.info("=== Test Summary ===")
    if tool_result:
        tool_work_items = len(tool_result.get('work_items', [])) if isinstance(tool_result, dict) else 0
        logger.info(f"Planning tool generated {tool_work_items} work items")
    else:
        logger.error("Planning tool failed")
    
    if compiler_result:
        if isinstance(compiler_result, dict) and 'phases' in compiler_result:
            total_work_items = sum(len(phase.get('work_items', [])) for phase in compiler_result['phases'])
            logger.info(f"Plan compiler organized {total_work_items} work items into {len(compiler_result['phases'])} phases")
        else:
            logger.warning("Plan compiler result doesn't have expected format")
    else:
        logger.error("Plan compiler failed")

if __name__ == "__main__":
    asyncio.run(main()) 