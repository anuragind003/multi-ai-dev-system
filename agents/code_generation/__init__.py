"""
Code Generation Package for Multi-AI Development System

This package contains SIMPLIFIED code generation agents following streamlined architecture:

SIMPLIFIED ARCHITECTURE (Post-Migration):
- 4 Simple Agents: SimpleBackendAgent, SimpleFrontendAgent, SimpleDatabaseAgent, SimpleOpsAgent
- 75% reduction in code complexity (~400KB to ~60KB)
- Unified approach using modern LLM capabilities
- Legacy agents moved to legacy/ folder for reference

AGENT RESPONSIBILITIES:
- SimpleBackendAgent: API development, business logic, integrations
- SimpleFrontendAgent: UI components, state management, routing
- SimpleDatabaseAgent: Schema design, migrations, queries
- SimpleOpsAgent: DevOps, testing, documentation, security
"""

# Ensure correct import paths
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# NEW SIMPLIFIED AGENTS (Primary)
from .simple_backend_agent import SimpleBackendAgent
from .simple_frontend_agent import SimpleFrontendAgent
from .simple_database_agent import SimpleDatabaseAgent
from .simple_ops_agent import SimpleOpsAgent

# Legacy agents (in legacy folder - for reference only)
# from .legacy.backend_orchestrator import BackendOrchestratorAgent
# from .legacy.architecture_generator import ArchitectureGeneratorAgent
# from .legacy.frontend_generator import FrontendGeneratorAgent  
# from .legacy.database_generator import DatabaseGeneratorAgent
# from .legacy.integration_generator import IntegrationGeneratorAgent
# from .legacy.base_code_generator import BaseCodeGeneratorAgent

__all__ = [
    # Simplified Agents (New Architecture)
    "SimpleBackendAgent",
    "SimpleFrontendAgent", 
    "SimpleDatabaseAgent",
    "SimpleOpsAgent"
]

# SIMPLIFIED GENERATOR MAPPING (New Standard)
SIMPLIFIED_GENERATORS = {
    "backend": SimpleBackendAgent,
    "frontend": SimpleFrontendAgent,
    "database": SimpleDatabaseAgent,
    "ops": SimpleOpsAgent,
    "devops": SimpleOpsAgent,
    "testing": SimpleOpsAgent,
    "documentation": SimpleOpsAgent,
    "security": SimpleOpsAgent,
    "monitoring": SimpleOpsAgent,
    "architecture": SimpleBackendAgent,  # Route to backend
    "integration": SimpleBackendAgent    # Route to backend
}

# Default mapping (points to simplified agents)
DEFAULT_GENERATORS = SIMPLIFIED_GENERATORS

