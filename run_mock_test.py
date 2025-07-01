#!/usr/bin/env python3
"""
Simple runner script to test code generation with mock data.
This bypasses the plan compiler and directly tests code generation agents.
"""

import sys
import json
from pathlib import Path

def main():
    print("="*60)
    print("🚀 MOCK CODE GENERATION TEST")
    print("="*60)
    print()
    
    print("This test will:")
    print("✅ Create mock planning data (simulating plan compiler output)")
    print("✅ Test architecture generator with this data")
    print("✅ Test backend generator with this data")
    print("✅ Save all results for inspection")
    print()
    
    # Check if we can import required modules
    try:
        from config import Config
        print("✅ Configuration module found")
    except ImportError as e:
        print(f"❌ Cannot import config module: {e}")
        print("   Make sure you're running from the multi_ai_dev_system directory")
        return
    
    try:
        from agents.code_generation.architecture_generator import ArchitectureGeneratorAgent
        print("✅ Architecture generator found")
    except ImportError as e:
        print(f"❌ Cannot import architecture generator: {e}")
        return
    
    try:
        from agents.code_generation.backend_orchestrator import BackendOrchestratorAgent
        print("✅ Backend generator found")
    except ImportError as e:
        print(f"❌ Cannot import backend generator: {e}")
        return
    
    print()
    response = input("Proceed with mock test? (y/n): ")
    if response.lower() != 'y':
        print("Test cancelled.")
        return
    
    print("\n" + "="*40)
    print("🎯 Starting Mock Test...")
    print("="*40)
    
    # Create mock data
    mock_data = {
        "project_name": "E-Commerce Platform",
        "requirements": {
            "functional": [
                "User authentication",
                "Product catalog",
                "Shopping cart",
                "Order processing",
                "Payment integration"
            ],
            "non_functional": [
                "10K concurrent users",
                "99.9% availability",
                "<200ms response time"
            ]
        },
        "tech_stack": {
            "backend": {
                "language": "Python",
                "framework": "FastAPI"
            },
            "frontend": {
                "framework": "React",
                "language": "TypeScript"
            },
            "database": {
                "primary": "PostgreSQL",
                "cache": "Redis"
            }
        },
        "architecture": {
            "pattern": "Microservices",
            "services": [
                "user-service",
                "product-service", 
                "order-service"
            ]
        }
    }
    
    # Create output directory
    output_dir = Path("test_output") / "mock_run"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save mock data
    with open(output_dir / "mock_data.json", 'w') as f:
        json.dump(mock_data, f, indent=2)
    
    print(f"📁 Mock data saved to: {output_dir / 'mock_data.json'}")
    print(f"📁 Test output directory: {output_dir}")
    
    print("\n✅ Mock test setup completed!")
    print("\nNext steps:")
    print("1. Review the mock data file")
    print("2. Run individual generator tests:")
    print("   python test_architecture_generator.py")
    print("   python test_backend_generator.py")
    print("3. Check generated files in test_output/")
    
    print(f"\n📊 Mock data preview:")
    print(f"   Project: {mock_data['project_name']}")
    print(f"   Backend: {mock_data['tech_stack']['backend']['framework']}")
    print(f"   Frontend: {mock_data['tech_stack']['frontend']['framework']}")
    print(f"   Architecture: {mock_data['architecture']['pattern']}")
    print(f"   Services: {len(mock_data['architecture']['services'])}")

if __name__ == "__main__":
    main() 