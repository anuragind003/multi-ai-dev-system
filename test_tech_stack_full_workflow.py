#!/usr/bin/env python3
"""
Test to debug the full tech stack approval workflow.
This will simulate the workflow and check the exact state and interrupt handling.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configuration is now handled by AdvancedWorkflowConfig
from config import AdvancedWorkflowConfig
from enhanced_graph_with_recovery import initialize_workflow_with_recovery
from agent_state import AgentState, StateFields

# Define the required configuration
default_config = {
    "rate_limiting": {
        "enabled": True,
        "max_requests_per_minute": 100
    },
    "logging": {
        "level": "INFO",
        "console": True,
        "file": True
    }
}

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_tech_stack_workflow():
    """Test the full workflow through tech stack approval"""
    
    print("="*80)
    print("TESTING TECH STACK APPROVAL WORKFLOW")
    print("="*80)
    
    try:
        # Create session ID first
        session_id = f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create the enhanced graph
        workflow_components = await initialize_workflow_with_recovery(session_id)
        graph = workflow_components["graph"]
        config = {"configurable": {"thread_id": session_id}}
        
        print(f"Created graph with session ID: {session_id}")
        
        # Define sample BRD content
        brd_content = """
        Project: E-commerce Platform
        
        Requirements:
        - User registration and authentication
        - Product catalog with search and filtering
        - Shopping cart functionality
        - Payment processing
        - Order management
        - Admin dashboard for product management
        
        Target Users: Small to medium businesses
        Expected Load: 1000 concurrent users
        Budget: Medium
        Timeline: 6 months
        """
        
        # Initial inputs
        inputs = {
            "brd_content": brd_content,
            "session_id": session_id,
            "workflow_start_time": datetime.now().isoformat(),
            "enhanced_recovery_enabled": True
        }
        
        print(f"Starting workflow with inputs: {list(inputs.keys())}")
        
        # Run the graph and track state
        node_count = 0
        last_state = None
        
        async for event in graph.astream(inputs, config):
            node_count += 1
            print(f"\n--- Event {node_count} ---")
            print(f"Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
            
            # Check for interruption
            if "__interrupt__" in event:
                print(f"WORKFLOW INTERRUPTED: {event['__interrupt__']}")
                
                # Get the current state
                current_state = graph.get_state(config)
                print(f"Current state next nodes: {current_state.next}")
                print(f"Current state values keys: {list(current_state.values.keys())}")
                
                # Check if we're at BRD approval
                if current_state.next and "human_approval_brd_node" in str(current_state.next):
                    print("\n🔍 BRD APPROVAL INTERRUPT DETECTED")
                    
                    # Check BRD analysis data
                    brd_analysis = current_state.values.get("requirements_analysis")
                    print(f"BRD analysis present: {brd_analysis is not None}")
                    if brd_analysis:
                        print(f"BRD analysis keys: {list(brd_analysis.keys()) if isinstance(brd_analysis, dict) else 'Not a dict'}")
                    
                    # Simulate BRD approval (proceed)
                    print("\n🔄 Simulating BRD approval...")
                    state_update = {
                        "human_decision": "proceed",
                        "revision_feedback": {},
                        "resume_from_approval": True,
                        "current_approval_stage": "BRD_ANALYSIS",
                        # Force next node to be tech_stack_recommendation_node
                        "next_stage": "TECH_STACK_RECOMMENDATION"
                    }
                    
                    graph.update_state(config, state_update)
                    print("State updated for BRD approval resumption")
                    
                    # Continue the workflow to reach tech stack
                    print("Continuing workflow to tech stack...")
                    continue_inputs = None  # Resume from interrupt point
                    
                    continue_node_count = 0
                    async for continue_event in graph.astream(continue_inputs, config):
                        continue_node_count += 1
                        print(f"Continue event {continue_node_count}: {list(continue_event.keys()) if isinstance(continue_event, dict) else continue_event}")
                        
                        # Check for tech stack interrupt
                        if "__interrupt__" in continue_event:
                            print(f"TECH STACK WORKFLOW INTERRUPTED: {continue_event['__interrupt__']}")
                            
                            # Get the current state again
                            tech_stack_state = graph.get_state(config)
                            print(f"Tech stack state next nodes: {tech_stack_state.next}")
                            print(f"Tech stack state values keys: {list(tech_stack_state.values.keys())}")
                            
                            # Check if we're at tech stack approval
                            if tech_stack_state.next and "tech_stack" in str(tech_stack_state.next):
                                print("\n🔍 TECH STACK APPROVAL INTERRUPT DETECTED")
                                
                                # Check state values
                                tech_stack_data = tech_stack_state.values.get("tech_stack_recommendation")
                                brd_analysis = tech_stack_state.values.get("requirements_analysis")
                                
                                print(f"Tech stack data present: {tech_stack_data is not None}")
                                if tech_stack_data:
                                    print(f"Tech stack data keys: {list(tech_stack_data.keys()) if isinstance(tech_stack_data, dict) else 'Not a dict'}")
                                    print(f"Tech stack data sample: {str(tech_stack_data)[:200]}...")
                                
                                print(f"BRD analysis present: {brd_analysis is not None}")
                                if brd_analysis:
                                    print(f"BRD analysis keys: {list(brd_analysis.keys()) if isinstance(brd_analysis, dict) else 'Not a dict'}")
                                
                                # Test the extract function
                                try:
                                    from app.server import extract_tech_stack_data
                                    extracted_data = await extract_tech_stack_data(tech_stack_state.values)
                                    print(f"✅ Extracted tech stack data successfully")
                                    print(f"Extracted data keys: {list(extracted_data.keys())}")
                                    print(f"Frontend framework: {extracted_data.get('frontend_framework', 'N/A')}")
                                    print(f"Backend framework: {extracted_data.get('backend_framework', 'N/A')}")
                                    print(f"Database: {extracted_data.get('database', 'N/A')}")
                                except Exception as e:
                                    print(f"❌ Failed to extract tech stack data: {e}")
                                
                                print("\n✅ TECH STACK APPROVAL TEST COMPLETED SUCCESSFULLY!")
                                return  # Exit the function here
                            
                            break
                        
                        # Log regular continue events
                        for node_name, node_output in continue_event.items():
                            if node_name.endswith("_node"):
                                print(f"Continue Node '{node_name}' completed")
                                if isinstance(node_output, dict):
                                    print(f"  Continue Output keys: {list(node_output.keys())}")
                        
                        # Break after many continue events to avoid infinite loop
                        if continue_node_count > 10:
                            print("Breaking continue loop after 10 events to avoid infinite loop")
                            break
                    
                    break
                
                break
            
            # Log regular events
            for node_name, node_output in event.items():
                if node_name.endswith("_node"):
                    print(f"Node '{node_name}' completed")
                    if isinstance(node_output, dict):
                        print(f"  Output keys: {list(node_output.keys())}")
                    
                    # Store last state
                    last_state = graph.get_state(config)
            
            # Break after many events to avoid infinite loop
            if node_count > 15:
                print("Breaking after 15 events to avoid infinite loop")
                break
        
        print(f"\nCompleted workflow test. Total events: {node_count}")
        
        # Final state check
        final_state = graph.get_state(config)
        if final_state:
            print(f"Final state next nodes: {final_state.next}")
            print(f"Final state values keys: {list(final_state.values.keys())}")
        
    except Exception as e:
        print(f"❌ Error in workflow test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_tech_stack_workflow())
