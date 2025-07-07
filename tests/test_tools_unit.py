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
            result = design_component_structure(**input_model.dict())
        
        # Verify the result
        self.assertEqual(result.name, "UserManagement")
        self.assertIn("Handle user authentication", result.responsibilities)
        self.assertEqual(len(result.internal_components), 1)
        self.assertEqual(result.internal_components[0].name, "AuthService")


if __name__ == "__main__":
    unittest.main()
