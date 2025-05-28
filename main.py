import os
import json
import shutil
import datetime

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
from tools.document_parser import DocumentParser
from tools.vector_store_manager import VectorStoreManager


def run_project_workflow():
    print("--- Starting Multi-AI Agentic System Workflow ---")

    # --- Resumption Logic Setup ---
    # First, let's find the latest existing run directory if any
    # This allows us to offer resuming a previous session.
    latest_run_folder_name = None
    output_base_dir = PROJECT_OUTPUT_DIR
    run_dirs = [d for d in os.listdir(output_base_dir) if os.path.isdir(os.path.join(output_base_dir, d)) and d.startswith("project_run_")]
    if run_dirs:
        latest_run_folder_name = sorted(run_dirs, reverse=True)[0]
        
    project_run_dir = None
    if latest_run_folder_name:
        resume_choice = input(f"Found previous run: '{latest_run_folder_name}'. Do you want to resume from it? (yes/no, default: no): ").lower().strip()
        if resume_choice == 'yes':
            project_run_dir = os.path.join(output_base_dir, latest_run_folder_name)
            print(f"Resuming workflow in: {project_run_dir}")
        else:
            print("Starting a new workflow run.")
    
    if not project_run_dir: # If not resuming, create a new one
        project_run_dir = os.path.join(PROJECT_OUTPUT_DIR, f"project_run_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}")
        os.makedirs(project_run_dir, exist_ok=True)
        print(f"All generated code and tests for this run will be placed in: {project_run_dir}")

    # 1. Initialize Shared Project Memory (SQLite per run)
    memory = SharedProjectMemory(run_dir=project_run_dir)
    print(f"Shared Project Memory initialized from {memory.db_path}.")

    # 2. Get LLM Model
    llm = get_gemini_model()
    print(f"Gemini model '{llm.model_name}' loaded.")

    # 3. Initialize the DocumentParser tool
    document_parser = DocumentParser()
    print("DocumentParser initialized for multi-format BRD input.")

    # 4. Initialize Vector Store Manager for RAG
    # Pass clean_existing=False when loading to allow resuming and adding more chunks
    vector_store_manager = VectorStoreManager(run_dir=project_run_dir)
    # The vector store will attempt to load existing data if it's there
    print("Vector Store Manager initialized for RAG.")


    # --- Phase 1 Steps (Sequential Execution) ---
    # Use memory.get() to check if a step was already completed and skip it.

    # Step 1: Taking BRD as Input
    print("\n--- Step 1: BRD Analysis ---")
    if memory.get("brd_analysis"):
        brd_analysis_output = memory.get("brd_analysis")
        print("BRD Analysis already completed. Resuming.")
        # Re-initialize RAG if needed, but it should load existing upon VectorStoreManager init
        # No need to add again, as it's part of init if exists.
    else:
        brd_file_path = input(
            f"Please enter the path to your BRD file "
            f"(e.g., {os.path.join(PROJECT_BRDS_DIR, 'simple_crud_api.md')}, a local .pdf/.docx, or a GCS path like gs://{os.getenv('GCP_BUCKET_NAME', 'your-bucket')}/brds/my_brd.pdf): "
        ).strip()
        
        if not brd_file_path:
            print("No BRD file path provided. Exiting.")
            return

        local_brd_path = ""
        try:
            if brd_file_path.startswith("gs://"):
                print(f"Downloading BRD from GCS: {brd_file_path}")
                client = storage.Client()
                bucket_name = brd_file_path.split("/")[2]
                blob_name = "/".join(brd_file_path.split("/")[3:])
                bucket = client.bucket(bucket_name)
                blob = bucket.blob(blob_name)
                
                temp_brd_dir = os.path.join(project_run_dir, "temp_brd_input") # Use run_dir for temp
                os.makedirs(temp_brd_dir, exist_ok=True)
                local_brd_path = os.path.join(temp_brd_dir, os.path.basename(brd_file_path))
                blob.download_to_filename(local_brd_path)
                print(f"Downloaded BRD to {local_brd_path}")
            else:
                local_brd_path = brd_file_path
            
            raw_brd = document_parser.parse_document(local_brd_path)
            memory.set("raw_brd", raw_brd) 
            memory.set("brd_file_path_used", brd_file_path)
            print(f"BRD loaded from {brd_file_path} (Parsed text length: {len(raw_brd)} chars).")

            brd_analyst_agent = BRDAnalystAgent(llm=llm, memory=memory)
            brd_analysis_output = brd_analyst_agent.run(raw_brd)
            memory.set("brd_analysis", brd_analysis_output)
            print("BRD Analysis Complete. Output stored in memory.")
            print(f"Summary: {brd_analysis_output.get('summary', 'N/A')}")
            
            vector_store_manager.initialize_vector_store([json.dumps(brd_analysis_output, indent=2)], clean_existing=True) # Clean and initialize for BRD
            print("BRD Analysis added to RAG store.")

        except FileNotFoundError as e:
            print(f"Error: {e}")
            return 
        except ValueError as e:
            print(f"Error parsing BRD: {e}")
            return
        except Exception as e:
            print(f"An unexpected error occurred during BRD Analysis: {e}")
            return 
        finally:
            if brd_file_path.startswith("gs://") and os.path.exists(temp_brd_dir):
                shutil.rmtree(temp_brd_dir)
                print(f"Cleaned up temporary BRD directory: {temp_brd_dir}")

    # Step 2: Deciding Tech Stack
    print("\n--- Step 2: Deciding Tech Stack ---")
    if memory.get("tech_stack_recommendation"):
        tech_stack_output = memory.get("tech_stack_recommendation")
        print("Tech Stack decision already completed. Resuming.")
    else:
        try:
            tech_stack_advisor_agent = TechStackAdvisorAgent(llm=llm, memory=memory)
            tech_stack_output = tech_stack_advisor_agent.run(memory.get("brd_analysis"))
            memory.set("tech_stack_recommendation", tech_stack_output)
            print("Tech Stack decision complete. Output stored in memory.")
            print(f"Backend: {tech_stack_output.get('backend', {}).get('name', 'N/A')}")
            print(f"Database: {tech_stack_output.get('database', {}).get('name', 'N/A')}")
            print(f"Overall Rationale: {tech_stack_output.get('overall_rationale', 'N/A')[:100]}...")
            
            vector_store_manager.add_documents_to_store([json.dumps(tech_stack_output, indent=2)])
            print("Tech Stack recommendation added to RAG store.")
        except Exception as e:
            print(f"Error during Tech Stack decision: {e}")
            return

    # Step 3: System Designing
    print("\n--- Step 3: System Designing ---")
    if memory.get("system_design"):
        system_design_output = memory.get("system_design")
        print("System Design already completed. Resuming.")
    else:
        try:
            system_designer_agent = SystemDesignerAgent(llm=llm, memory=memory)
            system_design_output = system_designer_agent.run(
                memory.get("brd_analysis"), memory.get("tech_stack_recommendation")
            )
            memory.set("system_design", system_design_output)
            print("System Design complete. Output stored in memory.")
            print(f"Architecture: {system_design_output.get('architecture_overview', 'N/A')}")
            print(f"Main Modules: {', '.join(system_design_output.get('main_modules', ['N/A']))}")
            
            vector_store_manager.add_documents_to_store([json.dumps(system_design_output, indent=2)])
            print("System Design added to RAG store.")
        except Exception as e:
            print(f"Error during System Designing: {e}")
            return

    # --- Phase 2: Introduce Basic Testing & Quality (Iterative Loop) ---
    
    code_execution_tool = CodeExecutionTool(output_dir=project_run_dir) 

    max_code_gen_retries = 3 # Re-set to 3 as requested
    current_code_gen_retry = memory.get("current_code_gen_retry", 0) # Load last retry count
    code_is_acceptable = memory.get("code_is_acceptable", False) # Load last status
    
    # If resuming, check if previous run was already successful.
    if code_is_acceptable and current_code_gen_retry > 0:
        print(f"\n--- Resuming from a previously successful iteration (Iteration {current_code_gen_retry}). ---")
    else:
        # If not resuming a success, make sure feedback is loaded for next retry
        memory.set("code_quality_feedback", memory.get("code_quality_feedback", ""))
        memory.set("test_results_feedback", memory.get("test_results_feedback", ""))
        
        # If starting a new loop, or resuming a failed one, ensure current_code_gen_retry is incremented
        # This prevents infinite loops if it loads a state where it failed but current_code_gen_retry wasn't incremented
        if not code_is_acceptable: # Only increment if previous state wasn't successful
             current_code_gen_retry += 1
             print(f"\n--- Starting Code Generation & Validation Iteration {current_code_gen_retry}/{max_code_gen_retries} ---")
        else: # If it was acceptable, we just print the success and skip loop
             print("\n--- Phase 2 Complete: Code Generated & Validated Successfully! ---")
             return # Exit if already successful

    rag_retriever = vector_store_manager.get_retriever(k=7) # Get the RAG retriever


    while not code_is_acceptable and current_code_gen_retry <= max_code_gen_retries: # Change to <= for correct count
        print(f"\n--- Code Generation & Validation Iteration {current_code_gen_retry}/{max_code_gen_retries} ---")
        
        combined_feedback = (memory.get("code_quality_feedback", "") + "\n" + 
                             memory.get("test_results_feedback", "")).strip()
        if combined_feedback:
            print(f"  Attempting to fix issues based on feedback:\n{combined_feedback}")

        # Step 4: Writing Whole Code (CodeGenerationAgent)
        # Only run if not already done in this iteration
        if not memory.get(f"iteration_{current_code_gen_retry}_code_gen_complete"):
            print("\n--- Step 4: Writing Whole Code ---")
            try:
                code_generation_agent = CodeGenerationAgent(
                    llm=llm, 
                    memory=memory, 
                    output_dir=project_run_dir, 
                    code_execution_tool=code_execution_tool,
                    rag_retriever=rag_retriever
                )
                generated_code_files = code_generation_agent.run(
                    brd_analysis=memory.get("brd_analysis"), 
                    tech_stack_recommendation=memory.get("tech_stack_recommendation"),
                    system_design=memory.get("system_design"),
                    error_feedback=combined_feedback 
                )
                if not generated_code_files:
                    print("Critical: Code generation failed to produce any files. Cannot proceed with validation.")
                    break 
                memory.set("generated_code_files", generated_code_files)
                memory.set("generated_app_root_path", project_run_dir) 
                memory.set(f"iteration_{current_code_gen_retry}_code_gen_complete", True) # Mark step as complete
                print("Code Generation complete. Files written to output directory.")
                
                code_snippets_for_rag = [f"--- File: {path} ---\n```\n{content}\n```" for path, content in generated_code_files.items()]
                vector_store_manager.add_documents_to_store(code_snippets_for_rag)
                print(f"Added {len(code_snippets_for_rag)} generated code snippets to RAG store.")

                memory.set("code_quality_feedback", "") # Clear feedback for new iteration
                memory.set("test_results_feedback", "")

            except Exception as e:
                print(f"Error during Code Generation (Iteration {current_code_gen_retry}): {e}")
                memory.set("code_quality_feedback", f"Code generation failed with error: {e}. Attempting regeneration in next iteration.")
                memory.set(f"iteration_{current_code_gen_retry}_code_gen_complete", False) # Mark as failed
                current_code_gen_retry += 1 # Increment for next retry
                continue # Go to next iteration

        # Get the actual generated app root path for tools
        current_app_root = memory.get("generated_app_root_path", project_run_dir)

        # Install dependencies
        if not memory.get(f"iteration_{current_code_gen_retry}_deps_installed"):
            print(f"\n--- Installing Dependencies for Generated Code at {current_app_root} ---")
            success, install_output = code_execution_tool.install_dependencies(
                current_app_root, memory.get("tech_stack_recommendation")
            )
            if not success:
                print(f"Dependency installation failed: {install_output}")
                memory.set("code_quality_feedback", f"Dependency installation failed: {install_output}. Generated code cannot run.")
                memory.set(f"iteration_{current_code_gen_retry}_deps_installed", False)
                current_code_gen_retry += 1
                continue 
            else:
                print("Dependencies installed successfully.")
                memory.set(f"iteration_{current_code_gen_retry}_deps_installed", True)

        # Step 6: Validating Code Sanity / Quality Check (CodeQualityAgent)
        if not memory.get(f"iteration_{current_code_gen_retry}_code_quality_complete"):
            print("\n--- Step 6: Validating Code Sanity / Quality Check ---")
            try:
                code_quality_agent = CodeQualityAgent(llm=llm, memory=memory, code_execution_tool=code_execution_tool)
                quality_report = code_quality_agent.run(
                    current_app_root,
                    memory.get("tech_stack_recommendation")
                )
                memory.set("code_quality_report", quality_report)
                memory.set(f"iteration_{current_code_gen_retry}_code_quality_complete", True) # Mark step as complete
                print("Code Quality Check complete. Report stored in memory.")
                
                vector_store_manager.add_documents_to_store([f"--- Code Quality Report (Iteration {current_code_gen_retry}) ---\n{json.dumps(quality_report, indent=2)}"])
                print("Code Quality Report added to RAG store.")

                if quality_report.get("has_critical_issues", False):
                    print("Critical code quality issues detected. Requesting code regeneration.")
                    memory.set("code_quality_feedback", quality_report.get("summary", "Critical quality issues detected."))
                    current_code_gen_retry += 1 # Increment for next retry
                    continue
                else:
                    print("Code quality is acceptable for now.")

            except Exception as e:
                print(f"Error during Code Quality Check (Iteration {current_code_gen_retry}): {e}")
                memory.set("code_quality_feedback", f"Code quality check failed with error: {e}. Please investigate and attempt regeneration.")
                memory.set(f"iteration_{current_code_gen_retry}_code_quality_complete", False)
                current_code_gen_retry += 1
                continue

        # Step 5: Writing Test Cases (TestCaseGeneratorAgent)
        if not memory.get(f"iteration_{current_code_gen_retry}_test_gen_complete"):
            print("\n--- Step 5: Writing Test Cases ---")
            try:
                test_case_generator_agent = TestCaseGeneratorAgent(
                    llm=llm, 
                    memory=memory, 
                    output_dir=current_app_root,
                    rag_retriever=rag_retriever
                )
                generated_test_files = test_case_generator_agent.run(
                    brd_analysis=memory.get("brd_analysis"),
                    system_design=memory.get("system_design"),
                    generated_code_files=memory.get("generated_code_files"),
                    tech_stack=memory.get("tech_stack_recommendation")
                )
                memory.set("generated_test_files", generated_test_files)
                memory.set(f"iteration_{current_code_gen_retry}_test_gen_complete", True) # Mark step as complete
                if not generated_test_files:
                    print("Warning: Test case generation failed to produce any test files. Cannot validate.")
                    memory.set("test_results_feedback", "Test case generation failed. Generated no test files.")
                    current_code_gen_retry += 1 # Increment for next retry
                    continue
                print("Test Case Generation complete. Test files written to output directory.")
                
                test_snippets_for_rag = [f"--- Test File: {path} ---\n```\n{content}\n```" for path, content in generated_test_files.items()]
                vector_store_manager.add_documents_to_store(test_snippets_for_rag)
                print(f"Added {len(test_snippets_for_rag)} generated test snippets to RAG store.")

            except Exception as e:
                print(f"Error during Test Case Generation (Iteration {current_code_gen_retry}): {e}")
                memory.set("test_results_feedback", f"Test case generation failed with error: {e}. Cannot validate code.")
                memory.set(f"iteration_{current_code_gen_retry}_test_gen_complete", False)
                current_code_gen_retry += 1
                continue

        # Step 7: Validating Test Cases (TestValidationAgent)
        if not memory.get(f"iteration_{current_code_gen_retry}_test_validation_complete"):
            print("\n--- Step 7: Validating Test Cases ---")
            try:
                test_validation_agent = TestValidationAgent(llm=llm, memory=memory, code_execution_tool=code_execution_tool)
                test_results = test_validation_agent.run(current_app_root)
                memory.set("test_results_report", test_results)
                memory.set(f"iteration_{current_code_gen_retry}_test_validation_complete", True) # Mark step as complete
                print("Test Validation complete. Report stored in memory.")
                
                vector_store_manager.add_documents_to_store([f"--- Test Results Report (Iteration {current_code_gen_retry}) ---\n{json.dumps(test_results, indent=2)}"])
                print("Test Results Report added to RAG store.")

                min_coverage_percent = 50 
                actual_coverage = test_results.get("coverage_percentage", 0)
                if isinstance(actual_coverage, str) and actual_coverage.startswith("N/A"):
                    actual_coverage = 0

                if test_results.get("all_tests_passed", False) and actual_coverage >= min_coverage_percent:
                    print(f"All tests passed and {actual_coverage}% coverage (>= {min_coverage_percent}%). Code is considered acceptable.")
                    code_is_acceptable = True 
                else:
                    print(f"Tests failed or coverage ({actual_coverage}%) too low. Requesting code regeneration.")
                    feedback = test_results.get("summary", "Tests failed or coverage too low.")
                    memory.set("test_results_feedback", feedback)
                    current_code_gen_retry += 1 # Increment for next retry
                    continue # Go to next iteration

            except Exception as e:
                print(f"Error during Test Validation (Iteration {current_code_gen_retry}): {e}")
                memory.set("test_results_feedback", f"Test validation failed with error: {e}. Cannot confirm code correctness.")
                memory.set(f"iteration_{current_code_gen_retry}_test_validation_complete", False)
                current_code_gen_retry += 1
                continue

    # After the loop, save the final status of iteration and acceptability
    memory.set("current_code_gen_retry", current_code_gen_retry -1) # Store last successfully attempted iteration
    memory.set("code_is_acceptable", code_is_acceptable)

    if code_is_acceptable:
        print("\n--- Phase 2 Complete: Code Generated & Validated Successfully! ---")
    else:
        print(f"\n--- Phase 2 Ended: Failed to produce acceptable code after {max_code_gen_retries} iterations. ---")
        print("Manual intervention may be required to resolve persistent issues.")
    
    # Close memory DB connection
    memory.close() # Explicitly close DB connection

if __name__ == "__main__":
    run_project_workflow()