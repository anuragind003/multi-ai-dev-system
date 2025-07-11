"""
Approval Service Module

This module handles all human approval logic, including:
- Approval payload creation
- Data extraction for different stages
- Standardized approval processing
"""

import logging
import time
from typing import Any, Dict, Optional, List

from models.data_contracts import ComprehensiveTechStackOutput
from models.human_approval import ApprovalPayload
from tools.tech_stack_tools_enhanced import fix_field_mappings

logger = logging.getLogger(__name__)

async def extract_brd_analysis_data(state_values: dict) -> dict:
    """Extract BRD analysis data from the workflow state."""
    brd_analysis = state_values.get("requirements_analysis", {})
    
    # Helper function to safely convert requirement objects to text
    def extract_requirement_text(req_list):
        texts = []
        for req in req_list:
            if isinstance(req, str):
                texts.append(req)
            elif isinstance(req, dict):
                text = req.get("description") or req.get("text") or req.get("requirement") or str(req)
                texts.append(text)
            else:
                texts.append(str(req))
        return texts

    functional_requirements = brd_analysis.get("functional_requirements", [])
    non_functional_requirements = brd_analysis.get("non_functional_requirements", [])
    
    processed_functional = extract_requirement_text(functional_requirements)
    processed_non_functional = extract_requirement_text(non_functional_requirements)
    
    # Create a comprehensive requirements list for display in the format the frontend expects
    combined_requirements = []
    
    for i, req_text in enumerate(processed_functional, 1):
        combined_requirements.append({
            "id": f"FR-{i}",
            "title": f"Functional Requirement {i}",
            "description": req_text,
            "acceptance_criteria": []  # Default empty list
        })
    
    for i, req_text in enumerate(processed_non_functional, 1):
        combined_requirements.append({
            "id": f"NFR-{i}",
            "title": f"Non-Functional Requirement {i}",
            "description": req_text,
            "acceptance_criteria": [] # Default empty list
        })

    # Fallback if no functional/non-functional found, but a root 'requirements' list exists
    if not combined_requirements and brd_analysis.get("requirements"):
        raw_requirements = brd_analysis.get("requirements", [])
        for i, req in enumerate(raw_requirements, 1):
            if isinstance(req, dict):
                combined_requirements.append({
                    "id": req.get("id", f"REQ-{i}"),
                    "title": req.get("title", f"Requirement {i}"),
                    "description": req.get("description", "No description provided."),
                    "acceptance_criteria": req.get("acceptance_criteria", [])
                })

    extracted_data = {
        "type": "brd_analysis",
        "timestamp": time.time(),
        "project_name": brd_analysis.get("project_name", "Unnamed Project"),
        "project_summary": brd_analysis.get("project_summary", ""),
        "business_context": brd_analysis.get("business_context", ""),
        "stakeholders": brd_analysis.get("stakeholders", []),
        "success_criteria": brd_analysis.get("success_criteria", []),
        "constraints": brd_analysis.get("constraints", []),
        "assumptions": brd_analysis.get("assumptions", []),
        "functional_requirements": processed_functional,
        "non_functional_requirements": processed_non_functional,
        "requirements": combined_requirements,
        "extracted_requirements": combined_requirements,
        "raw_analysis": brd_analysis
    }
    
    logger.info(f"Extracted BRD analysis data with {len(combined_requirements)} total requirements.")
    if combined_requirements:
        logger.info(f"First combined requirement: {combined_requirements[0]['description'][:100]}...")
    
    return extracted_data

async def extract_tech_stack_data(state_values: dict, user_feedback: Optional[Dict[str, Any]] = None) -> dict:
    """Extract tech stack recommendation data from the workflow state, handling multiple options and user selections."""
    tech_stack_output_raw = state_values.get("tech_stack_recommendation", {})
    logger.info(f"Extracting tech stack data. Received structure with keys: {list(tech_stack_output_raw.keys())}")
    
    # Handle nested structure where actual data is under 'tech_stack_result' key
    if "tech_stack_result" in tech_stack_output_raw:
        logger.info("Found tech_stack_result nested structure, extracting...")
        actual_tech_stack_data = tech_stack_output_raw["tech_stack_result"]
        # If it's a Pydantic model, convert to dict
        if hasattr(actual_tech_stack_data, 'model_dump'):
            tech_stack_output_raw = actual_tech_stack_data.model_dump()
        else:
            tech_stack_output_raw = actual_tech_stack_data
        logger.info(f"Extracted tech stack data from nested structure. New keys: {list(tech_stack_output_raw.keys()) if isinstance(tech_stack_output_raw, dict) else 'Not a dict'}")

    # Apply field mapping fixes before attempting to parse
    try:
        fixed_tech_stack_data = fix_field_mappings(tech_stack_output_raw)
        tech_stack_output = ComprehensiveTechStackOutput(**fixed_tech_stack_data)
    except Exception as e:
        logger.error(f"Failed to parse tech_stack_recommendation into ComprehensiveTechStackOutput: {e}", exc_info=True)
        # Fallback to a minimal, empty output if parsing fails
        tech_stack_output = ComprehensiveTechStackOutput()

    extracted_data = {
        "type": "tech_stack",
        "timestamp": time.time(),
        "raw_recommendation": tech_stack_output.model_dump(),
        "frontend_options": [],
        "backend_options": [],
        "database_options": [],
        "cloud_options": [],
        "architecture_options": [],
        "tool_options": [],
        "risks": [],
        "synthesis": tech_stack_output.synthesis.model_dump() if tech_stack_output.synthesis else {},
        "selected_stack": tech_stack_output.selected_stack.model_dump() if tech_stack_output.selected_stack else {}
    }

    # Helper to process options and mark selections
    def process_options(options: List[Any], feedback_key: str, default_name_key: str = 'name') -> List[dict]:
        processed = []
        selected_name = user_feedback.get(feedback_key) if user_feedback else None
        has_selection = False

        for i, option_raw in enumerate(options):
            # Ensure option is a dictionary, convert Pydantic models
            option_dict = option_raw.model_dump() if hasattr(option_raw, 'model_dump') else option_raw

            # Mark 'selected' based on user feedback or as the first option if no feedback
            is_selected = False
            if selected_name:
                if option_dict.get(default_name_key) == selected_name:
                    is_selected = True
                    has_selection = True
            elif i == 0 and not has_selection: # Default select the first if no user feedback for this category
                is_selected = True
                has_selection = True

            option_dict["selected"] = is_selected
            processed.append(option_dict)
        return processed

    extracted_data["frontend_options"] = process_options(tech_stack_output.frontend_options, "frontend_selection")
    extracted_data["backend_options"] = process_options(tech_stack_output.backend_options, "backend_selection")
    extracted_data["database_options"] = process_options(tech_stack_output.database_options, "database_selection")
    extracted_data["cloud_options"] = process_options(tech_stack_output.cloud_options, "cloud_selection")
    extracted_data["architecture_options"] = process_options(tech_stack_output.architecture_options, "architecture_selection", default_name_key='pattern')
    extracted_data["tool_options"] = process_options(tech_stack_output.tool_options, "tool_selection")
    
    # Risks are just a list of TechRisk objects, no 'selected' field needed
    extracted_data["risks"] = [risk.model_dump() for risk in tech_stack_output.risks]

    logger.info(f"Extracted tech stack data (after processing options): {list(extracted_data.keys())}")
    
    # Debug logging to help diagnose frontend issues
    logger.info(f"Frontend options count: {len(extracted_data['frontend_options'])}")
    logger.info(f"Backend options count: {len(extracted_data['backend_options'])}")
    logger.info(f"Database options count: {len(extracted_data['database_options'])}")
    logger.info(f"Architecture options count: {len(extracted_data['architecture_options'])}")
    
    if extracted_data['frontend_options']:
        logger.info(f"First frontend option: {extracted_data['frontend_options'][0]}")
    if extracted_data['backend_options']:
        logger.info(f"First backend option: {extracted_data['backend_options'][0]}")
        
    return extracted_data

async def extract_system_design_data(state_values: dict) -> dict:
    """Extract system design data from the workflow state."""
    system_design = state_values.get("system_design", {})
    
    return {
        "type": "system_design",
        "timestamp": time.time(),
        "architecture_overview": system_design.get("architecture", {}).get("pattern", ""),
        "components": system_design.get("components", []),
        "data_flow": system_design.get("data_flow", ""),
        "security_considerations": [m.get("implementation", "") for m in system_design.get("security", {}).get("security_measures", [])],
        "scalability_plan": system_design.get("scalability_and_performance", {}).get("summary", ""),

        "deployment_strategy": system_design.get("deployment_strategy", {}).get("summary", ""),
        "raw_design": system_design
    }

async def extract_plan_data(state_values: dict) -> dict:
    """Extract implementation plan data from the workflow state."""
    # Get the ComprehensiveImplementationPlanOutput object (as a dict)
    plan_output = state_values.get("implementation_plan", {})
    
    # The actual ImplementationPlan is nested under the 'plan' key
    # Check if plan_output is a Pydantic model and access 'plan' directly
    if hasattr(plan_output, 'plan'):
        implementation_plan = plan_output.plan.model_dump() # Convert to dict if it's a Pydantic model
    else:
        # Fallback for older structures or if it's already a dict
        implementation_plan = plan_output.get("plan", {})
    
    # Process phases to ensure proper format for frontend
    phases = []
    for phase_data in implementation_plan.get("phases", []):
        if hasattr(phase_data, 'model_dump'):
            phase_dict = phase_data.model_dump()
        else:
            phase_dict = phase_data
        
        # Ensure work_items are properly formatted
        work_items = []
        for item in phase_dict.get("work_items", []):
            if hasattr(item, 'model_dump'):
                work_items.append(item.model_dump())
            else:
                work_items.append(item)
        
        # Create properly formatted phase
        formatted_phase = {
            "name": phase_dict.get("name", ""),
            "description": phase_dict.get("description", ""),
            "duration": f"{phase_dict.get('estimated_duration_hours', 40)} hours",
            "work_items": work_items,
            "dependencies": phase_dict.get("dependencies", [])
        }
        phases.append(formatted_phase)
    
    # Properly serialize raw_plan to avoid string representation
    raw_plan_serialized = {}
    if hasattr(plan_output, 'model_dump'):
        raw_plan_serialized = plan_output.model_dump()
    elif isinstance(plan_output, dict):
        raw_plan_serialized = plan_output
    else:
        raw_plan_serialized = {"error": "Could not serialize plan_output"}
    
    return {
        "type": "implementation_plan",
        "timestamp": time.time(),
        "project_overview": implementation_plan.get("project_summary", {}).get("description", ""),
        "phases": phases,  # Frontend expects 'phases', not 'development_phases'
        "estimated_timeline": f"{sum(p.get('estimated_duration_hours', 40) for p in implementation_plan.get('phases', []))} hours total",
        "timeline_estimation": implementation_plan.get("timeline", {}).model_dump() if hasattr(implementation_plan.get("timeline", {}), 'model_dump') else implementation_plan.get("timeline", {}),
        "risk_assessment": implementation_plan.get("risks_and_mitigations", []),
        "resource_requirements": implementation_plan.get("resource_allocation", []),
        "deliverables": [item for phase in implementation_plan.get("phases", []) for item in phase.get("deliverables", [])],
        "dependencies": [], # Dependencies are usually at work item level, not direct plan level
        "raw_plan": raw_plan_serialized # Properly serialized instead of string representation
    }

# === Modular Human Approval Functions ===

async def create_brd_approval_payload(state_values: dict, user_feedback: Optional[Dict[str, Any]] = None) -> ApprovalPayload:
    """Create standardized approval payload for BRD analysis stage."""
    extracted_data = await extract_brd_analysis_data(state_values)
    
    return ApprovalPayload(
        step_name="brd_analysis",
        display_name="Business Requirements Analysis",
        data=extracted_data,
        instructions="Please review the extracted requirements and project analysis. Verify that all functional and non-functional requirements are correctly identified and categorized.",
        is_revision=user_feedback is not None,
        previous_feedback=user_feedback.get("feedback") if user_feedback else None
    )

async def create_tech_stack_approval_payload(state_values: dict, user_feedback: Optional[Dict[str, Any]] = None) -> ApprovalPayload:
    """Create standardized approval payload for technology stack recommendation stage."""
    extracted_data = await extract_tech_stack_data(state_values, user_feedback)
    
    return ApprovalPayload(
        step_name="tech_stack_recommendation",
        display_name="Technology Stack Recommendation",
        data=extracted_data,
        instructions="Please review the recommended technology stack. You can approve the selections, request revisions with specific feedback, or choose different options from the provided alternatives.",
        is_revision=user_feedback is not None,
        previous_feedback=user_feedback.get("feedback") if user_feedback else None
    )

async def create_system_design_approval_payload(state_values: dict, user_feedback: Optional[Dict[str, Any]] = None) -> ApprovalPayload:
    """Create standardized approval payload for system design stage."""
    extracted_data = await extract_system_design_data(state_values)
    
    return ApprovalPayload(
        step_name="system_design",
        display_name="System Architecture Design",
        data=extracted_data,
        instructions="Please review the system architecture design including components, data flow, security considerations, and scalability plan. Ensure the design aligns with your requirements and technical constraints.",
        is_revision=user_feedback is not None,
        previous_feedback=user_feedback.get("feedback") if user_feedback else None
    )

async def create_implementation_plan_approval_payload(state_values: dict, user_feedback: Optional[Dict[str, Any]] = None) -> ApprovalPayload:
    """Create standardized approval payload for implementation plan stage."""
    extracted_data = await extract_plan_data(state_values)
    
    return ApprovalPayload(
        step_name="implementation_plan",
        display_name="Implementation Plan",
        data=extracted_data,
        instructions="Please review the detailed implementation plan including development phases, timeline, resource allocation, and risk assessment. Verify that the plan is realistic and aligns with your project goals.",
        is_revision=user_feedback is not None,
        previous_feedback=user_feedback.get("feedback") if user_feedback else None
    )

async def get_approval_payload_for_stage(stage: str, state_values: dict, user_feedback: Optional[Dict[str, Any]] = None) -> ApprovalPayload:
    """
    Factory function to get the appropriate approval payload for any workflow stage.
    This centralizes approval payload creation and makes it easy to add new stages.
    
    Args:
        stage: The workflow stage name (e.g., 'brd_analysis', 'tech_stack_recommendation')
        state_values: Current workflow state values
        user_feedback: Optional user feedback for revision scenarios
        
    Returns:
        ApprovalPayload: Standardized approval payload for the stage
        
    Raises:
        ValueError: If the stage is not supported
    """
    stage_creators = {
        "brd_analysis": create_brd_approval_payload,
        "tech_stack_recommendation": create_tech_stack_approval_payload,
        "system_design": create_system_design_approval_payload,
        "implementation_plan": create_implementation_plan_approval_payload,
    }
    
    if stage not in stage_creators:
        raise ValueError(f"Unsupported approval stage: {stage}. Supported stages: {list(stage_creators.keys())}")
    
    return await stage_creators[stage](state_values, user_feedback) 