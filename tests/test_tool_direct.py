"""
Simple script to verify the refactored tools function correctly with the Golden Rule pattern.
"""
import sys
import os
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.data_contracts import (
    ComponentStructureDesignInput, 
    TechStackSynthesisInput,
    ApiEndpointsDesignInput
)

def main():
    """Test the refactored tools with direct invocation."""
    print("Testing refactored tools for ReAct Agent compatibility...")
    
    # Get the function implementations
    import tools.tech_stack_tools as tech_tools
    import tools.design_tools as design_tools
    
    # Create tech stack synthesis input
    tech_input = TechStackSynthesisInput(
        backend_recommendation={"language": "Python", "framework": "FastAPI"},
        frontend_recommendation={"language": "TypeScript", "framework": "React"},
        database_recommendation={"type": "PostgreSQL"}
    )
    
    # Get the actual function without decorator
    synthesize_tech_stack_func = tech_tools.synthesize_tech_stack.func
    
    print("\nTesting synthesize_tech_stack...")
    try:
        # Call the function directly
        result = synthesize_tech_stack_func(tech_input)
        print(f"Success! Tool returned: {type(result)}")
        print(f"  Backend: {result.backend['language']}/{result.backend['framework']}")
        print(f"  Frontend: {result.frontend['language']}/{result.frontend['framework']}")
        print(f"  Database: {result.database['type']}")
    except Exception as e:
        print(f"ERROR: {str(e)}")
    
    # Test component structure design
    print("\nTesting design_component_structure...")
    component_input = ComponentStructureDesignInput(
        component_name="UserManagement",
        requirements_summary="The system needs to handle user registration, authentication, and profile management."
    )
    
    design_component_func = design_tools.design_component_structure.func
    
    try:
        result = design_component_func(component_input)
        print(f"Success! Tool returned: {type(result)}")
        print(f"  Component name: {result.name}")
        print(f"  Responsibilities: {result.responsibilities[:2]}...")
        print(f"  Internal components: {len(result.internal_components)}")
    except Exception as e:
        print(f"ERROR: {str(e)}")
    
    # Test API endpoints design
    print("\nTesting design_api_endpoints...")
    api_input = ApiEndpointsDesignInput(
        requirements_summary="A RESTful API for managing blog posts and comments",
        components=json.dumps(["Posts", "Comments", "Users"])
    )
    
    design_api_func = design_tools.design_api_endpoints.func
    
    try:
        result = design_api_func(api_input)
        print(f"Success! Tool returned type: {type(result)}")
        api_data = json.loads(result)
        print(f"  API style: {api_data['style']}")
        print(f"  Endpoints: {len(api_data['endpoints'])}")
    except Exception as e:
        print(f"ERROR: {str(e)}")
    
    print("\nTesting complete!")

if __name__ == "__main__":
    main()
