"""
Simplified Plan Compiler Agent.
Directly calls the planning tool without ReAct framework overhead.
"""

import logging
from typing import Dict, Any, List
import asyncio
from datetime import datetime

from agents.base_agent import BaseAgent
from tools.planning_tools_enhanced import generate_comprehensive_work_item_backlog
from models.data_contracts import WorkItemBacklog, ComprehensiveImplementationPlanOutput, ImplementationPlan, ProjectSummary, DevelopmentPhase, ResourceAllocation, PlanMetadata, WorkItem

logger = logging.getLogger(__name__)

class PlanCompilerSimplifiedAgent(BaseAgent):
    """
    Simplified Plan Compiler Agent.
    Directly calls the planning tool without ReAct framework overhead.
    """

    def __init__(self, llm=None, **kwargs):
        """
        Initializes the PlanCompilerSimplifiedAgent.
        """
        super().__init__(
            llm=llm,
            agent_name="Plan Compiler Simplified Agent",
            agent_description="Generates comprehensive work item backlog based on system design.",
            **kwargs
        )

        # Store the tool for direct calling
        self.planning_tool = generate_comprehensive_work_item_backlog

        self.log_info("Plan Compiler Simplified Agent initialized successfully")

    def _convert_work_item_backlog_to_implementation_plan(self, backlog: WorkItemBacklog) -> ComprehensiveImplementationPlanOutput:
        """
        Converts a WorkItemBacklog into the ComprehensiveImplementationPlanOutput structure.
        This attempts to map granular work items into higher-level plan components.
        """
        self.log_info("Converting WorkItemBacklog to ComprehensiveImplementationPlanOutput.")

        # Project Summary (basic inference from backlog summary)
        project_summary = ProjectSummary(
            title=backlog.metadata.get("project_name", "Generated Project Plan"),
            description=backlog.summary,
            overall_complexity=backlog.metadata.get("estimated_complexity", "Medium"),
            estimated_duration=backlog.metadata.get("estimated_total_time", "TBD"),
            key_challenges=backlog.metadata.get("key_risks", [])
        )

        # Development Phases (group work items by agent_role or infer phases)
        phases_map: Dict[str, List[WorkItem]] = {}
        for item in backlog.work_items:
            # Use agent_role as a proxy for phase for simplicity
            phase_name = item.agent_role.replace("_developer", "").replace("_specialist", "").title() + " Phase"
            if phase_name not in phases_map:
                phases_map[phase_name] = []
            phases_map[phase_name].append(item)
        
        development_phases: List[Dict[str, Any]] = []
        for phase_name, work_items in phases_map.items():
            total_hours_for_phase = 0.0 # Initialize for each phase
            # Safely get estimated_time, default to "0 hours" if not present
            for item in work_items:
                estimated_time_str = item.estimated_time if hasattr(item, 'estimated_time') else "0 hours"
                time_value = 0.0
                if estimated_time_str and "hours" in estimated_time_str:
                    try:
                        time_value = float(estimated_time_str.split(" ")[0])
                    except ValueError:
                        logger.warning(f"Could not parse estimated_time: {estimated_time_str}")
                elif estimated_time_str and "day" in estimated_time_str:
                    try:
                        # Assuming a standard 8-hour workday for conversion
                        time_value = float(estimated_time_str.split(" ")[0]) * 8
                    except ValueError:
                        logger.warning(f"Could not parse estimated_time (days): {estimated_time_str}")
                total_hours_for_phase += time_value
            development_phases.append(DevelopmentPhase(
                name=phase_name,
                description=f"Tasks related to {phase_name.lower()}",
                deliverables=[f"Completed {item.id}" for item in work_items],
                estimated_duration_hours=total_hours_for_phase
            ).model_dump()) # Convert to dict as the ImplementationPlan expects Dict[str, Any]

        # Resource Allocation (basic inference from agent_roles)
        resource_roles = set(item.agent_role for item in backlog.work_items)
        resource_allocation = [
            ResourceAllocation(
                role=role.replace("_", " ").title(),
                count=1, # Default count
                estimated_time_allocation="100%",
                phases=[p["name"] for p in development_phases if role.replace("_developer", "").replace("_specialist", "").title() in p["name"]]
            ).model_dump() # Convert to dict
            for role in resource_roles
        ]

        # Risks and Mitigations (from backlog metadata)
        risks_and_mitigations = backlog.metadata.get("risk_assessment", {}).get("risks", [])

        # Timeline (basic inference or placeholder)
        timeline = {
            "start_date": datetime.now().isoformat(),
            "end_date": "TBD",
            "milestones": []
        }
        if "estimated_total_time" in backlog.metadata:
            timeline["overall_duration"] = backlog.metadata["estimated_total_time"]

        # Tech Stack (from backlog metadata if available)
        tech_stack = backlog.metadata.get("tech_stack_recommendation", {})
        
        # Metadata
        plan_metadata = PlanMetadata(
            generated_at=datetime.now().isoformat(),
            version="1.0",
            author="Multi-AI Dev System",
            notes=f"Converted from WorkItemBacklog. Original summary: {backlog.summary}"
        )

        # Create the ImplementationPlan instance
        implementation_plan = ImplementationPlan(
            project_summary=project_summary.model_dump(),
            phases=development_phases,
            resource_allocation=resource_allocation,
            risks_and_mitigations=risks_and_mitigations,
            timeline=timeline,
            tech_stack=tech_stack,
            metadata=plan_metadata.model_dump()
        )

        # Create the ComprehensiveImplementationPlanOutput instance
        comprehensive_plan_output = ComprehensiveImplementationPlanOutput(
            plan=implementation_plan,
            summary=backlog.summary,
            metadata=plan_metadata
        )
        
        self.log_info("Successfully converted WorkItemBacklog to ComprehensiveImplementationPlanOutput.")
        return comprehensive_plan_output

    def run(self, requirements_analysis: dict, tech_stack_recommendation: dict, system_design: dict, **kwargs) -> ComprehensiveImplementationPlanOutput:
        """
        Generates a comprehensive work item backlog by directly invoking the tool.
        This is the synchronous implementation.
        """
        self.log_info("Starting plan compilation with simplified agent (synchronous run).")
        
        try:
            # Directly call the planning tool
            self.log_info("Calling generate_comprehensive_work_item_backlog tool directly (synchronous call)")
            
            backlog_result = self.planning_tool.invoke({
                "requirements_analysis": requirements_analysis,
                "tech_stack_recommendation": tech_stack_recommendation,
                "system_design": system_design
            })
            
            self.log_info(f"Planning tool returned result type: {type(backlog_result)}")
            if isinstance(backlog_result, WorkItemBacklog):
                self.log_success("Planning tool executed successfully, converting to comprehensive plan output.")
                # Convert the WorkItemBacklog to the expected ComprehensiveImplementationPlanOutput
                return self._convert_work_item_backlog_to_implementation_plan(backlog_result)
            elif isinstance(backlog_result, dict) and "error" in backlog_result:
                self.log_error(f"Planning tool returned error: {backlog_result}")
                return self.get_default_response(Exception(backlog_result.get("details", "Unknown planning error")))
            else:
                self.log_info(f"Planning tool returned unexpected result type: {type(backlog_result)}. Attempting to wrap as default response.")
                return self.get_default_response(Exception(f"Unexpected planning tool result: {str(backlog_result)[:200]}"))
            
        except Exception as e:
            self.log_error(f"Error in synchronous plan compilation: {str(e)}", exc_info=True)
            return self.get_default_response(e)
        
    async def arun(self, requirements_analysis: dict, tech_stack_recommendation: dict, system_design: dict, **kwargs) -> ComprehensiveImplementationPlanOutput:
        """
        Asynchronously generates a comprehensive work item backlog by delegating to the synchronous run method.
        """
        self.log_info("Asynchronous run method called. Delegating to synchronous run.")
        return await asyncio.to_thread(self.run, requirements_analysis, tech_stack_recommendation, system_design, **kwargs)

    def get_default_response(self, error: Exception) -> ComprehensiveImplementationPlanOutput:
        """Returns a default, safe response in case of a critical failure."""
        self.log_error(f"Executing default response due to error: {error}", exc_info=True)
        # Return a valid, but empty/error-state ComprehensiveImplementationPlanOutput
        empty_plan = ImplementationPlan(
            project_summary=ProjectSummary(title="Error Plan", description=f"Failed to generate plan: {error}", overall_complexity="N/A", estimated_duration="N/A").model_dump(),
            phases=[],
            resource_allocation=[],
            risks_and_mitigations=[],
            timeline={},
            tech_stack={},
            metadata=PlanMetadata(notes="Generated due to error").model_dump()
        )
        return ComprehensiveImplementationPlanOutput(
            plan=empty_plan,
            summary=f"Error generating implementation plan: {error}",
            metadata=PlanMetadata(notes="Error occurred during plan compilation.")
        )
