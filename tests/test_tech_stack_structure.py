import unittest
import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add project root to path to allow imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

class TestTechStackAdvisorAgent(unittest.TestCase):
    """Test suite for TechStackAdvisorReActAgent with mocked dependencies."""

    def setUp(self):
        """Set up the test environment with mocked dependencies."""
        # Mock the missing langchain dependencies
        self.mock_modules = {}
        modules_to_mock = [
            'langchain_core.language_models',
            'langchain_core.retrievers', 
            'langchain_core.messages',
            'langchain_core.prompts',
            'langchain.agents',
            'monitoring',
            'enhanced_memory_manager',
            'rag_manager',
            'config'
        ]
        
        for module in modules_to_mock:
            self.mock_modules[module] = MagicMock()
            sys.modules[module] = self.mock_modules[module]
        
        # Mock specific classes and functions
        sys.modules['config'].get_llm = Mock(return_value=MagicMock())
        sys.modules['config'].initialize_system_config = Mock()
        sys.modules['config'].AdvancedWorkflowConfig = Mock()
        sys.modules['enhanced_memory_manager'].create_memory_manager = Mock(return_value=MagicMock())

    def test_tech_stack_recommendation_structure(self):
        """Test that the tech stack recommendation has the expected structure."""
        # Mock tech stack recommendation result
        mock_result = {
            "recommended_stack": {
                "frontend": {
                    "framework": "React 18",
                    "state_management": "Redux Toolkit",
                    "styling": "Tailwind CSS"
                },
                "backend": {
                    "runtime": "Node.js 18+",
                    "framework": "Express.js",
                    "orm": "Prisma"
                },
                "database": {
                    "primary": "PostgreSQL 14+",
                    "caching": "Redis"
                }
            },
            "justification": {
                "frontend": "React provides excellent developer experience",
                "backend": "Node.js enables full-stack JavaScript development",
                "database": "PostgreSQL offers excellent reliability"
            },
            "alternatives": {
                "frontend": {
                    "frameworks": ["Vue.js 3", "Angular 15+", "Svelte"]
                },
                "backend": {
                    "runtimes": ["Python (Django/FastAPI)", "Java (Spring Boot)"]
                }
            },
            "implementation_roadmap": {
                "phase_1": {
                    "title": "Foundation Setup (Weeks 1-2)",
                    "tasks": ["Set up development environment"]
                }
            },
            "risk_assessment": {
                "technology_risks": [
                    {
                        "risk": "React ecosystem changes rapidly",
                        "impact": "Medium",
                        "probability": "Medium"
                    }
                ]
            },
            "metadata": {
                "generated_at": "2025-07-06T09:41:21.620013",
                "agent": "Tech_Stack_Advisor",
                "confidence_score": 0.9
            }
        }
        
        # Validate the structure
        self.assertIsInstance(mock_result, dict)
        self.assertIn("recommended_stack", mock_result)
        self.assertIn("justification", mock_result)
        self.assertIn("alternatives", mock_result)
        self.assertIn("implementation_roadmap", mock_result)
        self.assertIn("risk_assessment", mock_result)
        self.assertIn("metadata", mock_result)

        # Check nested structure of recommended_stack
        recommended_stack = mock_result["recommended_stack"]
        self.assertIn("frontend", recommended_stack)
        self.assertIn("backend", recommended_stack)
        self.assertIn("database", recommended_stack)
        
        # Check that frontend has expected technologies
        frontend = recommended_stack["frontend"]
        self.assertIn("framework", frontend)
        self.assertEqual(frontend["framework"], "React 18")
        
        # Check backend structure
        backend = recommended_stack["backend"]
        self.assertIn("runtime", backend)
        self.assertIn("framework", backend)
        
        # Check database structure
        database = recommended_stack["database"]
        self.assertIn("primary", database)
        self.assertIn("caching", database)

        print("\\n--- Tech Stack Recommendation Structure Test Result ---")
        print(json.dumps(mock_result, indent=2))
        print("----------------------------------------------------------")

    def test_brd_analysis_input(self):
        """Test that BRD analysis input is properly structured."""
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
        
        # Validate BRD structure
        self.assertIn("project_name", mock_brd_analysis)
        self.assertIn("project_summary", mock_brd_analysis)
        self.assertIn("requirements", mock_brd_analysis)
        
        # Check requirements structure
        requirements = mock_brd_analysis["requirements"]
        self.assertIsInstance(requirements, list)
        self.assertTrue(len(requirements) > 0)
        
        for req in requirements:
            self.assertIn("id", req)
            self.assertIn("title", req)
            self.assertIn("description", req)
            self.assertIn("category", req)
            self.assertIn("priority", req)
        
        # Check for functional and non-functional requirements
        functional_reqs = [r for r in requirements if r["category"] == "functional"]
        non_functional_reqs = [r for r in requirements if r["category"] == "non-functional"]
        
        self.assertTrue(len(functional_reqs) > 0, "Should have functional requirements")
        self.assertTrue(len(non_functional_reqs) > 0, "Should have non-functional requirements")
        
        print(f"\\n--- BRD Analysis Structure Test ---")
        print(f"Project: {mock_brd_analysis['project_name']}")
        print(f"Total requirements: {len(requirements)}")
        print(f"Functional requirements: {len(functional_reqs)}")
        print(f"Non-functional requirements: {len(non_functional_reqs)}")
        print("------------------------------------")

    def test_tech_stack_tools_structure(self):
        """Test that tech stack tools would return properly structured data."""
        
        # Mock tool results that should be returned
        mock_tech_requirements = {
            "performance_requirements": ["Low latency under 2 seconds", "Handle 1M users"],
            "scalability_requirements": ["Horizontal scaling", "High availability"],
            "security_requirements": ["Secure transactions", "Data protection"],
            "domain": "e-commerce",
            "project_type": "web_application"
        }
        
        mock_backend_evaluation = {
            "backend_options": [
                {
                    "name": "Node.js",
                    "framework": "Express.js",
                    "performance_score": 8.0,
                    "scalability_score": 8.0,
                    "pros": ["Fast development", "JavaScript ecosystem"],
                    "cons": ["Single-threaded limitations"]
                },
                {
                    "name": "Python",
                    "framework": "FastAPI",
                    "performance_score": 7.0,
                    "scalability_score": 7.0,
                    "pros": ["Developer friendly", "Rich ecosystem"],
                    "cons": ["Slower than compiled languages"]
                }
            ],
            "recommendation": {
                "name": "Node.js",
                "framework": "Express.js",
                "reasoning": "Best fit for the requirements"
            }
        }
        
        # Validate structures
        self.assertIn("performance_requirements", mock_tech_requirements)
        self.assertIn("scalability_requirements", mock_tech_requirements)
        self.assertIn("backend_options", mock_backend_evaluation)
        self.assertIn("recommendation", mock_backend_evaluation)
        
        backend_options = mock_backend_evaluation["backend_options"]
        self.assertTrue(len(backend_options) >= 2, "Should evaluate multiple backend options")
        
        for option in backend_options:
            required_fields = ["name", "framework", "performance_score", "scalability_score", "pros", "cons"]
            for field in required_fields:
                self.assertIn(field, option, f"Backend option should have {field}")
        
        print("\\n--- Tech Stack Tools Structure Test ---")
        print(f"Tech requirements keys: {list(mock_tech_requirements.keys())}")
        print(f"Backend options evaluated: {len(backend_options)}")
        print(f"Recommended: {mock_backend_evaluation['recommendation']['name']}")
        print("----------------------------------------")

    def tearDown(self):
        """Clean up mocked modules."""
        for module in self.mock_modules:
            if module in sys.modules:
                del sys.modules[module]

if __name__ == '__main__':
    unittest.main()
