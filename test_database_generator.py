#!/usr/bin/env python3
"""
Test Database Generator Agent - Mock Data Test

This test demonstrates how to use mock data to test the DatabaseGeneratorAgent.
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
from agents.code_generation.database_generator import DatabaseGeneratorAgent

def test_database_generator():
    """Test the DatabaseGeneratorAgent with mock data."""
    
    print("🚀 Testing DatabaseGeneratorAgent with Mock Data")
    print("=" * 80)
    
    # Setup
    output_dir = "test_output/database_test"
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize components
    llm = get_llm(temperature=0.2)
    memory = SharedProjectMemory(run_dir=output_dir)
    code_execution_tool = CodeExecutionTool(output_dir)
    
    # Create Database Generator Agent
    database_generator = DatabaseGeneratorAgent(
        llm=llm,
        memory=memory,
        temperature=0.2,
        output_dir=output_dir,
        code_execution_tool=code_execution_tool
    )
    
    # Mock data for testing
    mock_system_design = {
        "architecture_pattern": "Microservices",
        "data_models": [
            {
                "name": "User",
                "description": "Represents a user of the system.",
                "fields": [
                    {"name": "id", "type": "int", "is_primary_key": True},
                    {"name": "username", "type": "string", "is_required": True},
                    {"name": "email", "type": "string", "is_required": True, "is_unique": True}
                ]
            },
            {
                "name": "Product",
                "description": "Represents a product in the catalog.",
                "fields": [
                    {"name": "id", "type": "int", "is_primary_key": True},
                    {"name": "name", "type": "string", "is_required": True},
                    {"name": "price", "type": "float", "is_required": True}
                ]
            }
        ]
    }
    
    mock_tech_stack = {
        "database": {
            "primary": "PostgreSQL",
            "orm": "SQLAlchemy"
        }
    }
    
    # Save mock data for inspection
    with open(Path(output_dir) / "mock_data.json", "w") as f:
        json.dump({
            "system_design": mock_system_design,
            "tech_stack": mock_tech_stack
        }, f, indent=4)
        
    print(f"📂 Mock data saved to {output_dir}/mock_data.json")
    print("🎯 Running database generation...")
    
    # Run the generator
    result = database_generator.run(
        system_design=mock_system_design,
        tech_stack=mock_tech_stack
    )
    
    # Check results
    print("✅ DATABASE GENERATOR TEST RESULTS")
    print("=" * 80)
    
    if result.get("status") == "success":
        files_generated = result.get('files', [])
        print(f"✅ Status: SUCCESS")
        print(f"📁 Files Generated: {len(files_generated)}")
        
        for file in files_generated:
            print(f"  - {file['path']}")
            
        print("\n📝 Sample Content (schema.sql):")
        for file in files_generated:
            if "schema.sql" in file['path']:
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
    test_database_generator() 