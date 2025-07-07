#!/usr/bin/env python3
"""
Direct test of the BRD analysis tool to debug the issue
"""

import sys
sys.path.append('.')
import logging
logging.basicConfig(level=logging.INFO)

# Initialize system config first
from config import initialize_system_config, AdvancedWorkflowConfig
adv_workflow_cfg = AdvancedWorkflowConfig.load_from_multiple_sources()
initialize_system_config(adv_workflow_cfg)

# Test the tool directly
from tools.brd_analysis_tools_enhanced import generate_comprehensive_brd_analysis

# Create a simple test BRD
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

print('Testing BRD analysis tool...')
try:
    result = generate_comprehensive_brd_analysis(test_brd)
    print(f'Tool result type: {type(result)}')
    
    if isinstance(result, dict):
        print(f'Tool result keys: {list(result.keys())}')
        print(f'Has requirements: {"requirements" in result}')
        print(f'Has functional_requirements: {"functional_requirements" in result}')
        print(f'Has project_name: {"project_name" in result}')
        
        if 'requirements' in result:
            reqs = result['requirements']
            req_count = len(reqs) if isinstance(reqs, list) else 'Not a list'
            print(f'Requirements count: {req_count}')
            
        if 'functional_requirements' in result:
            func_reqs = result['functional_requirements']
            func_count = len(func_reqs) if isinstance(func_reqs, list) else 'Not a list'
            print(f'Functional requirements count: {func_count}')
            
        if 'project_name' in result:
            print(f'Project name: {result["project_name"]}')
            
        # Print first few keys and values for debugging
        for key, value in list(result.items())[:5]:
            print(f'{key}: {str(value)[:100]}...' if len(str(value)) > 100 else f'{key}: {value}')
    else:
        print(f'Result is not a dict: {result}')
        
    print('Tool test completed successfully')
except Exception as e:
    print(f'Tool test failed: {e}')
    import traceback
    traceback.print_exc()
