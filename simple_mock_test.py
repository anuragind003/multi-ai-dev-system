#!/usr/bin/env python3
"""
Simple Mock Test for Code Generation
Creates mock data that simulates plan compiler output and saves it for testing.
"""

import json
import time
from pathlib import Path

def create_mock_data():
    """Create comprehensive mock data simulating plan compiler output"""
    
    return {
        "brd_analysis": {
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
                    ]
                }
            }
        },
        "tech_stack": {
            "status": "success",
            "tech_stack_recommendation": {
                "recommended_stack": {
                    "backend": {
                        "language": "Python",
                        "framework": "FastAPI",
                        "version": "0.104.1",
                        "database": "PostgreSQL",
                        "cache": "Redis"
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
        },
        "system_design": {
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
        },
        "comprehensive_plan": {
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
                    },
                    {
                        "phase_number": 3,
                        "name": "Shopping & Orders",
                        "duration_weeks": 4,
                        "components": ["Cart service", "Order service", "Payment integration"],
                        "deliverables": ["Shopping cart", "Order processing", "Payment gateway"]
                    }
                ]
            }
        }
    }

def main():
    """Main function to create and save mock data"""
    
    print("🚀 Creating Mock Data for Code Generation Testing")
    print("="*60)
    
    # Create output directory
    output_dir = Path("test_output") / f"mock_data_{int(time.time())}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Output directory: {output_dir}")
    
    # Create mock data
    mock_data = create_mock_data()
    
    # Save complete mock data
    with open(output_dir / "complete_mock_data.json", 'w') as f:
        json.dump(mock_data, f, indent=2)
    
    # Save individual components
    for component_name, component_data in mock_data.items():
        with open(output_dir / f"{component_name}.json", 'w') as f:
            json.dump(component_data, f, indent=2)
    
    print("✅ Mock data created successfully!")
    print("\n📊 Mock Data Summary:")
    print(f"   • BRD Analysis: {len(mock_data['brd_analysis']['analysis_result']['extracted_requirements']['functional_requirements'])} functional requirements")
    print(f"   • Tech Stack: {mock_data['tech_stack']['tech_stack_recommendation']['recommended_stack']['backend']['framework']} backend")
    print(f"   • System Design: {len(mock_data['system_design']['system_design']['data_models'])} data models")
    print(f"   • Plan: {len(mock_data['comprehensive_plan']['comprehensive_plan']['implementation_phases'])} implementation phases")
    
    print(f"\n📄 Files created:")
    for file in output_dir.glob("*.json"):
        print(f"   • {file.name}")
    
    print(f"\n🎯 Next Steps:")
    print("1. Review the generated mock data files")
    print("2. Test individual code generation agents with this data")
    print("3. Use this data to validate your code generation pipeline")
    
    print(f"\n💡 Example usage:")
    print(f"   python test_architecture_generator.py")
    print(f"   # (modify test script to load from {output_dir}/complete_mock_data.json)")
    
    return output_dir

if __name__ == "__main__":
    main() 