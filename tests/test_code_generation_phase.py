
import asyncio
import os
import shutil
import unittest
from unittest.mock import MagicMock

# Add project root to path to allow absolute imports
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.brd_analyst_react import BRDAnalystReActAgent
from agents.code_generation.backend_orchestrator import BackendOrchestratorAgent
from agents.code_generation.specialized.core_backend_agent import CoreBackendAgent
from agents.code_generation.specialized.devops_infrastructure_agent import DevOpsInfrastructureAgent
from agents.code_generation.specialized.documentation_agent import DocumentationAgent
from agents.code_generation.specialized.monitoring_observability_agent import MonitoringObservabilityAgent
from agents.code_generation.specialized.security_compliance_agent import SecurityComplianceAgent
from agents.code_generation.specialized.testing_qa_agent import TestingQAAgent
from agents.code_quality_agent import CodeQualityAgent
from agents.planning.plan_compiler_simplified import PlanCompilerSimplifiedAgent
from agents.system_designer_simplified import SystemDesignerSimplifiedAgent
from agents.tech_stack_advisor_simplified import TechStackAdvisorSimplifiedAgent
from tools.code_execution_tool import CodeExecutionTool
from enhanced_memory_manager import EnhancedSharedProjectMemory
from models.data_contracts import WorkItem
from config import initialize_system_config, AdvancedWorkflowConfig
from langchain_core.messages import AIMessage

class TestCodeGenerationPhase(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Set up the environment for the entire test class."""
        # Initialize system configuration
        config = AdvancedWorkflowConfig()
        initialize_system_config(config)

        # Create a mock LLM
        cls.mock_llm = MagicMock()
        
        # Create a real memory instance
        cls.memory = EnhancedSharedProjectMemory("test_code_generation_phase")
        
        # Define the output directory
        cls.output_dir = "multi-ai-dev-system/test_output/code_generation_test"

        # Create a code execution tool
        cls.code_execution_tool = CodeExecutionTool(output_dir=cls.output_dir)
        
        # Clean up any previous test runs
        if os.path.exists(cls.output_dir):
            shutil.rmtree(cls.output_dir)
        os.makedirs(cls.output_dir)

    def test_code_generation_phase(self):
        """
        Runs the code generation phase in isolation to test the agents.
        """
        # 1. Initialize Agents
        brd_analyst = BRDAnalystReActAgent(llm=self.mock_llm, memory=self.memory, temperature=0.1, rag_retriever=None)
        tech_stack_advisor = TechStackAdvisorSimplifiedAgent(llm=self.mock_llm, memory=self.memory, temperature=0.1, rag_retriever=None)
        system_designer = SystemDesignerSimplifiedAgent(llm=self.mock_llm, memory=self.memory, temperature=0.1, rag_retriever=None)
        plan_compiler = PlanCompilerSimplifiedAgent(llm=self.mock_llm, memory=self.memory, temperature=0.1, rag_retriever=None)
        backend_orchestrator = BackendOrchestratorAgent(llm=self.mock_llm, memory=self.memory, temperature=0.1, output_dir=self.output_dir, code_execution_tool=self.code_execution_tool, rag_retriever=None)
        
        # 2. Mock LLM Responses
        # Mock the response for the BRD Analyst
        self.mock_llm.invoke.side_effect = [
            # BRD Analyst Mock Response
            AIMessage(content='{"project_name": "Hello World", "project_summary": "A simple hello world application.", "requirements": [{"id": "REQ-001", "description": "Create a hello world application", "category": "Functional", "priority": 1}]}'),
            # Tech Stack Advisor Mock Response
            AIMessage(content='{"frontend_options": [{"name": "React"}], "backend_options": [{"name": "Python"}], "database_options": [{"name": "SQLite"}], "architecture_options": [], "tool_options": [], "risks": [], "synthesis": {"backend": {}, "frontend": {}, "database": {}, "architecture_pattern": "Monolith", "deployment_environment": {}, "key_libraries_tools": []}}'),
            # System Designer Mock Response
            AIMessage(content='{"architecture_overview": "Monolith", "database_schema": {"tables":[]}, "api_endpoints": [{"path":"/hello"}]}'),
            # Plan Compiler Mock Response
            AIMessage(content='{"summary": "Plan for hello world", "work_items": [{"id": "TASK-001", "description": "Create main.py", "dependencies": [], "estimated_time": "1h", "acceptance_criteria": [], "agent_role": "backend_developer"}]}'),
            # Backend Orchestrator Mock Response
            AIMessage(content='{"generated_files": [{"file_path": "main.py", "content": "print(\'hello world\')"}], "summary": "Generated main.py"}')
        ]
        
        # 3. Define a Sample BRD
        brd_content = "Create a simple hello world application."
        
        # 4. Run the Code Generation Phase
        # Step 1: BRD Analysis
        brd_analysis_result = brd_analyst.run(brd_content)
        
        # Step 2: Tech Stack Recommendation
        tech_stack_result = tech_stack_advisor.run(brd_content, brd_analysis_result)
        
        # Step 3: System Design
        system_design_result = system_designer.run(brd_analysis_result, tech_stack_result)
        
        # Step 4: Plan Compilation
        plan_result = plan_compiler.run(system_design_result)
        
        # Step 5: Code Generation
        work_item = WorkItem(id="TASK-001", description="Create main.py", dependencies=[], agent_role="backend_developer", acceptance_criteria=["main.py is created"], estimated_time="1h")
        state = {
            "tech_stack_recommendation": tech_stack_result,
            "system_design": system_design_result,
            "requirements_analysis": brd_analysis_result
        }
        code_generation_result = backend_orchestrator.run(work_item, state)
        
        # 5. Assertions
        self.assertIn("generated_files", code_generation_result)
        self.assertGreater(len(code_generation_result["generated_files"]), 0)
        
        # Check if the file was created
        generated_file_path = os.path.join(self.output_dir, code_generation_result["generated_files"][0]["file_path"])
        self.assertTrue(os.path.exists(generated_file_path))
        
        with open(generated_file_path, 'r') as f:
            content = f.read()
            self.assertEqual(content, "print('hello world')")
            
        print(f"\\n✅ Code generation phase test completed successfully.")
        print(f"Generated files can be found in: {self.output_dir}")

if __name__ == "__main__":
    unittest.main() 