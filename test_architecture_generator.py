#!/usr/bin/env python3
"""
Test Architecture Generator Agent specifically with mock planning data.
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import get_llm
from shared_memory import SharedProjectMemory
from agents.code_generation.architecture_generator import ArchitectureGeneratorAgent
from tools.code_execution_tool import CodeExecutionTool

def test_architecture_generator():
    """Test architecture generator with mock data"""
    
    print("🏗️  Testing Architecture Generator...")
    
    # Mock data simulating plan compiler output
    mock_requirements = {
        "functional_requirements": [
            "User registration and authentication",
            "Product catalog management",
            "Shopping cart functionality", 
            "Order processing and payment",
            "Inventory management"
        ],
        "non_functional_requirements": [
            "Support 10,000 concurrent users",
            "99.9% system availability",
            "Response time under 200ms"
        ]
    }
    
    mock_tech_stack = {
        "backend": {
            "language": "Python",
            "framework": "FastAPI",
            "database": "PostgreSQL"
        },
        "frontend": {
            "framework": "React",
            "language": "TypeScript",
            "styling": "Tailwind CSS"
        },
        "infrastructure": {
            "containerization": "Docker",
            "orchestration": "Kubernetes",
            "cloud_provider": "AWS"
        }
    }
    
    mock_system_design = {
        "architecture_pattern": "Microservices",
        "data_models": [
            {
                "entity": "User",
                "attributes": {
                    "id": "UUID primary key",
                    "email": "string unique",
                    "password_hash": "string",
                    "first_name": "string",
                    "last_name": "string"
                }
            },
            {
                "entity": "Product", 
                "attributes": {
                    "id": "UUID primary key",
                    "name": "string",
                    "description": "text",
                    "price": "decimal(10,2)",
                    "inventory_count": "integer"
                }
            }
        ],
        "backend_services": [
            {
                "name": "user-service",
                "port": 8001,
                "responsibilities": ["User management", "Authentication"]
            },
            {
                "name": "product-service",
                "port": 8002, 
                "responsibilities": ["Product catalog", "Inventory management"]
            }
        ]
    }
    
    try:
        # Setup test environment
        llm = get_llm(temperature=0.2)
        
        # Create output directory first
        output_dir = project_root / "test_output" / "architecture_test"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize memory with the output directory
        memory = SharedProjectMemory(run_dir=str(output_dir))
        
        # Create code execution tool
        code_execution_tool = CodeExecutionTool(str(output_dir))
        
        # Create architecture generator
        arch_generator = ArchitectureGeneratorAgent(
            llm=llm,
            memory=memory,
            temperature=0.2,
            output_dir=str(output_dir),
            code_execution_tool=code_execution_tool
        )
        
        print("🎯 Running architecture generation...")
        
        # Run the generator
        result = arch_generator.run(
            requirements_analysis=mock_requirements,
            tech_stack=mock_tech_stack,
            system_design=mock_system_design
        )
        
        # Check results
        if result.get("status") == "success":
            print("✅ Architecture generation successful!")
            files = result.get("files", [])
            print(f"📁 Generated {len(files)} files:")
            for file_obj in files[:5]:  # Show first 5 files
                if hasattr(file_obj, 'file_path'):
                    print(f"   - {file_obj.file_path}")
                elif isinstance(file_obj, dict):
                    print(f"   - {file_obj.get('file_path', 'unknown')}")
                    
            if len(files) > 5:
                print(f"   ... and {len(files) - 5} more files")
        else:
            print(f"❌ Architecture generation failed: {result.get('error', 'Unknown error')}")
            
        # Save test results
        with open(output_dir / "test_result.json", 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"\n📊 Results saved to: {output_dir}")
        return result
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    test_architecture_generator() 