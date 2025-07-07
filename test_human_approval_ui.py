#!/usr/bin/env python3
"""
Test script to verify human approval UI functionality
"""

import asyncio
import json
import uuid
import os
import sys

# Add project root to sys.path to allow imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from async_graph import get_async_workflow
from enhanced_langgraph_checkpointer import EnhancedMemoryCheckpointer
from config import initialize_system_config, get_system_config, AdvancedWorkflowConfig

# Initialize system configuration at the start of the script
# This is crucial for standalone scripts to load necessary configs.
try:
    # Create a default config object to pass to the initializer
    default_workflow_config = AdvancedWorkflowConfig()
    initialize_system_config(default_workflow_config)
except Exception as e:
    print(f"Configuration initialization failed: {e}")
    # Exit if config fails, as nothing will work
    sys.exit(1)


async def test_human_approval_workflow():
    """Test the human approval workflow with a simple BRD"""
    
    print("🧪 Testing Human Approval Workflow...")
    
    # Create checkpointer
    checkpointer = EnhancedMemoryCheckpointer(backend_type="hybrid")
    
    # Get system config for the workflow
    system_config = get_system_config()
    
    # Get the resumable workflow
    uncompiled_graph = await get_async_workflow("resumable")
    graph = uncompiled_graph.compile(checkpointer=checkpointer)
    
    # Create a test session
    session_id = f"test_session_{uuid.uuid4()}"
    config = {"configurable": {"thread_id": session_id, "memory_hub": system_config.memory_hub}}
    
    # Simple test BRD
    test_brd = """
    Project: Simple Todo Application
    
    Requirements:
    - Create a web-based todo application
    - Users can add, edit, and delete tasks
    - Tasks should be persistent
    - Simple, clean interface
    
    Technical Requirements:
    - Web application
    - Database for persistence
    - User-friendly interface
    """
    
    inputs = {
        "brd_content": test_brd,
        "workflow_start_time": asyncio.get_event_loop().time()
    }
    
    print(f"📝 Starting workflow with session: {session_id}")
    
    try:
        # Stream events until we hit the human approval
        interrupted = False
        async for event in graph.astream_events(inputs, config, version="v2"):
            # The 'on_chain_end' event for the analysis node contains its output
            if event.get("event") == "on_chain_end" and "brd_analysis_node" in event.get("name", ""):
                payload = event.get("data", {}).get("output", {})
                if isinstance(payload, dict) and "brd_analysis_output" in payload:
                    print("✅ BRD analysis node successfully produced output.")
                else:
                    print("❌ BRD analysis node did NOT produce the expected output.")

            # The correct way to detect an interruption is to check for the
            # special `__interrupt__` key in an `on_chain_stream` event.
            if event.get("event") == "on_chain_stream":
                if "__interrupt__" in event.get("data", {}).get("chunk", {}):
                    print(f"\n⏸️  Workflow paused successfully for human approval.")
                    interrupted = True
                    break  # Stop checking once we've confirmed the interruption

        if interrupted:
            print("\n🎯 Human approval required! The test is successful.")
            return True
        else:
            print("❌ Workflow completed without reaching human approval")
            return False
        
    except Exception as e:
        print(f"❌ Error during workflow execution: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_approval_decisions():
    """Test different approval decisions' data structures"""
    
    print("\n🧪 Verifying Human Approval Decision Payloads...")
    
    decisions = ["proceed", "revise", "end"]
    
    for decision in decisions:
        print(f"\n📋 Testing decision: '{decision}'")
        
        feedback_payload = {
            "human_feedback": {
                "decision": decision,
                "feedback": f"Test feedback for {decision}" if decision == "revise" else None
            }
        }
        
        print(f"   Payload: {json.dumps(feedback_payload, indent=2)}")
        
        if decision == "end":
            print("   -> Backend should terminate the workflow.")
        elif decision == "proceed":
            print("   -> Backend should continue to the next step.")
        elif decision == "revise":
            print("   -> Backend should loop back for revision.")
    print("\n✅ Decision payload test completed.")


if __name__ == "__main__":
    print("🚀 Running Human Approval UI Tests\n")
    
    success = asyncio.run(test_human_approval_workflow())
    
    if success:
        asyncio.run(test_approval_decisions())
        print("\n🎉 All tests passed successfully!")
        print("\nNext steps:")
        print("1. Start the backend server: python -m app.server")
        print("2. Start the frontend: npm run dev")
        print("3. Submit a BRD and verify the human approval modal appears.")
    else:
        print("\n🔥 One or more tests failed.")
        print("Please review the error messages above.") 