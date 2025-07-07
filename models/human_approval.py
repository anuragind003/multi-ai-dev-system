from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

class ApprovalPayload(BaseModel):
    """
    Standardized data contract for human approval steps.
    This model defines the structure of data sent to the frontend
    for any human-in-the-loop decision point.
    """
    step_name: str = Field(..., description="The name of the workflow step requiring approval, e.g., 'brd_analysis'.")
    display_name: str = Field(..., description="A human-readable name for the step, e.g., 'BRD Analysis'.")
    data: Dict[str, Any] = Field(..., description="The primary data payload to be reviewed, e.g., the BRD analysis JSON.")
    instructions: str = Field(
        "Please review the generated output. Provide specific feedback for revisions, or approve to continue.",
        description="Instructions displayed to the user for this approval step."
    )
    is_revision: bool = Field(False, description="True if this is a revised output based on previous feedback.")
    previous_feedback: Optional[str] = Field(None, description="The feedback provided by the user on the last iteration.")
    
    class Config:
        schema_extra = {
            "example": {
                "step_name": "tech_stack_recommendation",
                "display_name": "Technology Stack Recommendation",
                "data": {
                    "backend_language": "Python",
                    "frontend_framework": "React",
                    "database": "PostgreSQL"
                },
                "instructions": "Review the proposed tech stack. Ensure it aligns with the project requirements.",
                "is_revision": True,
                "previous_feedback": "The previous recommendation for Vue.js was not suitable. Please use React instead."
            }
        } 