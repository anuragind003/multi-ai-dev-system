import asyncio
import requests
import websockets
import json
import time
import threading

SERVER_URL = "http://localhost:8001"
WEBSOCKET_URL = "ws://localhost:8001/ws/agent-monitor"

SAMPLE_BRD = {
    "brd_content": """
Project Title: E-commerce Platform

1.  **Project Overview**: A modern e-commerce platform to sell various products online.
2.  **Functional Requirements**:
    -   User registration and login.
    -   Product catalog with search and filtering.
    -   Shopping cart functionality.
    -   Secure checkout process.
3.  **Non-Functional Requirements**:
    -   The platform must be fast and responsive.
    -   The platform must be secure to protect user data.
"""
}

def test_brd_approval_workflow():
    """
    Tests the full BRD approval workflow:
    1. Starts a workflow.
    2. Waits for BRD analysis approval.
    3. Approves the BRD.
    4. Confirms the workflow proceeds to the next step (tech stack).
    """
    session_id = None
    brd_approved = False
    next_step_is_tech_stack = False
    test_failed = False
    error_message = ""

    # --- WebSocket Listener ---
    async def listen_for_events():
        nonlocal session_id, brd_approved, next_step_is_tech_stack, test_failed, error_message
        
        try:
            async with websockets.connect(WEBSOCKET_URL) as websocket:
                print("✅ WebSocket connected.")
                
                # Wait for the workflow to start and give us a session ID
                while not session_id:
                    await asyncio.sleep(0.1)

                print(f"👂 Listening for events for session: {session_id}")

                while not next_step_is_tech_stack and not test_failed:
                    try:
                        message_str = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                        message = json.loads(message_str)

                        # Look for the paused event for BRD approval
                        if message.get("event") == "workflow_paused" and not brd_approved:
                            data = message.get("data", {})
                            if data.get("session_id") == session_id and data.get("approval_type") == "brd_analysis":
                                print("✅ Workflow paused for BRD approval. Approving...")
                                approve_brd(session_id)
                                brd_approved = True

                        # After approval, look for confirmation of the next step
                        if brd_approved:
                            if message.get("event") == "workflow_update":
                                event_data = message.get("data", {}).get("event", {})
                                if "tech_stack_recommendation_node" in event_data:
                                    print("✅ SUCCESS: Workflow proceeded to tech_stack_recommendation_node.")
                                    next_step_is_tech_stack = True
                                    break
                                # If it loops back, the test has failed
                                if "brd_analysis_node" in event_data:
                                    print("❌ FAILURE: Workflow looped back to brd_analysis_node after approval.")
                                    error_message = "Workflow looped back to brd_analysis_node."
                                    test_failed = True
                                    break
                    
                    except asyncio.TimeoutError:
                        error_message = "Test timed out waiting for WebSocket event."
                        test_failed = True
                        break
                    except Exception as e:
                        error_message = f"An error occurred in WebSocket listener: {e}"
                        test_failed = True
                        break
        except Exception as e:
            error_message = f"Failed to connect to WebSocket: {e}"
            test_failed = True

    # --- Helper Functions ---
    def start_workflow():
        nonlocal session_id
        print("🚀 Starting workflow...")
        try:
            response = requests.post(
                f"{SERVER_URL}/api/workflow/run_interactive",
                json={"inputs": SAMPLE_BRD},
                timeout=10
            )
            response.raise_for_status()
            session_id = response.json().get("session_id")
            print(f"✅ Workflow started with session ID: {session_id}")
        except requests.RequestException as e:
            nonlocal test_failed, error_message
            error_message = f"Failed to start workflow: {e}"
            test_failed = True

    def approve_brd(s_id):
        print(f"👍 Sending 'proceed' decision for session {s_id}...")
        try:
            response = requests.post(
                f"{SERVER_URL}/api/workflow/resume/{s_id}",
                json={"decision": "proceed"},
                timeout=10
            )
            response.raise_for_status()
            print("✅ Approval sent successfully.")
        except requests.RequestException as e:
            nonlocal test_failed, error_message
            error_message = f"Failed to send approval: {e}"
            test_failed = True

    # --- Test Execution ---
    listener_thread = threading.Thread(target=lambda: asyncio.run(listen_for_events()), daemon=True)
    listener_thread.start()

    # Give the listener a moment to connect
    time.sleep(1) 

    start_workflow()

    # Wait for the test to complete or fail
    listener_thread.join(timeout=120)

    if test_failed:
        print(f"\n--- ❌ TEST FAILED ---")
        print(f"Error: {error_message}")
        assert False, error_message
    elif next_step_is_tech_stack:
        print("\n--- ✅ TEST PASSED ---")
        print("Workflow correctly proceeded to the tech stack recommendation step after approval.")
    else:
        print("\n--- ❌ TEST FAILED ---")
        print("The test finished without confirming the next step.")
        assert False, "Test did not reach a conclusive state."

if __name__ == "__main__":
    # Ensure the server is running before executing this test
    print("--- Running BRD Approval Workflow Test ---")
    print("Please ensure the main server is running on http://localhost:8001")
    time.sleep(2)
    test_brd_approval_workflow() 