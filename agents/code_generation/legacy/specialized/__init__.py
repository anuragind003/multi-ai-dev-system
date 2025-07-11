"""
Specialized Code Generation Agents

This module contains specialized agents for industrial-grade backend generation:

- CoreBackendAgent: Models, controllers, services, basic configuration
- DevOpsInfrastructureAgent: Docker, Kubernetes, CI/CD, performance
- SecurityComplianceAgent: Security middleware, compliance, auditing  
- TestingQAAgent: Unit, integration, performance testing
- MonitoringObservabilityAgent: Prometheus, Grafana, tracing, alerting
- DocumentationAgent: API docs, architecture, operations guides

Each agent focuses on a specific domain to enable:
- Single responsibility principle
- Parallel processing
- Independent testing
- Easy maintenance and extension
"""

__version__ = "1.0.0"
__author__ = "Backend Orchestrator System"

from .core_backend_agent import CoreBackendAgent
from .devops_infrastructure_agent import DevOpsInfrastructureAgent
from .security_compliance_agent import SecurityComplianceAgent
from .testing_qa_agent import TestingQAAgent
from .monitoring_observability_agent import MonitoringObservabilityAgent
from .documentation_agent import DocumentationAgent

__all__ = [
    "CoreBackendAgent",
    "DevOpsInfrastructureAgent", 
    "SecurityComplianceAgent",
    "TestingQAAgent",
    "MonitoringObservabilityAgent",
    "DocumentationAgent"
] 