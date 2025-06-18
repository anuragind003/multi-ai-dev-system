import os
import json
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv

# Import core system components
from config import get_llm, get_system_config 
from shared_memory import SharedMemory
from monitoring import setup_logging
from agent_temperatures import AGENT_TEMPERATURES

# Import agents for testing
from agents.base_agent import BaseAgent
from agents.brd_analyst import BRDAnalystAgent
from agents.code_generation_agent import CodeGenerationAgent
from agents.test_validation_agent import TestValidationAgent

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class AgentTemperatureTester:
    """Framework for testing agent temperature binding and performance."""
    
    def __init__(self, memory: SharedMemory = None):
        """Initialize the temperature testing framework."""
        self.config = get_system_config()
        
        # Initialize memory if not provided
        self.memory = memory or SharedMemory()
        
        # Sample content for testing
        self.sample_brd = """
        Business Requirements Document
        
        Project: Customer Management System
        
        Requirements:
        1. Create a customer database with fields for name, email, phone, and address
        2. Implement CRUD operations for customer records
        3. Add search functionality by name, email or phone number
        4. Generate monthly reports of customer activity
        5. Implement user authentication with role-based access control
        """
        
        # Sample code for testing
        self.sample_code = """
        def calculate_total(items):
            total = 0
            for item in items:
                if item.get('price') and item.get('quantity'):
                    total += item['price'] * item['quantity']
            return total
        """
        
        # Store test results
        self.results = {
            "binding_verification": {},
            "temperature_comparison": {},
            "recommended_temp_validation": {}
        }
        
        logger.info("Agent Temperature Tester initialized")
    
    def get_agent_instance(self, agent_type: str) -> BaseAgent:
        """Create an instance of the specified agent type for testing."""
        # Get the base LLM with default temperature
        llm = get_llm()
        
        if agent_type == "BRDAnalyst":
            return BRDAnalystAgent(llm=llm, memory=self.memory)
        elif agent_type == "CodeGeneration":
            return CodeGenerationAgent(llm=llm, memory=self.memory)
        elif agent_type == "TestValidation":
            # Create a mock code execution tool for TestValidationAgent
            class MockCodeExecutionTool:
                def execute_tests(self, *args, **kwargs):
                    return {"status": "success", "output": "Mock test execution"}
            
            return TestValidationAgent(
                llm=llm, 
                memory=self.memory,
                code_execution_tool=MockCodeExecutionTool()
            )
        else:
            raise ValueError(f"Unsupported agent type: {agent_type}")
    
    def test_temperature_binding(self, agent: BaseAgent) -> Dict[str, Any]:
        """Test that temperature binding works correctly on the agent's LLM."""
        agent_name = agent.__class__.__name__
        logger.info(f"\n--- Testing temperature binding for {agent_name} ---")
        
        # Define temperatures to test binding with
        test_temperatures = [0.1, 0.4, 0.7]
        binding_results = []
        
        simple_prompt = "Generate a one-sentence response about software development."
        
        for temp in test_temperatures:
            try:
                # Test basic temperature binding
                llm_with_temp = agent.llm.bind(temperature=temp)
                
                # Use a simple prompt to verify output differs at different temperatures
                response = llm_with_temp.invoke(simple_prompt)
                
                # Extract content 
                content = response.content if hasattr(response, "content") else str(response)
                
                binding_results.append({
                    "temperature": temp,
                    "response": content[:100] + "..." if len(content) > 100 else content,
                    "bound_correctly": True
                })
                
                logger.info(f"Temperature {temp} binding successful")
                # Small delay to respect rate limits
                time.sleep(1.5)
                
            except Exception as e:
                logger.error(f"Error testing temperature {temp}: {str(e)}")
                binding_results.append({
                    "temperature": temp,
                    "error": str(e),
                    "bound_correctly": False
                })
        
        # Store results
        binding_result = {
            "agent": agent_name,
            "binding_tests": binding_results,
            "all_temps_bound_correctly": all(r["bound_correctly"] for r in binding_results)
        }
        
        self.results["binding_verification"][agent_name] = binding_result
        return binding_result
    
    def test_execute_llm_chain(self, agent: BaseAgent, task_input: Dict[str, Any], 
                              temperatures: List[float]) -> Dict[str, Any]:
        """Test execute_llm_chain with different temperatures."""
        agent_name = agent.__class__.__name__
        logger.info(f"\n--- Testing execute_llm_chain for {agent_name} ---")
        
        results = []
        
        # Ensure agent has a prompt template
        if not hasattr(agent, 'prompt_template') or agent.prompt_template is None:
            if isinstance(agent, BRDAnalystAgent):
                agent.prompt_template = agent.initial_assessment_template
            elif isinstance(agent, CodeGenerationAgent):
                agent.prompt_template = agent.code_generation_template
            elif isinstance(agent, TestValidationAgent):
                agent.prompt_template = agent.test_validation_template
        
        # If task_input doesn't have format_instructions and the agent has a json_parser
        if hasattr(agent, 'json_parser') and 'format_instructions' not in task_input:
            task_input['format_instructions'] = agent.json_parser.get_format_instructions()
        
        # Test with different temperatures
        for temp in temperatures:
            logger.info(f"Testing with temperature: {temp}")
            
            try:
                # Add max_output_tokens to limit response size
                additional_params = {"max_output_tokens": 800}
                
                start_time = time.time()
                result = agent.execute_llm_chain(
                    inputs=task_input,
                    task_specific_temp=temp,
                    additional_llm_params=additional_params
                )
                duration = time.time() - start_time
                
                # Store a truncated version of the result for logging
                result_summary = str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
                
                results.append({
                    "temperature": temp,
                    "success": True,
                    "duration": duration,
                    "result_summary": result_summary
                })
                
                logger.info(f"Temperature {temp} test completed in {duration:.2f}s")
                # Respect rate limits
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error with temperature {temp}: {str(e)}")
                results.append({
                    "temperature": temp,
                    "success": False,
                    "error": str(e)
                })
                time.sleep(1)
        
        comparison_result = {
            "agent": agent_name,
            "temperature_tests": results,
            "successful_temps": [r["temperature"] for r in results if r.get("success")]
        }
        
        self.results["temperature_comparison"][agent_name] = comparison_result
        return comparison_result
    
    def validate_recommended_temperatures(self) -> Dict[str, Any]:
        """Validate that agents are using their recommended temperatures."""
        logger.info("\n--- Validating recommended agent temperatures ---")
        
        validation_results = {}
        
        # Test each agent with their recommended temperature
        for agent_type, recommended_temp in AGENT_TEMPERATURES.items():
            try:
                # Skip if agent type isn't one we can test
                if agent_type not in ["BRDAnalyst", "CodeGeneration", "TestValidation"]:
                    continue
                
                agent = self.get_agent_instance(agent_type)
                agent_name = agent.__class__.__name__
                
                logger.info(f"Testing {agent_name} with recommended temperature {recommended_temp}")
                
                # Verify the default_temperature is properly set
                expected_temp = recommended_temp
                actual_temp = agent.default_temperature
                temp_match = abs(expected_temp - actual_temp) < 0.01  # Allow for minor float precision issues
                
                # Prepare appropriate input for this agent type
                if agent_type == "BRDAnalyst":
                    task_input = {"brd_excerpt": self.sample_brd}
                elif agent_type == "CodeGeneration":
                    task_input = {"requirements": "Create a function to validate email addresses", 
                                 "language": "Python"}
                else:  # TestValidation
                    task_input = {"code": self.sample_code, 
                                 "test_requirements": "Test that calculate_total works correctly"}
                
                # Add format instructions if agent has a json_parser
                if hasattr(agent, 'json_parser'):
                    task_input['format_instructions'] = agent.json_parser.get_format_instructions()
                
                # Set a prompt template if needed
                if not hasattr(agent, 'prompt_template') or agent.prompt_template is None:
                    # Set a simple prompt template for testing
                    if hasattr(agent, 'initial_assessment_template'):
                        agent.prompt_template = agent.initial_assessment_template
                    elif hasattr(agent, 'code_generation_template'):
                        agent.prompt_template = agent.code_generation_template
                    elif hasattr(agent, 'test_validation_template'):
                        agent.prompt_template = agent.test_validation_template
                
                # Test with their recommended temperature
                additional_params = {"max_output_tokens": 500}
                success = False
                error_msg = None
                
                try:
                    # Don't override with task_specific_temp - let default_temperature be used
                    result = agent.execute_llm_chain(
                        inputs=task_input,
                        additional_llm_params=additional_params
                    )
                    success = True
                except Exception as e:
                    error_msg = str(e)
                
                validation_results[agent_type] = {
                    "agent": agent_name,
                    "recommended_temp": recommended_temp,
                    "default_temp": actual_temp,
                    "temp_matches_recommended": temp_match,
                    "execution_success": success
                }
                
                if not success:
                    validation_results[agent_type]["error"] = error_msg
                
                # Respect rate limits
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error validating {agent_type}: {str(e)}")
                validation_results[agent_type] = {
                    "agent": agent_type,
                    "error": str(e),
                    "execution_success": False
                }
        
        self.results["recommended_temp_validation"] = validation_results
        return validation_results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all temperature tests and generate a comprehensive report."""
        logger.info("\n=== Starting comprehensive agent temperature testing ===")
        
        agents_to_test = ["BRDAnalyst", "CodeGeneration", "TestValidation"]
        
        # Test temperature binding for each agent
        for agent_type in agents_to_test:
            try:
                agent = self.get_agent_instance(agent_type)
                self.test_temperature_binding(agent)
                # Small delay between tests
                time.sleep(1) 
            except Exception as e:
                logger.error(f"Error testing binding for {agent_type}: {str(e)}")
        
        # Test execute_llm_chain with different temperatures
        test_temperatures = [0.1, 0.3, 0.7]
        for agent_type in agents_to_test:
            try:
                agent = self.get_agent_instance(agent_type)
                
                # Prepare appropriate input for this agent type
                if agent_type == "BRDAnalyst":
                    task_input = {"brd_excerpt": self.sample_brd}
                elif agent_type == "CodeGeneration":
                    task_input = {"requirements": "Create a function to validate email addresses", 
                                 "language": "Python"}
                else:  # TestValidation
                    task_input = {"code": self.sample_code, 
                                 "test_requirements": "Test that calculate_total works correctly"}
                
                self.test_execute_llm_chain(agent, task_input, test_temperatures)
                # Longer delay between agent tests
                time.sleep(3)
            except Exception as e:
                logger.error(f"Error testing execute_llm_chain for {agent_type}: {str(e)}")
        
        # Validate recommended temperatures
        self.validate_recommended_temperatures()
        
        # Generate summary
        summary = self._generate_summary()
        
        logger.info("\n=== Agent temperature testing completed ===")
        logger.info(f"Summary: {summary}")
        
        # Return all results
        return {
            "results": self.results,
            "summary": summary
        }
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate a summary of test results."""
        summary = {
            "binding_tests_passed": 0,
            "binding_tests_total": 0,
            "llm_chain_tests_passed": 0,
            "llm_chain_tests_total": 0,
            "recommended_temp_tests_passed": 0,
            "recommended_temp_tests_total": 0,
            "observations": []
        }
        
        # Count binding tests
        for agent, result in self.results["binding_verification"].items():
            tests = result.get("binding_tests", [])
            summary["binding_tests_total"] += len(tests)
            summary["binding_tests_passed"] += sum(1 for t in tests if t.get("bound_correctly"))
            
        # Count llm chain tests
        for agent, result in self.results["temperature_comparison"].items():
            tests = result.get("temperature_tests", [])
            summary["llm_chain_tests_total"] += len(tests)
            summary["llm_chain_tests_passed"] += sum(1 for t in tests if t.get("success"))
        
        # Count recommended temp validation tests
        for agent, result in self.results["recommended_temp_validation"].items():
            summary["recommended_temp_tests_total"] += 1
            if result.get("temp_matches_recommended") and result.get("execution_success"):
                summary["recommended_temp_tests_passed"] += 1
        
        # Add observations
        if summary["binding_tests_passed"] < summary["binding_tests_total"]:
            summary["observations"].append("Some temperature binding tests failed. Check detailed results.")
            
        if summary["llm_chain_tests_passed"] < summary["llm_chain_tests_total"]:
            summary["observations"].append("Some execute_llm_chain tests failed. This may be due to rate limits or other API issues.")
        
        if summary["recommended_temp_tests_passed"] < summary["recommended_temp_tests_total"]:
            summary["observations"].append("Some agents are not using their recommended temperature settings.")
        
        return summary

def main():
    """Run the agent temperature tests."""
    # Initialize memory
    memory = SharedMemory()
    
    # Create test runner
    tester = AgentTemperatureTester(memory=memory)
    
    # Run all tests
    results = tester.run_all_tests()
    
    # Save results to file
    results_path = os.path.join("tests", "results", "temperature_tests_results.json")
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Test results saved to {results_path}")

if __name__ == "__main__":
    main()