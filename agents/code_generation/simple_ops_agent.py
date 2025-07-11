"""
Simple Ops Agent - Unified DevOps, Documentation, and Testing
Replaces: DevOpsInfrastructureAgent + DocumentationAgent + TestingQAAgent (~1580 lines total)
"""

import asyncio
import json
import os
import time
from typing import Dict, Any, List, Set
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from agents.code_generation.simple_base_agent import SimpleBaseAgent
from tools.code_execution_tool import CodeExecutionTool
from tools.code_generation_utils import parse_llm_output_into_files
from models.data_contracts import WorkItem, CodeGenerationOutput, GeneratedFile

import logging
logger = logging.getLogger(__name__)

class SimpleOpsAgent(SimpleBaseAgent):
    """
    SIMPLIFIED Ops Agent - All operational needs in one focused agent
    
    Handles:
    ✅ Docker containerization
    ✅ CI/CD pipelines  
    ✅ Basic tests (unit + integration)
    ✅ Documentation (README + API docs)
    ✅ Environment configuration
    ✅ Monitoring setup
    ✅ Security basics
    """
    
    def __init__(self, llm: BaseLanguageModel, memory, temperature: float, output_dir: str, 
                 code_execution_tool: CodeExecutionTool, **kwargs):
        super().__init__(
            llm=llm,
            memory=memory,
            temperature=temperature,
            output_dir=output_dir,
            code_execution_tool=code_execution_tool,
            agent_name="Simple Ops Agent",
            **kwargs
        )
        self._initialize_simple_prompts()
        logger.info("Simple Ops Agent initialized - unified operations generation")

    def _initialize_simple_prompts(self):
        """Enhanced prompt for comprehensive operational infrastructure."""
        self.ops_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior DevOps engineer creating complete, production-ready operational infrastructure.

            CRITICAL REQUIREMENTS:
            - Generate EXACTLY 12-16 files (substantial, functional code)
            - Each file must serve a clear purpose in the operational infrastructure
            - Include comprehensive DevOps automation
            - Follow industry best practices and security standards
            - Implement proper monitoring and observability
            
            REQUIRED OPERATIONAL COMPONENTS (generate ALL):
            1. Multi-stage Dockerfile with optimization
            2. Docker Compose for development and production
            3. CI/CD pipeline (GitHub Actions or GitLab CI)
            4. Comprehensive test suite (unit, integration, e2e)
            5. Professional README with setup instructions
            6. API documentation (OpenAPI/Swagger)
            7. Environment configuration files (.env templates)
            8. Monitoring and logging setup (Prometheus, Grafana)
            9. Security configuration (HTTPS, headers, secrets)
            10. Deployment scripts and automation
            11. Health check and liveness probes
            12. Backup and recovery procedures
            13. Performance testing and benchmarks
            14. Code quality tools (linting, formatting)
            15. Infrastructure as Code (Terraform/Kubernetes)
            16. Troubleshooting and runbook documentation
            
            Use the ### FILE: path format for each file.
            Focus on production-ready, enterprise-grade operational setup."""),
            
            ("human", """Create complete operational infrastructure for: {description}
            
            **Technical Context:**
            - Language: {language}
            - Framework: {framework}
            - Deployment: {deployment_type}
            - Required Features: {features}
            - Work Item: {work_item}
            
            **Mandatory Requirements:**
            - Generate EXACTLY 12-16 substantial files
            - Docker containerization with multi-stage builds and optimization
            - Automated CI/CD pipeline with proper testing stages
            - Comprehensive testing setup (unit, integration, performance)
            - Professional documentation with clear setup instructions
            - Environment management with secure configuration
            - Monitoring and logging with alerting capabilities
            - Security best practices and vulnerability scanning
            - Deployment automation with rollback capabilities
            - Infrastructure as Code for reproducible deployments
            - Performance optimization and scalability considerations
            - Disaster recovery and backup procedures
            - Code quality enforcement and automated checks
            - Comprehensive troubleshooting documentation
            
            Focus on creating enterprise-grade operational infrastructure.
            Each file should be production-ready with comprehensive functionality and best practices.""")
        ])

    def run(self, work_item: WorkItem, state: Dict[str, Any]) -> CodeGenerationOutput:
        """Generate complete operational setup for a work item."""
        try:
            logger.info(f"SimpleOpsAgent processing: {work_item.description}")
            
            # Extract context
            tech_stack = state.get('tech_stack_recommendation', {})
            language = tech_stack.get('backend_language', 'Python')
            framework = tech_stack.get('backend_framework', 'FastAPI')
            deployment_type = tech_stack.get('deployment', 'Docker')
            
            # Determine features from work item
            features = self._extract_features(work_item.description)
            
            # Generate code with LLM
            prompt_input = {
                "description": work_item.description,
                "language": language,
                "framework": framework,
                "deployment_type": deployment_type,
                "features": ", ".join(features),
                "work_item": f"ID: {work_item.id}, Role: {work_item.agent_role}"
            }
            
            response = self.llm.invoke(self.ops_prompt.format_messages(**prompt_input))
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parse files
            generated_files = parse_llm_output_into_files(content)
            
            # Quality validation - ensure we have comprehensive operational files
            if len(generated_files) < 10:
                logger.error(f"Insufficient operational files generated: {len(generated_files)}. Expected at least 10 substantial files.")
                return CodeGenerationOutput(
                    generated_files=[],
                    summary=f"Ops generation failed: Only {len(generated_files)} files generated, expected at least 10",
                    status="error"
                )
            
            # Validate file content quality
            validated_files = self._validate_generated_files(generated_files, language, framework, deployment_type)
            if not validated_files:
                return CodeGenerationOutput(
                    generated_files=[],
                    summary="Ops generation failed: Files did not meet quality standards",
                    status="error"
                )
            
            # Save to disk
            self._save_files(validated_files)
            
            logger.info(f"Generated {len(validated_files)} high-quality operational files")
            return CodeGenerationOutput(
                generated_files=validated_files,
                summary=f"Complete operational setup with {len(validated_files)} production-ready files",
                status="success"
            )
            
        except Exception as e:
            logger.error(f"SimpleOpsAgent failed: {e}")
            return CodeGenerationOutput(
                generated_files=[],
                summary=f"Ops generation error: {e}",
                status="error"
            )

    def _extract_features(self, description: str) -> List[str]:
        """Extract required features from work item description."""
        features = []
        desc_lower = description.lower()
        
        # Enhanced feature detection
        feature_patterns = {
            "containerization": ["docker", "container", "image", "build"],
            "cicd_pipeline": ["ci", "cd", "pipeline", "deploy", "automation", "build"],
            "testing_suite": ["test", "testing", "unit", "integration", "e2e"],
            "documentation": ["doc", "readme", "guide", "manual", "instruction"],
            "monitoring": ["monitor", "logging", "metrics", "alerts", "observability"],
            "security": ["security", "auth", "ssl", "https", "cert", "secrets"],
            "performance": ["performance", "optimization", "benchmark", "load", "stress"],
            "backup_recovery": ["backup", "restore", "recovery", "disaster"],
            "infrastructure": ["infrastructure", "terraform", "kubernetes", "cloud"],
            "networking": ["network", "dns", "load balancer", "proxy", "ingress"],
            "database_ops": ["database", "migration", "backup", "replication"],
            "secret_management": ["secret", "vault", "key", "credential", "config"],
            "scalability": ["scale", "autoscale", "cluster", "distributed"],
            "compliance": ["compliance", "audit", "governance", "policy"]
        }
        
        for feature, keywords in feature_patterns.items():
            if any(keyword in desc_lower for keyword in keywords):
                features.append(feature)
                
        return features or ["basic_ops", "containerization", "cicd_pipeline"]

    def _validate_generated_files(self, generated_files: List[GeneratedFile], language: str, framework: str, deployment_type: str) -> List[GeneratedFile]:
        """Validate generated files meet operational quality standards."""
        validated_files = []
        
        # Define validation patterns for operational files
        ops_patterns = {
            "docker": ["dockerfile", "docker-compose", "containerization"],
            "cicd": ["github", "gitlab", "jenkins", "actions", "pipeline", "workflow"],
            "tests": ["test", "spec", "pytest", "jest", "cypress"],
            "docs": ["readme", "doc", "guide", "manual", "api"],
            "config": ["config", "env", "settings", "properties"],
            "monitoring": ["prometheus", "grafana", "logging", "metrics"],
            "security": ["security", "ssl", "cert", "auth", "vault"],
            "deploy": ["deploy", "script", "automation", "terraform", "k8s"],
            "backup": ["backup", "restore", "recovery"],
            "infra": ["infrastructure", "terraform", "kubernetes", "helm"]
        }
        
        # File extension patterns
        ops_extensions = [
            ".yml", ".yaml", ".json", ".toml", ".ini",
            ".sh", ".ps1", ".bat", ".py", ".js", ".tf",
            ".md", ".txt", ".dockerfile", ".dockerignore"
        ]
        
        for file_obj in generated_files:
            try:
                content = file_obj.content if hasattr(file_obj, 'content') else file_obj.get('content', '')
                file_path = file_obj.file_path if hasattr(file_obj, 'file_path') else file_obj.get('file_path', '')
                
                # Check if file has substantial content
                if len(content.strip()) < 50:
                    logger.warning(f"Skipping file {file_path}: insufficient content")
                    continue
                
                # Check file relevance to operational tasks
                file_path_lower = file_path.lower()
                content_lower = content.lower()
                
                # Check if file is ops-related by path or extension
                is_ops_relevant = (
                    any(pattern in file_path_lower for pattern_group in ops_patterns.values() for pattern in pattern_group) or
                    any(ext in file_path_lower for ext in ops_extensions) or
                    any(keyword in file_path_lower for keyword in [".github", ".gitlab", "scripts", "deploy", "infra", "monitoring"])
                )
                
                # Check if content has operational characteristics
                has_ops_content = (
                    any(keyword in content_lower for keyword in ["version:", "image:", "command:", "script:", "pipeline:", "deploy", "build", "test"]) or
                    "#!/" in content or  # Shell scripts
                    "FROM " in content or  # Dockerfile
                    "apiVersion:" in content or  # Kubernetes
                    "terraform" in content_lower
                )
                
                # Validate content quality
                if (is_ops_relevant or has_ops_content) and len(content.strip()) > 30:
                    validated_files.append(file_obj)
                else:
                    logger.warning(f"File {file_path} did not meet ops validation criteria")
                    
            except Exception as e:
                logger.error(f"Error validating ops file: {e}")
                continue
        
        return validated_files

    # Required abstract methods
    async def arun(self, **kwargs):
        """Async wrapper."""
        work_item = kwargs.get('work_item')
        state = kwargs.get('state', {})
        if work_item and state:
            return await asyncio.to_thread(self.run, work_item, state)
        return await asyncio.to_thread(self.run, **kwargs)
    
    def get_default_response(self) -> Dict[str, Any]:
        """Get default response for error cases."""
        return {
            "generated_files": [],
            "summary": "SimpleOpsAgent encountered an error",
            "status": "error"
        }

    # Simplified overrides
    def _generate_code(self, llm: BaseLanguageModel, invoke_config: Dict, **kwargs) -> Dict[str, Any]:
        """Override base method to use our simplified approach."""
        work_item = kwargs.get('work_item')
        state = kwargs.get('state', {})
        
        if not work_item:
            return {"generated_files": [], "summary": "No work item provided", "status": "error"}
        
        # Use the main run method
        result = self.run(work_item, state)
        
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        return result 