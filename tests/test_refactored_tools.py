"""
Tests for the refactored tools according to the Golden Rule pattern.
Tests how ReAct agents will call the tools, ensuring they handle single-argument input correctly.
"""
import json
import unittest
import sys
import os
import importlib

# Add the root directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.data_contracts import (
    ComponentStructureDesignInput, 
    TechStackSynthesisInput,
    ApiEndpointsDesignInput
)

# Import the modules, not the functions directly
import tools.tech_stack_tools as tech_tools
import tools.design_tools as design_tools


class TestRefactoredTools(unittest.TestCase):
    """Test cases for refactored tools to verify they handle ReAct agent-style input."""
    
    def test_synthesize_tech_stack_direct_input(self):
        """Test synthesize_tech_stack with direct input model."""
        input_model = TechStackSynthesisInput(
            backend_recommendation={"language": "Python", "framework": "FastAPI"},
            frontend_recommendation={"language": "JavaScript", "framework": "React"},
            database_recommendation={"type": "PostgreSQL"}
        )
        
        # Call the function directly, not through the @tool decorator
        result = tech_tools.synthesize_tech_stack.__wrapped__(input_model)
        self.assertIsNotNone(result)
        self.assertIn("backend", result.dict())
        self.assertIn("frontend", result.dict())
        self.assertIn("database", result.dict())
    
    def test_synthesize_tech_stack_json_string(self):
        """Test synthesize_tech_stack with JSON string input (ReAct agent style)."""
        # This simulates how a ReAct agent would pass data to the tool
        input_json = json.dumps({
            "backend_recommendation": {"language": "Python", "framework": "Django"},
            "frontend_recommendation": {"language": "TypeScript", "framework": "Angular"},
            "database_recommendation": {"type": "MongoDB"}
        })
        input_model = TechStackSynthesisInput(combined_input=input_json)
        
        # Call the function directly, not through the @tool decorator
        result = tech_tools.synthesize_tech_stack.__wrapped__(input_model)
        self.assertIsNotNone(result)
        self.assertIn("backend", result.dict())
        self.assertIn("frontend", result.dict())
        self.assertIn("database", result.dict())
    
    def test_design_component_structure(self):
        """Test design_component_structure with direct input model."""
        input_model = ComponentStructureDesignInput(
            component_name="UserManagement",
            requirements_summary="The system needs to handle user registration, authentication, and profile management."
        )
        
        # Call the function directly, not through the @tool decorator
        result = design_tools.design_component_structure.__wrapped__(input_model)
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "UserManagement")
        self.assertIsInstance(result.responsibilities, list)
        self.assertIsInstance(result.internal_components, list)
    
    def test_design_api_endpoints(self):
        """Test design_api_endpoints with direct input model."""
        input_model = ApiEndpointsDesignInput(
            requirements_summary="A RESTful API for managing blog posts and comments",
            components=json.dumps(["Posts", "Comments", "Users"])
        )
        
        # Call the function directly, not through the @tool decorator
        result = design_tools.design_api_endpoints.__wrapped__(input_model)
        self.assertIsNotNone(result)
        # The result is a JSON string
        api_design = json.loads(result)
        self.assertIn("style", api_design)
        self.assertIn("endpoints", api_design)


if __name__ == "__main__":
    unittest.main()
