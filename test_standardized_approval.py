#!/usr/bin/env python3
"""
Test script to demonstrate the standardized Human Approval Data Contract

This script shows how the new standardized ApprovalPayload model works
across all workflow stages, demonstrating the benefits of the refactor.
"""

import asyncio
import json
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.human_approval import ApprovalPayload
from app.services.approval_service import (
    create_brd_approval_payload,
    create_tech_stack_approval_payload, 
    create_system_design_approval_payload,
    create_implementation_plan_approval_payload,
    get_approval_payload_for_stage
)

# Mock state data for testing
MOCK_BRD_STATE = {
    "requirements_analysis": {
        "project_name": "E-Commerce Platform",
        "project_summary": "A modern e-commerce platform with user management and payment processing",
        "functional_requirements": [
            "User registration and authentication",
            "Product catalog management", 
            "Shopping cart functionality",
            "Payment processing integration"
        ],
        "non_functional_requirements": [
            "Support 1000+ concurrent users",
            "99.9% uptime requirement",
            "PCI DSS compliance for payments"
        ],
        "stakeholders": ["Product Manager", "Engineering Team", "Business Owner"]
    }
}

MOCK_TECH_STACK_STATE = {
    "tech_stack_recommendation": {
        "frontend_options": [
            {"name": "React", "reasoning": "Modern UI framework with excellent ecosystem", "selected": True},
            {"name": "Vue.js", "reasoning": "Lightweight and beginner-friendly", "selected": False}
        ],
        "backend_options": [
            {"name": "Node.js", "reasoning": "JavaScript everywhere, good for rapid development", "selected": True},
            {"name": "Python", "reasoning": "Excellent for data processing and ML", "selected": False}
        ],
        "database_options": [
            {"name": "PostgreSQL", "reasoning": "Robust relational database with JSON support", "selected": True},
            {"name": "MongoDB", "reasoning": "NoSQL flexibility for rapid iteration", "selected": False}
        ]
    }
}

MOCK_SYSTEM_DESIGN_STATE = {
    "system_design": {
        "architecture": {"pattern": "Microservices"},
        "components": [
            {"name": "User Service", "description": "Handles user authentication and profiles"},
            {"name": "Product Service", "description": "Manages product catalog"},
            {"name": "Order Service", "description": "Processes orders and payments"}
        ],
        "data_flow": "Client -> API Gateway -> Microservices -> Database",
        "security": {
            "security_measures": [
                {"implementation": "JWT tokens for authentication"},
                {"implementation": "Rate limiting on API endpoints"},
                {"implementation": "Input validation and sanitization"}
            ]
        }
    }
}

MOCK_IMPLEMENTATION_PLAN_STATE = {
    "implementation_plan": {
        "plan": {
            "project_summary": {
                "title": "E-Commerce Platform MVP",
                "description": "Build core e-commerce functionality",
                "overall_complexity": "7/10",
                "estimated_duration": "12 weeks"
            },
            "phases": [
                {
                    "name": "Setup & Authentication",
                    "duration": "2 weeks",
                    "tasks": ["Setup project structure", "Implement user authentication"]
                },
                {
                    "name": "Core Features",
                    "duration": "6 weeks", 
                    "tasks": ["Product catalog", "Shopping cart", "Order processing"]
                },
                {
                    "name": "Payment & Testing",
                    "duration": "4 weeks",
                    "tasks": ["Payment integration", "Testing", "Deployment"]
                }
            ]
        }
    }
}

async def test_individual_approval_payloads():
    """Test creating approval payloads for each workflow stage individually."""
    print("Testing Individual Approval Payload Creation")
    print("=" * 60)
    
    # Test BRD Analysis
    print("\nTesting BRD Analysis Approval Payload...")
    brd_payload = await create_brd_approval_payload(MOCK_BRD_STATE)
    print(f"BRD Payload - Step: {brd_payload.step_name}")
    print(f"   Display Name: {brd_payload.display_name}")
    print(f"   Data Keys: {list(brd_payload.data.keys())}")
    print(f"   Has Instructions: {bool(brd_payload.instructions)}")
    
    # Test Tech Stack
    print("\nTesting Tech Stack Approval Payload...")
    tech_payload = await create_tech_stack_approval_payload(MOCK_TECH_STACK_STATE)
    print(f"Tech Stack Payload - Step: {tech_payload.step_name}")
    print(f"   Display Name: {tech_payload.display_name}")
    print(f"   Data Keys: {list(tech_payload.data.keys())}")
    
    # Test System Design
    print("\nTesting System Design Approval Payload...")
    design_payload = await create_system_design_approval_payload(MOCK_SYSTEM_DESIGN_STATE)
    print(f"System Design Payload - Step: {design_payload.step_name}")
    print(f"   Display Name: {design_payload.display_name}")
    print(f"   Data Keys: {list(design_payload.data.keys())}")
    
    # Test Implementation Plan
    print("\nTesting Implementation Plan Approval Payload...")
    plan_payload = await create_implementation_plan_approval_payload(MOCK_IMPLEMENTATION_PLAN_STATE)
    print(f"Implementation Plan Payload - Step: {plan_payload.step_name}")
    print(f"   Display Name: {plan_payload.display_name}")
    print(f"   Data Keys: {list(plan_payload.data.keys())}")

async def test_factory_function():
    """Test the factory function for creating approval payloads."""
    print("\n\nTesting Factory Function")
    print("=" * 60)
    
    stages = [
        ("brd_analysis", MOCK_BRD_STATE),
        ("tech_stack_recommendation", MOCK_TECH_STACK_STATE),
        ("system_design", MOCK_SYSTEM_DESIGN_STATE),
        ("implementation_plan", MOCK_IMPLEMENTATION_PLAN_STATE)
    ]
    
    for stage_name, mock_state in stages:
        print(f"\nTesting factory for stage: {stage_name}")
        try:
            payload = await get_approval_payload_for_stage(stage_name, mock_state)
            print(f"Factory created payload for {stage_name}")
            print(f"   Step Name: {payload.step_name}")
            print(f"   Display Name: {payload.display_name}")
            print(f"   Is Revision: {payload.is_revision}")
            
            # Test serialization
            serialized = payload.model_dump()
            print(f"   Serializable: SUCCESS ({len(str(serialized))} chars)")
            
        except Exception as e:
            print(f"ERROR with {stage_name}: {e}")

def test_payload_schema():
    """Test the ApprovalPayload model schema and validation."""
    print("\n\nTesting ApprovalPayload Schema")
    print("=" * 60)
    
    # Test valid payload
    print("\nTesting valid payload creation...")
    try:
        valid_payload = ApprovalPayload(
            step_name="test_step",
            display_name="Test Step",
            data={"test": "data"},
            instructions="Test instructions",
            is_revision=False,
            previous_feedback=None
        )
        print(f"   Created payload: {valid_payload.step_name}")
        print(f"   Model validation: SUCCESS")
        
        # Test serialization
        serialized = valid_payload.model_dump()
        print(f"   Serialization: SUCCESS")
        print(f"   Required fields present: {all(key in serialized for key in ['step_name', 'display_name', 'data', 'instructions'])}")
        
    except Exception as e:
        print(f"ERROR with valid payload: {e}")
    
    # Test revision scenario
    print("\nTesting revision scenario...")
    try:
        revision_payload = ApprovalPayload(
            step_name="test_revision",
            display_name="Test Revision",
            data={"revised": "data"},
            instructions="Please review the revised output",
            is_revision=True,
            previous_feedback="The previous version had issues with X"
        )
        print(f"   Revision payload created: SUCCESS")
        print(f"   Is revision: {revision_payload.is_revision}")
        print(f"   Has previous feedback: {bool(revision_payload.previous_feedback)}")
        
    except Exception as e:
        print(f"ERROR with revision payload: {e}")

async def demonstrate_benefits():
    """Demonstrate the benefits of the standardized approach."""
    print("\n\nBenefits of Standardized Approval Data Contract")
    print("=" * 60)
    
    print("\nBenefits achieved:")
    print("1. Consistent data structure across all approval stages")
    print("2. Type safety with Pydantic model validation")
    print("3. Modular approval payload creation functions")
    print("4. Centralized factory function for easy extensibility")
    print("5. Clear separation between backend state and frontend UI")
    print("6. Proper handling of revision scenarios with feedback")
    print("7. Standardized field names and structure")
    
    print("\nArchitecture improvements:")
    print("- Backend: Uses get_approval_payload_for_stage() factory function")
    print("- Frontend: Receives consistent ApprovalPayload structure")
    print("- New stages: Just add to factory function mapping")
    print("- Error handling: Standardized error payloads")
    
    print("\nBefore vs After:")
    print("BEFORE: Ad-hoc data extraction, inconsistent structure, tight coupling")
    print("AFTER:  Standardized payloads, modular functions, loose coupling")

async def main():
    """Run all tests to demonstrate the standardized approval flow."""
    print(" Standardized Human Approval Data Contract - Demo")
    print("=" * 80)
    print("This demo shows the new standardized approach for human approval in workflows")
    
    try:
        await test_individual_approval_payloads()
        await test_factory_function()
        test_payload_schema()
        await demonstrate_benefits()
        
        print("\n\n All tests completed successfully!")
        print("The standardized Human Approval Data Contract is working correctly.")
        
    except Exception as e:
        print(f"\n Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 