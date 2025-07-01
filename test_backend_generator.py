#!/usr/bin/env python3
"""
Test Backend Generator Agent specifically with mock planning data.
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import get_llm
from shared_memory import SharedProjectMemory
from agents.code_generation.backend_orchestrator import BackendOrchestratorAgent
from tools.code_execution_tool import CodeExecutionTool

def test_backend_generator():
    """Test backend generator with mock data"""
    
    print("⚙️  Testing Backend Generator...")
    
    # Mock data simulating plan compiler output
    mock_requirements = {
        "functional_requirements": [
            "User registration and authentication system",
            "Product catalog with CRUD operations",
            "Shopping cart management",
            "Order processing with status tracking",
            "Payment integration",
            "Inventory management",
            "User profile management"
        ],
        "non_functional_requirements": [
            "Support 10,000 concurrent users",
            "99.9% system availability",
            "Response time under 200ms",
            "GDPR compliance",
            "PCI DSS compliance for payments"
        ]
    }
    
    mock_tech_stack = {
        "backend": {
            "language": "Python",
            "framework": "FastAPI",
            "version": "0.104.1",
            "database": "PostgreSQL",
            "cache": "Redis",
            "message_queue": "RabbitMQ"
        },
        "database": {
            "primary": "PostgreSQL",
            "version": "15.0",
            "cache": "Redis",
            "cache_version": "7.0"
        }
    }
    
    mock_system_design = {
        "architecture_pattern": "Microservices",
        "data_models": [
            {
                "entity": "User",
                "service": "user-service",
                "attributes": {
                    "id": "UUID primary key",
                    "email": "string unique",
                    "password_hash": "string",
                    "first_name": "string",
                    "last_name": "string",
                    "is_active": "boolean default true",
                    "created_at": "timestamp",
                    "updated_at": "timestamp"
                },
                "relationships": ["has_many orders", "has_one cart"]
            },
            {
                "entity": "Product",
                "service": "product-service",
                "attributes": {
                    "id": "UUID primary key",
                    "name": "string",
                    "description": "text",
                    "price": "decimal(10,2)",
                    "category_id": "UUID foreign key",
                    "sku": "string unique",
                    "inventory_count": "integer",
                    "is_active": "boolean default true",
                    "created_at": "timestamp",
                    "updated_at": "timestamp"
                },
                "relationships": ["belongs_to category", "has_many order_items", "has_many reviews"]
            },
            {
                "entity": "Order",
                "service": "order-service",
                "attributes": {
                    "id": "UUID primary key",
                    "user_id": "UUID foreign key",
                    "status": "enum(pending,confirmed,shipped,delivered,cancelled)",
                    "total_amount": "decimal(10,2)",
                    "shipping_address": "text",
                    "created_at": "timestamp",
                    "updated_at": "timestamp"
                },
                "relationships": ["belongs_to user", "has_many order_items"]
            }
        ],
        "api_design": {
            "endpoints": [
                {
                    "path": "/auth/register",
                    "method": "POST",
                    "service": "user-service",
                    "description": "User registration"
                },
                {
                    "path": "/auth/login",
                    "method": "POST",
                    "service": "user-service",
                    "description": "User authentication"
                },
                {
                    "path": "/products",
                    "method": "GET",
                    "service": "product-service",
                    "description": "Get paginated product list"
                },
                {
                    "path": "/products/{id}",
                    "method": "GET",
                    "service": "product-service",
                    "description": "Get product details"
                },
                {
                    "path": "/orders",
                    "method": "POST",
                    "service": "order-service",
                    "description": "Create new order"
                }
            ]
        },
        "backend_services": [
            {
                "name": "user-service",
                "port": 8001,
                "database": "users_db",
                "responsibilities": ["User management", "Authentication", "Profile management"]
            },
            {
                "name": "product-service",
                "port": 8002,
                "database": "products_db",
                "responsibilities": ["Product catalog", "Inventory management", "Search"]
            },
            {
                "name": "order-service",
                "port": 8003,
                "database": "orders_db",
                "responsibilities": ["Order processing", "Cart management", "Order history"]
            }
        ]
    }
    
    try:
        # Setup test environment
        llm = get_llm(temperature=0.2)
        
        # Create output directory first
        output_dir = project_root / "test_output" / "backend_test"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize memory with the output directory
        memory = SharedProjectMemory(run_dir=str(output_dir))
        
        # Create code execution tool
        code_execution_tool = CodeExecutionTool(str(output_dir))
        
        # Create backend generator
        backend_generator = BackendOrchestratorAgent(
            llm=llm,
            memory=memory,
            temperature=0.2,
            output_dir=str(output_dir),
            code_execution_tool=code_execution_tool
        )
        
        print("🎯 Running backend generation...")
        
        # Run the generator
        result = backend_generator.run(
            requirements_analysis=mock_requirements,
            tech_stack=mock_tech_stack,
            system_design=mock_system_design
        )
        
        # Check results - handle nested structure
        backend_output = result.get("backend_generation_output", result)
        status = backend_output.get("status", "unknown")
        
        if status == "success":
            print("✅ Backend generation successful!")
            files = backend_output.get("files", [])
            print(f"📁 Generated {len(files)} files:")
            
            # Group files by type for better display
            file_types = {}
            for file_obj in files:
                if hasattr(file_obj, 'file_path'):
                    path = file_obj.file_path
                elif isinstance(file_obj, dict):
                    path = file_obj.get('file_path', 'unknown')
                else:
                    path = 'unknown'
                
                # Extract file type from path
                if '/models/' in path:
                    file_type = 'models'
                elif '/routes/' in path or '/api/' in path:
                    file_type = 'api/routes'
                elif '/services/' in path:
                    file_type = 'services'
                elif path.endswith('.py'):
                    file_type = 'python_files'
                else:
                    file_type = 'other'
                
                if file_type not in file_types:
                    file_types[file_type] = []
                file_types[file_type].append(path)
            
            for file_type, paths in file_types.items():
                print(f"   {file_type}: {len(paths)} files")
                for path in paths[:3]:  # Show first 3 of each type
                    print(f"     - {path}")
                if len(paths) > 3:
                    print(f"     ... and {len(paths) - 3} more")
                    
            # Show metadata if available
            metadata = backend_output.get("metadata", {})
            if metadata:
                stats = metadata.get("generation_stats", {})
                print(f"\n📊 Generation Statistics:")
                print(f"   Time: {stats.get('total_time', 'N/A'):.1f}s")
                print(f"   Success Rate: {stats.get('success_rate', 0)*100:.1f}%")
                print(f"   Models: {metadata.get('models_count', 0)}")
                print(f"   Endpoints: {metadata.get('endpoints_count', 0)}")
                print(f"   Business Logic: {metadata.get('business_logic_count', 0)}")
                    
        else:
            print(f"❌ Backend generation failed: {backend_output.get('error', 'Unknown error')}")
            print(f"   Status: {status}")
            
            # Show what was actually generated for debugging
            files = backend_output.get("files", [])
            if files:
                print(f"   Partial files generated: {len(files)}")
                for file_obj in files[:3]:  # Show first 3 files
                    if isinstance(file_obj, dict):
                        path = file_obj.get('file_path', 'unknown')
                        content_length = len(file_obj.get('code', file_obj.get('content', '')))
                        print(f"     - {path} ({content_length} chars)")
                    else:
                        print(f"     - {file_obj}")
            
            # Debug: Show result structure keys
            print(f"   Result keys: {list(result.keys())}")
            if "backend_generation_output" in result:
                print(f"   Backend output keys: {list(result['backend_generation_output'].keys())}")
            
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
    test_backend_generator() 