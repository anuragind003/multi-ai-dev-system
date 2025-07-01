"""
Code Generation Package for Multi-AI Development System

This package contains specialized code generation agents following LLM-powered architecture:

ARCHITECTURE PARADIGM:
- LLM-Powered: Agents use reasoning and dynamic tool selection
- General Purpose: Adapt to ANY domain, framework, and scale without hardcoding  
- Tool-Based: Specialized tools that LLMs call intelligently based on context
- Context-Aware: Each generation informed by project requirements and previous results

BACKEND GENERATION APPROACHES:
1. GeneralizedBackendGenerator (RECOMMENDED): LLM-powered, framework-agnostic, domain-intelligent
2. BackendOrchestratorAgent (LEGACY): Industrial but with some hardcoded components

CONSISTENCY WITH SYSTEM:
- BRD Analyst, Tech Stack Advisor, System Designer: All use LLM-powered ReAct framework
- Plan Compiler: Uses dynamic reasoning and tool-based execution  
- Backend Generation: Should follow same paradigm for consistency
"""

# Ensure correct import paths
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Primary LLM-powered generators (aligned with system architecture)
from .backend_orchestrator import BackendOrchestratorAgent
from .architecture_generator import ArchitectureGeneratorAgent
from .frontend_generator import FrontendGeneratorAgent  
from .database_generator import DatabaseGeneratorAgent
from .integration_generator import IntegrationGeneratorAgent

# Legacy/Specialized generators
from .backend_orchestrator import BackendOrchestratorAgent

# Base classes
from .base_code_generator import BaseCodeGeneratorAgent

__all__ = [
    # LLM-Powered Generators (Primary)
    "GeneralizedBackendGenerator",
    "ArchitectureGeneratorAgent", 
    "FrontendGeneratorAgent",
    "DatabaseGeneratorAgent",
    "IntegrationGeneratorAgent",
    
    # Legacy/Specialized
    "BackendOrchestratorAgent",
    
    # Base
    "BaseCodeGeneratorAgent"
]

# Recommended generator mapping for new projects
RECOMMENDED_GENERATORS = {
    "backend": BackendOrchestratorAgent,
    "architecture": ArchitectureGeneratorAgent,
    "frontend": FrontendGeneratorAgent, 
    "database": DatabaseGeneratorAgent,
    "integration": IntegrationGeneratorAgent
}

# Legacy mapping for existing integrations
LEGACY_GENERATORS = {
    "backend": BackendOrchestratorAgent,
    "architecture": ArchitectureGeneratorAgent,
    "frontend": FrontendGeneratorAgent,
    "database": DatabaseGeneratorAgent, 
    "integration": IntegrationGeneratorAgent
}

