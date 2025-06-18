"""
Pydantic models for standardized code generation output across all generator agents.
These define the data contracts that all code generation agents must follow.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class GeneratedFile(BaseModel):
    """A structured representation of a single generated code file."""
    file_path: str = Field(description="The full relative path where the file should be saved, e.g., 'src/models/user.py'.")
    content: str = Field(description="The complete source code or text content for the file.")
    purpose: Optional[str] = Field(None, description="Brief description of the file's purpose.")
    status: str = Field("generated", description="Status of the file, e.g., 'generated', 'modified', 'error'.")
    error_message: Optional[str] = Field(None, description="Error message if status is 'error'.")

class CodeGenerationOutput(BaseModel):
    """The standardized output package for any code generation agent."""
    generated_files: List[GeneratedFile] = Field(description="A list of all files created or modified in this step.")
    summary: str = Field(description="A brief, human-readable summary of the actions taken.")
    status: str = Field("success", description="Overall status: 'success', 'partial', or 'error'.")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata about the generation process.")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Timestamp of generation.")