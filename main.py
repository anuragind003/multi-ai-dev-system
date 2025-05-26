import os
import json # Added for better printing of intermediate outputs
import shutil # For potential cleanup of output directory
import datetime # For potential timestamped output directories

from shared_memory import SharedProjectMemory
from config import get_gemini_model, PROJECT_BRDS_DIR, PROJECT_OUTPUT_DIR
from agents.brd_analyst import BRDAnalystAgent
from agents.tech_stack_advisor import TechStackAdvisorAgent
from agents.system_designer import SystemDesignerAgent
from agents.code_generation import CodeGenerationAgent
from agents.test_case_generator import TestCaseGeneratorAgent
from agents.code_quality_agent import CodeQualityAgent
from agents.test_validation_agent import TestValidationAgent
from tools.code_execution_tool import CodeExecutionTool


def load_brd_from_file(file_path):
    """Loads BRD content from a specified file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"BRD file not found: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def run_project_workflow():
    print("--- Starting Multi-AI Agentic System Workflow ---")

    memory = SharedProjectMemory()
    print("Shared Project Memory initialized.")

    llm = get_gemini_model()
    print(f"Gemini model '{llm.model_name}' loaded.")

    # --- Phase 1 Steps (Sequential Execution) ---

    # Step 1: Taking BRD as Input
    brd_file_path = os.path.join(PROJECT_BRDS_DIR, "simple_crud_api.md")
    try:
        raw_brd = load_brd_from_file(brd_file_path)
        memory.set("raw_brd", raw_brd)
        print(f"\n--- Step 1: BRD Analysis (Input: {brd_file_path}) ---")
        brd_analyst_agent = BRDAnalystAgent(llm=llm, memory=memory)
        brd_analysis_output = brd_analyst_agent.run(raw_brd)
        memory.set("brd_analysis", brd_analysis_output)
        print("BRD Analysis Complete. Output stored in memory.")
        print(f"Summary: {brd_analysis_output.get('summary', 'N/A')}")
        # print(json.dumps(brd_analysis_output, indent=2)) # Uncomment to see full output
    except Exception as e:
        print(f"Error during BRD Analysis: {e}")
        return # Stop workflow on critical error

    # Step 2: Deciding Tech Stack
    print("\n--- Step 2: Deciding Tech Stack ---")
    try:
        tech_stack_advisor_agent = TechStackAdvisorAgent(llm=llm, memory=memory)
        tech_stack_output = tech_stack_advisor_agent.run(memory.get("brd_analysis"))
        memory.set("tech_stack_recommendation", tech_stack_output)
        print("Tech Stack decision complete. Output stored in memory.")
        print(f"Backend: {tech_stack_output.get('backend', {}).get('name', 'N/A')}")
        print(f"Database: {tech_stack_output.get('database', {}).get('name', 'N/A')}")
        print(f"Overall Rationale: {tech_stack_output.get('overall_rationale', 'N/A')[:100]}...")
        # print(json.dumps(tech_stack_output, indent=2)) # Uncomment to see full output
    except Exception as e:
        print(f"Error during Tech Stack decision: {e}")
        return

    # Step 3: System Designing
    print("\n--- Step 3: System Designing ---")
    try:
        system_designer_agent = SystemDesignerAgent(llm=llm, memory=memory)
        system_design_output = system_designer_agent.run(
            memory.get("brd_analysis"), memory.get("tech_stack_recommendation")
        )
        memory.set("system_design", system_design_output)
        print("System Design complete. Output stored in memory.")
        print(f"Architecture: {system_design_output.get('architecture_overview', 'N/A')}")
        print(f"Main Modules: {', '.join(system_design_output.get('main_modules', ['N/A']))}")
        # print(json.dumps(system_design_output, indent=2)) # Uncomment to see full output
    except Exception as e:
        print(f"Error during System Designing: {e}")
        return

    # --- Phase 2: Introduce Basic Testing & Quality (Iterative Loop) ---

    # Dynamic project root based on initial CodeGenAgent output or a fixed name
    # For a simple CRUD API, LLM often suggests `app/` structure.
    # Let's clean the output directory for each full run of the workflow for simplicity in MVP.
    # In a real system, you'd version outputs (e.g., output/run_YYYYMMDD_HHMMSS/)
    project_run_dir = os.path.join(PROJECT_OUTPUT_DIR, f"project_run_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}")
    os.makedirs(project_run_dir, exist_ok=True)
    print(f"\nAll generated code and tests will be placed in: {project_run_dir}")
    
    code_execution_tool = CodeExecutionTool(output_dir=project_run_dir)

    max_code_gen_retries = 3 # Max attempts for the code-test-fix loop
    current_code_gen_retry = 0
    code_is_acceptable = False
    
    # Initialize feedback in memory
    memory.set("code_quality_feedback", "")
    memory.set("test_results_feedback", "")

    while not code_is_acceptable and current_code_gen_retry < max_code_gen_retries:
        current_code_gen_retry += 1
        print(f"\n--- Code Generation & Validation Iteration {current_code_gen_retry}/{max_code_gen_retries} ---")

        # Combine feedback from previous iteration if any
        combined_feedback = (memory.get("code_quality_feedback", "") + "\n" + 
                             memory.get("test_results_feedback", "")).strip()

        # Step 4: Writing Whole Code (CodeGenerationAgent)
        print("\n--- Step 4: Writing Whole Code ---")
        try:
            code_generation_agent = CodeGenerationAgent(llm=llm, memory=memory, output_dir=project_run_dir, code_execution_tool=code_execution_tool)
            generated_code_files = code_generation_agent.run(
                memory.get("brd_analysis"),
                memory.get("tech_stack_recommendation"),
                memory.get("system_design"),
                error_feedback=combined_feedback # Pass combined feedback to CodeGenAgent
            )
            # Ensure generated_code_files is not empty or None for subsequent steps
            if not generated_code_files:
                print("Critical: Code generation failed to produce any files. Cannot proceed with validation.")
                break
            memory.set("generated_code_files", generated_code_files)
            # Update the specific generated app root for subsequent agents if CodeGenAgent returns it
            # For our current simple case, it's just project_run_dir
            memory.set("generated_app_root_path", project_run_dir) 
            print("Code Generation complete. Files written to output directory.")
            
            # Clear feedback for new iteration (will be set again by quality/test agents)
            memory.set("code_quality_feedback", "")
            memory.set("test_results_feedback", "")

        except Exception as e:
            print(f"Error during Code Generation (Iteration {current_code_gen_retry}): {e}")
            memory.set("code_quality_feedback", f"Code generation failed with error: {e}. Attempting regeneration.")
            continue # Try next iteration

        # Get the actual generated app root path for tools
        current_app_root = memory.get("generated_app_root_path", project_run_dir)

        # First, install dependencies for the generated code
        print(f"\n--- Installing Dependencies for Generated Code at {current_app_root} ---")
        success, install_output = code_execution_tool.install_dependencies(
            current_app_root, memory.get("tech_stack_recommendation")
        )
        if not success:
            print(f"Dependency installation failed: {install_output}")
            memory.set("code_quality_feedback", f"Dependency installation failed: {install_output}. Generated code cannot run.")
            continue # Go to next iteration to allow CodeGenAgent to fix requirements.txt etc.
        else:
            print("Dependencies installed successfully.")

        # Step 6: Validating Code Sanity / Quality Check (CodeQualityAgent)
        print("\n--- Step 6: Validating Code Sanity / Quality Check ---")
        try:
            code_quality_agent = CodeQualityAgent(llm=llm, memory=memory, code_execution_tool=code_execution_tool)
            quality_report = code_quality_agent.run(
                current_app_root, # Pass the path to the generated code
                memory.get("tech_stack_recommendation")
            )
            memory.set("code_quality_report", quality_report)
            print("Code Quality Check complete. Report stored in memory.")
            
            if quality_report.get("has_critical_issues", False):
                print("Critical code quality issues detected. Requesting code regeneration.")
                memory.set("code_quality_feedback", quality_report.get("summary", "Critical quality issues detected."))
                continue # Go to next iteration
            else:
                print("Code quality is acceptable for now.")

        except Exception as e:
            print(f"Error during Code Quality Check (Iteration {current_code_gen_retry}): {e}")
            memory.set("code_quality_feedback", f"Code quality check failed with error: {e}. Please investigate.")
            continue

        # Step 5: Writing Test Cases (TestCaseGeneratorAgent) - moved AFTER initial quality check for better tests
        print("\n--- Step 5: Writing Test Cases ---")
        try:
            test_case_generator_agent = TestCaseGeneratorAgent(llm=llm, memory=memory, output_dir=current_app_root)
            generated_test_files = test_case_generator_agent.run(
                memory.get("brd_analysis"),
                memory.get("system_design"),
                memory.get("generated_code_files"), # Pass generated code for test context
                memory.get("tech_stack_recommendation")
            )
            memory.set("generated_test_files", generated_test_files)
            if not generated_test_files:
                print("Warning: Test case generation failed to produce any test files. Cannot validate.")
                memory.set("test_results_feedback", "Test case generation failed. Generated no test files.")
                continue # Go to next iteration for CodeGenAgent to retry
            print("Test Case Generation complete. Test files written to output directory.")
        except Exception as e:
            print(f"Error during Test Case Generation (Iteration {current_code_gen_retry}): {e}")
            memory.set("test_results_feedback", f"Test case generation failed with error: {e}. Cannot validate code.")
            continue

        # Step 7: Validating Test Cases (TestValidationAgent)
        print("\n--- Step 7: Validating Test Cases ---")
        try:
            test_validation_agent = TestValidationAgent(llm=llm, memory=memory, code_execution_tool=code_execution_tool)
            test_results = test_validation_agent.run(current_app_root)
            memory.set("test_results_report", test_results)
            print("Test Validation complete. Report stored in memory.")
            
            # Criteria for acceptable code: All tests passed AND a minimum coverage threshold
            min_coverage_percent = 50 # Example: at least 50% coverage
            actual_coverage = test_results.get("coverage_percentage", 0)
            if isinstance(actual_coverage, str) and actual_coverage.startswith("N/A"): # Handle N/A string
                 actual_coverage = 0 # Treat N/A as 0 for threshold check

            if test_results.get("all_tests_passed", False) and actual_coverage >= min_coverage_percent:
                print(f"All tests passed and {actual_coverage}% coverage (>= {min_coverage_percent}%). Code is considered acceptable.")
                code_is_acceptable = True # Exit the loop
            else:
                print(f"Tests failed or coverage ({actual_coverage}%) too low. Requesting code regeneration.")
                feedback = test_results.get("summary", "Tests failed or coverage too low.")
                memory.set("test_results_feedback", feedback)
                continue # Go to next iteration (Code Gen to fix)

        except Exception as e:
            print(f"Error during Test Validation (Iteration {current_code_gen_retry}): {e}")
            memory.set("test_results_feedback", f"Test validation failed with error: {e}. Cannot confirm code correctness.")
            continue # Go to next iteration

    if code_is_acceptable:
        print("\n--- Phase 2 Complete: Code Generated & Validated Successfully! ---")
    else:
        print(f"\n--- Phase 2 Ended: Failed to produce acceptable code after {max_code_gen_retries} iterations. ---")
        print("Manual intervention may be required to resolve persistent issues.")
    
    print(f"Final project context saved to {PROJECT_CONTEXT_FILE}")


if __name__ == "__main__":
    run_project_workflow()