"""
Tests for the refactored evaluate_all_technologies function.
This test verifies it can handle input coming from ReAct agents.
"""
import json
import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add the root directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.data_contracts import BatchTechnologyEvaluationInput
from tools.tech_stack_tools import evaluate_all_technologies

class TestEvaluateAllTechnologies(unittest.TestCase):
    """Test cases for the refactored evaluate_all_technologies function."""
    
    @patch('tools.tech_stack_tools.evaluate_backend_options')
    @patch('tools.tech_stack_tools.evaluate_frontend_options')
    @patch('tools.tech_stack_tools.evaluate_database_options')
    def test_with_direct_pydantic_model(self, mock_db, mock_frontend, mock_backend):
        """Test with direct Pydantic model input."""
        # Setup mocks
        mock_backend.return_value = {"name": "NodeJS", "score": 8}
        mock_frontend.return_value = {"name": "React", "score": 9}
        mock_db.return_value = {"name": "PostgreSQL", "score": 8}
        
        # Create test input
        test_input = BatchTechnologyEvaluationInput(
            requirements_summary="Build a scalable web application with high performance needs",
            evaluate_backend=True,
            evaluate_frontend=True,
            evaluate_database=True,
            ux_focus="Modern, responsive UI"
        )
        
        # Call the function
        result = evaluate_all_technologies.func(test_input)
        
        # Assert results
        self.assertIn('backend', result)
        self.assertIn('frontend', result)
        self.assertIn('database', result)
        self.assertEqual(mock_backend.call_count, 1)
        self.assertEqual(mock_frontend.call_count, 1)
        self.assertEqual(mock_db.call_count, 1)
    
    @patch('tools.tech_stack_tools.evaluate_backend_options')
    @patch('tools.tech_stack_tools.evaluate_frontend_options')
    @patch('tools.tech_stack_tools.evaluate_database_options')
    def test_with_json_string_input(self, mock_db, mock_frontend, mock_backend):
        """Test with JSON string input (ReAct agent style)."""
        # Setup mocks
        mock_backend.return_value = {"name": "Python", "score": 8}
        mock_frontend.return_value = {"name": "Angular", "score": 8}
        mock_db.return_value = {"name": "MongoDB", "score": 7}
        
        # Create JSON string input like ReAct agents would provide
        test_json = json.dumps({
            "requirements_summary": "Create a CRM system for small business",
            "evaluate_frontend": True,
            "evaluate_backend": True,
            "evaluate_database": False  # Only test two technologies
        })
        
        # Call the function with string input
        result = evaluate_all_technologies.func(test_json)
        
        # Assert results
        self.assertIn('backend', result)
        self.assertIn('frontend', result)
        self.assertNotIn('database', result)  # Should not be evaluated
        self.assertEqual(mock_backend.call_count, 1)
        self.assertEqual(mock_frontend.call_count, 1)
        self.assertEqual(mock_db.call_count, 0)
    
    @patch('tools.tech_stack_tools.evaluate_backend_options')
    @patch('tools.tech_stack_tools.evaluate_frontend_options')
    @patch('tools.tech_stack_tools.evaluate_database_options')
    def test_with_plain_string_input(self, mock_db, mock_frontend, mock_backend):
        """Test with a plain string input (error case)."""
        # Setup mocks
        mock_backend.return_value = {"name": "Java", "score": 7}
        mock_frontend.return_value = {"name": "Vue", "score": 8}
        mock_db.return_value = {"name": "MySQL", "score": 7}
        
        # Call the function with a plain string
        test_string = "Build a high-performance web application with complex data processing"
        result = evaluate_all_technologies.func(test_string)
        
        # Should use the string as requirements_summary and default evaluate flags
        self.assertIn('backend', result)
        self.assertIn('frontend', result)
        self.assertIn('database', result)
        self.assertEqual(mock_backend.call_count, 1)
        self.assertEqual(mock_frontend.call_count, 1)
        self.assertEqual(mock_db.call_count, 1)

if __name__ == "__main__":
    unittest.main()
