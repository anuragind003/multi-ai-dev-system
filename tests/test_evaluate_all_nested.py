"""
Tests for the nested function calls in evaluate_all_technologies.
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

class TestEvaluateAllNestedCalls(unittest.TestCase):
    """Test cases for nested function calls in evaluate_all_technologies."""
    
    @patch('tools.tech_stack_tools.evaluate_backend_options')
    @patch('tools.tech_stack_tools.evaluate_frontend_options')
    @patch('tools.tech_stack_tools.evaluate_database_options')
    def test_nested_function_calls(self, mock_db, mock_frontend, mock_backend):
        """Test that nested function calls use .func attribute."""
        # Setup mocks with func attribute
        mock_backend.func = MagicMock(return_value={"name": "NodeJS"})
        mock_frontend.func = MagicMock(return_value={"name": "React"})
        mock_db.func = MagicMock(return_value={"name": "PostgreSQL"})
        
        # Create test input
        test_input = BatchTechnologyEvaluationInput(
            requirements_summary="Build a scalable web application with high performance needs",
            evaluate_backend=True,
            evaluate_frontend=True, 
            evaluate_database=True
        )
        
        # Call the function
        result = evaluate_all_technologies.func(test_input)
        
        # Assert results
        self.assertIn('backend', result)
        self.assertIn('frontend', result)
        self.assertIn('database', result)
        
        # Assert that the .func attributes were called, not the decorated functions
        mock_backend.assert_not_called()
        mock_frontend.assert_not_called()
        mock_db.assert_not_called()
        
        mock_backend.func.assert_called_once()
        mock_frontend.func.assert_called_once()
        mock_db.func.assert_called_once()

if __name__ == "__main__":
    unittest.main()
