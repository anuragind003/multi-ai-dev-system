"""
Tests for the refactored tools according to the Golden Rule pattern.
Unit tests that directly call the implementation functions to verify correct behavior.
"""
import json
import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add the root directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.data_contracts import (
    ComponentStructureDesignInput, 
    TechStackSynthesisInput,
    ApiEndpointsDesignInput,
    TechStackSynthesisOutput,
    ComponentDesignOutput
)

class TestTechStackTools(unittest.TestCase):
    """Test the functionality of the refactored tech stack tools functions."""
    
    @patch('tools.tech_stack_tools.PydanticOutputParser')
    @patch('tools.tech_stack_tools.PromptTemplate')
    @patch('tools.tech_stack_tools.LLMChain')
    def test_synthesize_tech_stack(self, mock_llm_chain, mock_prompt, mock_parser):
        """Test the synthesize_tech_stack function implementation."""
        # Import here to avoid decorator execution
        from tools.tech_stack_tools import synthesize_tech_stack
        
        # Create mock outputs
        mock_parser_instance = MagicMock()
        mock_parser.return_value = mock_parser_instance
        mock_parser_instance.get_format_instructions.return_value = "FORMAT INSTRUCTIONS"
        
        mock_chain_instance = MagicMock()
        mock_llm_chain.return_value = mock_chain_instance
        
        # Create a sample output
        mock_output = TechStackSynthesisOutput(
            backend={"language": "Python", "framework": "FastAPI"},
            frontend={"language": "JavaScript", "framework": "React"},
            database={"type": "PostgreSQL"},
            architecture_pattern="Microservices",
            deployment_environment={"platform": "Kubernetes"},
            key_libraries_tools=[],
            estimated_complexity="Medium"
        )
        mock_chain_instance.invoke.return_value = mock_output
        
        # Create test input
        input_model = TechStackSynthesisInput(
            backend_recommendation={"language": "Python", "framework": "FastAPI"},
            frontend_recommendation={"language": "JavaScript", "framework": "React"},
            database_recommendation={"type": "PostgreSQL"}
        )
        
        # Call the function
        result = synthesize_tech_stack(input_model)
        
        # Verify the result
        self.assertEqual(result.backend["language"], "Python")
        self.assertEqual(result.frontend["framework"], "React")
        self.assertEqual(result.database["type"], "PostgreSQL")


class TestDesignTools(unittest.TestCase):
    """Test the functionality of the refactored design tools functions."""
    
    @patch('tools.design_tools.JsonHandler')
    def test_design_component_structure(self, mock_json_handler):
        """Test the design_component_structure function implementation."""
        # Import here to avoid decorator execution
        from tools.design_tools import design_component_structure
        
        # Create mock outputs
        mock_json_llm = MagicMock()
        mock_json_handler.create_strict_json_llm.return_value = mock_json_llm
        
        # Mock the JSON response
        component_design = {
            "name": "UserManagement",
            "responsibilities": ["Handle user authentication", "Manage user profiles"],
            "internal_components": [
                {"name": "AuthService", "responsibility": "Handle authentication"}
            ],
            "dependencies": ["Database"],
            "design_patterns": ["Repository", "Facade"]
        }
        mock_json_llm.invoke.return_value = component_design
        
        # Create test input
        input_model = ComponentStructureDesignInput(
            component_name="UserManagement",
            requirements_summary="User authentication and profile management"
        )
        
        # Call the function
        with patch('tools.design_tools.get_tool_llm'):
            result = design_component_structure(input_model)
        
        # Verify the result
        self.assertEqual(result.name, "UserManagement")
        self.assertIn("Handle user authentication", result.responsibilities)
        self.assertEqual(len(result.internal_components), 1)
        self.assertEqual(result.internal_components[0].name, "AuthService")


if __name__ == "__main__":
    unittest.main()
