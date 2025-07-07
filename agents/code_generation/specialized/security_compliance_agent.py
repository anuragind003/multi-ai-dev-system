"""
Security Compliance Agent - LLM-Powered Specialized Agent
Focuses on security and compliance using intelligent LLM reasoning.
"""

import json
import os
import time
from typing import Dict, Any, List, Optional, Set
from pathlib import Path

from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import ChatPromptTemplate

from agents.code_generation.base_code_generator import BaseCodeGeneratorAgent
from tools.code_execution_tool import CodeExecutionTool
from message_bus import MessageBus
from tools.code_generation_utils import parse_llm_output_into_files
from models.data_contracts import WorkItem, CodeGenerationOutput, GeneratedFile

import logging
logger = logging.getLogger(__name__)

class SecurityComplianceAgent(BaseCodeGeneratorAgent):
    """
    LLM-Powered Security Compliance Agent - Specialized for security and compliance
    
    Uses intelligent LLM generation for:
    - Security middleware (authentication, authorization, encryption)
    - Compliance frameworks (GDPR, SOX, PCI-DSS, HIPAA)
    - Audit logging and security monitoring
    - Security policies and configurations
    """
    
    def __init__(self, 
                 llm: BaseLanguageModel, 
                 memory, 
                 temperature: float,
                 output_dir: str, 
                 code_execution_tool: CodeExecutionTool,
                 rag_retriever: Optional[BaseRetriever] = None,
                 message_bus: Optional[MessageBus] = None):
        """Initialize LLM-Powered Security Compliance Agent."""
        
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Security Compliance Agent",
            temperature=temperature,
            output_dir=output_dir,
            code_execution_tool=code_execution_tool,
            rag_retriever=rag_retriever,
            message_bus=message_bus
        )
        
        self._initialize_security_prompts()
        logger.info("LLM-Powered Security Compliance Agent initialized")
    
    def _initialize_security_prompts(self):
        """Initialize LLM prompt templates for security and compliance generation."""
        
        self.security_generation_template = ChatPromptTemplate.from_messages([
            ("system",
             "You are an expert cybersecurity architect specializing in ENTERPRISE SECURITY "
             "and REGULATORY COMPLIANCE. You generate production-ready, security-hardened "
             "infrastructure that meets the highest industry standards for data protection, "
             "access control, and regulatory compliance.\n\n"
             
             "**SECURITY ARCHITECTURE EXPERTISE:**\n"
             "You are certified in and implement:\n"
             "- Zero Trust Architecture principles\n"
             "- Defense in Depth strategies\n"
             "- OWASP Top 10 mitigation\n"
             "- Identity and Access Management (IAM)\n"
             "- Cryptographic best practices\n"
             "- Security incident response\n"
             "- Penetration testing methodologies\n\n"
             
             "**COMPLIANCE FRAMEWORK KNOWLEDGE:**\n"
             "- GDPR (General Data Protection Regulation)\n"
             "- HIPAA (Health Insurance Portability and Accountability Act)\n"
             "- SOX (Sarbanes-Oxley Act)\n"
             "- PCI-DSS (Payment Card Industry Data Security Standard)\n"
             "- ISO 27001/27002 Information Security Management\n"
             "- NIST Cybersecurity Framework\n"
             "- SOC 2 Type II compliance\n\n"
             
             "**MANDATORY SECURITY COMPONENTS:**\n"
             "You MUST generate ALL of the following security infrastructure:\n\n"
             
             "1. **AUTHENTICATION & AUTHORIZATION:**\n"
             "   - Multi-factor authentication (MFA) implementation\n"
             "   - JWT token management with refresh mechanisms\n"
             "   - Role-Based Access Control (RBAC) system\n"
             "   - Attribute-Based Access Control (ABAC) where needed\n"
             "   - Session management with secure timeouts\n"
             "   - OAuth 2.0/OpenID Connect integration\n"
             "   - Single Sign-On (SSO) capability\n\n"
             
             "2. **ENCRYPTION & DATA PROTECTION:**\n"
             "   - End-to-end encryption implementation\n"
             "   - Data at rest encryption (AES-256)\n"
             "   - Data in transit encryption (TLS 1.3)\n"
             "   - Key management and rotation\n"
             "   - Password hashing (bcrypt/Argon2)\n"
             "   - Secure random number generation\n"
             "   - Data masking and tokenization\n\n"
             
             "3. **SECURITY MIDDLEWARE & HARDENING:**\n"
             "   - Input validation and sanitization\n"
             "   - SQL injection prevention\n"
             "   - XSS (Cross-Site Scripting) protection\n"
             "   - CSRF (Cross-Site Request Forgery) protection\n"
             "   - Rate limiting and DDoS protection\n"
             "   - Security headers (CSP, HSTS, etc.)\n"
             "   - API security and throttling\n\n"
             
             "4. **AUDIT & MONITORING:**\n"
             "   - Comprehensive audit logging\n"
             "   - Security event monitoring\n"
             "   - Intrusion detection systems\n"
             "   - Real-time security alerts\n"
             "   - Compliance reporting automation\n"
             "   - Security metrics and dashboards\n"
             "   - Incident response automation\n\n"
             
             "5. **COMPLIANCE AUTOMATION:**\n"
             "   - Automated compliance checking\n"
             "   - Data retention and purging\n"
             "   - Privacy impact assessments\n"
             "   - Consent management systems\n"
             "   - Data lineage tracking\n"
             "   - Regulatory reporting tools\n"
             "   - Compliance audit trails\n\n"
             
             "**DOMAIN-SPECIFIC SECURITY:**\n"
             "- Healthcare: HIPAA compliance, PHI protection, audit logging, access controls\n"
             "- Financial: PCI-DSS compliance, fraud detection, transaction security, SOX controls\n"
             "- E-commerce: Payment security, customer data protection, fraud prevention\n"
             "- IoT: Device security, secure communication, edge protection\n\n"
             
             "Generate enterprise-grade security infrastructure that provides comprehensive "
             "protection against modern threats while ensuring full regulatory compliance."),
            
            ("human",
             "Generate COMPREHENSIVE SECURITY AND COMPLIANCE INFRASTRUCTURE for a "
             "**{domain}** application using **{framework}** ({language}) with **{security_level}** "
             "security level and **{compliance_requirements}** compliance.\n\n"
             
             "**Project Context:**\n"
             "- Domain: {domain}\n"
             "- Language: {language}\n"
             "- Framework: {framework}\n"
             "- Security Level: {security_level}\n"
             "- Compliance Requirements: {compliance_requirements}\n"
             "- Scale: {scale}\n"
             "- Features: {features}\n\n"
             
             "**MANDATORY SECURITY FILES:**\n"
             "1. Authentication middleware and handlers\n"
             "2. Authorization and access control systems\n"
             "3. Encryption utilities and key management\n"
             "4. Security middleware (input validation, XSS, CSRF protection)\n"
             "5. Audit logging and security monitoring\n"
             "6. Compliance-specific modules for {compliance_requirements}\n"
             "7. Security configuration and policies\n"
             "8. Security testing and validation tools\n"
             "9. Incident response and alerting systems\n\n"
             
             "**COMPLIANCE-SPECIFIC REQUIREMENTS:**\n"
             "{compliance_details}\n\n"
             
             "**DOMAIN SECURITY CONSIDERATIONS:**\n"
             "{domain_security_requirements}\n\n"
             
             "**FRAMEWORK SECURITY PATTERNS:**\n"
             "{framework_security_patterns}\n\n"
             
             "Generate production-ready security infrastructure with comprehensive "
             "threat protection, regulatory compliance, and enterprise-grade monitoring. "
             "Include proper error handling, logging, and security documentation.")
        ])
        
        # New prompt for generating fallback security files
        self.fallback_security_prompt = ChatPromptTemplate.from_messages([
            ("system",
             """You are an expert cybersecurity architect. Your task is to generate basic, essential security and compliance related files as a fallback.
These files should provide a minimal, yet functional, security foundation for an application.
Generate files for authentication middleware, an authentication handler, and an audit logger.
If GDPR compliance is specified, also generate a GDPR compliance module.
Output the content of these files in the specified multi-file format.

CRITICAL OUTPUT FORMAT - FOLLOW EXACTLY:
        You MUST provide your response as a single block of text with multiple files using this EXACT format:

        ### FILE: filename.ext
        ```filetype
        // Full content of the file goes here
        // Do not include any other text or explanations outside the content
        ```

        ### FILE: another_file.ext
        ```filetype
        // Full content of the second file goes here
        ```

        IMPORTANT RULES:
        1. Start each file with exactly "### FILE: " followed by the relative file path
        2. Use ONLY "filetype" as the code block language identifier
        3. Do NOT include explanations, comments, or other text between files
        4. File paths should be relative to project root (e.g., "security/middleware/auth.py")
        5. Generate all specified files.
"""
            ),
            ("human",
             """Generate fallback security files for a **{language}** application using **{framework}** for the **{domain}** domain.
Compliance requirements: {compliance_requirements}.
Provide the files in the specified format."""
            )
        ])
    
    def generate_security_infrastructure(self, 
                                       domain: str,
                                       language: str,
                                       framework: str,
                                       security_level: str,
                                       compliance_requirements: List[str],
                                       features: Set[str],
                                       scale: str = "enterprise") -> Dict[str, Any]:
        """Generate comprehensive security infrastructure using LLM."""
        
        start_time = time.time()
        
        try:
            logger.info(f"Generating LLM-powered security infrastructure for {domain} ({security_level} security)")
            
            # Prepare intelligent security context
            compliance_details = self._get_compliance_details(compliance_requirements)
            domain_security = self._get_domain_security_requirements(domain)
            framework_patterns = self._get_framework_security_patterns(framework)
            
            # Create LLM prompt
            prompt_input = {
                "domain": domain,
                "language": language,
                "framework": framework,
                "security_level": security_level,
                "compliance_requirements": ", ".join(compliance_requirements),
                "scale": scale,
                "features": ", ".join(sorted(features)),
                "compliance_details": compliance_details,
                "domain_security_requirements": domain_security,
                "framework_security_patterns": framework_patterns
            }
            
            # Generate using LLM
            response = self.security_generation_template.invoke(prompt_input)
            
            # Parse LLM output into files
            parsed_files = parse_llm_output_into_files(
                response.content if hasattr(response, 'content') else str(response)
            )
            
            # Ensure minimum security file count
            if len(parsed_files) < 6:
                logger.warning(f"LLM generated only {len(parsed_files)} files, adding fallback security files")
                parsed_files.extend(self._create_fallback_security_files(language, framework, domain, compliance_requirements))
            
            # Save files to output directory
            saved_files = []
            for file_info in parsed_files:
                file_path = os.path.join(self.output_dir, file_info["path"])
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file_info["content"])
                
                saved_files.append({
                    "name": file_info["name"],
                    "path": file_info["path"],
                    "type": file_info.get("type", "security"),
                    "size": len(file_info["content"])
                })
            
            execution_time = time.time() - start_time
            
            logger.info(f"LLM-powered security infrastructure generated: {len(saved_files)} files in {execution_time:.1f}s")
            
            return {
                "status": "success",
                "files": saved_files,
                "execution_time": execution_time,
                "summary": {
                    "language": language,
                    "framework": framework,
                    "domain": domain,
                    "security_level": security_level,
                    "compliance": compliance_requirements,
                    "files_count": len(saved_files),
                    "components": ["auth", "encryption", "audit", "compliance"],
                    "generation_method": "llm_powered"
                }
            }
            
        except Exception as e:
            logger.error(f"LLM-powered security infrastructure generation failed: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    def _get_compliance_details(self, compliance_requirements: List[str]) -> str:
        """Get detailed compliance requirements and implementation guidelines."""
        details = []
        
        for compliance in compliance_requirements:
            if compliance == "GDPR":
                details.append(
                    "GDPR: Data protection by design, consent management, data subject rights (access, portability, erasure), "
                    "privacy impact assessments, data breach notification within 72 hours"
                )
            elif compliance == "HIPAA":
                details.append(
                    "HIPAA: PHI protection, access controls, audit trails, encryption of electronic PHI, "
                    "business associate agreements, minimum necessary standard"
                )
            elif compliance == "SOX":
                details.append(
                    "SOX: Internal controls over financial reporting, audit trails for financial data, "
                    "segregation of duties, change management controls"
                )
            elif compliance == "PCI-DSS":
                details.append(
                    "PCI-DSS: Cardholder data protection, secure payment processing, network segmentation, "
                    "regular security testing, access control measures"
                )
        
        return "\n".join(details) if details else "Standard enterprise security practices"
    
    def _get_domain_security_requirements(self, domain: str) -> str:
        """Get domain-specific security requirements."""
        requirements = {
            "Healthcare": "PHI encryption, access logging, patient consent tracking, medical device security, telehealth protection",
            "Financial": "Transaction integrity, fraud detection, customer data protection, regulatory reporting, insider threat protection",
            "E-commerce": "Payment card security, customer data protection, fraud prevention, inventory protection, order integrity",
            "IoT": "Device authentication, secure communication protocols, firmware protection, edge security, data collection privacy",
            "General": "User data protection, secure authentication, data integrity, privacy controls, access management"
        }
        return requirements.get(domain, requirements["General"])
    
    def _get_framework_security_patterns(self, framework: str) -> str:
        """Get framework-specific security implementation patterns."""
        patterns = {
            "FastAPI": "Use OAuth2 with JWT, dependency injection for auth, middleware for security headers, Pydantic for validation",
            "Django": "Use Django security middleware, authentication backends, permission classes, CSRF protection",
            "Express": "Use helmet for security headers, passport.js for authentication, express-rate-limit, cors middleware",
            "Spring Boot": "Use Spring Security, @PreAuthorize annotations, security filters, JWT authentication"
        }
        return patterns.get(framework, "Implement framework-appropriate security patterns and middleware")
    
    def _create_fallback_security_files(self, language: str, framework: str, domain: str, compliance: List[str]) -> List[Dict[str, Any]]:
        """Create minimal fallback security files if LLM generation is insufficient, using LLM for content."""
        self.log_info(f"Generating fallback security files for {domain} ({language}/{framework}) with compliance {compliance}")

        ext = "py" if language.lower() == "python" else "js"

        compliance_str = ", ".join(compliance) if compliance else "None"

        # Prepare prompt context
        prompt_context = {
            "language": language,
            "framework": framework,
            "domain": domain,
            "compliance_requirements": compliance_str
        }

        # Use LLM to generate fallback files
        response = self.fallback_security_prompt.invoke(prompt_context)
        content = response.content if hasattr(response, 'content') else str(response)

        parsed_files = parse_llm_output_into_files(content)
        return parsed_files
    
    def _generate_code(self, llm, invoke_config: Dict, **kwargs) -> Dict[str, Any]:
        """Implementation of the abstract method from base class."""
        # Extract parameters
        domain = kwargs.get('domain', 'General')
        language = kwargs.get('language', 'Python')
        framework = kwargs.get('framework', 'FastAPI')
        security_level = kwargs.get('security_level', 'medium')
        compliance_requirements = kwargs.get('compliance_requirements', [])
        features = kwargs.get('features', set())
        scale = kwargs.get('scale', 'enterprise')
        
        return self.generate_security_infrastructure(
            domain, language, framework, security_level, compliance_requirements, features, scale
        )

    def run(self, work_item: WorkItem, state: Dict[str, Any]) -> CodeGenerationOutput:
        """
        Applies security and compliance requirements to the codebase for a single work item.
        """
        logger.info(f"SecurityComplianceAgent starting work item: {work_item.id}")

        all_files = []
        for completed_item in state.get("completed_work_items", []):
            code_gen_result = completed_item.get("code_generation_result", {})
            all_files.extend(code_gen_result.get("generated_files", []))
        
        project_context_files = {f['path']: f['content'] for f in all_files}

        prompt = self._create_work_item_prompt(work_item, project_context_files, state)

        response = self.llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        
        modified_files = parse_llm_output_into_files(content)

        return CodeGenerationOutput(
            generated_files=[FileOutput(**f) for f in modified_files],
            summary=f"Applied security review for work item {work_item.id}, modifying {len(modified_files)} files."
        )

    def _create_work_item_prompt(self, work_item: WorkItem, project_files: Dict[str, str], state: Dict[str, Any]) -> str:
        
        files_to_review_str = ""
        # The work item's acceptance criteria should list the files to review/modify.
        files_to_review_paths = work_item.acceptance_criteria
        
        for path in files_to_review_paths:
            if path in project_files:
                files_to_review_str += f"### FILE: {path}\n```\n{project_files[path]}\n```\n\n"

        if not files_to_review_str:
            return "No files found to review for this security work item."

        return f"""
        You are an expert cybersecurity architect. Your task is to review and modify the provided code to meet the security requirements outlined in the work item.

        **Work Item: {work_item.id}**
        - **Description:** {work_item.description}

        **Files to Review and Modify:**
        {files_to_review_str}

        **Instructions:**
        - Review the files for security vulnerabilities related to the work item's description.
        - Modify the files to patch vulnerabilities and add the required security features.
        - Return the COMPLETE, updated content of every file you modify.
        - If you do not need to modify a file, do not include it in your output.
        - Use the multi-file output format.

        CRITICAL OUTPUT FORMAT - FOLLOW EXACTLY:
        ### FILE: path/to/modified/file.ext
        ```filetype
        // The *full*, updated content of the file goes here.
        ```
        """ 