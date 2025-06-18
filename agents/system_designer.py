import json
import copy  # Add this missing import
import logging  # Add this missing import
logger = logging.getLogger(__name__)
from tools.json_handler import JsonHandler  # Add this import for JSON handling
from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser  # Add this import
from typing import Optional, Dict, Any, List, Tuple
import re
import monitoring
from agents.base_agent import BaseAgent
from agent_temperatures import get_agent_temperature


class SystemDesignerAgent(BaseAgent):
    """
    DEPRECATED: This implementation is being replaced by SystemDesignerReActAgent.
    
    Original system designer agent that uses sequential prompt-based approach.
    Kept for compatibility and fallback purposes.
    """
    
    def __init__(self, 
                 llm: BaseLanguageModel, 
                 memory, 
                 temperature: float,  # Add explicit temperature parameter
                 rag_retriever: Optional[BaseRetriever] = None,
                 message_bus=None):
        
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="System Designer Agent",
            temperature=temperature,  # Use the passed temperature
            rag_retriever=rag_retriever
        )
        
        self.message_bus = message_bus
        
        # Set up output parser for structured output
        self.json_parser = JsonOutputParser()
        
        # Initialize prompt templates
        self._initialize_prompt_templates()
        
        # Store design stages for progressive refinement
        self.design_stages = []
        
        # Max tokens configurations for response optimization
        self.max_tokens = {
            "architecture_pattern": 3072,
            "module_structure": 4096,
            "data_model": 4096,
            "api_design": 3584,
            "security_architecture": 3072,
            "system_synthesis": 6144,
            "validation": 3072
        }
        
        # Maximum examples to include in each section
        self.max_examples = {
            "api_endpoints": 5,
            "database_tables": 8,
            "modules": 10
        }
        
        # Maximum RAG documents to retrieve per query
        self.max_rag_docs = 3
    
    def _initialize_prompt_templates(self):
        """Initialize optimized prompt templates for multi-stage design."""
        # Call parent method to get base templates
        
        
        # Get format instructions with strict JSON-only directive
        format_instructions = self.json_parser.get_format_instructions()
        strict_format_instr = "Return ONLY valid JSON with no additional text or explanations.\n" + format_instructions
        
        # 1. Optimized architecture pattern template
        self.architecture_pattern_template = ChatPromptTemplate.from_messages([
            SystemMessage(content="""
                Expert Software Architect: Select optimal architecture pattern.
                CRITICAL: Return ONLY valid JSON with no explanations outside the JSON.
                Response MUST start with '{' and end with '}'.
            """),
            HumanMessage(content="""
                BRD REQUIREMENTS:
                {brd_analysis}
                
                TECH STACK:
                {tech_stack}
                
                NON-FUNCTIONAL REQUIREMENTS:
                {non_functional_requirements}
                
                DOMAIN CHARACTERISTICS:
                {domain_characteristics}
                
                {format_instructions}
                
                Select the best architecture pattern providing:
                1. Pattern name
                2. Key components
                3. Benefits for this specific project
                4. Implementation considerations
                
                CRITICAL: Response MUST be valid JSON only, no markdown, explanations, or text outside the JSON.
            """)
        ])
        
        # Apply a much stricter format directive
        self.architecture_pattern_template = self.architecture_pattern_template.partial(
            format_instructions="""
            CRITICAL: Your entire response must be ONLY valid JSON.
            - Do not include any text, explanations or markdown outside the JSON
            - Do not include ```json or ``` markers
            - Start immediately with { and end with }
            - Use double quotes for all keys and string values
            """
        )
        
        # 2. Optimized module decomposition template
        self.module_decomposition_template = PromptTemplate(
            template="""
            Expert Software Architect for system modularization.
            
            BRD: {brd_analysis}
            TECH STACK: {tech_stack}
            ARCHITECTURE: {architecture_pattern}
            
            {format_instructions}
            
            Design modules with:
            1. Clear responsibilities
            2. Dependencies
            3. Interfaces
            4. Internal components
            
            Focus: high cohesion, loose coupling, domain alignment.
            """,
            input_variables=["brd_analysis", "tech_stack", "architecture_pattern"],
            partial_variables={"format_instructions": strict_format_instr}
        )
        
        # 3. Optimized data model template
        self.data_model_template = PromptTemplate(
            template="""
            Expert Database Architect for {database_technology} schema design.
            
            BRD: {brd_analysis}
            TECH STACK: {tech_stack}
            
            {format_instructions}
            
            Design schema with:
            1. Tables/collections with purpose
            2. Fields/attributes with types
            3. Relationships with cardinality
            4. Indexes for performance
            5. {database_technology} specific optimizations
            """,
            input_variables=["brd_analysis", "tech_stack", "database_technology"],
            partial_variables={"format_instructions": strict_format_instr}
        )
        
        # 4. Optimized API design template
        self.api_design_template = PromptTemplate(
            template="""
            Expert API Designer for RESTful, GraphQL, and RPC APIs.
            
            BRD: {brd_analysis}
            TECH STACK: {tech_stack}
            MODULES: {system_modules}
            
            {format_instructions}
            
            Design API with:
            1. API style selection
            2. Endpoints/queries
            3. Request/response formats
            4. Authentication/authorization
            5. Error handling
            6. Pagination/filtering
            7. Versioning strategy
            
            Include documentation and examples for critical endpoints.
            """,
            input_variables=["brd_analysis", "tech_stack", "system_modules"],
            partial_variables={"format_instructions": strict_format_instr}
        )
        
        # 5. Optimized security architecture template
        self.security_architecture_template = PromptTemplate(
            template="""
            Expert Security Architect for application security.
            
            BRD: {brd_analysis}
            TECH STACK: {tech_stack}
            ARCHITECTURE: {architecture_pattern}
            API DESIGN: {api_design}
            
            {format_instructions}
            
            Create security architecture with:
            1. Authentication mechanisms
            2. Authorization model
            3. Data protection
            4. Input validation
            5. OWASP Top 10 protections
            6. Component communication security
            7. Secrets management
            8. Audit logging
            
            Specify implementation approach for each measure.
            """,
            input_variables=["brd_analysis", "tech_stack", "architecture_pattern", "api_design"],
            partial_variables={"format_instructions": strict_format_instr}
        )
        
        # 6. Optimized system design synthesis template
        self.system_design_synthesis_template = PromptTemplate(
            template="""
            Expert System Architect: Synthesize components into cohesive system design.
            
            BRD: {brd_analysis}
            TECH STACK: {tech_stack}
            ARCHITECTURE: {architecture_pattern}
            MODULES: {module_structure}
            DATABASE: {database_design}
            API: {api_design}
            SECURITY: {security_architecture}
            
            {format_instructions}
            
            Synthesize design with:
            1. Integrated components
            2. Cross-cutting concerns
            3. Deployment architecture
            4. Observability
            5. Performance optimization
            6. Scalability approach
            7. File structure
            8. Integration points
            9. Design patterns
            """,
            input_variables=[
                "brd_analysis", "tech_stack", "architecture_pattern", "module_structure",
                "database_design", "api_design", "security_architecture"
            ],
            partial_variables={"format_instructions": strict_format_instr}
        )
        
        # 7. Optimized architecture validation template
        self.architecture_validation_template = PromptTemplate(
            template="""
            Expert Architecture Reviewer for risk assessment.
            
            DESIGN: {system_design}
            BRD: {brd_analysis}
            TECH STACK: {tech_stack}
            
            {format_instructions}
            
            Review architecture for:
            1. Architectural risks with impact
            2. Component inconsistencies
            3. Performance bottlenecks
            4. Scalability limitations
            5. Security vulnerabilities
            6. Deployment complexity
            7. Technology compatibility
            
            For each issue: describe problem, impact, severity, mitigation.
            """,
            input_variables=["system_design", "brd_analysis", "tech_stack"],
            partial_variables={"format_instructions": strict_format_instr}
        )
        
        # 8. Optimized domain adaptation template
        self.domain_adaptation_template = PromptTemplate(
            template="""
            Domain Architect for industry-specific adaptations.
            
            DESIGN: {system_design}
            INDUSTRY: {domain}
            REQUIREMENTS: {industry_requirements}
            
            {format_instructions}
            
            Enhance design with:
            1. Industry-specific architecture patterns
            2. Industry-specific components
            3. Regulatory compliance features
            4. Industry-specific data models
            5. Industry integrations
            6. Industry-specific security measures
            
            CRITICAL: Return ONLY valid JSON. Do not include any template variables 
            like {{task_id}} or {{domain_specific}} in your response.
            """,
            input_variables=["system_design", "domain", "industry_requirements"],
            partial_variables={"format_instructions": strict_format_instr}
        )
        
        # Set the main prompt template
        self.prompt_template = self.system_design_synthesis_template

    def run(self, brd_analysis: Dict[str, Any], tech_stack_recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create comprehensive system design with progressive refinement, validation, and domain adaptation.
        Token-optimized implementation with staged execution.
        """
        self.log_start("Starting progressive system design creation")
        self.log_info(f"Using agent default temperature: {self.default_temperature}")
        self.design_stages = []
        
        # Validate inputs
        if not brd_analysis or not isinstance(brd_analysis, dict):
            self.log_warning("Invalid BRD analysis input - using default design")
            return self.get_default_response()
        
        if not tech_stack_recommendation or not isinstance(tech_stack_recommendation, dict):
            self.log_warning("Invalid tech stack input - using default design")
            return self.get_default_response()
        
        try:
            # Create pruned version of BRD for token efficiency
            pruned_brd = self._prune_brd_for_design(brd_analysis)
            
            # STAGE 1: Architecture pattern selection
            self.log_info("Stage 1: Selecting optimal architecture pattern")
            architecture_pattern = self._select_architecture_pattern(pruned_brd, tech_stack_recommendation)
            self.design_stages.append({"stage": "architecture_pattern", "result": architecture_pattern})
            
            # STAGE 2: Module decomposition
            self.log_info("Stage 2: Designing modular structure")
            module_structure = self._design_module_structure(
                pruned_brd, 
                tech_stack_recommendation,
                architecture_pattern
            )
            self.design_stages.append({"stage": "module_structure", "result": module_structure})
            
            # STAGE 3: Data model design
            self.log_info("Stage 3: Designing data model")
            database_technology = tech_stack_recommendation.get("database", {}).get("type", "")
            database_design = self._design_data_model(
                pruned_brd,
                tech_stack_recommendation,
                database_technology
            )
            self.design_stages.append({"stage": "database_design", "result": database_design})
            
            # STAGE 4: API design with pruned inputs
            self.log_info("Stage 4: Designing API")
            pruned_modules = self._prune_modules_for_api_design(module_structure)
            api_design = self._design_api(
                pruned_brd,
                tech_stack_recommendation,
                pruned_modules
            )
            self.design_stages.append({"stage": "api_design", "result": api_design})
            
            # STAGE 5: Security architecture
            self.log_info("Stage 5: Designing security architecture")
            pruned_api = self._prune_api_for_security(api_design)
            security_architecture = self._design_security(
                pruned_brd,
                tech_stack_recommendation,
                architecture_pattern,
                pruned_api
            )
            self.design_stages.append({"stage": "security_architecture", "result": security_architecture})
            
            # STAGE 6: System design synthesis with pruned inputs
            self.log_info("Stage 6: Synthesizing complete system design")
            system_design = self._synthesize_system_design(
                pruned_brd,
                tech_stack_recommendation,
                self._extract_pattern_name(architecture_pattern),
                self._prune_for_synthesis(module_structure, "module_structure"),
                self._prune_for_synthesis(database_design, "database"),
                self._prune_for_synthesis(api_design, "api"),
                self._prune_for_synthesis(security_architecture, "security")
            )
            self.design_stages.append({"stage": "system_design", "result": system_design})
            
            # STAGE 7: Architecture validation with pruned inputs
            self.log_info("Stage 7: Validating architecture and assessing risks")
            pruned_design = self._prune_design_for_validation(system_design)
            validation_result = self._validate_architecture(
                pruned_design,
                pruned_brd,
                tech_stack_recommendation
            )
            self.design_stages.append({"stage": "validation", "result": validation_result})
            
            # STAGE 8: Domain-specific adaptation if domain information available
            domain = self._extract_domain(brd_analysis)
            if domain:
                self.log_info(f"Stage 8: Adapting design for {domain} domain")
                industry_requirements = self._extract_industry_requirements(brd_analysis)
                adapted_design = self._adapt_for_domain(
                    pruned_design,
                    domain,
                    industry_requirements
                )
                system_design = adapted_design
                self.design_stages.append({"stage": "domain_adaptation", "result": adapted_design})
            
            # Add verification and consistency checks
            verified_design = self.verify_design_consistency(system_design, tech_stack_recommendation)
            
            # Add metadata about the design process
            verified_design["design_metadata"] = {
                "design_approach": "progressive multi-stage refinement",
                "stages_completed": len(self.design_stages),
                "architecture_pattern": self._extract_pattern_name(architecture_pattern),
                "domain_specific_adaptations": bool(domain),
                "risks_identified": len(validation_result.get("risks", [])),
                "validation_score": validation_result.get("overall_score", 0)
            }
            
            # Log execution summary
            self.log_execution_summary(verified_design)
            
            return verified_design
            
        except Exception as e:
            self.log_error(f"Progressive system design generation failed: {str(e)}")
            return self.get_default_response()

    def _select_architecture_pattern(self, brd_analysis: Dict[str, Any], 
                      tech_stack_recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Select optimal architecture pattern through multi-option analysis with strict JSON enforcement."""
        try:
            # CRITICAL: Force ZERO temperature for reliable JSON generation
            binding_args = {
                "temperature": 0.0,
                "max_output_tokens": self.max_tokens["architecture_pattern"]
            }
            llm_json_strict = self.llm.bind(**binding_args)
            
            # Extract non-functional requirements and domain characteristics
            non_functional_requirements = self._extract_non_functional_requirements(brd_analysis)
            domain_characteristics = self._extract_domain_characteristics(brd_analysis)
            
            # IMPROVED: Use simplified string summary instead of complex JSON
            tech_stack_summary = self._prune_tech_stack_for_design(tech_stack_recommendation)
            brd_summary = self._summarize_brd_for_design(brd_analysis)
            
            # Create architecture pattern example for clarity
            pattern_example = """
            {
            "selected_pattern": "Microservices",
            "pattern_analysis": {
                "benefits": [
                "Independent scalability of components",
                "Technology diversity",
                "Resilience"
                ],
                "considerations": [
                "Increased operational complexity",
                "Network latency",
                "Data consistency challenges"
                ]
            },
            "pattern_components": [
                {
                "name": "API Gateway",
                "purpose": "Entry point for client requests"
                },
                {
                "name": "Service Discovery",
                "purpose": "Dynamic service registration and lookup"
                }
            ],
            "pattern_justification": "The microservices pattern aligns with the project's scalability requirements and need for independent service deployment"
            }
            """
            
            # Use the new strict JSON template approach with SIMPLIFIED INPUTS
            instructions = f"""Analyze BRD and tech stack to select optimal architecture pattern:
            
            BRD SUMMARY:
            {brd_summary}
            
            TECH STACK SUMMARY:
            {tech_stack_summary}
            
            NON-FUNCTIONAL REQUIREMENTS:
            {", ".join(non_functional_requirements.keys())}
            
            DOMAIN CHARACTERISTICS:
            {domain_characteristics}
            
            Select the best architecture pattern providing:
            1. Pattern name
            2. Key components
            3. Benefits for this specific project
            4. Implementation considerations
            """
            
            # Create strict template
            messages = self.create_strict_json_template(
                "Architecture Pattern Selection",
                instructions,
                pattern_example
            )


            # Add context for monitoring
            invoke_config = {
                "agent_context": f"{self.agent_name}:architecture_pattern_selection",
                "temperature_used": binding_args["temperature"],
                "model_name": getattr(self.llm, "model_name", "unknown")
            }
            
            # Direct LLM invocation with strict JSON template
            response = llm_json_strict.invoke(messages, config=invoke_config)
            response_text = self._extract_text_content(response)
            
            # Use robust fallbacks for parsing
            result = self._parse_json_with_robust_fallbacks(
                response_text,
                default_response={
                    "selected_pattern": tech_stack_recommendation.get("architecture_pattern", "Layered Architecture"),
                    "pattern_justification": "Default selection due to JSON parsing error"
                }
            )
            
            # Extract the selected pattern for logging
            selected_pattern = self._extract_pattern_name(result)
            self.log_info(f"Selected architecture pattern: {selected_pattern}")
            
            return result
            
        except Exception as e:
            self.log_warning(f"Architecture pattern selection failed: {e}")
            # Return minimal structure with default pattern
            return {
                "selected_pattern": tech_stack_recommendation.get("architecture_pattern", "Layered Architecture"),
                "pattern_analysis": "Pattern selection failed, using recommendation from tech stack",
                "pattern_justification": "Default selection due to analysis error"
            }
    
    def _design_module_structure(self, brd_analysis: Dict[str, Any],
                           tech_stack_recommendation: Dict[str, Any],
                           architecture_pattern: Dict[str, Any]) -> Dict[str, Any]:
        """Design modular structure based on architecture pattern with adaptive retries."""
        # IMPROVED: Use simplified string summaries
        brd_summary = self._summarize_brd_for_design(brd_analysis)
        tech_stack_summary = self._prune_tech_stack_for_design(tech_stack_recommendation)
        pattern_name = self._extract_pattern_name(architecture_pattern)
        
        # Create modules example for clarity
        modules_example = """
        {
        "modules": [
            {
            "name": "User Authentication Module",
            "responsibility": "Handle user identity and access management",
            "interfaces": ["REST API", "Internal Service API"],
            "components": ["Login Service", "Registration Service", "Token Service"]
            },
            {
            "name": "Data Management Module",
            "responsibility": "Manage core data operations and storage",
            "interfaces": ["Internal Service API", "Database Connector"],
            "components": ["Data Service", "Query Handler", "Cache Manager"]
            }
        ],
        "communication_patterns": ["HTTP/REST", "Dependency Injection"],
        "file_organization": {
            "type": "Feature-based",
            "structure": "Each module organized as separate directory with component subdirectories"
        }
        }
        """
        
        # Create base instructions
        base_instructions = f"""Design module structure based on architecture pattern:
        
        BRD SUMMARY:
        {brd_summary}
        
        TECH STACK:
        {tech_stack_summary}
        
        ARCHITECTURE PATTERN:
        {pattern_name}
        
        Design modules with:
        1. Clear responsibilities
        2. Dependencies
        3. Interfaces
        4. Internal components
        
        Focus: high cohesion, loose coupling, domain alignment.
        """
        
        # Store prompt for potential escalation
        self.last_json_prompt = base_instructions
        
        # Import and use JsonHandler
        from multi_ai_dev_system.tools.json_handler import JsonHandler
        handler = JsonHandler()
        
        # Use the adaptive retry mechanism
        result = handler.retry_json_generation_with_adaptive_prompts(
            llm=self.llm,
            base_instructions=base_instructions,
            example_json=modules_example,
            stage_name="Module Structure Design", 
            max_attempts=3,
            default_response=self._get_default_module_structure(),
            max_tokens=self.max_tokens["module_structure"]
        )
        
        return result
    
    def _design_data_model(self, brd_analysis: Dict[str, Any],
                 tech_stack_recommendation: Dict[str, Any],
                 database_technology: str) -> Dict[str, Any]:
        """Design database schema optimized for selected database technology with strict JSON enforcement."""
        try:
            # CRITICAL: Force ZERO temperature for reliable JSON output
            binding_args = {
                "temperature": 0.0,  # Changed from 0.1 to 0.0 for deterministic JSON
                "max_output_tokens": self.max_tokens["data_model"]
            }
            llm_json_strict = self.llm.bind(**binding_args)
            
            # Add context for monitoring
            invoke_config = {
                "agent_context": f"{self.agent_name}:data_model_design",
                "temperature_used": binding_args["temperature"],
                "model_name": getattr(self.llm, "model_name", "unknown")
            }
            
            # Get RAG context for database schema design if available
            db_context = ""
            if self.rag_retriever:
                query = f"database schema design best practices for {database_technology}"
                db_context = self._get_optimized_rag_context(query)
            
            # Create data model example for clarity
            data_model_example = """
            {
            "schema_type": "Relational Database Schema",
            "tables": [
                {
                "name": "users",
                "purpose": "Store user account information",
                "fields": [
                    {"name": "id", "type": "UUID", "description": "Primary key", "constraints": ["PRIMARY KEY"]},
                    {"name": "username", "type": "VARCHAR(255)", "description": "User login name", "constraints": ["UNIQUE", "NOT NULL"]}
                ],
                "relationships": [
                    {"related_to": "user_profiles", "type": "one-to-one", "via": "id"}
                ],
                "indexes": ["username", "email"]
                }
            ]
            }
            """
            
            # Create strict template with instructions
            pruned_brd = self._extract_data_requirements(brd_analysis)
            pruned_tech = {
                "database": tech_stack_recommendation.get("database", {}),
                "backend": {"language": tech_stack_recommendation.get("backend", {}).get("language", "")}
            }
            
            instructions = f"""Design database schema optimized for {database_technology}:
            
            BRD REQUIREMENTS:
            {json.dumps(pruned_brd, indent=2)}
            
            TECH STACK:
            {json.dumps(pruned_tech, indent=2)}
            
            RAG CONTEXT:
            {db_context[:1000] if db_context else "No additional context available"}
            
            Design schema with:
            1. Tables/collections with purpose
            2. Fields/attributes with types
            3. Relationships with cardinality
            4. Indexes for performance
            5. {database_technology} specific optimizations
            """
            
            # Create strict template
            messages = self.create_strict_json_template(
                "Database Schema Design",
                instructions,
                data_model_example
            )
            
            # Direct invocation with strict JSON template
            response = llm_json_strict.invoke(messages, config=invoke_config)
            response_text = self._extract_text_content(response)
            # Parse with robust fallbacks
            result = self._parse_json_with_robust_fallbacks(
                response_text,
                default_response=self._get_default_database_design(database_technology)
            )
            
            table_count = len(result.get("tables", []))
            self.log_info(f"Designed data model with {table_count} tables/collections")
            
            return result
            
        except Exception as e:
            self.log_warning(f"Data model design failed: {e}")
            return self._get_default_database_design(database_technology)
    
    def _design_api(self, brd_analysis: Dict[str, Any],
           tech_stack_recommendation: Dict[str, Any],
           system_modules: Dict[str, Any]) -> Dict[str, Any]:
        """Design API based on system modules and requirements."""
        try:
            # Lower temperature for precise API design using binding_args
            binding_args = {
                "temperature": 0.1,  # Lowest temperature for precise API design
                "max_output_tokens": self.max_tokens["api_design"]
            }
            llm_with_temp = self.llm.bind(**binding_args)
            
            # Add context for monitoring
            invoke_config = {
                "agent_context": f"{self.agent_name}:api_design",
                "temperature_used": binding_args["temperature"],
                "model_name": getattr(self.llm, "model_name", "unknown")
            }
            
            # Get RAG context for API design patterns if available
            api_context = ""
            if self.rag_retriever:
                api_style = tech_stack_recommendation.get("api_style", "REST")
                query = f"{api_style} API design best practices"
                api_context = self._get_optimized_rag_context(query)
            
            # Execute API design with pruned inputs
            pruned_brd = self._extract_api_requirements(brd_analysis)
            pruned_tech = {
                "backend": tech_stack_recommendation.get("backend", {}),
                "api_style": tech_stack_recommendation.get("api_style", "REST")
            }
            
            # REPLACE LangChain chain with JsonHandler strict template pattern
            from multi_ai_dev_system.tools.json_handler import JsonHandler
            
            api_example = """
            {
            "style": "REST",
            "base_url": "/api/v1",
            "authentication": "JWT",
            "endpoints": [
                {
                "method": "GET",
                "path": "/users",
                "purpose": "Get all users",
                "authentication_required": true
                }
            ]
            }
            """
            
            instructions = f"""Design API based on system modules:
            
            BRD ANALYSIS:
            {json.dumps(pruned_brd, indent=2)}
            
            TECH STACK:
            {json.dumps(pruned_tech, indent=2)}
            
            SYSTEM MODULES:
            {json.dumps(system_modules, indent=2)}
            
            Design API with:
            1. API style selection
            2. Endpoints/queries
            3. Request/response formats
            4. Authentication/authorization
            5. Error handling
            6. Pagination/filtering
            7. Versioning strategy
            """
            
            template = self.create_strict_json_template(
                "API Design",
                instructions,
                api_example
            )
            
            response = llm_with_temp.invoke(template, config=invoke_config)
            response_text = self._extract_text_content(response)
            # Use the super() implementation of parse_json_with_error_tracking
            result = self._parse_json_with_robust_fallbacks(
                response_text,
                default_response=self._get_default_api_design()
            )
            
            # Limit the number of endpoint examples
            if "endpoints" in result and len(result["endpoints"]) > self.max_examples["api_endpoints"]:
                result["endpoints"] = result["endpoints"][:self.max_examples["api_endpoints"]]
                result["endpoints"].append({
                    "note": f"Additional endpoints truncated to save tokens. Full API has more endpoints."
                })
            
            endpoint_count = len(result.get("endpoints", []))
            self.log_info(f"Designed API with {endpoint_count} endpoints")
            
            return result
            
        except Exception as e:
            self.log_warning(f"API design failed: {e}")
            return self._get_default_api_design()
    
    def _design_security(self, brd_analysis: Dict[str, Any],
                   tech_stack_recommendation: Dict[str, Any],
                   architecture_pattern: Dict[str, Any],
                   api_design: Dict[str, Any]) -> Dict[str, Any]:
        """Design security architecture with strict JSON enforcement."""
        try:
            # CRITICAL: Force ZERO temperature for reliable JSON output
            binding_args = {
                "temperature": 0.0,  # Changed from 0.1 to 0.0 for deterministic JSON
                "max_output_tokens": self.max_tokens["security_architecture"]
            }
            llm_json_strict = self.llm.bind(**binding_args)
            
            # Get RAG context for security best practices if available
            security_context = ""
            if self.rag_retriever:
                pattern = self._extract_pattern_name(architecture_pattern)
                query = f"security best practices for {pattern} architecture"
                security_context = self._get_optimized_rag_context(query)
            
            # Extract pattern from architecture recommendation
            pattern_name = self._extract_pattern_name(architecture_pattern)
            
            # Create security example for clarity
            security_example = """
            {
            "authentication_method": "JWT with OAuth 2.0 flows",
            "authorization_strategy": "Role-Based Access Control (RBAC)",
            "data_encryption": {
                "in_transit": "TLS 1.3",
                "at_rest": "AES-256"
            },
            "security_measures": [
                {
                "category": "Authentication",
                "implementation": "JWT token-based authentication with refresh tokens",
                "mitigation": "Prevents unauthorized access to protected resources"
                }
            ]
            }
            """
            
            # Execute security design with strict JSON template
            pruned_brd = self._extract_security_requirements(brd_analysis)
            pruned_tech = {
                "backend": tech_stack_recommendation.get("backend", {}),
                "security": tech_stack_recommendation.get("security", {})
            }
            
            # Create instructions for security design
            instructions = f"""Design security architecture for system:
            
            BRD REQUIREMENTS:
            {json.dumps(pruned_brd, indent=2)}
            
            TECH STACK:
            {json.dumps(pruned_tech, indent=2)}
            
            ARCHITECTURE PATTERN:
            {pattern_name}
            
            API DESIGN:
            {json.dumps(api_design, indent=2)}
            
            RAG CONTEXT:
            {security_context[:1000] if security_context else "No additional context available"}
            
            Create security architecture with:
            1. Authentication mechanisms
            2. Authorization model
            3. Data protection
            4. Input validation
            5. OWASP Top 10 protections
            6. Component communication security
            7. Secrets management
            8. Audit logging
            
            Specify implementation approach for each measure.
            """
            
            # Create strict template
            messages = self.create_strict_json_template(
                "Security Architecture Design",
                instructions,
                security_example
            )
            
            # Direct invocation with strict JSON template
            invoke_config = {
                "agent_context": f"{self.agent_name}:security_architecture_design",
                "temperature_used": binding_args["temperature"],
                "model_name": getattr(self.llm, "model_name", "unknown")
            }
            
            response = llm_json_strict.invoke(messages, config=invoke_config)
            response_text = self._extract_text_content(response)
            # Parse with robust fallbacks
            result = self._parse_json_with_robust_fallbacks(
                response_text,
                default_response=self._get_default_security_design()
            )
            
            measure_count = len(result.get("security_measures", []))
            self.log_info(f"Designed security architecture with {measure_count} security measures")
            
            return result
            
        except Exception as e:
            self.log_warning(f"Security design failed: {e}")
            return self._get_default_security_design()
    
    def _synthesize_system_design(self, brd_analysis: Dict[str, Any],
                            tech_stack_recommendation: Dict[str, Any],
                            architecture_pattern: str,
                            module_structure: Dict[str, Any],
                            database_design: Dict[str, Any],
                            api_design: Dict[str, Any],
                            security_architecture: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize complete system design with strict JSON enforcement."""
        try:
            # CRITICAL: Force ZERO temperature for reliable JSON output
            binding_args = {
                "temperature": 0.0,
                "max_output_tokens": self.max_tokens["system_synthesis"]
            }
            llm_json_strict = self.llm.bind(**binding_args)
            
            # IMPROVED: Use simplified string summaries for all inputs
            brd_summary = self._summarize_brd_for_design(brd_analysis)
            tech_stack_summary = self._prune_tech_stack_for_design(tech_stack_recommendation)
            modules_summary = self._summarize_modules(module_structure)
            database_summary = self._summarize_database(database_design)
            api_summary = self._summarize_api(api_design)
            security_summary = self._summarize_security(security_architecture)
            
            # Create synthesis example for clarity
            synthesis_example = """
            {
            "architecture_overview": {
                "pattern": "Microservices",
                "description": "Distributed system with independent services"
            },
            "main_modules": [
                {"name": "User Service", "responsibility": "User management"}
            ],
            "integration_points": [
                {"source": "API Gateway", "destination": "User Service", "protocol": "REST"}
            ],
            "deployment_architecture": {
                "containerization": {"approach": "Docker with Kubernetes"},
                "scalability": {"approach": "Horizontal scaling"}
            }
            }
            """
            
            # Execute system design synthesis with SIMPLIFIED INPUTS
            instructions = f"""Synthesize complete system design from components:
            
            BRD SUMMARY:
            {brd_summary}
            
            TECH STACK:
            {tech_stack_summary}
            
            ARCHITECTURE PATTERN:
            {architecture_pattern}
            
            MODULE STRUCTURE:
            {modules_summary}
            
            DATABASE DESIGN:
            {database_summary}
            
            API DESIGN:
            {api_summary}
            
            SECURITY ARCHITECTURE:
            {security_summary}
            
            Synthesize design with:
            1. Integrated components
            2. Cross-cutting concerns
            3. Deployment architecture
            4. Observability
            5. Performance optimization
            6. Scalability approach
            7. File structure
            8. Integration points
            9. Design patterns
            """
        
        # Rest of the method remains the same...
        
            # Create strict template
            messages = self.create_strict_json_template(
                "System Design Synthesis",
                instructions,
                synthesis_example
            )
            
            # Direct invocation with strict JSON template
            invoke_config = {
                "agent_context": f"{self.agent_name}:system_design_synthesis",
                "temperature_used": binding_args["temperature"],
                "model_name": getattr(self.llm, "model_name", "unknown")
            }
            
            response = llm_json_strict.invoke(messages, config=invoke_config)
            response_text = self._extract_text_content(response)
            # Parse with robust fallbacks
            result = self._parse_json_with_robust_fallbacks(
                response_text,
                default_response=self._manual_design_integration(
                    {"selected_pattern": architecture_pattern}, module_structure, 
                    database_design, api_design, security_architecture
                )
            )
            
            self.log_info("Synthesized complete system design")
            
            return result
        
        except Exception as e:
            self.log_warning(f"System design synthesis failed: {e}")
            # Integrate components manually as fallback
            return self._manual_design_integration(
                {"selected_pattern": architecture_pattern}, 
                module_structure, database_design, 
                api_design, security_architecture
            )
    
    def _validate_architecture(self, system_design: Dict[str, Any],
                         brd_analysis: Dict[str, Any],
                         tech_stack_recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Validate architecture and identify risks with strict JSON enforcement."""
        try:
            # CRITICAL: Force ZERO temperature for reliable JSON output
            binding_args = {
                "temperature": 0.0,  # Changed from 0.15 to 0.0 for deterministic JSON
                "max_output_tokens": self.max_tokens["validation"]
            }
            llm_json_strict = self.llm.bind(**binding_args)
            
            # Create validation example for clarity
            validation_example = """
            {
            "risks": [
                {
                "description": "Database connection pooling not configured optimally",
                "impact": "May cause performance bottlenecks under load",
                "severity": "Medium",
                "mitigation": "Implement connection pooling with size limits and timeouts"
                }
            ],
            "inconsistencies": [
                {
                "description": "API authentication doesn't align with security requirements",
                "components": ["API Design", "Security Architecture"]
                }
            ],
            "overall_score": 7
            }
            """
            
            # Execute architecture validation with strict JSON template
            pruned_brd = self._extract_core_summary(brd_analysis)
            pruned_tech = self._extract_core_summary(tech_stack_recommendation)
            
            # Create instructions for architecture validation
            instructions = f"""Validate architecture and identify risks:
            
            SYSTEM DESIGN:
            {json.dumps(system_design, indent=2)}
            
            BRD ANALYSIS:
            {json.dumps(pruned_brd, indent=2)}
            
            TECH STACK:
            {json.dumps(pruned_tech, indent=2)}
            
            Review architecture for:
            1. Architectural risks with impact
            2. Component inconsistencies
            3. Performance bottlenecks
            4. Scalability limitations
            5. Security vulnerabilities
            6. Deployment complexity
            7. Technology compatibility
            
            For each issue: describe problem, impact, severity, mitigation.
            """
            
            # Create strict template
            messages = self.create_strict_json_template(
                "Architecture Validation",
                instructions,
                validation_example
            )
            
            # Direct invocation with strict JSON template
            invoke_config = {
                "agent_context": f"{self.agent_name}:architecture_validation",
                "temperature_used": binding_args["temperature"],
                "model_name": getattr(self.llm, "model_name", "unknown")
            }
            
            response = llm_json_strict.invoke(messages, config=invoke_config)
            response_text = self._extract_text_content(response)
            # Parse with robust fallbacks
            result = self._parse_json_with_robust_fallbacks(
                response_text,
                default_response={
                    "risks": [
                        {
                            "description": "Validation failed - architecture may have undetected risks",
                            "impact": "Potential implementation issues or suboptimal design choices",
                            "severity": "Medium",
                            "mitigation": "Conduct manual architecture review before implementation"
                        }
                    ],
                    "inconsistencies": [],
                    "improvement_opportunities": [],
                    "overall_score": 5
                }
            )
            
            risk_count = len(result.get("risks", []))
            
            high_risks = sum(1 for r in result.get("risks", []) 
                        if isinstance(r, dict) and r.get("severity", "").lower() == "high")
            
            self.log_info(f"Identified {risk_count} architectural risks ({high_risks} high severity)")
            
            return result
            
        except Exception as e:
            self.log_warning(f"Architecture validation failed: {e}")
            return {
                "risks": [
                    {
                        "description": "Validation failed - architecture may have undetected risks",
                        "impact": "Potential implementation issues or suboptimal design choices",
                        "severity": "Medium",
                        "mitigation": "Conduct manual architecture review before implementation"
                    }
                ],
                "inconsistencies": [],
                "improvement_opportunities": [],
                "overall_score": 5
            }
    
    def _adapt_for_domain(self, system_design: Dict[str, Any],
                domain: str,
                industry_requirements: str) -> Dict[str, Any]:
        """Adapt system design for specific industry domain with strict JSON enforcement."""
        try:
            # CRITICAL: Force ZERO temperature for reliable JSON output
            binding_args = {
                "temperature": 0.0,  # Changed from 0.3 to 0.0 for deterministic JSON
                "max_output_tokens": self.max_tokens.get("domain_adaptation", 4096)
            }
            llm_json_strict = self.llm.bind(**binding_args)
            
            # Add context for monitoring
            invoke_config = {
                "agent_context": f"{self.agent_name}:domain_adaptation",
                "temperature_used": binding_args["temperature"],
                "model_name": getattr(self.llm, "model_name", "unknown"),
                "domain": domain
            }
            
            # Get RAG context for domain-specific patterns if available
            domain_context = ""
            if self.rag_retriever:
                query = f"architecture patterns for {domain} industry applications"
                domain_context = self._get_optimized_rag_context(query)
            
            # Create domain adaptation example for clarity
            adaptation_example = """
            {
            "domain_adaptations": [
                {
                "component": "Data Model",
                "adaptation": "Added HIPAA-compliant audit logging",
                "rationale": "Healthcare domain requires comprehensive audit trails"
                }
            ],
            "compliance_features": [
                {
                "requirement": "Data retention policy",
                "implementation": "Time-based data archiving rules"
                }
            ],
            "industry_specific_components": [
                {
                "name": "Regulatory Reporting Module",
                "purpose": "Generate compliance reports"
                }
            ]
            }
            """
            # FIXED: Use concrete values instead of template variables for domain-specific strings
            domain_specific_instructions = f"""Adapt system design for the {domain} industry sector:

SYSTEM DESIGN:
{json.dumps(pruned_design, indent=2)}

INDUSTRY SECTOR:
{domain}

INDUSTRY REQUIREMENTS:
{industry_requirements}

RAG CONTEXT:
{domain_context[:1000] if domain_context else "No additional context available"}

Enhance the design with these industry-specific additions:
- Architecture patterns appropriate for {domain}
- Components needed in {domain} applications
- Regulatory compliance required in {domain}
- Data models common in {domain}
- Integrations typically needed in {domain}
- Security measures important in {domain}

CRITICAL: DO NOT include any template variables or placeholders in your response.
Your response must be valid JSON only, with no template variables like {{task_id}}.
"""
            
            # Execute domain adaptation with strict JSON template
            pruned_design = self._prune_design_for_domain_adaptation(system_design)
            
            # Create instructions for domain adaptation
            instructions = f"""Adapt system design for {domain} industry:
            
            SYSTEM DESIGN:
            {json.dumps(pruned_design, indent=2)}
            
            DOMAIN:
            {domain}
            
            INDUSTRY REQUIREMENTS:
            {industry_requirements}
            
            RAG CONTEXT:
            {domain_context[:1000] if domain_context else "No additional context available"}
            {domain_specific_instructions}
            """
            
            
            
            # Create strict template
            messages = self.create_strict_json_template(
                f"{domain.title()} Domain Adaptation",
                instructions,
                adaptation_example
            )
            
            # Direct invocation with strict JSON template
            response = llm_json_strict.invoke(messages, config=invoke_config)
            response_text = self._extract_text_content(response)
             # ADDED: Check for template variables before parsing
            if "{" in response_text and any(var in response_text for var in [
                "{task_id", "{domain_", "{extracted_", "{system_", "{industry_"
            ]):
                self.log_warning("Detected template variable leakage in domain adaptation - using fallback")
                return system_design
            # Parse with robust fallbacks
            result = self._parse_json_with_robust_fallbacks(
                response_text,
                default_response={
                    "domain_adaptations": [
                        {
                            "component": "System Design",
                            "adaptation": f"Default {domain} adaptations",
                            "rationale": "JSON parsing error occurred"
                        }
                    ]
                }
            )
            
            self.log_info(f"Adapted system design for {domain} industry")
            
            # Merge adaptations with original design
            adapted_design = system_design.copy()
            
            # Update sections that were adapted
            for key, value in result.items():
                if key in adapted_design and value:
                    adapted_design[key] = value
            
            # Record domain adaptation
            adapted_design["domain_adaptations"] = result.get("domain_adaptations", [])
            
            return adapted_design
            
        except Exception as e:
            self.log_warning(f"Domain adaptation failed: {e}")
            return system_design

    # NEW HELPER METHODS FOR TOKEN OPTIMIZATION

    def _prune_brd_for_design(self, brd_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create a pruned version of BRD for token efficiency in design phases."""
        pruned = {
            "project_name": brd_analysis.get("project_name", ""),
            "project_summary": brd_analysis.get("project_summary", ""),
            "project_goals": brd_analysis.get("project_goals", []),
        }
        
        # Include only essential requirements
        if "requirements" in brd_analysis:
            requirements = brd_analysis["requirements"]
            # Take maximum 15 requirements or all if fewer
            max_reqs = min(len(requirements), 15)
            pruned["requirements"] = requirements[:max_reqs]
            if len(requirements) > max_reqs:
                pruned["requirements"].append({
                    "id": "additional",
                    "title": "Additional Requirements",
                    "description": f"Plus {len(requirements) - max_reqs} more requirements (truncated to save tokens)"
                })
        
        # Include key information categories
        for key in ["constraints", "assumptions", "domain_specific_details"]:
            if key in brd_analysis:
                pruned[key] = brd_analysis[key]
        
        return pruned
    
    def _extract_core_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract core summary from comprehensive data objects."""
        if not data or not isinstance(data, dict):
            return {}
        
        summary = {}
        
        # Process top-level key-value pairs
        for key, value in data.items():
            if isinstance(value, (str, bool, int, float)):
                summary[key] = value
            elif isinstance(value, list) and len(value) > 0:
                # Include only first 3 items from lists to save tokens
                summary[key] = value[:min(3, len(value))]
                if len(value) > 3:
                    summary[key].append(f"...{len(value) - 3} more items")
            elif isinstance(value, dict):
                # Include only key names from nested dictionaries
                summary[key] = {k: "..." for k in value.keys()}
        
        return summary
    
    def _extract_pattern_name(self, architecture_pattern: Dict[str, Any]) -> str:
        """Extract pattern name from architecture pattern object."""
        if not architecture_pattern:
            return "Layered Architecture"
            
        pattern = architecture_pattern.get("selected_pattern")
        if not pattern and "recommendation" in architecture_pattern:
            pattern = architecture_pattern.get("recommendation", {}).get("pattern")
        
        return pattern or "Layered Architecture"
    
    def _extract_data_requirements(self, brd_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data-related requirements for database design."""
        data_requirements = {
            "project_name": brd_analysis.get("project_name", ""),
            "project_summary": brd_analysis.get("project_summary", ""),
        }
        
        # Look for data-specific sections
        if "data_requirements" in brd_analysis:
            data_requirements["data_requirements"] = brd_analysis["data_requirements"]
        
        # Filter requirements related to data
        data_related_reqs = []
        keywords = ["data", "database", "entity", "storage", "record", "table", "schema"]
        
        if "requirements" in brd_analysis:
            for req in brd_analysis["requirements"]:
                description = req.get("description", "").lower()
                title = req.get("title", "").lower()
                
                if any(kw in description or kw in title for kw in keywords):
                    data_related_reqs.append(req)
        
        data_requirements["data_related_requirements"] = data_related_reqs
        
        return data_requirements
    
    def _extract_api_requirements(self, brd_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract API-related requirements for API design."""
        api_requirements = {
            "project_name": brd_analysis.get("project_name", ""),
            "project_summary": brd_analysis.get("project_summary", ""),
        }
        
        # Look for API-specific sections
        if "api_requirements" in brd_analysis:
            api_requirements["api_requirements"] = brd_analysis["api_requirements"]
        
        # Filter requirements related to APIs
        api_related_reqs = []
        keywords = ["api", "endpoint", "interface", "service", "rest", "graphql", "request", "response"]
        
        if "requirements" in brd_analysis:
            for req in brd_analysis["requirements"]:
                description = req.get("description", "").lower()
                title = req.get("title", "").lower()
                
                if any(kw in description or kw in title for kw in keywords):
                    api_related_reqs.append(req)
        
        api_requirements["api_related_requirements"] = api_related_reqs
        
        return api_requirements
    
    def _extract_security_requirements(self, brd_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract security-related requirements for security design."""
        security_requirements = {
            "project_name": brd_analysis.get("project_name", ""),
            "project_summary": brd_analysis.get("project_summary", ""),
        }
        
        # Filter requirements related to security
        security_related_reqs = []
        keywords = ["security", "authentication", "authorization", "privacy", "encrypt", 
                  "confidential", "compliance", "access control", "role", "permission"]
        
        if "requirements" in brd_analysis:
            for req in brd_analysis["requirements"]:
                description = req.get("description", "").lower()
                title = req.get("title", "").lower()
                
                if any(kw in description or kw in title for kw in keywords):
                    security_related_reqs.append(req)
        
        security_requirements["security_related_requirements"] = security_related_reqs
        
        return security_requirements
    
    def _prune_modules_for_api_design(self, module_structure: Dict[str, Any]) -> Dict[str, Any]:
        """Prune module structure for API design to reduce tokens."""
        if not module_structure or "modules" not in module_structure:
            return module_structure
        
        pruned_modules = {"modules": []}
        
        # Include only name, interfaces and responsibilities
        for module in module_structure["modules"]:
            pruned_module = {
                "name": module.get("name", ""),
                "interfaces": module.get("interfaces", [])
            }
            if "responsibility" in module:
                pruned_module["responsibility"] = module["responsibility"]
            
            pruned_modules["modules"].append(pruned_module)
        
        if "communication_patterns" in module_structure:
            pruned_modules["communication_patterns"] = module_structure["communication_patterns"]
            
        return pruned_modules
    
    def _prune_api_for_security(self, api_design: Dict[str, Any]) -> Dict[str, Any]:
        """Prune API design for security architecture to reduce tokens."""
        if not api_design:
            return {}
        
        pruned_api = {
            "style": api_design.get("style", ""),
            "authentication": api_design.get("authentication", ""),
            "base_url": api_design.get("base_url", "")
        }
        
        # Include only security-relevant endpoint details
        if "endpoints" in api_design:
            security_endpoints = []
            security_keywords = ["login", "auth", "user", "admin", "profile", "password", "secure", "token"]
            
            # Include only security-related endpoints
            for endpoint in api_design["endpoints"][:min(5, len(api_design["endpoints"]))]:
                path = endpoint.get("path", "").lower()
                purpose = endpoint.get("purpose", "").lower()
                
                if any(kw in path or kw in purpose for kw in security_keywords):
                    # Include only security-relevant fields
                    security_endpoints.append({
                        "method": endpoint.get("method", ""),
                        "path": path,
                        "purpose": purpose,
                        "authentication_required": endpoint.get("authentication_required", False)
                    })
            
            pruned_api["security_endpoints"] = security_endpoints
            
        return pruned_api
    
    def _prune_for_synthesis(self, component: Dict[str, Any], component_type: str) -> Dict[str, Any]:
        """Prune component for system design synthesis to reduce tokens."""
        if not component:
            return {}
        
        # Apply different pruning strategies based on component type
        if component_type == "module_structure":
            return self._prune_modules_for_synthesis(component)
        elif component_type == "database":
            return self._prune_database_for_synthesis(component)
        elif component_type == "api":
            return self._prune_api_for_synthesis(component)
        elif component_type == "security":
            return self._prune_security_for_synthesis(component)
        else:
            return component
    
    def _prune_modules_for_synthesis(self, modules: Dict[str, Any]) -> Dict[str, Any]:
        """Prune module structure for synthesis."""
        if not modules or "modules" not in modules:
            return modules
            
        pruned = {"modules": []}
        
        # Take only core module information
        for i, module in enumerate(modules["modules"]):
            # Include full details for first few modules
            if i < min(5, len(modules["modules"])):
                pruned["modules"].append(module)
            else:
                # For remaining modules, include only core information
                pruned["modules"].append({
                    "name": module.get("name", ""),
                    "responsibility": module.get("responsibility", "")
                })
                
        # Include communication patterns
        if "communication_patterns" in modules:
            pruned["communication_patterns"] = modules["communication_patterns"]
            
        return pruned
    
    def _prune_database_for_synthesis(self, database: Dict[str, Any]) -> Dict[str, Any]:
        """Prune database design for synthesis."""
        if not database:
            return {}
            
        pruned = {
            "schema_type": database.get("schema_type", "")
        }
        
        # Include tables/collections with limited fields
        if "tables" in database:
            tables = database["tables"]
            pruned_tables = []
            
            for i, table in enumerate(tables):
                if i < self.max_examples["database_tables"]:
                    # For each table, include only core information
                    pruned_table = {
                        "name": table.get("name", ""),
                        "purpose": table.get("purpose", "")
                    }
                    
                    # Include only field names
                    if "fields" in table:
                        pruned_table["field_count"] = len(table["fields"])
                        
                    # Include only relationship types
                    if "relationships" in table:
                        pruned_table["relationships"] = [
                            {"related_to": r.get("related_to", "")} for r in table["relationships"]
                        ]
                        
                    pruned_tables.append(pruned_table)
            
            if len(tables) > self.max_examples["database_tables"]:
                pruned_tables.append({
                    "name": "additional_tables",
                    "note": f"Plus {len(tables) - self.max_examples['database_tables']} more tables"
                })
                
            pruned["tables"] = pruned_tables
            
        elif "collections" in database:
            # Similar structure for NoSQL collections
            collections = database["collections"]
            pruned["collections"] = collections[:min(self.max_examples["database_tables"], len(collections))]
            
        return pruned
    
    def _prune_api_for_synthesis(self, api: Dict[str, Any]) -> Dict[str, Any]:
        """Prune API design for synthesis."""
        if not api:
            return {}
            
        pruned = {
            "style": api.get("style", ""),
            "base_url": api.get("base_url", ""),
            "versioning_strategy": api.get("versioning_strategy", ""),
            "authentication": api.get("authentication", "")
        }
        
        # Include limited endpoints
        if "endpoints" in api:
            endpoints = api["endpoints"]
            pruned_endpoints = []
            
            for i, endpoint in enumerate(endpoints):
                if i < self.max_examples["api_endpoints"]:
                    # Include only core endpoint information
                    pruned_endpoints.append({
                        "method": endpoint.get("method", ""),
                        "path": endpoint.get("path", ""),
                        "purpose": endpoint.get("purpose", ""),
                        "authentication_required": endpoint.get("authentication_required", False)
                    })
            
            if len(endpoints) > self.max_examples["api_endpoints"]:
                pruned_endpoints.append({
                    "note": f"Plus {len(endpoints) - self.max_examples['api_endpoints']} more endpoints"
                })
                
            pruned["endpoints"] = pruned_endpoints
            
        return pruned
    
    def _prune_security_for_synthesis(self, security: Dict[str, Any]) -> Dict[str, Any]:
        """Prune security architecture for synthesis."""
        if not security:
            return {}
            
        pruned = {
            "authentication_method": security.get("authentication_method", ""),
            "authorization_strategy": security.get("authorization_strategy", "")
        }
        
        # Include data encryption if present
        if "data_encryption" in security:
            pruned["data_encryption"] = security["data_encryption"]
            
        # Include limited security measures
        if "security_measures" in security:
            measures = security["security_measures"]
            # Include only category and implementation
            pruned["security_measures"] = [
                {
                    "category": m.get("category", ""),
                    "implementation": m.get("implementation", "")
                } for m in measures[:min(5, len(measures))]
            ]
            
        return pruned
    
    def _prune_design_for_validation(self, design: Dict[str, Any]) -> Dict[str, Any]:
        """Prune system design for validation to reduce tokens."""
        if not design:
            return {}
            
        pruned = {
            "architecture_overview": design.get("architecture_overview", {}),
        }
        
        # Include pruned modules
        if "main_modules" in design:
            modules = design["main_modules"]
            pruned["main_modules"] = [
                {"name": m.get("name", ""), "responsibility": m.get("responsibility", "")}
                for m in modules[:min(self.max_examples["modules"], len(modules))]
            ]
            
        # Include pruned database design
        pruned["database_design"] = self._prune_database_for_synthesis(design.get("database_design", {}))
        
        # Include pruned API design
        pruned["api_design"] = self._prune_api_for_synthesis(design.get("api_design", {}))
        
        # Include core security info
        if "security_design" in design:
            security = design["security_design"]
            pruned["security_design"] = {
                "authentication_method": security.get("authentication_method", ""),
                "authorization_strategy": security.get("authorization_strategy", "")
            }
            
        # Include deployment architecture
        if "deployment_architecture" in design:
            pruned["deployment_architecture"] = design["deployment_architecture"]
            
        return pruned
    
    def _prune_design_for_domain_adaptation(self, design: Dict[str, Any]) -> Dict[str, Any]:
        """Prune system design for domain adaptation to reduce tokens."""
        # Similar to validation pruning but with different focus
        pruned = self._prune_design_for_validation(design)
        
        # Add domain-specific sections if present
        for key in ["domain_specific_details", "business_rules", "compliance_requirements"]:
            if key in design:
                pruned[key] = design[key]
                
        return pruned
    
    def _get_optimized_rag_context(self, query: str) -> str:
        """Get optimized RAG context with token limitation."""
        if not self.rag_retriever:
            return ""
            
        try:
            # FIXED: Use invoke() instead of deprecated get_relevant_documents()
            docs = self.rag_retriever.invoke(query)
            
            # Apply limit after invoke
            if hasattr(self, 'max_rag_docs'):
                docs = docs[:self.max_rag_docs]
            
            # Rest of method remains unchanged...
            # Limit context length
            max_context_length = 2000
            context_parts = []
            current_length = 0
            
            for doc in docs:
                content = doc.page_content
                # Add document if it doesn't exceed max length
                if current_length + len(content) <= max_context_length:
                    context_parts.append(content)
                    current_length += len(content)
                else:
                    # Add truncated version to fit remaining space
                    remaining = max_context_length - current_length
                    if remaining > 200:  # Only add if we can include meaningful content
                        context_parts.append(content[:remaining] + "...")
                    break
                    
            return "\n\n".join(context_parts)
            
        except Exception as e:
            self.log_warning(f"Error retrieving RAG context: {e}")
            return ""
    
    def log_execution_summary(self, response: Dict[str, Any]):
        """Log detailed execution summary for system design."""
        # Extract key metrics for summary
        arch_pattern = response.get("architecture_overview", {}).get("pattern", "Not specified")
        modules = response.get("main_modules", [])
        tables = len(response.get("database_design", {}).get("tables", []))
        endpoints = len(response.get("api_design", {}).get("endpoints", []))
        integrations = len(response.get("integration_points", []))
        deployment = response.get("deployment_architecture", {}).get("containerization", {}).get("approach", "Not specified")
        
        # Log success with summary stats
        summary = (f"System design complete - Architecture: {arch_pattern}, " +
                  f"{len(modules)} modules, {tables} DB tables, " +
                  f"{endpoints} API endpoints, {integrations} integrations, " +
                  f"Deployment: {deployment}")
        
        self.log_success(summary)
        
        # Log detailed component breakdowns
        self.log_info(f"   Architecture Pattern: {arch_pattern}")
        self.log_info(f"   Modules: {len(modules)} ({', '.join(m.get('name', '') for m in modules[:3])}{'...' if len(modules) > 3 else ''})")
        self.log_info(f"   Database Tables: {tables}")
        self.log_info(f"   API Endpoints: {endpoints}")
        self.log_info(f"   Integrations: {integrations}")
        
        # Log design patterns used
        patterns = response.get("design_patterns_used", [])
        if patterns:
            self.log_info(f"   Design Patterns: {', '.join(p.get('pattern', '') for p in patterns)}")
        
        # Log any design risks
        risks = response.get("design_risks_mitigations", [])
        if risks:
            self.log_info(f"   Design Risks Identified: {len(risks)}")
            for risk in risks:
                if risk.get("impact", "").lower() in ["high", "severe", "critical"]:
                    self.log_warning(f"   HIGH RISK: {risk.get('risk', '')}")
    
    def get_default_response(self) -> Dict[str, Any]:
        """Returns a default system design when analysis fails."""
        return {
            "status": "error",
            "message": "System design generation failed",
            "architecture_overview": {
                "pattern": "Fallback Three-Tier Architecture",
                "description": "Standard separation of presentation, business logic, and data layers"
            },
            "main_modules": [
                {"name": "Frontend Module", "responsibility": "User interface and presentation"},
                {"name": "Backend Module", "responsibility": "Business logic and processing"},
                {"name": "Data Module", "responsibility": "Data storage and retrieval"}
            ],
            "database_design": {
                "technology": "Generic Relational Database",
                "tables": []
            },
            "api_design": {
                "style": "REST",
                "endpoints": []
            },
            "integration_points": [],
            "security_architecture": {
                "authentication": "Standard JWT-based authentication",
                "authorization": "Role-based access control"
            },
            "error_message": "System design generation failed. This is a fallback design."
        }
    
    def _extract_non_functional_requirements(self, brd_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract non-functional requirements from BRD analysis."""
        try:
            nfrs = {}
            # Extract from requirements list
            requirements = brd_analysis.get("requirements", [])
            nfr_categories = ["performance", "security", "scalability", "reliability", 
                            "availability", "usability", "maintainability"]
            
            for req in requirements:
                category = req.get("category", "").lower()
                if category in nfr_categories or "non-functional" in category:
                    key = category.replace(" ", "_").replace("-", "_")
                    if key not in nfrs:
                        nfrs[key] = []
                    nfrs[key].append({
                        "id": req.get("id", ""),
                        "title": req.get("title", ""),
                        "description": req.get("description", ""),
                        "priority": req.get("priority", "medium")
                    })
                    
            # Add general constraints
            if "constraints" in brd_analysis:
                nfrs["constraints"] = brd_analysis["constraints"]
                
            return nfrs
        except Exception as e:
            self.log_warning(f"Failed to extract non-functional requirements: {str(e)}")
            return {
                "performance": [],
                "security": [],
                "scalability": [],
                "reliability": [],
                "constraints": []
            }
    
    def _extract_domain_characteristics(self, brd_analysis: Dict[str, Any]) -> str:
        """Extract domain-specific characteristics from BRD analysis."""
        domain_info = []
        
        # Extract domain from domain-specific details if available
        if "domain_specific_details" in brd_analysis:
            domain_details = brd_analysis["domain_specific_details"]
            if isinstance(domain_details, dict):
                # Convert dict to list of characteristics
                for key, value in domain_details.items():
                    if isinstance(value, str):
                        domain_info.append(f"{key}: {value}")
                    elif isinstance(value, (list, dict)):
                        domain_info.append(f"{key}: {json.dumps(value)}")
            elif isinstance(domain_details, str):
                domain_info.append(domain_details)
        
        # Extract domain from project name or summary
        domain_keywords = ["healthcare", "finance", "retail", "education", "manufacturing", 
                           "logistics", "ecommerce", "social", "media", "government"]
        
        for field in ["project_name", "project_summary"]:
            if field in brd_analysis and isinstance(brd_analysis[field], str):
                text = brd_analysis[field].lower()
                for keyword in domain_keywords:
                    if keyword in text and f"Domain: {keyword}" not in domain_info:
                        domain_info.append(f"Domain: {keyword}")
        
        # Check if any domain was found
        if not domain_info:
            domain_info.append("Domain: general software application")
        
        return "\n".join(domain_info)
    
    
    
    def _get_default_database_design(self, database_technology: str) -> Dict[str, Any]:
        """Return default database design when data model design fails."""
        db_type = database_technology.lower() if database_technology else "unknown"
        
        # Default SQL-based design
        if any(sql_type in db_type for sql_type in ["sql", "postgres", "mysql", "oracle", "relational"]):
            return {
                "schema_type": "Relational Database",
                "technology": database_technology or "SQL Database",
                "tables": [
                    {
                        "name": "users",
                        "purpose": "Store user account information",
                        "fields": [
                            {"name": "id", "type": "UUID/Integer", "description": "Primary key"},
                            {"name": "username", "type": "String", "description": "User login name"},
                            {"name": "email", "type": "String", "description": "User email address"},
                            {"name": "password_hash", "type": "String", "description": "Hashed password"}
                        ]
                    },
                    {
                        "name": "app_data",
                        "purpose": "Store application data",
                        "fields": [
                            {"name": "id", "type": "UUID/Integer", "description": "Primary key"},
                            {"name": "name", "type": "String", "description": "Data name"},
                            {"name": "value", "type": "String/JSON", "description": "Data value"}
                        ]
                    }
                ],
                "indexes": [
                    {"table": "users", "fields": ["email"], "type": "UNIQUE"}
                ]
            }
        
        # NoSQL document-based design
        elif any(doc_type in db_type for doc_type in ["mongo", "document", "cosmos", "nosql"]):
            return {
                "schema_type": "Document Database",
                "technology": database_technology or "MongoDB",
                "collections": [
                    {
                        "name": "users",
                        "document_structure": {
                            "id": "ObjectId",
                            "username": "String",
                            "email": "String",
                            "password_hash": "String", 
                            "profile": {
                                "full_name": "String",
                                "preferences": "Object"
                            }
                        }
                    },
                    {
                        "name": "app_data",
                        "document_structure": {
                            "id": "ObjectId",
                            "name": "String",
                            "value": "Mixed",
                            "created_at": "Date"
                        }
                    }
                ]
            }
        
        # Generic default if technology not recognized
        else:
            return {
                "schema_type": "Generic Database",
                "technology": database_technology or "Database",
                "data_structures": [
                    {
                        "name": "users",
                        "fields": [
                            {"name": "id", "type": "ID"},
                            {"name": "username", "type": "String"},
                            {"name": "email", "type": "String"}
                        ]
                    },
                    {
                        "name": "app_data",
                        "fields": [
                            {"name": "id", "type": "ID"},
                            {"name": "name", "type": "String"},
                            {"name": "value", "type": "String"}
                        ]
                    }
                ]
            }

    def _get_default_microservice_modules(self) -> Dict[str, Any]:
        """Return default module structure for microservice architecture."""
        return {
            "architecture_type": "Microservice Architecture",
            "modules": [
                {
                    "name": "User Service",
                    "responsibility": "User authentication and profile management",
                    "interfaces": ["REST API", "Message Queue"],
                    "components": ["User Controller", "Profile Manager", "Auth Service"]
                },
                {
                    "name": "Data Service",
                    "responsibility": "Core data storage and retrieval operations",
                    "interfaces": ["REST API", "Message Queue"],
                    "components": ["Data Controller", "Storage Manager", "Search Component"]
                },
                {
                    "name": "API Gateway",
                    "responsibility": "Route requests and handle cross-cutting concerns",
                    "interfaces": ["REST API"],
                    "components": ["Router", "Load Balancer", "Auth Middleware"]
                },
                {
                    "name": "Notification Service",
                    "responsibility": "Handle system notifications and alerts",
                    "interfaces": ["Message Queue"],
                    "components": ["Event Listener", "Notification Manager"]
                }
            ],
            "communication_patterns": ["HTTP/REST", "Message Queue", "Event Sourcing"],
            "design_notes": "Default microservice structure. Expand based on domain requirements."
        }

    def _get_default_event_driven_modules(self) -> Dict[str, Any]:
        """Return default module structure for event-driven architecture."""
        return {
            "architecture_type": "Event-Driven Architecture",
            "modules": [
                {
                    "name": "Event Producer Module",
                    "responsibility": "Generate domain events from user actions",
                    "interfaces": ["Message Queue", "REST API"],
                    "components": ["Event Generator", "API Controller"]
                },
                {
                    "name": "Event Consumer Module",
                    "responsibility": "Process domain events and update view models",
                    "interfaces": ["Message Queue"],
                    "components": ["Event Processor", "View Model Updater"]
                },
                {
                    "name": "Query Service",
                    "responsibility": "Handle read operations for view models",
                    "interfaces": ["REST API"],
                    "components": ["Query Handler", "View Repository"]
                },
                {
                    "name": "Event Store",
                    "responsibility": "Persistent storage for domain events",
                    "interfaces": ["API"],
                    "components": ["Event Repository", "Event Publisher"]
                }
            ],
            "communication_patterns": ["Event Streaming", "Message Queue", "HTTP/REST"],
            "design_notes": "Default event-driven structure. Define domain events based on business processes."
        }

    def _get_default_layered_modules(self) -> Dict[str, Any]:
        """Return default module structure for layered architecture."""
        return {
            "architecture_type": "Layered Architecture",
            "modules": [
                {
                    "name": "Presentation Layer",
                    "responsibility": "Handle user interface and user interaction",
                    "interfaces": ["UI Components", "REST API"],
                    "components": ["Views", "Controllers", "View Models"]
                },
                {
                    "name": "Business Logic Layer",
                    "responsibility": "Implement domain logic and business rules",
                    "interfaces": ["Service API"],
                    "components": ["Services", "Domain Model", "Business Rules"]
                },
                {
                    "name": "Data Access Layer",
                    "responsibility": "Handle data storage and retrieval",
                    "interfaces": ["Repository API"],
                    "components": ["Repositories", "Data Mappers", "Query Services"]
                },
                {
                    "name": "Infrastructure Layer",
                    "responsibility": "Provide cross-cutting technical capabilities",
                    "interfaces": ["Various APIs"],
                    "components": ["Logging", "Authentication", "Messaging"]
                }
            ],
            "communication_patterns": ["Dependency Injection", "Repository Pattern", "Service Pattern"],
            "design_notes": "Default layered structure following separation of concerns."
        }

    def _get_default_modules_for_pattern(self, pattern: str) -> Dict[str, Any]:
        """Return default module structure based on architecture pattern."""
        pattern_lower = pattern.lower()
        
        if "microservice" in pattern_lower:
            return self._get_default_microservice_modules()
        elif "event" in pattern_lower:
            return self._get_default_event_driven_modules()
        else:
            return self._get_default_layered_modules()

    def _get_default_api_design(self) -> Dict[str, Any]:
        """Return default API design when API design process fails."""
        return {

            "style": "REST",
            "base_url": "/api/v1",
            "versioning_strategy": "URL Path Versioning",
            "authentication": "JWT Bearer Token",
            "endpoints": [
                {
                    "method": "GET",
                    "path": "/users",
                    "purpose": "Get a list of users",
                    "parameters": [
                        {"name": "page", "type": "integer", "required": False, "description": "Page number for pagination"}
                    ],
                    "response": {"type": "array", "items": {"type": "User"}},

                    "authentication_required": True
                },
                {
                    "method": "POST",
                    "path": "/users",
                    "purpose": "Create a new user",
                    "request_body": {"type": "User"},
                    "response": {"type": "User"},
                    "authentication_required": True
                },
                {
                    "method": "POST",
                    "path": "/auth/login",
                    "purpose": "Authenticate user",
                    "request_body": {"type": "Credentials"},
                    "response": {"type": "TokenResponse"},
                    "authentication_required": False
                }
            ],
            "data_formats": ["JSON"],
            "error_handling": {
                "strategy": "Standard HTTP status codes with error details in response body",
                "error_response": {
                    "type": "object",
                    "properties": {
                        "error": "string",
                        "message": "string",
                        "status": "integer"
                    }
                }
            },
            "pagination": {
                "strategy": "Page-based with limit/offset",
                "parameters": ["page", "limit"]
            },
            "design_notes": "Default REST API design. Expand with domain-specific endpoints."
        }

    def _get_default_security_design(self) -> Dict[str, Any]:
        """Return default security architecture when security design process fails."""
        return {
            "authentication_method": "JWT with OAuth 2.0 flows",
            "authorization_strategy": "Role-Based Access Control (RBAC)",
            "data_encryption": {
                "in_transit": "TLS 1.3",
                "at_rest": "AES-256"
            },
            "security_measures": [
                {
                    "category": "Authentication",
                    "implementation": "JWT token-based authentication with refresh tokens",
                    "mitigation": "Prevents unauthorized access to protected resources"
                },
                {
                    "category": "Input Validation",
                    "implementation": "Server-side validation with sanitization",
                    "mitigation": "Prevents injection attacks like XSS and SQL injection"
                },
                {
                    "category": "Authorization",
                    "implementation": "Role-based access control with permission checks",
                    "mitigation": "Ensures users can only access permitted resources"
                },
                {
                    "category": "Secrets Management",
                    "implementation": "Environment variables and secure vault",
                    "mitigation": "Protects sensitive configuration and credentials"
                }
            ],
            "security_headers": [
                "Content-Security-Policy",
                "X-XSS-Protection",
                "X-Content-Type-Options",
                "Strict-Transport-Security"
            ],
            "logging_auditing": {
                "approach": "Centralized logging with security events",
                "retention": "90 days minimum"
            },
            "design_notes": "Default security architecture. Review and enhance based on specific threat model."
        }

    def _manual_design_integration(self, architecture_pattern, module_structure, 
                          database_design, api_design, security_architecture) -> Dict[str, Any]:
        """Manually integrate design components when synthesis fails."""
        pattern_name = architecture_pattern.get("selected_pattern", "Layered Architecture")
        
        return {
            "architecture_overview": {
                "pattern": pattern_name,
                "description": "Integrated architecture design with modular components",
                "principles": ["Separation of Concerns", "Modularity", "Security by Design"]
            },
            "main_modules": module_structure.get("modules", []),
            "database_design": database_design,
            "api_design": api_design,
            "security_design": security_architecture,
            "integration_points": [
               
                {
                    "source": "API Gateway/Controllers",
                    "destination": "Business Logic Modules",
                    "protocol": "Internal API calls"
                },
                {
                    "source": "Business Logic Modules",
                    "destination": "Data Access Layer",
                    "protocol": "Repository Pattern"
                }
            ],
            "deployment_architecture": {
                "containerization": {
                    "approach": "Docker with Kubernetes orchestration",
                    "components": ["Application Containers", "Database", "API Gateway"]
                },
                "scalability": {
                    "approach": "Horizontal scaling with load balancing",
                    "components": ["Web Tier", "Application Tier"]
                }
            },
            "design_patterns_used": [
                {
                    "pattern": "Repository Pattern",
                    "purpose": "Abstract data access logic"
                },
                {
                    "pattern": "Dependency Injection",
                    "purpose": "Manage component dependencies"
                }
            ],
            "design_notes": "Manually integrated design components. Review for consistency."
        }
    
    def _extract_domain(self, brd_analysis: Dict[str, Any]) -> str:
        """Extract domain information from BRD analysis."""
        try:
            # Extract from domain-specific details if available
            if "domain_specific_details" in brd_analysis and isinstance(brd_analysis["domain_specific_details"], dict):
                domain_info = brd_analysis["domain_specific_details"].get("industry", "")
                if domain_info:
                    return domain_info
        
            # Try to extract from project name or summary
            domain_keywords = ["healthcare", "finance", "banking", "retail", "education", "manufacturing", 
                             "logistics", "ecommerce", "social", "media", "government", "insurance"]
            
            for field in ["project_name", "project_summary", "domain"]:
                if field in brd_analysis and isinstance(brd_analysis[field], str):
                    text = brd_analysis[field].lower()
                    for keyword in domain_keywords:
                        if keyword in text:
                            return keyword
        
            # Extract from requirements
            if "requirements" in brd_analysis:
                text = json.dumps(brd_analysis["requirements"]).lower()
                for keyword in domain_keywords:
                    if keyword in text:
                        return keyword
        
            # Default if nothing found
            return ""
            
        except Exception as e:
            self.log_warning(f"Error extracting domain: {e}")
            return ""

    def _extract_industry_requirements(self, brd_analysis: Dict[str, Any]) -> str:
        """Extract industry-specific requirements from BRD analysis."""
        try:
            industry_reqs = []
            
            # Check for explicit industry requirements
            if "compliance_requirements" in brd_analysis:
                compliance = brd_analysis["compliance_requirements"]
                if isinstance(compliance, dict):
                    industry_reqs.extend([f"{k}: {v}" for k, v in compliance.items()])
                elif isinstance(compliance, list):
                    industry_reqs.extend(compliance)
                elif isinstance(compliance, str):
                    industry_reqs.append(compliance)
            
            # Check for regulations in requirements
            regulation_keywords = ["regulation", "compliance", "standard", "law", "requirement", "gdpr", "hipaa", "pci"]
            if "requirements" in brd_analysis:
                for req in brd_analysis["requirements"]:
                    description = req.get("description", "").lower()
                    if any(keyword in description for keyword in regulation_keywords):
                        industry_reqs.append(req.get("description", ""))
            
            # Format the result
            if industry_reqs:
                return "\n".join(industry_reqs)
            else:
                # Domain from extract_domain method to provide generic requirements
                domain = self._extract_domain(brd_analysis)
                if domain:
                    return f"Standard industry requirements for {domain} domain."
                else:
                    return "No specific industry requirements identified."
                    
        except Exception as e:
            self.log_warning(f"Error extracting industry requirements: {e}")
            return "Error extracting industry requirements."

    def verify_design_consistency(self, system_design: Dict[str, Any], tech_stack_recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Verify consistency of the system design and return enhanced design with consistency checks."""
        try:
            # Make a copy to avoid modifying the original
            verified_design = copy.deepcopy(system_design)
            
            # Add a verification section if it doesn't exist
            if "verification" not in verified_design:
                verified_design["verification"] = {}
            
            # Check database technology consistency
            db_tech_stack = tech_stack_recommendation.get("database", {}).get("type", "")
            db_design = verified_design.get("database_design", {}).get("technology", "")
            
            verified_design["verification"]["database_consistency"] = db_tech_stack == db_design
            
            # Check backend technology consistency
            backend_tech_stack = tech_stack_recommendation.get("backend", {}).get("language", "")
            backend_design = self._extract_backend_technology(verified_design)
            
            verified_design["verification"]["backend_consistency"] = backend_tech_stack.lower() in backend_design.lower()
            
            # Add overall consistency score
            consistency_checks = [
                verified_design["verification"].get("database_consistency", False),
                verified_design["verification"].get("backend_consistency", False)
            ]
            
            consistency_score = sum(1 for check in consistency_checks if check) / len(consistency_checks) * 10
            verified_design["verification"]["consistency_score"] = round(consistency_score, 1)
            
            return verified_design
            
        except Exception as e:
            self.log_warning(f"Design consistency verification failed: {e}")
            # Return original design if verification fails
            return system_design

    def _extract_backend_technology(self, system_design: Dict[str, Any]) -> str:
        """Extract backend technology from the system design."""
        # Look in various locations where backend technology might be mentioned
        if "architecture_overview" in system_design and "backend" in system_design["architecture_overview"]:
            return system_design["architecture_overview"]["backend"]
        
        # Check in modules
        for module in system_design.get("main_modules", []):
            name = module.get("name", "").lower()
            if "backend" in name or "server" in name:
                return module.get("technology", "")
        
        # Default if not found
        return ""

    def _process_llm_response(self, response, default_result=None):
        """Process LLM response with proper text extraction and error handling."""
        try:
            # First extract text from AIMessage or other response types
            response_text = JsonHandler._extract_text_content(response)
            
            # Then perform JSON parsing on the extracted text
            result = self.parse_json_with_error_tracking(
                response_text,
                default_response=default_result
            )
            
            return result
        except Exception as e:
            self.log_warning(f"Error processing LLM response: {str(e)}")
            return default_result if default_result is not None else {}
    
    # ADDED: Method to proactively check for template variables in prompts
    def _check_for_template_variables(self, text: str) -> bool:
        """Check if text contains any template-like variables that might cause issues."""
        suspicious_patterns = [
            r'\{task_id', r'\{domain_specific', r'\{extracted', r'\{system_design', 
            r'\{industry_', r'\{prompt', r'\{response'
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, text):
                self.log_warning(f"Detected suspicious template pattern in prompt: {pattern}")
                return True
        return False


        # Add this method to sanitize responses
    def _sanitize_template_variables(self, response_text: str) -> str:
        """Remove any template-like variables from response text."""
        # Replace any instances of {task_id} with "task_identifier"
        sanitized = re.sub(r'\{task_id\}', '"task_identifier"', response_text)
        # Replace other common template patterns
        sanitized = re.sub(r'\{[a-z_]+\}', '"value"', sanitized)
        return sanitized
    
    def _prune_tech_stack_for_design(self, tech_stack: Dict[str, Any]) -> str:
        """Creates a concise string summary of the tech stack, NOT a large JSON."""
        if not tech_stack: return "Not specified."
        
        backend_lang = tech_stack.get('backend', {}).get('language', 'N/A')
        backend = tech_stack.get('backend', {}).get('framework', 'N/A')
        frontend = tech_stack.get('frontend', {}).get('framework', 'N/A')
        database = tech_stack.get('database', {}).get('type', 'N/A')
        arch = tech_stack.get('architecture_pattern', 'N/A')
        
        return (f"Backend: {backend_lang} with {backend}, Frontend: {frontend}, "
                f"Database: {database}, Architecture: {arch}.")


    def _summarize_brd_for_design(self, brd_analysis: Dict[str, Any]) -> str:
        """Create a concise string summary of the BRD for design stages."""
        if not brd_analysis:
            return "Not specified."
        
        summary_parts = []
        
        # Add project name and summary
        project_name = brd_analysis.get("project_name", "Unnamed Project")
        summary_parts.append(f"Project: {project_name}")
        
        # Add project summary if available
        if "project_summary" in brd_analysis:
            project_summary = brd_analysis["project_summary"]
            if len(project_summary) > 200:
                project_summary = project_summary[:197] + "..."
            summary_parts.append(f"Summary: {project_summary}")
        
        # Add key goals
        goals = brd_analysis.get("project_goals", [])
        if goals:
            goal_str = ", ".join(goals[:3])
            if len(goals) > 3:
                goal_str += f" (and {len(goals) - 3} more)"
            summary_parts.append(f"Goals: {goal_str}")
        
        # Add key requirements count
        if "requirements" in brd_analysis:
            req_count = len(brd_analysis["requirements"])
            req_types = {}
            for req in brd_analysis["requirements"]:
                category = req.get("category", "unknown")
                req_types[category] = req_types.get(category, 0) + 1
            
            summary_parts.append(f"Requirements: {req_count} total ({', '.join(f'{count} {cat}' for cat, count in req_types.items())})")
        
        return "\n".join(summary_parts)

    def _summarize_modules(self, module_structure: Dict[str, Any]) -> str:
        """Create a concise string summary of the module structure."""
        if not module_structure or "modules" not in module_structure:
            return "Not specified."
        
        modules = module_structure.get("modules", [])
        if not modules:
            return "No modules defined."
        
        summary_parts = []
        for i, module in enumerate(modules[:5]):  # List up to 5 modules
            name = module.get("name", f"Module {i+1}")
            summary_parts.append(f"{name}: {module.get('responsibility', 'No responsibility defined')}")
        
        if len(modules) > 5:
            summary_parts.append(f"Plus {len(modules) - 5} more modules...")
        
        comm_patterns = module_structure.get("communication_patterns", [])
        if comm_patterns:
            summary_parts.append(f"Communication: {', '.join(comm_patterns[:3])}")
        
        return "\n".join(summary_parts)
    
    def _summarize_database(self, database_design: Dict[str, Any]) -> str:
        """Create a concise string summary of the database design."""
        if not database_design:
            return "Not specified."
        
        schema_type = database_design.get("schema_type", "Unknown schema type")
        technology = database_design.get("technology", "Unknown technology")
        
        # Count tables/collections
        tables = database_design.get("tables", [])
        collections = database_design.get("collections", [])
        data_structures = tables or collections
        
        structure_count = len(data_structures)
        structure_name = "tables" if tables else "collections"
        
        # List some key structures
        key_structures = []
        for struct in data_structures[:3]:
            name = struct.get("name", "unnamed")
            key_structures.append(name)
        
        structure_str = ", ".join(key_structures)
        if structure_count > 3:
            structure_str += f" (plus {structure_count - 3} more)"
        
        return f"{schema_type} using {technology} with {structure_count} {structure_name}: {structure_str}"
    
    def _summarize_api(self, api_design: Dict[str, Any]) -> str:
        """Create a concise string summary of the API design."""
        if not api_design:
            return "Not specified."
        
        style = api_design.get("style", "Unknown")
        auth = api_design.get("authentication", "None")
        
        endpoints = api_design.get("endpoints", [])
        endpoint_count = len(endpoints)
        
        key_endpoints = []
        for endpoint in endpoints[:3]:
            method = endpoint.get("method", "")
            path = endpoint.get("path", "")
            if method and path:
                key_endpoints.append(f"{method} {path}")
        
        endpoint_str = ", ".join(key_endpoints)
        if endpoint_count > 3:
            endpoint_str += f" (plus {endpoint_count - 3} more)"
        
        return f"{style} API with {auth} authentication. {endpoint_count} endpoints: {endpoint_str}"



    def _summarize_security(self, security_architecture: Dict[str, Any]) -> str:
        """Create a concise string summary of the security architecture."""
        if not security_architecture:
            return "Not specified."
        
        auth_method = security_architecture.get("authentication_method", "Not specified")
        auth_strategy = security_architecture.get("authorization_strategy", "Not specified")
        
        # Count security measures
        measures = security_architecture.get("security_measures", [])
        measure_count = len(measures)
        
        # Get encryption details
        encryption = security_architecture.get("data_encryption", {})
        transit = encryption.get("in_transit", "Not specified")
        
        return f"Auth: {auth_method}, Authorization: {auth_strategy}, Encryption: {transit} (transit). {measure_count} security measures defined."




