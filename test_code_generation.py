import json
import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# --- Imports from your project ---
from config import get_llm
from tools.code_execution_tool import CodeExecutionTool
from agents.code_generation.database_generator import DatabaseGeneratorAgent
from agents.code_generation.backend_generator import BackendGeneratorAgent
from agents.code_generation.frontend_generator import FrontendGeneratorAgent

# Create a simple mock memory class that implements required methods
class MockMemory:
    """Mock implementation of memory for testing purposes."""
    
    def __init__(self):
        self.activities = []
        self.logs = []
    
    def store_agent_activity(self, agent_name, activity_type, prompt=None, response=None, metadata=None):
        """Mock implementation of store_agent_activity."""
        self.activities.append({
            "agent_name": agent_name,
            "activity_type": activity_type,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
        return True
    
    def log_agent_action(self, agent_name, action, details=None):
        """Mock implementation of log_agent_action."""
        self.logs.append({
            "agent_name": agent_name,
            "action": action,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        return True
    
    def get_agent_activities(self, agent_name=None, limit=10):
        """Mock implementation for retrieving activities."""
        return self.activities[:limit]

def setup_logging():
    """Sets up basic logging for the test script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def load_mock_data(file_path: str) -> dict:
    """Loads a JSON file from the test_data directory."""
    full_path = Path("test_data") / file_path
    logging.info(f"Loading mock data from: {full_path}")
    with open(full_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def validate_generated_files(result, expected_file_types):
    """Validates that expected file types were generated."""
    if not result or not result.get("generated_files"):
        return False
        
    files = result["generated_files"]
    for file_type in expected_file_types:
        if not any(file for file in files if file.endswith(file_type)):
            logging.warning(f"Missing expected file type: {file_type}")
            return False
    return True

def main():
    """Main function to run the isolated code generation test."""
    setup_logging()
    
    # --- 1. Setup Environment ---
    logging.info("Setting up test environment...")
    
    # Create a dedicated output directory for this test run
    output_dir = Path("test_output") / "code_gen_run"
    output_dir.mkdir(parents=True, exist_ok=True)
    logging.info(f"Test output will be saved to: {output_dir}")

    # Initialize the LLM and mock memory
    llm = get_llm(temperature=0.1)
    mock_memory = MockMemory()  # Create our mock memory object
    
    if not llm:
        logging.error("Failed to initialize LLM. Check your API keys and config.")
        return

    # --- 2. Load Mock Data ---
    # Load the "golden" inputs that the generator agents expect
    try:
        mock_reqs = load_mock_data("mock_requirements.json")
        mock_tech = load_mock_data("mock_tech_stack.json")
        mock_design = load_mock_data("mock_system_design.json")
        # Fix this line:
        mock_plan = load_mock_data("mock_implementation.json")  # Corrected file name
    except FileNotFoundError as e:
        logging.error(f"Mock data file not found: {e}. Please create it in the 'test_data/' directory.")
        return
        
    # --- 3. Instantiate and Test Specific Generators ---
    
    # === Test 1: DatabaseGeneratorAgent ===
    try:
        logging.info("\n--- Testing DatabaseGeneratorAgent ---")
        db_agent = DatabaseGeneratorAgent(
            llm=llm, 
            memory=mock_memory,  # Use mock_memory instead of None
            temperature=0.1, 
            output_dir=str(output_dir), 
            rag_retriever=None
        )
        db_result = db_agent.run(
            requirements_analysis=mock_reqs, tech_stack=mock_tech, system_design=mock_design,
            # Pass implementation_plan if the method signature requires it
            implementation_plan=mock_plan 
        )
        logging.info("DatabaseGeneratorAgent Result:")
        print(json.dumps(db_result, indent=2))
        if db_result and db_result.get("generated_files"):
            logging.info("[SUCCESS] DatabaseGeneratorAgent produced files successfully!")
        else:
            logging.error("[FAILURE] DatabaseGeneratorAgent failed to produce files.")
    except Exception as e:
        logging.error(f"An exception occurred while testing DatabaseGeneratorAgent: {e}", exc_info=True)

    # Add this after the database generation test
    db_schema = db_result.get("database_schema", {})

    # Validate generated files for DatabaseGeneratorAgent
    db_success = validate_generated_files(
        db_result, [".sql", ".py"]
    )
    if not db_success:
        logging.error("DatabaseGeneratorAgent did not generate the expected files. Check the output above.")
        return  # Stop further testing if DB generation failed

    # === Test 2: BackendGeneratorAgent ===
    try:
        logging.info("\n--- Testing BackendGeneratorAgent ---")
        code_tool = CodeExecutionTool(output_dir=str(output_dir))
        backend_agent = BackendGeneratorAgent(
            llm=llm, 
            memory=mock_memory,  # Use mock_memory here too
            temperature=0.1, 
            output_dir=str(output_dir), 
            code_execution_tool=code_tool, 
            rag_retriever=None
        )
        # Before testing backend/frontend, create mock architecture result
        mock_architecture = {
            "project_structure": {
                "directories": [
                    {"path": "src/", "purpose": "Main source code directory"},
                    {"path": "src/models/", "purpose": "Database models"},
                    {"path": "src/routes/", "purpose": "API routes"},
                    {"path": "src/static/", "purpose": "Static assets"}
                ]
            }
        }

        # Then pass it to backend generator
        backend_result = backend_agent.run(
            requirements_analysis=mock_reqs, 
            tech_stack=mock_tech, 
            system_design=mock_design,
            implementation_plan=mock_plan,
            database_schema=db_schema,  # Pass the generated schema
            architecture_generation_result=mock_architecture  # Pass mock architecture
        )
        logging.info("BackendGeneratorAgent Result:")
        print(json.dumps(backend_result, indent=2))
        if backend_result and backend_result.get("generated_files"):
            logging.info("[SUCCESS] BackendGeneratorAgent produced files successfully!")
        else:
            logging.error("[FAILURE] BackendGeneratorAgent failed to produce files.")
    except Exception as e:
        logging.error(f"An exception occurred while testing BackendGeneratorAgent: {e}", exc_info=True)

    # === Test 3: FrontendGeneratorAgent ===
    try:
        logging.info("\n--- Testing FrontendGeneratorAgent ---")
        # The FrontendGenerator may not need the code_execution_tool, so we can pass None
        frontend_agent = FrontendGeneratorAgent(
            llm=llm, 
            memory=mock_memory,  # Use mock_memory here too
            temperature=0.1, 
            output_dir=str(output_dir), 
            code_execution_tool=None, 
            rag_retriever=None
        )
        frontend_result = frontend_agent.run(
            requirements_analysis=mock_reqs, tech_stack=mock_tech, system_design=mock_design,
            implementation_plan=mock_plan
        )
        logging.info("FrontendGeneratorAgent Result:")
        print(json.dumps(frontend_result, indent=2))
        if frontend_result and frontend_result.get("generated_files"):
            logging.info("[SUCCESS] FrontendGeneratorAgent produced files successfully!")
        else:
            logging.error("[FAILURE] FrontendGeneratorAgent failed to produce files.")
    except Exception as e:
        logging.error(f"An exception occurred while testing FrontendGeneratorAgent: {e}", exc_info=True)


if __name__ == "__main__":
    main()