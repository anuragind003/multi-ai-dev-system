#!/usr/bin/env python3
"""
Test script for the Generalized Backend Generator
Demonstrates how LLM-powered dynamic generation works vs hardcoded templates
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.code_generation.generalized_backend_generator import GeneralizedBackendGenerator
from tools.code_execution_tool import CodeExecutionTool
from config import get_llm
from utils.shared_memory_hub import get_shared_memory_hub

def create_mock_data():
    """Create comprehensive mock data for testing."""
    return {
        "requirements_analysis": {
            "functional_requirements": {
                "user_management": "Users can register, login, and manage profiles",
                "product_catalog": "Browse products with search, filter, and categories",
                "shopping_cart": "Add/remove items, calculate totals with tax",
                "order_processing": "Checkout, payment integration, order tracking",
                "authentication": "Secure login with JWT tokens and sessions",
                "file_upload": "Upload product images and user avatars",
                "email_notifications": "Send order confirmations and updates",
                "real_time_updates": "Live inventory and order status updates"
            },
            "non_functional_requirements": {
                "performance": {
                    "concurrent_users": 50000,
                    "response_time": "<100ms",
                    "throughput": "5000 rps"
                },
                "scalability": {
                    "horizontal_scaling": True,
                    "auto_scaling": True
                },
                "security": {
                    "data_encryption": True,
                    "secure_authentication": True,
                    "audit_logging": True
                }
            }
        },
        "tech_stack": {
            "backend": {
                "language": "Python",
                "framework": "FastAPI"
            },
            "database": {
                "primary": "PostgreSQL",
                "cache": "Redis"
            },
            "infrastructure": {
                "containerization": "Docker",
                "orchestration": "Kubernetes"
            }
        },
        "system_design": {
            "architecture_pattern": "Microservices",
            "deployment_strategy": "Cloud-native",
            "monitoring": {
                "metrics": "Prometheus",
                "logging": "ELK Stack",
                "tracing": "Jaeger"
            }
        }
    }

def test_different_frameworks():
    """Test the generator with different frameworks to show adaptability."""
    
    frameworks_to_test = [
        {"language": "Python", "framework": "FastAPI"},
        {"language": "Python", "framework": "Django"},
        {"language": "JavaScript", "framework": "Express"},
        {"language": "Java", "framework": "Spring Boot"}
    ]
    
    base_data = create_mock_data()
    
    for tech in frameworks_to_test:
        print(f"\n🚀 Testing {tech['framework']} ({tech['language']}) Generation")
        print("=" * 60)
        
        # Update tech stack
        test_data = base_data.copy()
        test_data["tech_stack"]["backend"] = tech
        
        # Create generator
        llm = get_llm()
        memory = get_shared_memory_hub()
        code_execution_tool = CodeExecutionTool(
            output_dir=f"test_output/generalized_{tech['framework'].lower()}_test"
        )
        
        generator = GeneralizedBackendGenerator(
            llm=llm,
            memory=memory,
            temperature=0.3,
            output_dir=f"test_output/generalized_{tech['framework'].lower()}_test",
            code_execution_tool=code_execution_tool
        )
        
        # Generate backend
        result = generator.generate_backend(
            tech_stack=test_data["tech_stack"],
            system_design=test_data["system_design"],
            requirements_analysis=test_data["requirements_analysis"]
        )
        
        # Display results
        if result["status"] == "success":
            print(f"✅ Generated {result['summary']['total_files']} files successfully!")
            print(f"   - Generated modules: {result['summary']['generated_modules']}")
            print(f"   - Supporting files: {result['summary']['supporting_files']}")
            print(f"   - Generation method: {result['summary']['generation_method']}")
            print(f"   - Framework adaptability: {result['summary']['adaptability']}")
            print(f"   - Domain awareness: {result['summary']['domain_awareness']}")
            
            # Show some generated files
            print(f"\n📁 Generated files for {tech['framework']}:")
            for i, file in enumerate(result["files"][:5]):  # Show first 5 files
                print(f"   {i+1}. {file['name']} - {file['description']}")
            if len(result["files"]) > 5:
                print(f"   ... and {len(result['files']) - 5} more files")
                
        else:
            print(f"❌ Generation failed: {result.get('error', 'Unknown error')}")

def test_different_domains():
    """Test the generator with different domains to show domain awareness."""
    
    domains_to_test = [
        {
            "name": "E-commerce",
            "requirements": {
                "functional_requirements": {
                    "product_catalog": "Manage products, categories, inventory",
                    "shopping_cart": "Add items, calculate totals, apply discounts",
                    "payment_processing": "Integrate with Stripe, PayPal",
                    "order_management": "Track orders, shipping, returns"
                }
            }
        },
        {
            "name": "Healthcare",
            "requirements": {
                "functional_requirements": {
                    "patient_records": "Manage HIPAA-compliant patient data",
                    "appointment_scheduling": "Book and manage medical appointments",
                    "medical_history": "Track patient medical history and treatments",
                    "prescription_management": "Manage prescriptions and refills"
                }
            }
        },
        {
            "name": "Financial",
            "requirements": {
                "functional_requirements": {
                    "account_management": "Manage customer financial accounts",
                    "transaction_processing": "Process secure financial transactions",
                    "fraud_detection": "Monitor and detect fraudulent activities",
                    "compliance_reporting": "Generate SOX and regulatory reports"
                }
            }
        }
    ]
    
    base_data = create_mock_data()
    
    for domain in domains_to_test:
        print(f"\n🏥 Testing {domain['name']} Domain Generation")
        print("=" * 60)
        
        # Update requirements for domain
        test_data = base_data.copy()
        test_data["requirements_analysis"].update(domain["requirements"])
        
        # Create generator
        llm = get_llm()
        memory = get_shared_memory_hub()
        code_execution_tool = CodeExecutionTool(
            output_dir=f"test_output/generalized_{domain['name'].lower()}_test"
        )
        
        generator = GeneralizedBackendGenerator(
            llm=llm,
            memory=memory,
            temperature=0.3,
            output_dir=f"test_output/generalized_{domain['name'].lower()}_test",
            code_execution_tool=code_execution_tool
        )
        
        # Generate backend
        result = generator.generate_backend(
            tech_stack=test_data["tech_stack"],
            system_design=test_data["system_design"],
            requirements_analysis=test_data["requirements_analysis"]
        )
        
        # Display results
        if result["status"] == "success":
            spec = result["backend_specification"]
            print(f"✅ Generated {domain['name']} backend successfully!")
            print(f"   - Domain: {spec['domain']}")
            print(f"   - Scale: {spec['scale']}")
            print(f"   - Security Level: {spec['security_level']}")
            print(f"   - Compliance: {', '.join(spec['compliance'])}")
            print(f"   - Features: {', '.join(spec['features'][:5])}...")
            print(f"   - Total Files: {result['summary']['total_files']}")
            
        else:
            print(f"❌ Generation failed: {result.get('error', 'Unknown error')}")

def demonstrate_key_advantages():
    """Demonstrate the key advantages of the generalized approach."""
    
    print("\n" + "="*80)
    print("🎯 GENERALIZED BACKEND GENERATOR - KEY ADVANTAGES")
    print("="*80)
    
    advantages = [
        {
            "title": "🔄 Framework Agnostic",
            "description": "Adapts to any backend framework without code changes",
            "examples": ["FastAPI", "Django", "Express", "Spring Boot", "ASP.NET"]
        },
        {
            "title": "🧠 Domain Intelligence", 
            "description": "Understands domain requirements and generates appropriate code",
            "examples": ["E-commerce", "Healthcare", "Finance", "IoT", "SaaS"]
        },
        {
            "title": "📈 Scale Awareness",
            "description": "Optimizes for different production scales automatically", 
            "examples": ["Startup", "Enterprise", "Hyperscale"]
        },
        {
            "title": "🔒 Security & Compliance",
            "description": "Implements domain-appropriate security and compliance",
            "examples": ["HIPAA", "GDPR", "SOX", "PCI-DSS"]
        },
        {
            "title": "⚡ Dynamic Feature Detection",
            "description": "Analyzes requirements to determine needed features",
            "examples": ["Authentication", "Caching", "WebSockets", "Background Jobs"]
        },
        {
            "title": "🎨 LLM-Powered Generation",
            "description": "Uses intelligent prompting for context-aware code generation",
            "examples": ["No hardcoded templates", "Adaptive to context", "Best practices"]
        }
    ]
    
    for advantage in advantages:
        print(f"\n{advantage['title']}")
        print(f"   {advantage['description']}")
        print(f"   Examples: {', '.join(advantage['examples'])}")
    
    print(f"\n💡 COMPARISON: Hardcoded vs Generalized")
    print("   ❌ Hardcoded Templates:")
    print("      - Fixed for specific frameworks")
    print("      - Manual updates for new features")
    print("      - No domain awareness")
    print("      - Limited adaptability")
    
    print("   ✅ Generalized LLM-Powered:")
    print("      - Adapts to any framework")
    print("      - Intelligent feature detection")
    print("      - Domain-aware generation")
    print("      - Context-sensitive optimization")

if __name__ == "__main__":
    print("🚀 GENERALIZED BACKEND GENERATOR DEMONSTRATION")
    print("This shows how to move from hardcoded templates to intelligent generation")
    
    try:
        # Demonstrate key advantages
        demonstrate_key_advantages()
        
        # Test framework adaptability
        print(f"\n🔄 TESTING FRAMEWORK ADAPTABILITY")
        test_different_frameworks()
        
        # Test domain intelligence
        print(f"\n🧠 TESTING DOMAIN INTELLIGENCE") 
        test_different_domains()
        
        print(f"\n🎉 DEMONSTRATION COMPLETE!")
        print("The generalized approach shows how LLM-powered generation")
        print("eliminates hardcoding while providing superior adaptability.")
        
    except Exception as e:
        print(f"❌ Demonstration failed: {str(e)}")
        import traceback
        traceback.print_exc() 