#!/usr/bin/env python3
"""
Test Frontend Generator Agent - Mock Data Test

This test demonstrates how to use mock data to test the FrontendGeneratorAgent.
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
from agents.code_generation.frontend_generator import FrontendGeneratorAgent

def test_frontend_generator():
    """Test the FrontendGeneratorAgent with mock data."""
    
    print("🚀 Testing FrontendGeneratorAgent with Mock Data")
    print("=" * 80)
    
    # Setup
    output_dir = "test_output/frontend_test"
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize components
    llm = get_llm(temperature=0.2)
    memory = SharedProjectMemory(run_dir=output_dir)
    code_execution_tool = CodeExecutionTool(output_dir)
    
    # Create Frontend Generator Agent
    frontend_generator = FrontendGeneratorAgent(
        llm=llm,
        memory=memory,
        temperature=0.2,
        output_dir=output_dir,
        code_execution_tool=code_execution_tool
    )
    
    # Mock data for testing
    mock_system_design = {
        "api_design": {
            "endpoints": [
                {"path": "/api/users", "method": "GET", "description": "Get all users"},
                {"path": "/api/products", "method": "GET", "description": "Get all products"}
            ]
        },
        "ui_design": {
            "theme": "modern",
            "pages": ["HomePage", "ProductsPage", "UserProfilePage"]
        }
    }
    
    mock_tech_stack = {
        "frontend": {
            "framework": "React",
            "language": "TypeScript",
            "styling": "TailwindCSS"
        }
    }
    
    # Save mock data for inspection
    with open(Path(output_dir) / "mock_data.json", "w") as f:
        json.dump({
            "system_design": mock_system_design,
            "tech_stack": mock_tech_stack
        }, f, indent=4)
        
    print(f"📂 Mock data saved to {output_dir}/mock_data.json")
    print("🎯 Running frontend generation...")
    
    # Run the generator
    result = frontend_generator.run(
        system_design=mock_system_design,
        tech_stack=mock_tech_stack
    )
    
    # Check results
    print("✅ FRONTEND GENERATOR TEST RESULTS")
    print("=" * 80)
    
    if result.get("status") == "success":
        files_generated = result.get('files', [])
        print(f"✅ Status: SUCCESS")
        print(f"📁 Files Generated: {len(files_generated)}")
        
        for file in files_generated:
            print(f"  - {file['path']}")
            
        print("\n📝 Sample Content (App.tsx):")
        for file in files_generated:
            if "App.tsx" in file['path']:
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
    test_frontend_generator() 