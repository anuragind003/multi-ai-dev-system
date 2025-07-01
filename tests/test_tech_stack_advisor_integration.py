"""
Integration test for the TechStackAdvisorReActAgent with refactored tools.
"""
import json
import logging
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

# Add the root directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import agent and necessary components
from agents.tech_stack_advisor_react import TechStackAdvisorReActAgent
from models.data_contracts import TechStackSynthesisOutput

class TestTechStackAdvisorIntegration(unittest.TestCase):
    """Integration tests for the TechStackAdvisorReActAgent with refactored tools."""
    
    def setUp(self):
        """Set up test environment."""
        # Create mock LLM and memory
        self.mock_llm = MagicMock()
        self.mock_memory = MagicMock()
        self.mock_llm.bind.return_value = self.mock_llm
        
        # Sample BRD analysis for testing
        self.brd_analysis = {
            "project_name": "Test CRM System",
            "project_summary": "A customer relationship management system for small businesses",
            "requirements": [
                {
                    "id": "REQ-001",
                    "description": "The system must handle user authentication and authorization",
                    "category": "Functional",
                    "priority": 1
                },
                {
                    "id": "REQ-002",
                    "description": "The system must provide a responsive UI for all device sizes",
                    "category": "Non-Functional",
                    "priority": 2
                }
            ],
            "technical_constraints": [
                "Must be scalable to handle up to 10,000 users",
                "Must have 99.9% uptime"
            ]
        }
    
    @patch('agents.tech_stack_advisor_react.create_json_chat_agent')
    @patch('agents.tech_stack_advisor_react.AgentExecutor')
    @patch('agents.tech_stack_advisor_react.get_agent_temperature')
    def test_agent_initialization(self, mock_get_temp, mock_executor, mock_create_agent):
        """Test that the agent initializes with the proper tools."""
        # Set up mocks
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance
        mock_get_temp.return_value = 0.2
        
        # Create agent
        agent = TechStackAdvisorReActAgent(self.mock_llm, self.mock_memory)
        
        # Verify tools were initialized properly
        self.assertTrue(len(agent.tools) > 0)
        
        # Verify tool names
        tool_names = [tool.name for tool in agent.tools]
        self.assertIn("evaluate_all_technologies", tool_names)
        self.assertIn("synthesize_tech_stack", tool_names)
        
    @patch('agents.tech_stack_advisor_react.create_json_chat_agent')
    @patch('agents.tech_stack_advisor_react.AgentExecutor')
    @patch('agents.tech_stack_advisor_react.get_agent_temperature')
    def test_run_with_mocks(self, mock_get_temp, mock_executor, mock_create_agent):
        """Test the agent's run method with mocked components."""
        # Set up mocks
        mock_agent = MagicMock()
        mock_create_agent.return_value = mock_agent
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance
        mock_get_temp.return_value = 0.2
        
        # Set up return value for agent execution
        mock_executor_instance.invoke.return_value = {
            "output": "I recommend using Node.js for backend, React for frontend, and PostgreSQL for database.",
            "intermediate_steps": []
        }
        
        # Create agent
        agent = TechStackAdvisorReActAgent(self.mock_llm, self.mock_memory)
        
        # Run the agent
        result = agent.run(self.brd_analysis)
        
        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn("backend", result)
        self.assertIn("frontend", result)
        self.assertIn("database", result)
        self.assertIn("recommendation_metadata", result)

if __name__ == "__main__":
    unittest.main()
