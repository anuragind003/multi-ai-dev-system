#!/usr/bin/env python3
"""
Direct test of the Tech Stack tool to debug the issue
"""

import sys
sys.path.append('.')
import logging
logging.basicConfig(level=logging.INFO)

# Initialize system config first
from config import initialize_system_config, AdvancedWorkflowConfig
adv_workflow_cfg = AdvancedWorkflowConfig.load_from_multiple_sources()
initialize_system_config(adv_workflow_cfg)

# Test the tech stack tool
from agents.tech_stack_advisor_react import TechStackAdvisorReActAgent
from config import get_llm
from enhanced_memory_manager import create_memory_manager

# Create test data (using the BRD analysis result structure)
test_brd = '''
Project: Test E-commerce Platform

Business Requirements:
1. Users must be able to register and login
2. Users must be able to browse products
3. Users must be able to add products to cart
4. Users must be able to checkout and pay
5. System must handle 1000 concurrent users

Stakeholders:
- Product Manager
- Development Team
- End Users
'''

# Sample requirements analysis (what would come from BRD analysis)
requirements_analysis = {
    'project_name': 'Test E-commerce Platform',
    'project_summary': 'E-commerce platform for users to browse, add products to cart, checkout and pay.',
    'requirements': [
        'Users must be able to register and login',
        'Users must be able to browse products', 
        'Users must be able to add products to cart',
        'Users must be able to checkout and pay',
        'System must handle 1000 concurrent users'
    ],
    'functional_requirements': [
        'User registration and authentication',
        'Product browsing functionality',
        'Shopping cart management',
        'Checkout and payment processing'
    ],
    'non_functional_requirements': [
        'Handle 1000 concurrent users'
    ],
    'stakeholders': ['Product Manager', 'Development Team', 'End Users']
}

print('Testing Tech Stack Advisor agent...')
try:
    # Create agent instance
    llm = get_llm(temperature=0.2)
    memory = create_memory_manager()
    
    agent = TechStackAdvisorReActAgent(llm=llm, memory=memory)
    
    # Run the agent
    result = agent.run(raw_brd=test_brd, requirements_analysis=requirements_analysis)
    
    print(f'Agent result type: {type(result)}')
    
    if isinstance(result, dict):
        print(f'Agent result keys: {list(result.keys())}')
        
        # Check for expected tech stack fields
        expected_fields = ['recommended_stack', 'frontend', 'backend', 'database', 'justification']
        for field in expected_fields:
            if field in result:
                print(f'Has {field}: True')
                if isinstance(result[field], dict):
                    print(f'  {field} keys: {list(result[field].keys())}')
                else:
                    print(f'  {field} type: {type(result[field])}')
            else:
                print(f'Has {field}: False')
                
        # Print first few keys and values for debugging
        print('\nFirst few fields:')
        for key, value in list(result.items())[:5]:
            if len(str(value)) > 100:
                print(f'{key}: {str(value)[:100]}...')
            else:
                print(f'{key}: {value}')
    else:
        print(f'Result is not a dict: {result}')
        
    print('Tech Stack Advisor test completed successfully')
except Exception as e:
    print(f'Tech Stack Advisor test failed: {e}')
    import traceback
    traceback.print_exc()
