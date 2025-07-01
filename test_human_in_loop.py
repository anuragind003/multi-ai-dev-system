import asyncio
import uuid
from typing import Dict, Any

from langgraph.graph import StateGraph
from langgraph.types import Command

from agent_state import AgentState, StateFields
from async_graph import get_async_workflow
from enhanced_memory_manager import get_project_memory
from enhanced_langgraph_checkpointer import EnhancedMemoryCheckpointer
from monitoring import setup_logging

# It's good practice to set up the environment for logging, etc.
setup_logging()

async def run_test():
    """
    Tests the human-in-the-loop functionality by running the resumable
    workflow until it pauses for human approval, then resumes it.
    """
    print("--- 🧪 Starting Human-in-the-Loop Backend Test ---")

    # 1. Initialize components
    session_id = f"test_session_{uuid.uuid4()}"
    memory_manager = get_project_memory(f"./test_output/run_{session_id}")
    checkpointer = EnhancedMemoryCheckpointer(memory_manager=memory_manager, backend_type="hybrid")
    
    # 2. Get the resumable async workflow
    # We need to get the uncompiled graph first
    uncompiled_graph = await get_async_workflow("resumable")
    
    # Now, compile it with our checkpointer
    resumable_workflow = uncompiled_graph.compile(checkpointer=checkpointer)

    print(f"✅ Workflow compiled with session ID: {session_id}")

    # 3. Invoke the workflow to run it until the interrupt
    config = {"configurable": {"thread_id": session_id}}
    initial_input = {StateFields.BRD_CONTENT: "Create a simple web server with a single endpoint."}
    
    print("\n--- ▶️ Running workflow to first interruption point... ---")
    interrupted_state = None
    async for event in resumable_workflow.astream(initial_input, config, stream_mode="values"):
        print(f"EVENT: {list(event.keys())}")
        if "__interrupt__" in event:
            interrupted_state = event
            print("🛑 Workflow interrupted as expected.")
            break
        
    # 4. Assert that the workflow was interrupted
    assert interrupted_state is not None, "Workflow did not interrupt as expected!"
    assert "__interrupt__" in interrupted_state, "Interrupt information not found in state."
    
    interrupt_data = interrupted_state["__interrupt__"][0].value
    print(f"✅ Interrupt successful. Data for user: {interrupt_data}")
    assert "tech_stack_node" in interrupted_state, "Test assumes interruption happens after tech_stack_node."


    # 5. Resume the workflow with a mocked human decision
    print("\n--- 🔄 Resuming workflow with 'approve' decision... ---")
    
    # The 'Command' object is used to send instructions back to the graph
    resume_command = Command(resume="approve")
    
    final_state = None
    async for event in resumable_workflow.astream(resume_command, config, stream_mode="values"):
        print(f"EVENT: {list(event.keys())}")
        final_state = event
    
    # 6. Confirm that the workflow proceeded
    assert final_state is not None, "Workflow did not produce a final state after resuming."
    assert "human_approval_node" in final_state, "Human approval node was not in the final state."
    assert final_state["human_approval_node"]["human_decision"] == "approve", "Human decision was not 'approve'."
    assert "system_design_node" in final_state, "Workflow did not proceed to system_design_node after approval."

    print("\n--- ✅ Test Passed! Human-in-the-Loop backend logic is working correctly. ---")


if __name__ == "__main__":
    asyncio.run(run_test())
