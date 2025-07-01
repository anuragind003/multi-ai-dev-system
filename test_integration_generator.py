#!/usr/bin/env python3
"""
Test Integration Generator Agent - Mock Data Test

This test demonstrates how to use mock data to test the IntegrationGeneratorAgent.
"""

import os
import sys
import json
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import get_llm
from shared_memory import SharedProjectMemory
from tools.code_execution_tool import CodeExecutionTool
from agents.code_generation.integration_generator import IntegrationGeneratorAgent

def test_integration_generator():
    """Test the IntegrationGeneratorAgent with mock data."""
    
    print("🚀 Testing IntegrationGeneratorAgent with Mock Data")
    print("=" * 80)
    
    # Setup
    output_dir = "test_output/integration_test"
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize components
    llm = get_llm(temperature=0.2)
    memory = SharedProjectMemory(run_dir=output_dir)
    code_execution_tool = CodeExecutionTool(output_dir)
    
    # Create Integration Generator Agent
    integration_generator = IntegrationGeneratorAgent(
        llm=llm,
        memory=memory,
        temperature=0.2,
        output_dir=output_dir,
        code_execution_tool=code_execution_tool
    )
    
    # Mock data for testing
    mock_system_design = {
        "integration_points": [
            {"name": "Stripe", "type": "payment", "description": "Payment processing"},
            {"name": "Twilio", "type": "sms", "description": "SMS notifications"}
        ]
    }
    
    mock_tech_stack = {
        "backend": {
            "language": "Python",
            "framework": "FastAPI"
        }
    }
    
    # Save mock data for inspection
    with open(Path(output_dir) / "mock_data.json", "w") as f:
        json.dump({
            "system_design": mock_system_design,
            "tech_stack": mock_tech_stack
        }, f, indent=4)
        
    print(f"📂 Mock data saved to {output_dir}/mock_data.json")
    print("🎯 Running integration generation...")
    
    # Run the generator
    result = integration_generator.run(
        system_design=mock_system_design,
        tech_stack=mock_tech_stack
    )
    
    # Check results
    print("✅ INTEGRATION GENERATOR TEST RESULTS")
    print("=" * 80)
    
    if result.get("status") == "success":
        files_generated = result.get('files', [])
        print(f"✅ Status: SUCCESS")
        print(f"📁 Files Generated: {len(files_generated)}")
        
        for file in files_generated:
            print(f"  - {file['path']}")
            
        print("\n📝 Sample Content (stripe_service.py):")
        for file in files_generated:
            if "stripe_service.py" in file['path']:
                print("-" * 20)
                print(file['content'][:300] + "...")
                print("-" * 20)
                break
    else:
        print(f"❌ Status: FAILED")
        print(f"   Error: {result.get('error')}")
        
    print("=" * 80)
    print(f"✅ Test complete. Check the output in the '{output_dir}' directory.")

if __name__ == "__main__":
    test_integration_generator() 