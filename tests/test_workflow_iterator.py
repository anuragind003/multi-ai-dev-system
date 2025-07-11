"""
Test for the async work item iterator and its router.
Ensures that the data parsing and state propagation fixes are working correctly.
"""

import asyncio
import unittest
from unittest.mock import MagicMock

# Add project root to path to allow absolute imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from async_graph_nodes import async_work_item_iterator_node, async_route_after_work_item_iterator
from agent_state import AgentState, StateFields
from models.data_contracts import ComprehensiveImplementationPlanOutput, ImplementationPlan, WorkItem, PlanMetadata

class TestWorkflowIterator(unittest.TestCase):

    def test_iterator_and_router_integration(self):
        """
        Tests that the iterator correctly parses the plan and the router
        correctly interprets the subsequent state.
        """
        # 1. Arrange: Create a mock state with a realistic project plan
        mock_work_item = WorkItem(
            id="FE-001",
            description="Create the main application layout.",
            agent_role="frontend_developer",
            dependencies=[],
            # --- NEW: Add required fields for WorkItem Pydantic model ---
            estimated_time="8 hours",
            acceptance_criteria=["Layout renders correctly", "All components are in place"]
            # ----------------------------------------------------------
        )
        mock_plan = ImplementationPlan(
            project_summary={
                "title": "Mock Project",
                "description": "A test project for iteration.",
                "overall_complexity": "Low",
                "estimated_duration": "1 day"
            },
            # Directly include work_items at the top level of the plan
            # This structure is what the iterator expects for direct processing
            work_items=[mock_work_item],
            phases=[
                {
                    "name": "Phase 1: Frontend Development",
                    "description": "Develop the frontend UI.",
                    "deliverables": ["UI components"],
                    "estimated_duration_hours": 8.0
                }
            ],
            resource_allocation=[
                {
                    "role": "Frontend Developer",
                    "count": 1,
                    "estimated_time_allocation": "100%",
                    "phases": ["Phase 1: Frontend Development"],
                    "skills_required": ["Vue.js", "TypeScript"]
                }
            ],
            timeline={
                "start_date": "2025-01-01",
                "end_date": "2025-01-01",
                "milestones": [{"name": "UI Complete", "date": "2025-01-01"}]
            },
            tech_stack={
                "frontend": {"framework": "Vue.js"},
                "backend": {"framework": "FastAPI"},
            }
        )
        mock_plan_output = ComprehensiveImplementationPlanOutput(
            plan=mock_plan,
            summary="A comprehensive plan for the mock project.",
            metadata=PlanMetadata() # Using the default PlanMetadata for simplicity
        )
        
        initial_state = AgentState(
            {
                StateFields.IMPLEMENTATION_PLAN: mock_plan_output,
                StateFields.COMPLETED_WORK_ITEMS: set()
            }
        )
        
        mock_config = {"configurable": {}}

        # 2. Act: Run the iterator node
        print("\n--- Running async_work_item_iterator_node ---")
        iterator_result = asyncio.run(async_work_item_iterator_node(initial_state, mock_config))
        
        # The node directly mutates the state, so we check the `initial_state` object
        print(f"State after iterator: {initial_state}")

        # 3. Assert: Check the results from the iterator
        self.assertIsNotNone(initial_state.get("current_work_item"), "current_work_item should be set in the state")
        self.assertEqual(initial_state["current_work_item"].id, "FE-001", "The correct work item should be selected")
        self.assertEqual(initial_state.get("_routing_decision"), "proceed", "_routing_decision should be 'proceed'")
        
        # 4. Act: Run the router function with the updated state
        print("\n--- Running async_route_after_work_item_iterator ---")
        routing_decision = asyncio.run(async_route_after_work_item_iterator(initial_state))
        print(f"Router decision: '{routing_decision}'")

        # 5. Assert: Check the router's decision
        self.assertEqual(routing_decision, "proceed", "The router should decide to proceed")
        
        print("\n Test PASSED: Iterator and router are working together correctly.")

if __name__ == "__main__":
    unittest.main() 