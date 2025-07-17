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
    ✅ Testing (unit, integration, e2e, automation)
    ✅ QA processes and test frameworks
    ✅ Documentation (README, API docs, user guides)
    ✅ Technical writing and documentation systems
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
            ("system", """You are a senior DevOps engineer, QA engineer, and technical writer creating complete, production-ready operational infrastructure, testing frameworks, and comprehensive documentation.

            CRITICAL REQUIREMENTS:
            - Generate EXACTLY 12-16 files (substantial, functional code/documentation)
            - Each file must serve a clear purpose in the operational infrastructure, testing, or documentation
            - Include comprehensive DevOps automation, QA processes, and technical documentation
            - Follow industry best practices and security standards
            - Implement proper monitoring, testing, and documentation systems
            
            REQUIRED OPERATIONAL COMPONENTS (generate ALL applicable):
            
            **DevOps & Infrastructure:**
            1. Multi-stage Dockerfile with optimization
            2. Docker Compose for development and production  
            3. CI/CD pipeline (GitHub Actions or GitLab CI)
            4. Environment configuration files (.env templates)
            5. Security configuration (HTTPS, headers, secrets)
            6. Deployment scripts and automation
            7. Health check and liveness probes
            8. Backup and recovery procedures
            9. Infrastructure as Code (Terraform/Kubernetes)
            
            **QA & Testing:**
            10. Comprehensive test suite (unit, integration, e2e)
            11. Test automation frameworks (Selenium, Cypress, Pytest)
            12. Performance testing and benchmarks (JMeter, Artillery)
            13. Code quality tools (linting, formatting, coverage)
            14. Test data management and fixtures
            15. QA processes and test plans
            
            **Documentation & Technical Writing:**
            16. Professional README with setup instructions
            17. API documentation (OpenAPI/Swagger)
            18. User guides and tutorials
            19. Developer documentation and architecture guides
            20. Troubleshooting and runbook documentation
            21. Installation and deployment guides
            22. Monitoring and logging setup documentation
            
            Use the ### FILE: path format for each file.
            Focus on production-ready, enterprise-grade operational setup with comprehensive testing and documentation."""),
            
            ("human", """Create complete operational infrastructure for: {description}
            
            **Technical Context:**
            - Backend: {backend_tech}
            - Frontend: {frontend_tech}  
            - Database: {database_tech}
            - Language: {language}
            - Framework: {framework}
            - Deployment: {deployment_type}
            - Required Features: {features}
            - Work Item: {work_item}
            
            **Work Item Dependencies:**
            {dependencies}
            
            **Acceptance Criteria:**
            {acceptance_criteria}
            
            **Role Focus:**
            {role_focus}
            
            **Expected File Structure (MUST FOLLOW EXACTLY):**
            {expected_files}
            
            **CRITICAL: File Structure Requirements:**
            - You MUST create files that match the expected file structure above
            - Use the EXACT file paths and names specified
            - If Dockerfile is expected, create appropriate Dockerfile for {language}/{framework}
            - If package.json is in expected files, create Node.js compatible infrastructure
            - If requirements.txt is in expected files, create Python compatible infrastructure
            - Follow the file naming conventions shown in the expected structure
            - Ensure generated files serve the purposes implied by their paths
            
            **Mandatory Requirements:**
            - Generate files that match the expected structure above
            - Use {language} with {framework} as specified for backend
            - Ensure all acceptance criteria are met in the infrastructure
            - Consider and handle dependencies appropriately in deployment
            
            **DevOps & Infrastructure Requirements:**
            - Docker containerization with multi-stage builds and optimization
            - Automated CI/CD pipeline with proper testing stages for {language}
            - Environment management with secure configuration
            - Monitoring and logging with alerting capabilities
            - Security best practices and vulnerability scanning
            - Deployment automation with rollback capabilities
            - Infrastructure as Code for reproducible deployments
            - Performance optimization and scalability considerations
            - Disaster recovery and backup procedures
            
            **QA & Testing Requirements (if QA role):**
            - Comprehensive testing frameworks (unit, integration, e2e)
            - Test automation setup (Selenium, Cypress, Pytest for Python, Jest for Node.js)
            - Performance testing tools and benchmarks
            - Code quality enforcement and automated checks for {language}
            - Test data management and fixtures
            - QA processes and testing workflows
            - Coverage reporting and quality metrics
            
            **Documentation & Technical Writing Requirements (if technical writer role):**
            - Professional documentation with clear setup instructions
            - Comprehensive API documentation (OpenAPI/Swagger)
            - User guides and step-by-step tutorials
            - Developer documentation and architecture guides
            - Installation and deployment guides
            - Troubleshooting and runbook documentation
            - Contributing guidelines and code standards
            - Release notes and changelog templates
            
            **Role-Specific Priority Guidelines:**
            - If QA/Testing focused: Prioritize test frameworks, automation scripts, coverage tools, and quality processes
            - If Documentation focused: Prioritize comprehensive docs, user guides, API documentation, and technical writing
            - Otherwise: Balanced approach covering DevOps, testing, and documentation needs
            
            Focus on creating enterprise-grade operational infrastructure that follows the exact file structure specified and meets all acceptance criteria.
            Each file should be production-ready with comprehensive functionality and best practices for {language}/{framework}.""")
        ])

    def run(self, work_item: WorkItem, state: Dict[str, Any]) -> CodeGenerationOutput:
        """Generate complete operational setup for a work item."""
        try:
            logger.info(f"SimpleOpsAgent processing: {work_item.description}")
            
            # ENHANCED: Extract technology stack from enhanced state
            tech_stack_info = state.get('tech_stack_info', {})
            backend_tech = tech_stack_info.get('backend', 'Python with FastAPI')
            frontend_tech = tech_stack_info.get('frontend', 'JavaScript with React')
            database_tech = tech_stack_info.get('database', 'PostgreSQL')
            expected_files = tech_stack_info.get('expected_file_structure', [])
            
            # Parse backend technology for infrastructure decisions
            if 'node.js' in backend_tech.lower() or 'express' in backend_tech.lower():
                language = 'JavaScript'
                framework = 'Node.js/Express'
            elif 'python' in backend_tech.lower():
                language = 'Python'
                if 'django' in backend_tech.lower():
                    framework = 'Django'
                else:
                    framework = 'FastAPI'
            elif 'java' in backend_tech.lower():
                language = 'Java'
                framework = 'Spring Boot'
            else:
                # Fallback parsing
                parts = backend_tech.split(' with ')
                language = parts[0] if len(parts) > 0 else 'Python'
                framework = parts[1] if len(parts) > 1 else 'FastAPI'
            
            deployment_type = 'Docker'  # Default deployment
            
            logger.info(f"SimpleOpsAgent using: {language} with {framework}")
            logger.info(f"Expected files: {expected_files}")
            
            # Detect specific role focus
            agent_role = tech_stack_info.get('agent_role', '').lower()
            is_qa_focused = any(role in agent_role for role in ['qa', 'test', 'quality', 'automation_engineer'])
            is_docs_focused = any(role in agent_role for role in ['technical_writer', 'documentation', 'writer', 'content_writer', 'documentation_engineer'])
            
            logger.info(f"SimpleOpsAgent role focus - QA: {is_qa_focused}, Docs: {is_docs_focused}, Role: {agent_role}")
            
            # Determine features from work item
            features = self._extract_features(work_item.description)
            
            # Add role-specific features
            if is_qa_focused:
                features.extend(["qa_automation", "test_coverage", "performance_testing"])
            if is_docs_focused:
                features.extend(["technical_writing", "api_documentation", "user_documentation"])
            
            # Generate code with LLM - Enhanced with work item details
            dependencies = tech_stack_info.get('work_item_dependencies', [])
            acceptance_criteria = tech_stack_info.get('work_item_acceptance_criteria', [])
            
            prompt_input = {
                "description": work_item.description,
                "language": language,
                "framework": framework,
                "deployment_type": deployment_type,
                "features": ", ".join(features),
                "work_item": f"ID: {work_item.id}, Role: {work_item.agent_role}",
                "expected_files": "\n".join(expected_files) if expected_files else "No specific file structure specified",
                "backend_tech": backend_tech,
                "frontend_tech": frontend_tech,
                "database_tech": database_tech,
                "dependencies": "\n".join([f"- {dep}" for dep in dependencies]) if dependencies else "No dependencies",
                "acceptance_criteria": "\n".join([f"✓ {criteria}" for criteria in acceptance_criteria]) if acceptance_criteria else "No specific acceptance criteria",
                "role_focus": f"QA/Testing focused: {is_qa_focused}, Documentation focused: {is_docs_focused}"
            }
            
            response = self.llm.invoke(self.ops_prompt.format_messages(**prompt_input))
            raw_content = response.content if hasattr(response, 'content') else str(response)

            # Handle case where content is a list of strings/chunks
            if isinstance(raw_content, list):
                content = "".join(raw_content)
            else:
                content = str(raw_content)

            # Parse files
            generated_files = parse_llm_output_into_files(content)
            
            # ENHANCED: More flexible quality validation for operational files
            min_files_required = 1  # Accept even single files if they're meaningful
            
            if len(generated_files) < min_files_required:
                logger.warning(f"Generated {len(generated_files)} operational files. Minimum recommended: {min_files_required}")
                # Don't fail immediately - let validation decide
            else:
                logger.info(f"Generated {len(generated_files)} operational files - sufficient for deployment")
            
            # Validate file content quality
            validated_files = self._validate_generated_files(generated_files, language, framework, deployment_type)
            
            # More flexible success criteria
            if not validated_files:
                logger.error(f"No valid operational files after validation from {len(generated_files)} generated files")
                return CodeGenerationOutput(
                    generated_files=[],
                    summary=f"Ops generation failed: No valid files after validation from {len(generated_files)} candidates",
                    status="error"
                )
            elif len(validated_files) < min_files_required:
                logger.warning(f"Only {len(validated_files)} valid files generated, but proceeding as they may be sufficient")
                # Proceed anyway - some deployments might need fewer files
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
        
        # Enhanced feature detection including QA and technical writing
        feature_patterns = {
            "containerization": ["docker", "container", "image", "build"],
            "cicd_pipeline": ["ci", "cd", "pipeline", "deploy", "automation", "build"],
            "testing_suite": ["test", "testing", "unit", "integration", "e2e"],
            "qa_automation": ["qa", "quality assurance", "test automation", "test framework", "selenium", "cypress", "pytest", "jest"],
            "test_coverage": ["coverage", "test coverage", "code coverage", "quality metrics"],
            "performance_testing": ["performance test", "load test", "stress test", "benchmark", "jmeter"],
            "documentation": ["doc", "readme", "guide", "manual", "instruction"],
            "technical_writing": ["technical writing", "user guide", "tutorial", "how-to", "documentation system"],
            "api_documentation": ["api doc", "swagger", "openapi", "postman", "api guide"],
            "user_documentation": ["user manual", "user guide", "help", "support doc", "faq"],
            "developer_documentation": ["dev doc", "developer guide", "code doc", "architecture doc"],
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