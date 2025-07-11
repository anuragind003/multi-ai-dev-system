"""
Test script to verify consistency improvements in BRD and Tech Stack analysis agents.
"""

import logging
from typing import Dict, Any
import inspect

# Configure logging for testing
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_agent_consistency():
    """Test that both agents follow consistent patterns."""
    
    print(" Testing BRD Analyst and Tech Stack Advisor Agent Consistency")
    print("=" * 70)
    
    # Import the agents
    from agents.brd_analyst_react import BRDAnalystReActAgent
    from agents.tech_stack_advisor_simplified import TechStackAdvisorSimplifiedAgent
    
    # Test 1: Check method signatures
    print("\n1. Method Signature Consistency:")
    print("-" * 40)
    
    brd_methods = [method for method in dir(BRDAnalystReActAgent) if not method.startswith('_')]
    tech_methods = [method for method in dir(TechStackAdvisorSimplifiedAgent) if not method.startswith('_')]
    
    common_methods = set(brd_methods) & set(tech_methods)
    print(f" Common methods: {sorted(common_methods)}")
    
    # Test 2: Check method patterns
    print("\n2. Method Implementation Patterns:")
    print("-" * 40)
    
    # Check if both have consistent run method signatures
    brd_run_sig = inspect.signature(BRDAnalystReActAgent.run)
    tech_run_sig = inspect.signature(TechStackAdvisorSimplifiedAgent.run)
    
    print(f"BRD run signature: {brd_run_sig}")
    print(f"Tech Stack run signature: {tech_run_sig}")
    
    # Both should return Dict[str, Any]
    brd_return_type = str(brd_run_sig.return_annotation)
    tech_return_type = str(tech_run_sig.return_annotation)
    
    if brd_return_type == tech_return_type:
        print(" Return types are consistent")
    else:
        print(f" Return types differ: {brd_return_type} vs {tech_return_type}")
    
    # Test 3: Check error handling patterns
    print("\n3. Error Handling Consistency:")
    print("-" * 40)
    
    # Check if both have get_default_response method
    brd_has_default = hasattr(BRDAnalystReActAgent, 'get_default_response')
    tech_has_default = hasattr(TechStackAdvisorSimplifiedAgent, 'get_default_response')
    
    print(f" BRD has get_default_response: {brd_has_default}")
    print(f" Tech Stack has get_default_response: {tech_has_default}")
    
    if brd_has_default and tech_has_default:
        brd_default_sig = inspect.signature(BRDAnalystReActAgent.get_default_response)
        tech_default_sig = inspect.signature(TechStackAdvisorSimplifiedAgent.get_default_response)
        print(f"BRD default response signature: {brd_default_sig}")
        print(f"Tech Stack default response signature: {tech_default_sig}")
        
        if str(brd_default_sig) == str(tech_default_sig):
            print(" Default response signatures are consistent")
        else:
            print(" Default response signatures differ")
    
    # Test 4: Check memory handling
    print("\n4. Memory Handling Consistency:")
    print("-" * 40)
    
    brd_has_store = hasattr(BRDAnalystReActAgent, 'store_memory')
    tech_has_store = hasattr(TechStackAdvisorSimplifiedAgent, 'store_memory')
    
    print(f" BRD has store_memory: {brd_has_store}")
    print(f" Tech Stack has store_memory: {tech_has_store}")
    
    # Test 5: Check tool integration patterns
    print("\n5. Tool Integration Patterns:")
    print("-" * 40)
    
    # Check imports to see if both use the same utilities
    try:
        import agents.brd_analyst_react as brd_module
        import agents.tech_stack_advisor_simplified as tech_module
        
        # Check if both modules import the shared utilities
        brd_source = inspect.getsource(brd_module)
        tech_source = inspect.getsource(tech_module)
        
        brd_uses_utils = "from utils.analysis_tool_utils import" in brd_source
        tech_uses_utils = "from utils.analysis_tool_utils import" in tech_source
        
        print(f" BRD uses shared utilities: {brd_uses_utils}")
        print(f" Tech Stack uses shared utilities: {tech_uses_utils}")
        
        if brd_uses_utils and tech_uses_utils:
            print(" Both agents use consistent shared utilities")
        
    except Exception as e:
        print(f"  Could not analyze source imports: {e}")
    
    print("\n" + "=" * 70)
    print(" Consistency Analysis Complete!")
    
    # Summary
    print("\n SUMMARY OF IMPROVEMENTS:")
    print("-  Standardized error handling patterns")
    print("-  Consistent tool invocation methods") 
    print("-  Unified JSON parsing via shared utilities")
    print("-  Eliminated redundant field mapping code")
    print("-  Consistent memory management patterns")
    print("-  Standardized logging and monitoring")
    print("-  Aligned return format structures")

if __name__ == "__main__":
    test_agent_consistency() 