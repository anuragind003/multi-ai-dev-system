#!/usr/bin/env python3
"""
Test script for code generation agents using mock data from plan compiler.
This script simulates the output from the plan compiler and tests each code generation agent.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import required components
from config import get_llm
from shared_memory import SharedProjectMemory
from tools.code_execution_tool import CodeExecutionTool
import logging
from agents.code_generation.backend_orchestrator import BackendOrchestratorAgent

def load_mock_data() -> Dict[str, Any]:
    """Load mock data that simulates plan compiler output"""
    
    # Mock BRD Analysis
    brd_analysis = {
        "status": "success",
        "analysis_result": {
            "project_feasibility": {
                "overall_score": 8.5,
                "technical_feasibility": 9.0,
                "resource_feasibility": 8.0,
                "timeline_feasibility": 8.5,
                "risk_level": "Medium"
            },
            "extracted_requirements": {
                "functional_requirements": [
                    "User registration and authentication system",
                    "Product catalog with search and filtering",
                    "Shopping cart and checkout process",
                    "Order management system",
                    "Payment processing integration",
                    "Inventory management",
                    "User profile management",
                    "Product reviews and ratings"
                ],
                "non_functional_requirements": [
                    "Support 10,000 concurrent users",
                    "99.9% system availability", 
                    "Response time under 200ms",
                    "GDPR compliance for user data",
                    "PCI DSS compliance for payments",
                    "Mobile responsive design"
                ],
                "business_requirements": [
                    "Multi-vendor marketplace capability",
                    "Commission-based revenue model",
                    "Real-time inventory tracking",
                    "Analytics and reporting dashboard",
                    "Customer support integration"
                ]
            }
        }
    }
    
    # Mock Tech Stack
    tech_stack = {
        "status": "success",
        "tech_stack_recommendation": {
            "recommended_stack": {
                "backend": {
                    "language": "Python",
                    "framework": "FastAPI",
                    "version": "0.104.1"
                },
                "database": {
                    "primary": "PostgreSQL",
                    "version": "15.0",
                    "cache": "Redis",
                    "cache_version": "7.0"
                },
                "frontend": {
                    "framework": "React",
                    "version": "18.2.0",
                    "language": "TypeScript",
                    "styling": "Tailwind CSS",
                    "state_management": "Redux Toolkit"
                },
                "infrastructure": {
                    "containerization": "Docker",
                    "orchestration": "Kubernetes",
                    "cloud_provider": "AWS",
                    "monitoring": "Prometheus + Grafana"
                }
            }
        }
    }
    
    # Mock System Design
    system_design = {
        "status": "success",
        "system_design": {
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
                        "created_at": "timestamp",
                        "updated_at": "timestamp"
                    },
                    "relationships": ["belongs_to category", "has_many order_items"]
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
                    "responsibilities": ["User management", "Authentication"]
                },
                {
                    "name": "product-service", 
                    "port": 8002,
                    "database": "products_db",
                    "responsibilities": ["Product catalog", "Inventory management"]
                },
                {
                    "name": "order-service",
                    "port": 8003,
                    "database": "orders_db",
                    "responsibilities": ["Order processing", "Cart management"]
                }
            ]
        }
    }
    
    # Mock Plan Compiler Output
    comprehensive_plan = {
        "status": "success",
        "comprehensive_plan": {
            "project_name": "E-Commerce Platform",
            "project_summary": {
                "overview": "A modern e-commerce platform with microservices architecture",
                "domain": "E-Commerce",
                "scale": "Medium",
                "target_users": 10000
            },
            "implementation_phases": [
                {
                    "phase_number": 1,
                    "name": "Foundation & Authentication",
                    "duration_weeks": 2,
                    "components": ["Architecture setup", "User service", "Authentication system"],
                    "deliverables": ["Project structure", "User registration/login", "JWT authentication"]
                },
                {
                    "phase_number": 2,
                    "name": "Product Catalog",
                    "duration_weeks": 3,
                    "components": ["Product service", "Category management", "Search functionality"],
                    "deliverables": ["Product CRUD APIs", "Category hierarchy", "Product search"]
                }
            ]
        }
    }
    
    return {
        "brd_analysis": brd_analysis,
        "tech_stack": tech_stack,
        "system_design": system_design,
        "comprehensive_plan": comprehensive_plan
    }

def setup_test_environment():
    """Setup test environment with logging and output directories"""
    
    # Setup basic logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Create test output directory
    test_output_dir = project_root / "test_output" / f"code_gen_test_{int(time.time())}"
    test_output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Created test output directory: {test_output_dir}")
    
    return logger, test_output_dir

def test_architecture_generator(mock_data: Dict[str, Any], output_dir: Path, memory: SharedProjectMemory, logger):
    """Test the Architecture Generator Agent"""
    
    logger.info("Testing Architecture Generator Agent...")
    
    try:
        # Setup config and LLM
        config = Config()
        llm = config.get_llm(temperature=0.2)
        
        # Create code execution tool
        code_execution_tool = CodeExecutionTool(str(output_dir))
        
        # Create Architecture Generator
        arch_agent = ArchitectureGeneratorAgent(
            llm=llm,
            memory=memory,
            temperature=0.2,
            output_dir=str(output_dir / "architecture"),
            code_execution_tool=code_execution_tool
        )
        
        # Run architecture generation
        result = arch_agent.run(
            requirements_analysis=mock_data["brd_analysis"]["analysis_result"],
            tech_stack=mock_data["tech_stack"]["tech_stack_recommendation"]["recommended_stack"],
            system_design=mock_data["system_design"]["system_design"]
        )
        
        logger.info(f"Architecture generation result: {result.get('status', 'unknown')}")
        if result.get("files"):
            logger.info(f"Generated {len(result['files'])} architecture files")
            
        return result
        
    except Exception as e:
        logger.error(f"Architecture generator test failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}

def test_backend_generator(mock_data: Dict[str, Any], output_dir: Path, memory: SharedProjectMemory, logger):
    """Test the Backend Generator Agent"""
    
    logger.info("Testing Backend Generator Agent...")
    
    try:
        # Setup config and LLM
        config = Config()
        llm = config.get_llm(temperature=0.2)
        
        # Create code execution tool
        code_execution_tool = CodeExecutionTool(str(output_dir))
        
        # Create Backend Generator
        backend_agent = BackendOrchestratorAgent(
            llm=llm,
            memory=memory,
            temperature=0.2,
            output_dir=str(output_dir / "backend"),
            code_execution_tool=code_execution_tool
        )
        
        # Run backend generation
        result = backend_agent.run(
            requirements_analysis=mock_data["brd_analysis"]["analysis_result"],
            tech_stack=mock_data["tech_stack"]["tech_stack_recommendation"]["recommended_stack"],
            system_design=mock_data["system_design"]["system_design"]
        )
        
        logger.info(f"Backend generation result: {result.get('status', 'unknown')}")
        if result.get("files"):
            logger.info(f"Generated {len(result['files'])} backend files")
            
        return result
        
    except Exception as e:
        logger.error(f"Backend generator test failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}

def test_database_generator(mock_data: Dict[str, Any], output_dir: Path, memory: SharedProjectMemory, logger):
    """Test the Database Generator Agent"""
    
    logger.info("Testing Database Generator Agent...")
    
    try:
        # Setup config and LLM
        config = Config()
        llm = config.get_llm(temperature=0.2)
        
        # Create code execution tool
        code_execution_tool = CodeExecutionTool(str(output_dir))
        
        # Create Database Generator
        db_agent = DatabaseGeneratorAgent(
            llm=llm,
            memory=memory,
            temperature=0.2,
            output_dir=str(output_dir / "database"),
            code_execution_tool=code_execution_tool
        )
        
        # Run database generation
        result = db_agent.run(
            requirements_analysis=mock_data["brd_analysis"]["analysis_result"],
            tech_stack=mock_data["tech_stack"]["tech_stack_recommendation"]["recommended_stack"],
            system_design=mock_data["system_design"]["system_design"]
        )
        
        logger.info(f"Database generation result: {result.get('status', 'unknown')}")
        if result.get("files"):
            logger.info(f"Generated {len(result['files'])} database files")
            
        return result
        
    except Exception as e:
        logger.error(f"Database generator test failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}

def run_comprehensive_test():
    """Run comprehensive test of all code generation agents"""
    
    # Setup test environment
    logger, test_output_dir = setup_test_environment()
    
    logger.info("Starting comprehensive code generation test...")
    logger.info(f"Test output directory: {test_output_dir}")
    
    # Load mock data
    mock_data = load_mock_data()
    logger.info("Loaded mock planning data")
    
    # Setup shared memory
    memory = SharedProjectMemory()
    
    # Store mock data in memory (simulate plan compiler output)
    memory.set("brd_analysis", mock_data["brd_analysis"])
    memory.set("tech_stack_recommendation", mock_data["tech_stack"])
    memory.set("system_design", mock_data["system_design"])
    memory.set("comprehensive_plan", mock_data["comprehensive_plan"])
    
    # Test results
    test_results = {}
    
    # Test Architecture Generator
    test_results["architecture"] = test_architecture_generator(mock_data, test_output_dir, memory, logger)
    
    # Test Backend Generator 
    test_results["backend"] = test_backend_generator(mock_data, test_output_dir, memory, logger)
    
    # Test Database Generator
    test_results["database"] = test_database_generator(mock_data, test_output_dir, memory, logger)
    
    # Save test results
    results_file = test_output_dir / "test_results.json"
    with open(results_file, 'w') as f:
        json.dump(test_results, f, indent=2, default=str)
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("CODE GENERATION TEST SUMMARY")
    logger.info("="*60)
    
    for agent_name, result in test_results.items():
        status = result.get('status', 'unknown')
        file_count = len(result.get('files', []))
        logger.info(f"{agent_name.title()} Generator: {status} ({file_count} files)")
    
    logger.info(f"\nTest output saved to: {test_output_dir}")
    logger.info(f"Detailed results saved to: {results_file}")
    
    return test_results

def run_code_generation_test():
    """Main test function for code generation"""
    print("🚀 Starting Code Generation Test...")
    
    # Mock data that simulates plan compiler output
    mock_data = {
        "brd_analysis": {
            "status": "success",
            "analysis_result": {
                "functional_requirements": [
                    "User authentication system",
                    "Product catalog management", 
                    "Shopping cart functionality",
                    "Order processing"
                ]
            }
        },
        "tech_stack": {
            "backend": {"language": "Python", "framework": "FastAPI"},
            "frontend": {"framework": "React", "language": "TypeScript"},
            "database": {"primary": "PostgreSQL", "cache": "Redis"}
        },
        "system_design": {
            "architecture_pattern": "Microservices",
            "data_models": [
                {"name": "User", "fields": ["id", "email", "password_hash"]},
                {"name": "Product", "fields": ["id", "name", "price"]},
                {"name": "Order", "fields": ["id", "user_id", "total_amount"]}
            ]
        }
    }
    
    print("✅ Mock data loaded successfully")
    print(f"📊 Mock data includes: {list(mock_data.keys())}")
    
    # Create test output directory
    test_output_dir = project_root / "test_output" / f"mock_test_{int(time.time())}"
    test_output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Test output directory: {test_output_dir}")
    
    # Save mock data for inspection
    with open(test_output_dir / "mock_data.json", 'w') as f:
        json.dump(mock_data, f, indent=2)
    
    print("✅ Test setup completed successfully!")
    print(f"🎯 Use this mock data to test individual code generation agents")
    
    return mock_data, test_output_dir

if __name__ == "__main__":
    try:
        mock_data, output_dir = run_code_generation_test()
        print(f"\n📋 Next steps:")
        print(f"1. Review mock data at: {output_dir}/mock_data.json")
        print(f"2. Test individual generators with this data")
        print(f"3. Check output in: {output_dir}")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 