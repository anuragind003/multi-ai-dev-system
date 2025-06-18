import json
import re
import copy
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging  # Ensure this import is present

# Create a module-level logger
logger = logging.getLogger(__name__)  # Add this line to ensure logging is available

from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser

import monitoring
from .base_agent import BaseAgent
from agent_temperatures import get_agent_temperature
from tools.json_handler import JsonHandler


class TechStackAdvisorAgent(BaseAgent):
    """
    Enhanced Tech Stack Advisor that recommends optimal technologies through:
    1. Multi-stage analysis with specialized sub-evaluations
    2. Trade-off analysis with quantified scoring
    3. Trend-aware recommendations with market maturity assessment
    4. Risk/benefit profiling for technology choices
    """
    
    def __init__(self, llm: BaseLanguageModel, memory, temperature: float, rag_retriever: Optional[BaseRetriever] = None):
        # Get the conceptual default temperature for this agent type
        agent_default_temp = get_agent_temperature("Tech Stack Advisor Agent")
        
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Tech Stack Advisor Agent",
            temperature=temperature,  # Use temperature from agent_temperatures
            rag_retriever=rag_retriever
        )
        
        # Initialize JsonOutputParser for structured JSON output
        from langchain_core.output_parsers import JsonOutputParser
        self.json_parser = JsonOutputParser()
        
        # Initialize specialized prompt templates
        self._initialize_prompt_templates()
        
        # Technology recommendation tracking
        self.recommendation_stages = []
        self.tech_evaluations = {}
        
        # Token optimization configurations
        self.max_tokens = {
            "requirements_extraction": 4096,
            "backend_evaluation": 4096, 
            "database_evaluation": 4096,
            "frontend_evaluation": 4096,
            "architecture_evaluation": 4096,
            "tech_stack_synthesis": 8192,
            "risk_analysis": 4096
        }
        
        # Maximum examples to include in evaluations
        self.max_examples = {
            "backend_options": 3,
            "database_options": 3,
            "frontend_options": 3,
            "architecture_options": 3,
            "library_tools": 8
        }
        # Add JSON examples similar to BRDAnalystAgent
        self.json_examples = {
            "requirements_extraction": """
            {
            "scale": {
                "user_count": "10,000+",
                "data_volume": "moderate",
                "transaction_rate": "high"
            },
            "security": {
                "level": "high",
                "authentication": "required",
                "authorization": "role-based"
            },
            "technical_requirements": [
                {
                "category": "data",
                "description": "Must store customer information securely"
                }
            ]
            }
            """,
            
            "backend_evaluation": """
            {
            "backend_options": [
                {
                "language": "Python",
                "framework": "Django",
                "performance_score": 8,
                "scalability_score": 9,
                "developer_productivity": 8,
                "ecosystem_maturity": 9,
                "overall_score": 8.5,
                "reasoning": "Django provides a robust framework with strong ORM capabilities"
                }
            ],
            "recommendation": {
                "language": "Python",
                "framework": "Django",
                "reasoning": "Best matches the project requirements for rapid development with good scalability"
            }
            }
            """,
            
            "database_evaluation": """
            {
            "database_options": [
                {
                "name": "PostgreSQL",
                "type": "Relational",
                "performance_score": 8,
                "scalability_score": 8,
                "flexibility_score": 7,
                "complexity_score": 6,
                "overall_score": 7.5,
                "reasoning": "Strong ACID compliance and robust feature set"
                }
            ],
            "recommendation": {
                "name": "PostgreSQL",
                "type": "Relational",
                "reasoning": "Best matches project data structure and reliability requirements"
            }
            }
            """,
            
            "frontend_evaluation": """
            {
            "frontend_options": [
                {
                "language": "JavaScript",
                "framework": "React",
                "performance_score": 8,
                "developer_productivity_score": 9,
                "ui_capability_score": 9,
                "ecosystem_score": 9,
                "overall_score": 8.8,
                "reasoning": "React provides excellent component reusability and performance"
                }
            ],
            "recommendation": {
                "language": "JavaScript",
                "framework": "React",
                "reasoning": "Offers best balance of developer productivity and UI capabilities"
            }
            }
            """,
            
            "architecture_evaluation": """
            {
            "architecture_options": [
                {
                "pattern": "Microservices",
                "scalability_score": 9,
                "maintainability_score": 7,
                "development_speed_score": 6,
                "complexity_score": 8,
                "overall_score": 7.5,
                "reasoning": "Excellent for independent scaling and technology diversity"
                }
            ],
            "recommendation": {
                "pattern": "Microservices",
                "reasoning": "Recommended due to scalability requirements and team structure"
            }
            }
            """,
            
            "tech_stack_synthesis": """
            {
            "backend": {
                "language": "Python",
                "framework": "Django",
                "reasoning": "Best balance of productivity and performance"
            },
            "frontend": {
                "language": "JavaScript",
                "framework": "React",
                "reasoning": "Component reusability and strong ecosystem"
            },
            "database": {
                "type": "PostgreSQL",
                "reasoning": "Strong relational capabilities and data integrity"
            },
            "architecture_pattern": "Layered Architecture",
            "deployment_environment": {
                "platform": "AWS",
                "containerization": "Docker"
            },
            "key_libraries_tools": [
                {"name": "Redis", "purpose": "Caching layer"},
                {"name": "Pytest", "purpose": "Test automation"}
            ],
            "estimated_complexity": "Medium"
            }
            """,
            
            "risk_analysis": """
            {
            "risks": [
                {
                "category": "Technology",
                "description": "GraphQL learning curve may slow development",
                "severity": "Medium",
                "likelihood": "High",
                "mitigation": "Provide focused team training on GraphQL"
                }
            ],
            "technology_compatibility_issues": [
                {
                "components": ["React", "Django"],
                "potential_issue": "Integration between frontend and backend",
                "solution": "Use Django REST framework with clear API contracts"
                }
            ]
            }
            """
        }
        
        # Maximum RAG documents to retrieve per query
        self.max_rag_docs = 3
        
    def _initialize_prompt_templates(self):
        """Initialize streamlined prompt templates for multi-stage tech analysis."""
        # 1. Optimized requirements extraction template
        self.requirements_extraction_template = PromptTemplate(
            template="""
            Expert BRD-to-technical requirements analyzer.
            
            Analyze BRD to extract key technical requirements in these categories:
            1. SCALE: User/transaction volumes, data size, feature complexity
            2. DATA: Entity relationships, access patterns, consistency, governance
            3. PERFORMANCE: Response times, throughput, latency constraints
            4. SECURITY: Authentication, data protection, compliance
            5. INTEGRATION: External systems, APIs, data exchange
            6. UX: UI complexity, interactivity, responsiveness
            7. DEPLOYMENT: Environment constraints, scaling, distribution
            8. CONSTRAINTS: Budget, skills, timeline
            
            BRD ANALYSIS:
            {brd_analysis}
            
            {format_instructions}
            
            Provide specific metrics where possible (e.g., "5ms response time" not "fast response").
            """,
            input_variables=["brd_analysis"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()}
        )
        
        # 2. Optimized backend technology evaluation template
        self.backend_evaluation_template = ChatPromptTemplate.from_messages([
            SystemMessage(content="Expert Backend Technology Advisor evaluating server-side options based on requirements."),
            HumanMessage(content="""
                PROJECT REQUIREMENTS:
                {requirements_str}
                
                CONTEXT:
                - {project_context}
                - Scale: {scale}
                - Data: {data_complexity}
                - Security: {security_level}
                - Performance: {performance_needs}
                
                {format_instructions}
                
                Evaluate 3 backend technology options with:
                1. Scores (1-10) on technical dimensions
                2. Reasoning tied to requirements
                3. Trade-offs
                4. Implementation risks
            """)
        ])
        
        # 3. Optimized database technology evaluation template
        self.database_evaluation_template = PromptTemplate(
            template="""
            Expert Database Advisor for data storage solutions.
            
            PROJECT REQUIREMENTS:
            {extracted_requirements}
            
            CONTEXT:
            - Scale: {scale}
            - Data complexity: {data_complexity}
            - Security: {security_level}
            - Performance: {performance_needs}
            
            {format_instructions}
            
            Evaluate 3 database technologies with:
            1. Technology name and type
            2. Scores (1-10): Performance, Scalability, Flexibility, Complexity
            3. Reasoning for project fit
            4. Limitations and risks
            """,
            input_variables=[
                "extracted_requirements", "scale", "data_complexity", 
                "security_level", "performance_needs"
            ],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()}
        )
        
        # 4. Optimized frontend technology evaluation template
        self.frontend_evaluation_template = PromptTemplate(
            template="""
            Expert Frontend Technology Advisor for UI frameworks.
            
            PROJECT REQUIREMENTS:
            {extracted_requirements}
            
            UI/UX NEEDS:
            {ui_ux_requirements}
            
            CONTEXT:
            - Performance: {performance_needs}
            - Mobile requirements: {mobile_requirements}
            
            {format_instructions}
            
            Evaluate 3 frontend options with:
            1. Language and framework
            2. Scores (1-10): Developer productivity, Performance, UI capability, Ecosystem
            3. Reasoning for project fit
            4. Mobile strategy
            5. State management
            """,
            input_variables=[
                "extracted_requirements", "ui_ux_requirements", 
                "performance_needs", "mobile_requirements"
            ],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()}
        )
        
        # 5. Optimized architecture pattern evaluation template
        self.architecture_evaluation_template = ChatPromptTemplate.from_messages([
            SystemMessage(content="Expert Software Architect evaluating system architecture patterns."),
            HumanMessage(content="""
                PROJECT REQUIREMENTS:
                {extracted_requirements}
                
                TECHNICAL CONTEXT:
                - Scale: {scale}
                - Data: {data_complexity}
                - Backend: {backend_choice}
                - Database: {database_choice}
                - Frontend: {frontend_choice}
                
                {format_instructions}
                
                Evaluate 3 architecture patterns with:
                1. Pattern name 
                2. Scores (1-10): Scalability, Maintainability, Dev speed, Complexity
                3. Project-specific reasoning
                4. Implementation guidance
            """)
        ])
        
        # 6. Fixed tech stack synthesis template with clean variable names
        self.tech_stack_synthesis_template = PromptTemplate(
            template="""
            Expert Technology Stack Architect for final recommendations.
            
            SYNTHESIS INPUTS:
            1. REQUIREMENTS: {extracted_requirements}
            2. BACKEND: {backend_evaluation}
            3. DATABASE: {database_evaluation}
            4. FRONTEND: {frontend_evaluation}
            5. ARCHITECTURE: {architecture_evaluation}
            
            {format_instructions}
            
            Create integrated tech stack with:
            1. Cohesive, consistent components
            2. Clear reasoning for each choice
            3. Specific libraries and tools
            4. Deployment strategy
            5. Complexity assessment
            
            CRITICAL: Return ONLY valid JSON with no explanations or markdown formatting outside the JSON structure.
            """,
            input_variables=[
                "extracted_requirements", "backend_evaluation", "database_evaluation",
                "frontend_evaluation", "architecture_evaluation"
            ],
            partial_variables={"format_instructions": "Your response MUST be valid JSON."}
        )
        
        # 7. Optimized risk analysis template
        self.risk_analysis_template = PromptTemplate(
            template="""
            Expert technology risk assessor.
            
            TECHNOLOGY STACK:
            {final_recommendation}
            
            PROJECT REQUIREMENTS:
            {extracted_requirements}
            
            {format_instructions}
            
            Assess risks with:
            1. Technology-specific risks
            2. Integration risks
            3. Implementation risks
            4. Maintenance risks
            5. Mitigation strategies
            
            For each risk, include severity and likelihood (High/Medium/Low).
            """,
            input_variables=["final_recommendation", "extracted_requirements"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()}
        )

        # Apply format_instructions to ChatPromptTemplates after definition
        format_instructions = self.json_parser.get_format_instructions()
        
        # Apply to backend evaluation template
        self.backend_evaluation_template = self.backend_evaluation_template.partial(
            format_instructions=format_instructions
        )
        
        # Apply to architecture evaluation template
        self.architecture_evaluation_template = self.architecture_evaluation_template.partial(
            format_instructions=format_instructions
        )
        
    def run(self, brd_analysis: Dict[str, Any], project_context: str = "") -> Dict[str, Any]:
        """Generate technology stack recommendations using sequential chain approach with simplified prompts."""
        self.log_start("Starting tech stack analysis")
        self.recommendation_stages = []
        
        try:
            # Input validation
            if not brd_analysis or not isinstance(brd_analysis, dict):
                self.log_warning("Invalid BRD analysis input - using default recommendations")
                return self.get_default_response()
            
            # STEP 1: Create a concise text summary of requirements
            self.log_info("Step 1: Creating concise requirements summary")
            requirements_summary = self._create_requirements_summary(brd_analysis)
            self.log_info(f"Created concise requirements summary: {len(requirements_summary)} chars")
            
            # STEP 2: Evaluate backend technology options using the SUMMARY
            self.log_info("Step 2: Evaluating backend technology options")
            backend_evaluation = self._evaluate_backend_technologies(requirements_summary, project_context)
            backend_choice = self._extract_top_choice(backend_evaluation, "backend")
            self.log_info(f"Selected backend: {backend_choice}")
            self.recommendation_stages.append({"stage": "backend_evaluation", "result": backend_evaluation})
            
            # STEP 3: Evaluate database technology options using the SUMMARY
            self.log_info("Step 3: Evaluating database technology options")
            database_evaluation = self._evaluate_database_technologies(requirements_summary)
            database_choice = self._extract_top_choice(database_evaluation, "database")
            self.log_info(f"Selected database: {database_choice}")
            self.recommendation_stages.append({"stage": "database_evaluation", "result": database_evaluation})
            
            # STEP 4: Evaluate frontend technology options using the SUMMARY
            self.log_info("Step 4: Evaluating frontend technology options")
            frontend_evaluation = self._evaluate_frontend_technologies(requirements_summary)
            frontend_choice = self._extract_top_choice(frontend_evaluation, "frontend")
            self.log_info(f"Selected frontend: {frontend_choice}")
            self.recommendation_stages.append({"stage": "frontend_evaluation", "result": frontend_evaluation})
            
            # STEP 5: Evaluate architecture patterns using SIMPLE CHOICES
            self.log_info("Step 5: Evaluating architecture patterns")
            architecture_evaluation = self._evaluate_architecture_patterns(
                requirements_summary,
                backend_choice,
                database_choice,
                frontend_choice
            )
            architecture_choice = self._extract_top_choice(architecture_evaluation, "architecture")
            self.log_info(f"Selected architecture: {architecture_choice}")
            self.recommendation_stages.append({"stage": "architecture_evaluation", "result": architecture_evaluation})
            
            # STEP 6: Synthesize final tech stack using SIMPLE STRING CHOICES ONLY
            self.log_info("Step 6: Synthesizing final technology stack")
            final_recommendation = self._synthesize_tech_stack(
                requirements_summary,
                backend_choice,
                database_choice, 
                frontend_choice,
                architecture_choice
            )
            self.recommendation_stages.append({"stage": "tech_stack_synthesis", "result": final_recommendation})
            
            # STEP 7: Risk analysis using simplified inputs
            self.log_info("Step 7: Performing risk analysis")
            risk_summary = f"Tech Stack: {backend_choice} backend, {database_choice} database, {frontend_choice} frontend, {architecture_choice} architecture"
            enhanced_recommendation = self._perform_risk_analysis(
                final_recommendation,
                risk_summary + "\n" + requirements_summary
            )
            self.recommendation_stages.append({"stage": "risk_analysis", "result": enhanced_recommendation})
            
            # Add metadata to final response
            final_response = enhanced_recommendation
            final_response["recommendation_metadata"] = {
                "analysis_approach": "sequential chain with simplified prompts",
                "evaluation_stages": len(self.recommendation_stages),
                "top_backend": backend_choice,
                "top_database": database_choice,
                "top_frontend": frontend_choice,
                "top_architecture": architecture_choice,
                "timestamp": datetime.now().isoformat(),
                "technologies_evaluated": self._count_evaluated_technologies()
            }
            
            # Log execution summary
            self.log_execution_summary(final_response)
            
            return final_response
            
        except Exception as e:
            self.log_error(f"Tech stack recommendation failed: {str(e)}")
            return self.get_default_response()

    # NEW TOKEN OPTIMIZATION METHODS

    def _prune_brd_for_tech_analysis(self, brd_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create a pruned version of BRD for token efficiency in tech analysis."""
        pruned = {
            "project_name": brd_analysis.get("project_name", ""),
            "project_summary": brd_analysis.get("project_summary", ""),
            "project_goals": brd_analysis.get("project_goals", [])
        }
        
        # Include only technical requirements
        if "requirements" in brd_analysis:
            requirements = brd_analysis["requirements"]
            # Extract technical categories
            tech_categories = ["functional", "non-functional", "technical", "integration", "performance", "security"]
            tech_reqs = [req for req in requirements if req.get("category", "").lower() in tech_categories]
            
            # Take maximum 12 requirements or all if fewer
            max_reqs = min(len(tech_reqs), 12)
            pruned["requirements"] = tech_reqs[:max_reqs]
            if len(tech_reqs) > max_reqs:
                pruned["requirements"].append({
                    "id": "additional",
                    "title": "Additional Requirements",
                    "description": f"Plus {len(tech_reqs) - max_reqs} more technical requirements (truncated)"
                })
        
        # Include key constraints
        if "constraints" in brd_analysis:
            pruned["constraints"] = brd_analysis["constraints"]
            
        return pruned
        
    def _extract_detailed_requirements(self, brd_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract detailed requirements using strict JSON approach identical to BRDAnalyst."""
        try:
            # Create specialized LLM for JSON generation
            llm_json = JsonHandler.create_strict_json_llm(
                self.llm,
                max_tokens=self.max_tokens["requirements_extraction"]
            )
            
            # Create a hardcoded task description without any template variables
            task_description = f"""
            Analyze the following BRD to extract key technical requirements.
            
            BRD:
            {json.dumps(brd_analysis, indent=2)}
            
            Format your response as a JSON object with these categories:
            1. scale: User/transaction volumes, data size, feature complexity
            2. data: Entity relationships, access patterns, consistency, governance
            3. performance: Response times, throughput, latency constraints
            4. security: Authentication, data protection, compliance
            5. integration: External systems, APIs, data exchange
            6. user_experience: UI complexity, interactivity, responsiveness
            7. deployment: Environment constraints, scaling, distribution
            8. constraints: Budget, skills, timeline
            
            Provide specific metrics where possible (e.g., "5ms response time" not "fast response").
            Do not include template variables or placeholders in your response.
            """
            
            # Create a messages object directly rather than using another template
            messages = [
                SystemMessage(content="Technical Requirements Extractor. Produce valid JSON only."),
                HumanMessage(content=task_description)
            ]
            
            # Force temperature to 0.0
            invoke_config = {
                "agent_context": f"{self.agent_name}:requirements_extraction",
                "temperature_used": 0.0
            }
            
            # Direct invocation with zero temperature
            response = llm_json.invoke(messages, config=invoke_config)
            
            # Extract text content
            response_text = JsonHandler._extract_text_content(response)
            
            # Check for template variables and reject if found
            if "{" in response_text and any(var in response_text for var in [
                "{extracted_", "{brd_", "{requirement", "{task_", "{example"
            ]):
                self.log_warning("Detected template variable pattern in requirements extraction - using fallback")
                return self._create_fallback_requirements()
            
            # Parse JSON with robust handling
            result = JsonHandler.parse_json_with_error_tracking(
                response_text,
                default_response={"technical_requirements": []}
            )
            
            return result
    
        except Exception as e:
            self.log_warning(f"Detailed requirements extraction failed: {str(e)}")
            return self._create_fallback_requirements()

    def _create_fallback_requirements(self):
        """Create fallback requirements when extraction fails."""
        return {
            "scale": {
                "user_count": "Medium",
                "data_volume": "Moderate",
                "transaction_rate": "Standard"
            },
            "data": {
                "complexity": "Medium",
                "relationships": "Standard",
                "consistency": "Required"
            },
            "performance": {
                "response_time": "Under 1s",
                "throughput": "Standard",
                "latency_constraints": "Normal"
            },
            "security": {
                "level": "Standard",
                "authentication": "Required",
                "authorization": "Role-based"
            },
            "technical_requirements": [
                {
                "category": "data",
                "description": "Store application data securely"
                },
                {
                "category": "performance", 
                "description": "Respond to user requests promptly"
                }
            ]
        }
        
    def _prune_requirements_for_risk_analysis(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Prune requirements for risk analysis to reduce tokens."""
        if not requirements:
            return {}
            
        pruned = {}
        
        # Include only high-level requirements summaries
        high_level_keys = ["scale", "security", "performance", "data"]
        for key in high_level_keys:
            if key in requirements:
                if isinstance(requirements[key], dict):
                    pruned[key] = {k: v for k, v in requirements[key].items() if k in ["summary", "level", "priority"]}
                else:
                    pruned[key] = requirements[key]
        
        return pruned

    def _prune_for_synthesis(self, evaluation: Dict[str, Any], component_type: str) -> Dict[str, Any]:
        """Prune evaluation results for tech stack synthesis to reduce tokens."""
        if not evaluation:
            return {}
            
        pruned = {}
        
        # Extract recommendation
        if "recommendation" in evaluation:
            pruned["recommendation"] = evaluation["recommendation"]
            
        # Extract limited options based on component type
        options_key = f"{component_type}_options"
        if options_key in evaluation:
            options = evaluation[options_key]
            max_options = self.max_examples.get(options_key, 3)
            
            if len(options) > max_options:
                # Include limited number of options with core information
                pruned_options = []
                for i, option in enumerate(options[:max_options]):
                    if component_type == "backend":
                        pruned_options.append({
                            "language": option.get("language", ""),
                            "framework": option.get("framework", ""),
                            "overall_score": option.get("overall_score", 0)
                        })
                    elif component_type == "database":
                        pruned_options.append({
                            "name": option.get("name", ""),
                            "type": option.get("type", ""),
                            "overall_score": option.get("overall_score", 0)
                        })
                    elif component_type == "frontend":
                        pruned_options.append({
                            "language": option.get("language", ""),
                            "framework": option.get("framework", ""),
                            "overall_score": option.get("overall_score", 0)
                        })
                    else:
                        pruned_options.append({
                            "name": option.get("name", ""),
                            "overall_score": option.get("overall_score", 0)
                        })
                
                pruned[options_key] = pruned_options
            else:
                pruned[options_key] = options
                
        return pruned

    def _get_optimized_rag_context(self, query: str) -> str:
        """Get optimized RAG context with token limitation."""
        if not self.rag_retriever:
            return ""
            
        try:
            # FIXED: Replace deprecated get_relevant_documents with invoke
            docs = self.rag_retriever.invoke(query)
            
            # If a limit is needed, apply it after invoke
            if hasattr(self, 'max_rag_docs'):
                docs = docs[:self.max_rag_docs]
            
            # Rest of method unchanged...
            max_context_length = 1500  # Or whatever is appropriate
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
                    if remaining > 150:  # Only add if we can include meaningful content
                        context_parts.append(content[:remaining] + "...")
                    break
                    
            return "\n\n".join(context_parts)
            
        except Exception as e:
            self.log_warning(f"Error retrieving RAG context: {e}")
            return ""

    def get_rag_context(self, query: str) -> str:
        """Get RAG context with token optimization."""
        return self._get_optimized_rag_context(query)

    def _evaluate_backend_technologies(self, requirements_summary: str, project_context: str) -> Dict[str, Any]:
        """Evaluate backend technology options using text summary instead of full JSON."""
        try:
            # Create specialized LLM for JSON generation
            llm_json = JsonHandler.create_strict_json_llm(
                self.llm,
                max_tokens=self.max_tokens["backend_evaluation"]
            )
            
            # Get RAG context for backend technologies if available
            rag_context = ""
            if self.rag_retriever:
                backend_query = f"backend technology comparison for web applications"
                rag_context = self._get_optimized_rag_context(backend_query)
                if rag_context and project_context:
                    project_context = f"{project_context}\n\nAdditional context: {rag_context}"
                elif rag_context:
                    project_context = f"Additional context: {rag_context}"

            # Create task description with the simplified requirements summary
            task_description = f"""
            Evaluate backend technology options for this project:
            
            PROJECT REQUIREMENTS SUMMARY:
            {requirements_summary}
            
            CONTEXT:
            {project_context}
            
            Evaluate EXACTLY 3 backend technology options with:
            1. Scores (1-10) on technical dimensions
            2. Reasoning tied to requirements
            3. Trade-offs
            4. Implementation risks
            
            Format your response as VALID JSON with the exact structure shown in the example.
            """
            
            # Create strict JSON template
            messages = JsonHandler.create_strict_json_template(
                "Backend Technology Evaluation",
                task_description,
                self.json_examples["backend_evaluation"]
            )
            
            # Add tracing configuration
            invoke_config = {
                "agent_context": f"{self.agent_name}:backend_evaluation",
                "temperature_used": 0.0
            }
            
            # Direct invocation with explicit JSON config
            response = llm_json.invoke(messages, config=invoke_config)
            
            # Use the enhanced parsing from BRDAnalyst
            result = JsonHandler.parse_json_with_error_tracking(
                JsonHandler._extract_text_content(response), 
                default_response={"backend_options": [], "recommendation": None}
            )
            
            # Validate and limit the number of options
            if "backend_options" in result and len(result.get("backend_options", [])) > self.max_examples["backend_options"]:
                result["backend_options"] = result["backend_options"][:self.max_examples["backend_options"]]
                
            self.log_info(f"Evaluated {len(result.get('backend_options', []))} backend technology options")
            self.tech_evaluations["backend"] = result
            return result
        
        except Exception as e:
            self.log_warning(f"Backend technology evaluation failed: {e}")
            return {"backend_options": [], "recommendation": None, "reasoning": "Evaluation failed"}

    def _prune_requirements_for_backend_evaluation(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
            """Prune requirements for backend evaluation."""
            pruned = {}
            
            # Include only requirements relevant for backend evaluation
            relevant_keys = ["scale", "performance", "security", "integration", "data"]
            for key in relevant_keys:
                if key in requirements:
                    pruned[key] = requirements[key]
                    
            # Include technical requirements if available
            if "technical_requirements" in requirements:
                pruned["technical_requirements"] = requirements["technical_requirements"]
                
            return pruned

    def _evaluate_database_technologies(self, requirements_summary: str) -> Dict[str, Any]:
            """Evaluate database technology options using text summary instead of full JSON."""
            try:
                # Create specialized LLM for JSON generation
                llm_json = JsonHandler.create_strict_json_llm(
                    self.llm,
                    max_tokens=self.max_tokens["database_evaluation"]
                )
                
                # Get RAG context for database technologies if available
                rag_context = ""
                if self.rag_retriever:
                    database_query = f"database comparison for web applications with {requirements_summary}"
                    rag_context = self._get_optimized_rag_context(database_query)
            
                # Create task description with the simplified requirements summary
                task_description = f"""
                Evaluate database technology options for this project:
                
                PROJECT REQUIREMENTS SUMMARY:
                {requirements_summary}
                
                {rag_context if rag_context else ""}
                
                Evaluate EXACTLY 3 database technology options with:
                1. Database name and type (SQL/NoSQL)
                2. Scores (1-10) on performance, scalability, flexibility, complexity
                3. Reasoning tied to requirements
                4. Trade-offs
                
                Format your response as VALID JSON with the exact structure shown in the example.
                """
                
                # Create strict JSON template
                messages = JsonHandler.create_strict_json_template(
                    "Database Technology Evaluation",
                    task_description,
                    self.json_examples["database_evaluation"]
                )
                
                # Add tracing configuration
                invoke_config = {
                    "agent_context": f"{self.agent_name}:database_evaluation",
                    "temperature_used": 0.0
                }
                
                # Direct invocation with explicit JSON config
                response = llm_json.invoke(messages, config=invoke_config)
                
                # Use the enhanced parsing
                result = JsonHandler.parse_json_with_error_tracking(
                    JsonHandler._extract_text_content(response), 
                    default_response={"database_options": [], "recommendation": None}
                )
                
                # Validate and limit the number of options
                if "database_options" in result and len(result.get("database_options", [])) > self.max_examples["database_options"]:
                    result["database_options"] = result["database_options"][:self.max_examples["database_options"]]
                
                self.log_info(f"Evaluated {len(result.get('database_options', []))} database technology options")
                self.tech_evaluations["database"] = result
                return result
        
            except Exception as e:
                self.log_warning(f"Database technology evaluation failed: {e}")
                return {"database_options": [], "recommendation": None, "reasoning": "Evaluation failed"}

    def _prune_requirements_for_database_evaluation(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Prune requirements for database evaluation."""
        pruned = {}
        
        # Include only requirements relevant for database evaluation
        data_keys = ["data", "scale", "performance", "security"]
        for key in data_keys:
            if key in requirements:
                pruned[key] = requirements[key]
                
        # Extract data-related requirements
        if "technical_requirements" in requirements:
            data_reqs = []
            for req in requirements["technical_requirements"]:
                if isinstance(req, dict) and any(kw in str(req).lower() for kw in ["data", "database", "storage", "entity"]):
                    data_reqs.append(req)
            if data_reqs:
                pruned["data_requirements"] = data_reqs
                
        return pruned

    def _evaluate_frontend_technologies(self, requirements_summary: str) -> Dict[str, Any]:
        """Evaluate frontend technology options using text summary."""
        try:
            # Create specialized LLM for JSON generation
            llm_json = JsonHandler.create_strict_json_llm(
                self.llm,
                max_tokens=self.max_tokens["frontend_evaluation"]
            )
            
            # Create task description with the simplified requirements summary
            task_description = f"""
            Evaluate frontend technology options for this project:
            
            PROJECT REQUIREMENTS SUMMARY:
            {requirements_summary}
            
            Evaluate EXACTLY 3 frontend technology options with:
            1. Language and framework
            2. Scores (1-10): Developer productivity, Performance, UI capability, Ecosystem
            3. Reasoning tied to requirements
            4. Mobile support strategy
            
            Format your response as VALID JSON with the exact structure shown in the example.
            """
            
            # Create strict JSON template
            messages = JsonHandler.create_strict_json_template(
                "Frontend Technology Evaluation",
                task_description,
                self.json_examples["frontend_evaluation"]
            )
            
            # Add tracing configuration
            invoke_config = {
                "agent_context": f"{self.agent_name}:frontend_evaluation",
                "temperature_used": 0.0
            }
            
            # Direct invocation with explicit JSON config
            response = llm_json.invoke(messages, config=invoke_config)
            
            # Use the enhanced parsing
            result = JsonHandler.parse_json_with_error_tracking(
                JsonHandler._extract_text_content(response), 
                default_response={"frontend_options": [], "recommendation": None}
            )
            
            # Validate and limit the number of options
            if "frontend_options" in result and len(result.get("frontend_options", [])) > self.max_examples["frontend_options"]:
                result["frontend_options"] = result["frontend_options"][:self.max_examples["frontend_options"]]
                
            self.log_info(f"Evaluated {len(result.get('frontend_options', []))} frontend technology options")
            self.tech_evaluations["frontend"] = result
            return result
        
        except Exception as e:
            self.log_warning(f"Frontend technology evaluation failed: {e}")
            return {"frontend_options": [], "recommendation": None, "reasoning": "Evaluation failed"}

    def _prune_requirements_for_frontend_evaluation(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Prune requirements for frontend evaluation."""
        pruned = {}
        
        # Include only requirements relevant for frontend evaluation
        ui_keys = ["user_experience", "performance"]
        for key in ui_keys:
            if key in requirements:
                pruned[key] = requirements[key]
                
        # Extract UI-related requirements
        if "technical_requirements" in requirements:
            ui_reqs = []
            for req in requirements["technical_requirements"]:
                if isinstance(req, dict) and any(kw in str(req).lower() for kw in ["ui", "user", "interface", "mobile", "responsive"]):
                    ui_reqs.append(req)
            if ui_reqs:
                pruned["ui_requirements"] = ui_reqs
                
        return pruned

    def _evaluate_architecture_patterns(self, 
                          requirements_summary: str,
                          backend_choice: str,
                          database_choice: str,
                          frontend_choice: str) -> Dict[str, Any]:
        """Evaluate architecture patterns using text summary."""
        try:
            # Create specialized LLM for JSON generation
            llm_json = JsonHandler.create_strict_json_llm(
                self.llm,
                max_tokens=self.max_tokens["architecture_evaluation"]
            )
            
            # Create task description with the simplified requirements summary
            task_description = f"""
            Evaluate architecture patterns for this project:
            
            PROJECT REQUIREMENTS SUMMARY:
            {requirements_summary}
            
            TECHNICAL CONTEXT:
            - Backend: {backend_choice}
            - Database: {database_choice}
            - Frontend: {frontend_choice}
            
            Evaluate EXACTLY 3 architecture patterns with:
            1. Pattern name 
            2. Scores (1-10): Scalability, Maintainability, Development speed, Complexity
            3. Reasoning tied to requirements
            4. Implementation guidance
            
            Format your response as VALID JSON with the exact structure shown in the example.
            """
            
            # Create strict JSON template
            messages = JsonHandler.create_strict_json_template(
                "Architecture Pattern Evaluation",
                task_description,
                self.json_examples["architecture_evaluation"]
            )
            
            # Add tracing configuration
            invoke_config = {
                "agent_context": f"{self.agent_name}:architecture_evaluation",
                "temperature_used": 0.0
            }
            
            # Direct invocation with explicit JSON config
            response = llm_json.invoke(messages, config=invoke_config)
            
            # Use the enhanced parsing
            result = JsonHandler.parse_json_with_error_tracking(
                JsonHandler._extract_text_content(response), 
                default_response={"architecture_options": [], "recommendation": None}
            )
            
            # Validate and limit the number of options
            if "architecture_options" in result and len(result.get("architecture_options", [])) > self.max_examples["architecture_options"]:
                result["architecture_options"] = result["architecture_options"][:self.max_examples["architecture_options"]]
                
            self.log_info(f"Evaluated {len(result.get('architecture_options', []))} architecture patterns")
            self.tech_evaluations["architecture"] = result
            return result
        
        except Exception as e:
            self.log_warning(f"Architecture pattern evaluation failed: {e}")
            return {"architecture_options": [], "recommendation": None, "reasoning": "Evaluation failed"}

    def _prune_requirements_for_architecture_evaluation(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Prune requirements for architecture evaluation."""
        pruned = {}
        
        # Include only requirements relevant for architecture evaluation
        arch_keys = ["scale", "performance", "security", "integration"]
        for key in arch_keys:
            if key in requirements:
                pruned[key] = requirements[key]
                
        return pruned

    def _synthesize_tech_stack(self, 
                          requirements_summary: str,
                          backend_choice: str,
                          database_choice: str, 
                          frontend_choice: str,
                          architecture_choice: str) -> Dict[str, Any]:
        """Synthesize final tech stack with adaptive retry mechanism."""
        # Create a concrete hard-coded example based on actual choices
        concrete_example = {
            "backend": {
                "language": "Python" if "Python" in backend_choice else "Java",
                "framework": "Django" if "Django" in backend_choice else "Spring",
                "reasoning": "Selected based on project requirements"
            },
            "frontend": {
                "language": "JavaScript",
                "framework": "React" if "React" in frontend_choice else "Angular",
                "reasoning": "Selected based on project requirements"
            },
            "database": {
                "type": database_choice,
                "reasoning": "Selected based on project requirements"
            },
            "architecture_pattern": architecture_choice,
            "deployment_environment": {
                "platform": "AWS",
                "containerization": "Docker"
            },
            "key_libraries_tools": [
                {"name": "Redis", "purpose": "Caching layer"},
                {"name": "Jest", "purpose": "Testing framework"}
            ],
            "estimated_complexity": "Medium"
        }
        
        # Create base instructions 
        base_instructions = f"""Create a comprehensive technology stack specification based on these choices:
    
    BACKEND CHOICE: {backend_choice}
    DATABASE CHOICE: {database_choice}
    FRONTEND CHOICE: {frontend_choice}
    ARCHITECTURE: {architecture_choice}
    
    Project requirements summary:
    {requirements_summary}
    
    Return a complete technology stack specification that includes backend, frontend, database,
    architecture pattern, deployment environment, and key libraries/tools.
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
            example_json=json.dumps(concrete_example, indent=2),
            stage_name="Tech Stack Synthesis",
            max_attempts=3,
            default_response=self._get_default_tech_stack(
                backend_choice, database_choice, frontend_choice, architecture_choice
            ),
            max_tokens=self.max_tokens["tech_stack_synthesis"]
        )
    
        return result

    def _prune_requirements_for_synthesis(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Prune requirements for tech stack synthesis."""
        pruned = {}
        
        # Include only high-level requirements summaries
        for key, value in requirements.items():
            if isinstance(value, dict):
                # Include only key metrics and summary fields
                summary_keys = ["summary", "level", "priority", "complexity"]
                pruned[key] = {k: v for k, v in value.items() if k in summary_keys}
            elif isinstance(value, list) and key == "technical_requirements":
                # Include only top 5 technical requirements
                pruned[key] = value[:min(5, len(value))]
            else:
                pruned[key] = value
                
        return pruned

    def _perform_risk_analysis(self, final_recommendation: Dict[str, Any], 
                     requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Perform risk analysis with token optimization."""
        try:
            # FIXED: Changed temperature from 0.1 to 0.0
            binding_args = {
                "temperature": 0.0,
                "max_output_tokens": self.max_tokens["risk_analysis"]
            }
            llm_json_strict = self.llm.bind(**binding_args)
            
            # Add context for monitoring
            invoke_config = {
                "agent_context": f"{self.agent_name}:risk_analysis",
                "temperature_used": binding_args["temperature"],
                "model_name": getattr(self.llm, "model_name", "unknown")
            }
            
            # Prepare inputs for risk analysis
            recommendation_str = json.dumps(final_recommendation, indent=2)
            requirements_str = json.dumps(requirements, indent=2)
            
            # FIXED: Direct invocation instead of chain
            response = llm_json_strict.invoke(self.risk_analysis_template.format(
                final_recommendation=recommendation_str,
                extracted_requirements=requirements_str
            ), config=invoke_config)
            
            # FIXED: Using parse_json_with_error_tracking
            risk_analysis = JsonHandler.parse_json_with_error_tracking(
                JsonHandler._extract_text_content(response),
                default_response={"risks": []}
            )
            
            # Add risk analysis to final recommendation
            enhanced_recommendation = final_recommendation.copy()
            enhanced_recommendation["risk_analysis"] = risk_analysis
            
            self.log_info(f"Identified {len(risk_analysis.get('risks', []))} risks in technology stack")
            return enhanced_recommendation
            
        except Exception as e:
            self.log_warning(f"Risk analysis failed: {e}")
            return final_recommendation

    def extract_brd_requirements(self, brd_analysis):
        """Extract detailed technical requirements from BRD analysis with token optimization."""
        try:
            # FIXED: Changed temperature from 0.1 to 0.0
            binding_args = {
                "temperature": 0.0,
                "max_output_tokens": self.max_tokens["requirements_extraction"]
            }
            llm_json_strict = self.llm.bind(**binding_args)
            
            # Convert BRD analysis to JSON string for LLM processing
            brd_analysis_str = json.dumps(brd_analysis, indent=2)
            
            # Use the requirements extraction template
            response = llm_json_strict.invoke(self.requirements_extraction_template.format(
                brd_analysis=brd_analysis_str
            ))
            
            # FIXED: Using parse_json_with_error_tracking
            result = JsonHandler.parse_json_with_error_tracking(
                JsonHandler._extract_text_content(response),
                default_response={"technical_requirements": []}
            )
            
            # Log the extraction success
            self.log_info(f"Extracted {len(result.get('technical_requirements', []))} technical requirements")
            
            return result
        except Exception as e:
            self.log_warning(f"Detailed requirements extraction failed: {e}")
            return {
                "technical_requirements": [],
                "simplified_requirements": {
                    "scale": "medium",
                    "data_complexity": "medium",
                    "security_level": "standard",
                    "performance_needs": "standard"
                }
            }

    def get_default_response(self) -> Dict[str, Any]:
        """Returns a default tech stack recommendation when analysis fails."""
        return {
            "status": "error",
            "message": f"An error occurred in {self.agent_name}.",
            "tech_stack_recommendation": {
                "backend": ["Python", "Flask"],
                "frontend": ["React", "TypeScript"],
                "database": ["PostgreSQL"],
                "infrastructure": ["Docker", "AWS"],
                "note": "This is a fallback recommendation based on general best practices."
            },
            "reasoning": "Unable to analyze specific requirements due to processing error.",
            "confidence_score": 0.5
        }

    # If TechStackAdvisorAgent has its own self_reflect method, fix this:
    def self_reflect(self, task_description, result, issues_identified="", improvements_made=""):
        """Delegate to parent class for robust reflection handling."""
        return super().self_reflect(task_description, result, issues_identified, improvements_made)

    def _enhance_requirements_with_metrics(self, requirements: Dict[str, Any], brd_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance extracted requirements with quantitative metrics based on BRD analysis.
        This adds specific numerical values and measurable criteria to requirements.
        """
        enhanced_reqs = requirements.copy() if requirements else {}
        
        # Add scale metrics if available
        if "scale" in enhanced_reqs:
            # Extract user counts if available in BRD
            if "target_audience" in brd_analysis and isinstance(brd_analysis["target_audience"], list):
                audience_size = len(brd_analysis["target_audience"])
                if "scale" not in enhanced_reqs:
                    enhanced_reqs["scale"] = {}
                if isinstance(enhanced_reqs["scale"], dict):
                    enhanced_reqs["scale"]["user_count_estimate"] = audience_size * 100  # Simple estimate
        
        # Add performance metrics based on complexity
        if "requirements" in brd_analysis:
            high_priority_count = sum(1 for req in brd_analysis.get("requirements", []) 
                                   if isinstance(req, dict) and req.get("priority") == "high")
            
            if "performance" not in enhanced_reqs:
                enhanced_reqs["performance"] = {}
            if isinstance(enhanced_reqs["performance"], dict):
                enhanced_reqs["performance"]["high_priority_requirements"] = high_priority_count
        
        # Add constraints based on project risks
        if "risks" in brd_analysis and isinstance(brd_analysis["risks"], list):
            risk_count = len(brd_analysis["risks"])
            if "constraints" not in enhanced_reqs:
                enhanced_reqs["constraints"] = {}
            if isinstance(enhanced_reqs["constraints"], dict):
                enhanced_reqs["constraints"]["identified_risks"] = risk_count
        
        self.log_info(f"Enhanced requirements with metrics")
        return enhanced_reqs

    def _simplify_requirements(self, requirements: Dict[str, Any]) -> Dict[str, str]:
        """
        Convert complex requirement structures into simplified string descriptions
        for easier template usage and token efficiency.
        """
        simplified = {}
        
        # Extract scale requirements
        if "scale" in requirements:
            scale_info = requirements["scale"]
            if isinstance(scale_info, dict):
                # Extract key scale indicators
                user_count = scale_info.get("user_count", "unknown")
                data_volume = scale_info.get("data_volume", "moderate")
                transaction_rate = scale_info.get("transaction_rate", "standard")
                
                # Create readable summary
                simplified["scale"] = f"Users: {user_count}, Data: {data_volume}, Transactions: {transaction_rate}"
            else:
                simplified["scale"] = str(scale_info)
        else:
            simplified["scale"] = "medium scale (default)"
        
        # Data complexity
        if "data" in requirements:
            data_info = requirements["data"]
            if isinstance(data_info, dict):
                complexity = data_info.get("complexity", "medium")
                relationships = data_info.get("relationships", "standard")
                simplified["data_complexity"] = f"{complexity} complexity with {relationships} relationships"
            else:
                simplified["data_complexity"] = str(data_info)
        else:
            simplified["data_complexity"] = "medium complexity (default)"
        
        # Security level
        if "security" in requirements:
            security_info = requirements["security"]
            if isinstance(security_info, dict):
                level = security_info.get("level", security_info.get("requirement", "standard"))
                auth = security_info.get("authentication", "required")
                simplified["security_level"] = f"{level} security with {auth} authentication"
            else:
                simplified["security_level"] = str(security_info)
        else:
            simplified["security_level"] = "standard security (default)"
        
        # Performance needs
        if "performance" in requirements:
            perf_info = requirements["performance"]
            if isinstance(perf_info, dict):
                response_time = perf_info.get("response_time", perf_info.get("latency", "quick"))
                throughput = perf_info.get("throughput", "standard")
                simplified["performance_needs"] = f"{response_time} response time with {throughput} throughput"
            else:
                simplified["performance_needs"] = str(perf_info)
        else:
            simplified["performance_needs"] = "standard performance (default)"
        
        # UI/UX requirements
        if "ui" in requirements or "ux" in requirements:
            ui_info = requirements.get("ui", requirements.get("ux", {}))
            if isinstance(ui_info, dict):
                complexity = ui_info.get("complexity", "medium")
                responsiveness = ui_info.get("responsiveness", "expected")
                simplified["ui_ux_requirements"] = f"{complexity} UI complexity with {responsiveness} responsiveness"
            else:
                simplified["ui_ux_requirements"] = str(ui_info)
        else:
            simplified["ui_ux_requirements"] = "standard UI/UX (default)"
        
        # Mobile requirements
        if "mobile" in requirements:
            mobile_info = requirements.get("mobile", {})
            if isinstance(mobile_info, dict):
                support = mobile_info.get("required", "partial")
                simplified["mobile_requirements"] = f"{support} mobile support"
            else:
                simplified["mobile_requirements"] = str(mobile_info)
        else:
            simplified["mobile_requirements"] = "basic mobile support (default)"
        
        self.log_info(f"Simplified requirements into descriptive strings")
        return simplified

    def _extract_top_choice(self, evaluation: Dict[str, Any], component_type: str) -> str:
        """Extract the top choice from evaluation results."""
        try:
            if not evaluation or not isinstance(evaluation, dict):
                return f"Default {component_type}"
                
            # Different component types have different structures
            if component_type == "backend":
                # FIXED: Correct key name for backend options
                if "recommendation" in evaluation and isinstance(evaluation["recommendation"], dict):
                    language = evaluation["recommendation"].get("language", "")
                    framework = evaluation["recommendation"].get("framework", "")
                    if language and framework:
                        return f"{language} with {framework}"
                    elif language:
                        return language
                
                # Fallback to options list
                options = evaluation.get("backend_options", [])
                if options and len(options) > 0:
                    language = options[0].get("language", "")
                    framework = options[0].get("framework", "")
                    if language and framework:
                        return f"{language} with {framework}"
                    elif language:
                        return language
                    
            elif component_type == "database":
                # FIXED: Correct key name for database options
                if "recommendation" in evaluation and isinstance(evaluation["recommendation"], dict):
                    return evaluation["recommendation"].get("name", f"Default {component_type}")
                    
                options = evaluation.get("database_options", [])
                if options and len(options) > 0:
                    return options[0].get("name", f"Default {component_type}")
                    
            elif component_type == "frontend":
                if "recommendation" in evaluation and isinstance(evaluation["recommendation"], dict):
                    language = evaluation["recommendation"].get("language", "")
                    framework = evaluation["recommendation"].get("framework", "")
                    if language and framework:
                        return f"{language} with {framework}"
                    elif language:
                        return language
                    
                options = evaluation.get("frontend_options", [])
                if options and len(options) > 0:
                    language = options[0].get("language", "")
                    framework = options[0].get("framework", "")
                    if language and framework:
                        return f"{language} with {framework}"
                    elif language:
                        return options[0].get("option_name", f"Default {component_type}")
                    
            elif component_type == "architecture":
                if "recommendation" in evaluation and isinstance(evaluation["recommendation"], dict):
                    return evaluation["recommendation"].get("pattern", f"Default {component_type}")
                    
                # FIXED: Correct key name for architecture options
                options = evaluation.get("architecture_options", [])
                if options and len(options) > 0:
                    return options[0].get("pattern", f"Default {component_type}")
                    
            # If we couldn't find a match or the structure is unexpected
            return f"Default {component_type}"
        except Exception as e:
            self.log_warning(f"Error extracting top {component_type} choice: {str(e)}")
            return f"Default {component_type}"

    def _count_evaluated_technologies(self) -> int:
        """Count the total number of technology options evaluated across all categories."""
        total = 0
        
        # Count backend options
        if "backend" in self.tech_evaluations and "backend_options" in self.tech_evaluations["backend"]:
            total += len(self.tech_evaluations["backend"]["backend_options"])
            
        # Count database options
        if "database" in self.tech_evaluations and "database_options" in self.tech_evaluations["database"]:
            total += len(self.tech_evaluations["database"]["database_options"])
            
        # Count frontend options
        if "frontend" in self.tech_evaluations and "frontend_options" in self.tech_evaluations["frontend"]:
            total += len(self.tech_evaluations["frontend"]["frontend_options"])
            
        # Count architecture options
        if "architecture" in self.tech_evaluations and "architecture_options" in self.tech_evaluations["architecture"]:
            total += len(self.tech_evaluations["architecture"]["architecture_options"])
            
        return total

    def _fallback_tech_stack_synthesis(self, backend_eval, database_eval, frontend_eval, architecture_eval) -> Dict[str, Any]:
        """Create a fallback tech stack when full synthesis fails."""
        fallback_stack = {
            "backend": {
                "language": "Unknown",
                "framework": "Unknown",
                "reasoning": "Fallback synthesis due to synthesis failure"
            },
            "frontend": {
                "language": "Unknown", 
                "framework": "Unknown",
                "reasoning": "Fallback synthesis due to synthesis failure"
            },
            "database": {
                "type": "Unknown",
                "reasoning": "Fallback synthesis due to synthesis failure"
            },
            "architecture_pattern": "Layered Architecture",
            "deployment_environment": {
                "platform": "Cloud",
                "containerization": "Docker",
                "reasoning": "Generic deployment environment"
            },
            "key_libraries_tools": [],
            "estimated_complexity": "Medium",
            "overall_reasoning": "This is a fallback recommendation created due to synthesis failure."
        }
        
        # Try to extract backend from evaluation
        backend_choice = self._extract_top_choice(backend_eval, "backend")
        if backend_choice and "Unknown" not in backend_choice:
            parts = backend_choice.split(" with ")
            if len(parts) == 2:
                fallback_stack["backend"]["language"] = parts[0]
                fallback_stack["backend"]["framework"] = parts[1]
        
        # Try to extract database from evaluation
        database_choice = self._extract_top_choice(database_eval, "database")
        if database_choice and "Unknown" not in database_choice:
            fallback_stack["database"]["type"] = database_choice
        
        # Try to extract frontend from evaluation
        frontend_choice = self._extract_top_choice(frontend_eval, "frontend")
        if frontend_choice and "Unknown" not in frontend_choice:
            parts = frontend_choice.split(" with ")
            if len(parts) == 2:
                fallback_stack["frontend"]["language"] = parts[0]
                fallback_stack["frontend"]["framework"] = parts[1]
        
        # Try to extract architecture pattern
        architecture_choice = self._extract_top_choice(architecture_eval, "architecture")
        if architecture_choice and "Unknown" not in architecture_choice:
            fallback_stack["architecture_pattern"] = architecture_choice
        
        return fallback_stack

    def log_execution_summary(self, final_response):
        """Log a summary of the tech stack advisory execution."""
        self.log_info(f"Tech stack recommendation complete with {len(self.recommendation_stages)} stages")
        
        # Log selected technology components
        if "backend" in final_response:
            self.log_info(f"Recommended backend: {final_response.get('backend', {}).get('language', 'Unknown')} with {final_response.get('backend', {}).get('framework', 'Unknown')}")
        
        if "database" in final_response:
            self.log_info(f"Recommended database: {final_response.get('database', {}).get('type', 'Unknown')}")
        
        if "frontend" in final_response:
            self.log_info(f"Recommended frontend: {final_response.get('frontend', {}).get('language', 'Unknown')} with {final_response.get('frontend', {}).get('framework', 'Unknown')}")
        
        if "architecture_pattern" in final_response:
            self.log_info(f"Recommended architecture: {final_response.get('architecture_pattern', 'Unknown')}")
        
        # Log complexity assessment
        if "estimated_complexity" in final_response:
            self.log_info(f"Estimated implementation complexity: {final_response.get('estimated_complexity', 'Unknown')}")
        
        # Log risk assessment
        if "risk_analysis" in final_response and "risks" in final_response["risk_analysis"]:
            risk_count = len(final_response["risk_analysis"]["risks"])
            self.log_info(f"Identified {risk_count} implementation risks")
    



    def _initialize_llm_for_tech_stack(self):
        """Initialize specialized LLM configuration for tech stack evaluation."""
        # Create a JSON-specific LLM with explicit instructions
        self.json_llm = JsonHandler.create_strict_json_llm(
            self.llm, 
            max_tokens=8192,
        )
        
        # Add preflight configuration to ensure model can handle JSON
        from langchain_core.output_parsers import JsonOutputParser
        self.json_parser = JsonOutputParser()
        
        # Create prompt templates that use the strict JSON format
        self._initialize_prompt_templates()
        
        self.log_info("Initialized specialized JSON-mode LLM for tech stack evaluation")
    
    def _extract_key_requirements(self, requirements: Dict[str, Any]) -> str:
        """Extract a simple text summary of key requirements for prompt use."""
        summary_parts = []
        
        # Add scale information
        if "scale" in requirements:
            if isinstance(requirements["scale"], dict):
                scale_info = requirements["scale"].get("summary", "medium scale")
                summary_parts.append(f"scale: {scale_info}")
            else:
                summary_parts.append(f"scale: {str(requirements['scale'])}")
                
        # Add security information
        if "security" in requirements:
            if isinstance(requirements["security"], dict):
                security_info = requirements["security"].get("level", "standard security")
                summary_parts.append(f"security: {security_info}")
            else:
                summary_parts.append(f"security: {str(requirements['security'])}")
        
        # Add performance information
        if "performance" in requirements:
            if isinstance(requirements["performance"], dict):
                perf_info = requirements["performance"].get("summary", "standard performance")
                summary_parts.append(f"performance: {perf_info}")
            else:
                summary_parts.append(f"performance: {requirements['performance']}")
        
        # If we don't have much, add a default
        if len(summary_parts) < 2:
            summary_parts.append("standard web application functionality")
        
        return ", ".join(summary_parts)

    def _create_prompt_summary(self, requirements: Dict[str, Any]) -> str:
        """
        Create a concise, human-readable text summary of requirements for prompts.
        This prevents the model from being overwhelmed by large JSON structures.
        """
        summary_parts = []
        
        # Extract key information in sentence form
        if "scale" in requirements and isinstance(requirements["scale"], dict):
            users = requirements["scale"].get("user_count", "unknown users")
            data = requirements["scale"].get("data_volume", "moderate data volume")
            txn = requirements["scale"].get("transaction_rate", "standard transaction rate")
            summary_parts.append(f"Scale requirements: {users} users with {data} and {txn}.")
        
        if "security" in requirements:
            if isinstance(requirements["security"], dict):
                level = requirements["security"].get("level", "standard")
                auth = requirements["security"].get("authentication", "required")
                summary_parts.append(f"Security needs: {level} level with {auth} authentication.")
            else:
                summary_parts.append(f"Security needs: {requirements['security']}.")
        
        if "performance" in requirements:
            if isinstance(requirements["performance"], dict):
                response = requirements["performance"].get("response_time", "")
                if response:
                    summary_parts.append(f"Performance: {response} response time required.")
            else:
                summary_parts.append(f"Performance: {requirements['performance']}.")
        
        # Add technical requirements in simple form
        tech_reqs = []
        for req in requirements.get("technical_requirements", [])[:5]:  # Limit to 5 key requirements
            if isinstance(req, dict):
                desc = req.get("description", "")
                cat = req.get("category", "")
                if desc:
                    tech_reqs.append(f"{desc} ({cat})" if cat else desc)
        
        if tech_reqs:
            summary_parts.append("Technical requirements: " + "; ".join(tech_reqs) + ".")
        
        # Add constraints if available
        if "constraints" in requirements and isinstance(requirements["constraints"], dict):
            constraints = []
            for key, value in requirements["constraints"].items():
                constraints.append(f"{key}: {value}")
            if constraints:
                summary_parts.append("Constraints: " + ", ".join(constraints) + ".")
        
        # Return the full summary or a default if empty
        if not summary_parts:
            return "Standard web application with moderate scale, security, and performance requirements."
        
        return " ".join(summary_parts)

    def _create_requirements_summary(self, brd_analysis: Dict[str, Any]) -> str:
        """Creates a concise string summary of requirements for more reliable prompts."""
        if not brd_analysis:
            return "No requirements specified."
        
        summary_parts = []
        
        # Project overview
        project_name = brd_analysis.get("project_name", "Unnamed Project")
        project_summary = brd_analysis.get("project_summary", "")
        summary_parts.append(f"PROJECT: {project_name}")
        if project_summary:
            summary_parts.append(f"SUMMARY: {project_summary}")
        
        # Goals
        goals = brd_analysis.get("project_goals", [])
        if goals:
            summary_parts.append("\nGOALS:")
            for i, goal in enumerate(goals[:3]):  # Limit to top 3 goals
                summary_parts.append(f"- {goal}")
        
        # Requirements
        requirements = brd_analysis.get("requirements", [])
        if requirements:
            func_reqs = [r for r in requirements if r.get("category", "").lower() in 
                        ["functional", "feature", "user story"]]
            tech_reqs = [r for r in requirements if r.get("category", "").lower() in 
                        ["technical", "non-functional", "performance", "security"]]
            
            # Functional requirements
            if func_reqs:
                summary_parts.append("\nKEY FUNCTIONAL REQUIREMENTS:")
                for i, req in enumerate(func_reqs[:5]):  # Limit to top 5
                    summary_parts.append(f"- {req.get('title', '')}: {req.get('description', '')}")
            
            # Technical requirements
            if tech_reqs:
                summary_parts.append("\nKEY TECHNICAL REQUIREMENTS:")
                for i, req in enumerate(tech_reqs[:5]):  # Limit to top 5
                    summary_parts.append(f"- {req.get('title', '')}: {req.get('description', '')}")
        
        # Constraints
        constraints = brd_analysis.get("constraints", [])
        if constraints and isinstance(constraints, list):
            summary_parts.append("\nCONSTRAINTS:")
            for i, constraint in enumerate(constraints[:3]):  # Limit to top 3
                if isinstance(constraint, str):
                    summary_parts.append(f"- {constraint}")
                elif isinstance(constraint, dict):
                    summary_parts.append(f"- {constraint.get('description', '')}")
    
        # User types/audience
        users = brd_analysis.get("target_audience", [])
        if users:
            summary_parts.append("\nUSER TYPES: " + ", ".join(users[:3]))
    
        # Generate final summary
        full_summary = "\n".join(summary_parts)
        
        # If summary is too long, create a more condensed version
        if len(full_summary) > 1500:
            return self._create_condensed_summary(brd_analysis)
            
        return full_summary








