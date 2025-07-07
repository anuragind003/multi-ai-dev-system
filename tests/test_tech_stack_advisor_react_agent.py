import unittest
import json
import os
import sys

# Add project root to path to allow imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from agents.tech_stack_advisor_react import TechStackAdvisorReActAgent
from config import get_llm, initialize_system_config, AdvancedWorkflowConfig
from enhanced_memory_manager import create_memory_manager

# Import the rate limiter instance to configure it for the test
try:
    from config import advanced_rate_limiter
    RATE_LIMITER_AVAILABLE = True
except ImportError:
    RATE_LIMITER_AVAILABLE = False

class TestTechStackAdvisorAgent(unittest.TestCase):

    def setUp(self):
        """Set up the test environment."""
        
        # Initialize system config FIRST, so all dependencies are available
        initialize_system_config(AdvancedWorkflowConfig())

        # Now, configure the rate limiter with the aggressive test settings
        if RATE_LIMITER_AVAILABLE:
            print("Applying aggressive rate limiting for test to avoid API quota issues...")
            if hasattr(advanced_rate_limiter, 'rate_limiter') and hasattr(advanced_rate_limiter.rate_limiter, 'config'):
                # Make the rate limiter much more conservative for the test run
                config = advanced_rate_limiter.rate_limiter.config
                config.initial_delay = 15.0  # Start with a very long 15-second delay
                config.min_delay = 10.0      # Never go below a 10-second delay
                config.max_delay = 60.0      # Maximum delay of 60 seconds
                config.backoff_factor = 2.0
            else:
                print("Warning: Rate limiter config not found, test may fail.")

        self.llm = get_llm()
        self.memory = create_memory_manager(backend_type='hybrid')
        self.agent = TechStackAdvisorReActAgent(llm=self.llm, memory=self.memory)

    def test_run_agent_with_mock_brd(self):
        """Test the agent's run method with a mock BRD analysis."""
        mock_brd_analysis = {
            "project_name": "AI-Powered E-commerce Recommendation System",
            "project_summary": "A web application that provides personalized product recommendations to users based on their browsing history and purchase patterns. The system should be scalable to handle millions of users and products.",
            "requirements": [
                {"id": "REQ-001", "title": "User Authentication", "description": "Users must be able to sign up, log in, and log out.", "category": "functional", "priority": "high"},
                {"id": "REQ-002", "title": "Product Catalog", "description": "Display products with details and images.", "category": "functional", "priority": "high"},
                {"id": "REQ-003", "title": "Recommendation Engine", "description": "Generate and display personalized recommendations.", "category": "functional", "priority": "high"},
                {"id": "REQ-004", "title": "High Performance", "description": "The system must have low latency, with page loads under 2 seconds.", "category": "non-functional", "priority": "high"},
                {"id": "REQ-005", "title": "Scalability", "description": "The system should handle 1 million active users.", "category": "non-functional", "priority": "high"},
                {"id": "REQ-006", "title": "Secure Transactions", "description": "All transactions and user data must be secure.", "category": "non-functional", "priority": "high"},
            ]
        }

        result = self.agent.run(brd_analysis=mock_brd_analysis)

        self.assertIsInstance(result, dict)
        self.assertIn("recommended_stack", result)
        self.assertIn("justification", result)
        self.assertIn("alternatives", result)
        self.assertIn("implementation_roadmap", result)
        self.assertIn("risk_assessment", result)
        self.assertIn("metadata", result)

        # Check nested structure of recommended_stack
        self.assertIn("recommended_stack", result)
        recommended_stack = result["recommended_stack"]
        self.assertIn("frontend", recommended_stack)
        self.assertIn("backend", recommended_stack)
        self.assertIn("database", recommended_stack)

        print("\\n--- Tech Stack Advisor Agent Test Result ---")
        # Pretty print the JSON result
        print(json.dumps(result, indent=2))
        print("------------------------------------------")

if __name__ == '__main__':
    unittest.main() 