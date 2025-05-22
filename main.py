import os
from shared_memory import SharedProjectMemory
from config import get_gemini_model, PROJECT_BRDS_DIR, PROJECT_CONTEXT_FILE
from agents.brd_analyst import BRDAnalystAgent
from agents.tech_stack_advisor import TechStackAdvisorAgent
from agents.system_designer import SystemDesignerAgent


def load_brd_from_file(file_path):
    """Load the BRD content from a file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"BRD file not found at {file_path}")
        
    with open(file_path, 'r') as f:
        return f.read()

def run_project_workflow():
    print("--- Starting Multi-AI Agentic System Workflow ---")

    memory = SharedProjectMemory()
    print("Shared Project Memory initialized.")

    llm = get_gemini_model()
    print(f"Gemini model '{llm.model_name}' loaded.")

    # --- Phase 1: Core BRD to Code Generation MVP ---

    # Step 1: BRD Analysis (Assumed to be working)
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
    except Exception as e:
        print(f"Error during BRD Analysis: {e}")
        return

    # Step 2: Deciding Tech Stack (Assumed to be working)
    print("\n--- Step 2: Deciding Tech Stack ---")
    try:
        tech_stack_advisor_agent = TechStackAdvisorAgent(llm=llm, memory=memory)
        tech_stack_output = tech_stack_advisor_agent.run(memory.get("brd_analysis"))
        memory.set("tech_stack_recommendation", tech_stack_output)
        print("Tech Stack decision complete. Output stored in memory.")
        print(f"Backend: {tech_stack_output.get('backend', {}).get('name', 'N/A')}")
        print(f"Database: {tech_stack_output.get('database', {}).get('name', 'N/A')}")
        print(f"Overall Rationale: {tech_stack_output.get('overall_rationale', 'N/A')[:100]}...")
    except Exception as e:
        print(f"Error during Tech Stack decision: {e}")
        return

    # Step 3: System Designing (Placeholder - Will uncomment later)
    print("\n--- Step 3: System Designing (Next Feature) ---")
    system_designer_agent = SystemDesignerAgent(llm=llm, memory=memory)
    system_design_output = system_designer_agent.run(
        memory.get("brd_analysis"), memory.get("tech_stack_recommendation")
    )
    memory.set("system_design", system_design_output)
    print("System Design will go here.")

    # Step 4: Writing Whole Code (Placeholder for now)
    print("\n--- Step 4: Writing Whole Code (Next Feature) ---")
    print("Code Generation will go here.")

    print("\n--- Workflow End for Phase 1 ---")
    print(f"Final project context saved to {PROJECT_CONTEXT_FILE}")


if __name__ == "__main__":
    run_project_workflow()