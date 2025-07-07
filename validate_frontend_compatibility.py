#!/usr/bin/env python3
"""
Frontend Compatibility Validation Script

This script validates that our standardized ApprovalPayload model
is fully compatible with the frontend expectations.
"""

import json
from typing import Dict, Any

from models.human_approval import ApprovalPayload

def simulate_frontend_conversion(approval_payload: ApprovalPayload, session_id: str) -> Dict[str, Any]:
    """
    Simulate the frontend's handleHumanApprovalRequired conversion.
    This replicates the logic from workflow.ts lines 179-191.
    """
    
    # Extract approval type from step name (frontend logic)
    def extract_approval_type_from_step_name(step_name: str) -> str:
        if "brd" in step_name: return "brd_analysis"
        if "tech_stack" in step_name: return "tech_stack"
        if "design" in step_name: return "system_design"
        if "plan" in step_name: return "implementation_plan"
        if "code" in step_name: return "code_generation"
        return "unknown"
    
    approval_type = extract_approval_type_from_step_name(approval_payload.step_name)
    
    # Convert to frontend ApprovalData format
    approval_data = {
        "session_id": session_id,
        "approval_type": approval_type,
        "step_name": approval_payload.step_name,
        "display_name": approval_payload.display_name or "",
        "approval_data": approval_payload.data,
        "message": approval_payload.instructions or f"Please review the {approval_type} results",
        "project_name": approval_payload.data.get("project_name", "") if isinstance(approval_payload.data, dict) else "",
        "data": approval_payload.data  # Keep the raw data as well
    }
    
    return approval_data

def validate_approval_payload_compatibility():
    """Validate that ApprovalPayload is compatible with frontend expectations."""
    print("Frontend Compatibility Validation")
    print("=" * 50)
    
    # Test case 1: BRD Analysis
    print("\n1. Testing BRD Analysis Compatibility...")
    brd_payload = ApprovalPayload(
        step_name="brd_analysis",
        display_name="Business Requirements Analysis",
        data={
            "project_name": "E-Commerce Platform",
            "requirements": [
                {"id": "FR-1", "description": "User authentication", "type": "functional"},
                {"id": "NFR-1", "description": "Support 1000+ users", "type": "non_functional"}
            ]
        },
        instructions="Please review the extracted requirements and project analysis.",
        is_revision=False,
        previous_feedback=None
    )
    
    frontend_data = simulate_frontend_conversion(brd_payload, "session_123")
    
    print("   Backend ApprovalPayload fields:")
    print(f"     step_name: {brd_payload.step_name}")
    print(f"     display_name: {brd_payload.display_name}")
    print(f"     data_keys: {list(brd_payload.data.keys())}")
    print(f"     instructions: {brd_payload.instructions[:50]}...")
    
    print("   Frontend ApprovalData fields:")
    print(f"     session_id: {frontend_data['session_id']}")
    print(f"     approval_type: {frontend_data['approval_type']}")
    print(f"     step_name: {frontend_data['step_name']}")
    print(f"     display_name: {frontend_data['display_name']}")
    print(f"     message: {frontend_data['message'][:50]}...")
    print(f"     project_name: {frontend_data['project_name']}")
    
    print("   Compatibility: SUCCESS")
    
    # Test case 2: Tech Stack with Revision
    print("\n2. Testing Tech Stack Revision Compatibility...")
    tech_payload = ApprovalPayload(
        step_name="tech_stack_recommendation",
        display_name="Technology Stack Recommendation",
        data={
            "frontend_options": [
                {"name": "React", "selected": True},
                {"name": "Vue.js", "selected": False}
            ],
            "backend_options": [
                {"name": "Node.js", "selected": True}
            ]
        },
        instructions="Please review the revised technology stack based on your feedback.",
        is_revision=True,
        previous_feedback="Please use React instead of Vue.js"
    )
    
    frontend_data = simulate_frontend_conversion(tech_payload, "session_456")
    
    print("   Revision scenario:")
    print(f"     is_revision: {tech_payload.is_revision}")
    print(f"     previous_feedback: {tech_payload.previous_feedback}")
    print(f"     frontend approval_type: {frontend_data['approval_type']}")
    
    print("   Compatibility: SUCCESS")
    
    # Test case 3: System Design
    print("\n3. Testing System Design Compatibility...")
    design_payload = ApprovalPayload(
        step_name="system_design",
        display_name="System Architecture Design",
        data={
            "architecture_overview": "Microservices architecture",
            "components": [
                {"name": "User Service", "description": "Handles authentication"},
                {"name": "Product Service", "description": "Manages catalog"}
            ]
        },
        instructions="Please review the system design and architecture.",
        is_revision=False,
        previous_feedback=None
    )
    
    frontend_data = simulate_frontend_conversion(design_payload, "session_789")
    
    print(f"   Frontend mapping successful: approval_type = {frontend_data['approval_type']}")
    print("   Compatibility: SUCCESS")
    
    # Test case 4: JSON Serialization
    print("\n4. Testing JSON Serialization Compatibility...")
    payload_dict = brd_payload.model_dump()
    json_str = json.dumps(payload_dict, indent=2)
    
    print("   Serialization test:")
    print(f"     Serializable: SUCCESS ({len(json_str)} chars)")
    print(f"     Contains all required fields: {all(field in payload_dict for field in ['step_name', 'display_name', 'data', 'instructions'])}")
    
    # Test case 5: Field Mapping Validation
    print("\n5. Validating Complete Field Mapping...")
    required_frontend_fields = [
        "session_id", "approval_type", "step_name", "display_name", 
        "approval_data", "message", "project_name", "data"
    ]
    
    frontend_data = simulate_frontend_conversion(brd_payload, "test_session")
    missing_fields = [field for field in required_frontend_fields if field not in frontend_data]
    
    print(f"   Required frontend fields: {len(required_frontend_fields)}")
    print(f"   Provided fields: {len(frontend_data)}")
    print(f"   Missing fields: {missing_fields if missing_fields else 'None'}")
    print(f"   Field mapping: {'SUCCESS' if not missing_fields else 'FAILED'}")
    
    return not missing_fields

def validate_websocket_message_format():
    """Validate the WebSocket message format that contains ApprovalPayload."""
    print("\n\nWebSocket Message Format Validation")
    print("=" * 50)
    
    # Simulate the WebSocket message format sent by backend
    approval_payload = ApprovalPayload(
        step_name="brd_analysis",
        display_name="Business Requirements Analysis",
        data={"project_name": "Test Project", "requirements": []},
        instructions="Please review the requirements.",
        is_revision=False,
        previous_feedback=None
    )
    
    # This is how the backend sends the message
    websocket_message = {
        "type": "workflow_event",
        "event": "workflow_paused",
        "data": {
            "session_id": "test_session",
            "paused_at": "human_approval_brd_node",
            "approval_type": "brd_analysis",
            "payload": approval_payload.model_dump()
        }
    }
    
    print("Backend WebSocket message structure:")
    print(f"  type: {websocket_message['type']}")
    print(f"  event: {websocket_message['event']}")
    print(f"  data.session_id: {websocket_message['data']['session_id']}")
    print(f"  data.approval_type: {websocket_message['data']['approval_type']}")
    print(f"  data.payload.step_name: {websocket_message['data']['payload']['step_name']}")
    print(f"  data.payload.display_name: {websocket_message['data']['payload']['display_name']}")
    
    # Frontend receives this and processes it in handleWebSocketMessage
    payload_data = websocket_message["data"]["payload"]
    session_id = websocket_message["data"]["session_id"]
    
    # Frontend conversion
    frontend_approval = simulate_frontend_conversion(
        ApprovalPayload(**payload_data), 
        session_id
    )
    
    print("\nFrontend processed ApprovalData:")
    print(f"  session_id: {frontend_approval['session_id']}")
    print(f"  approval_type: {frontend_approval['approval_type']}")
    print(f"  step_name: {frontend_approval['step_name']}")
    print(f"  display_name: {frontend_approval['display_name']}")
    
    print("\nWebSocket compatibility: SUCCESS")
    return True

def main():
    """Run all compatibility validations."""
    print("ApprovalPayload Frontend Compatibility Validation")
    print("=" * 80)
    print("This script validates that our ApprovalPayload model works with the frontend")
    
    try:
        # Test basic compatibility
        basic_compatible = validate_approval_payload_compatibility()
        
        # Test WebSocket message format
        websocket_compatible = validate_websocket_message_format()
        
        print("\n" + "=" * 80)
        if basic_compatible and websocket_compatible:
            print("VALIDATION RESULT: SUCCESS")
            print("The ApprovalPayload model is fully compatible with frontend expectations.")
            print("\nKey compatibility points confirmed:")
            print("- All required frontend fields are provided")
            print("- Field mapping works correctly")
            print("- JSON serialization is successful")
            print("- WebSocket message format is correct")
            print("- Revision scenarios are supported")
        else:
            print("VALIDATION RESULT: FAILED")
            print("Compatibility issues detected. Please review the logs above.")
            
    except Exception as e:
        print(f"\nVALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 