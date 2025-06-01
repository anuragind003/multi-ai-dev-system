import json
from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import PromptTemplate
from typing import Optional, Dict, Any, List
import monitoring
from .base_agent import BaseAgent

class BRDAnalystAgent(BaseAgent):
    """Enhanced BRD Analyst Agent with comprehensive analysis capabilities,
    risk assessment, gap detection, and advanced validation."""
    
    def __init__(self, llm: BaseLanguageModel, memory, rag_retriever: Optional[BaseRetriever] = None):
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="BRD Analyst Agent",
            temperature=0.3,  # Balanced analysis and extraction
            rag_retriever=rag_retriever
        )
        
        # Initialize prompt template with enhanced analysis capabilities
        self.prompt_template = PromptTemplate(
            template="""
            You are an expert Business Requirements Document (BRD) Analyst AI with extensive experience in software development projects.
            Your task is to thoroughly analyze the provided BRD, extract all key information, identify gaps, assess risks, 
            detect inconsistencies, and present it in a structured JSON format.

            **IMPORTANT**: Do NOT extract requirements to match the output structure examples below. 
            You must analyze the actual BRD content and identify requirements that truly exist in the document.

            **Deep Analysis Instructions:**
            Analyze the BRD thoroughly using these steps:
            1. Extract explicit requirements and categorize them appropriately
            2. Identify implicit requirements that are suggested but not clearly stated
            3. Detect potential gaps where requirements may be missing
            4. Assess risks and dependencies between requirements
            5. Identify inconsistencies or conflicts between requirements
            6. Evaluate the quality and completeness of the BRD

            Extract the following information:

            1. **Project Overview**: Comprehensive summary of project goals, scope, and business context
            2. **Functional Requirements**: All explicit and implicit features/capabilities needed
            3. **Non-Functional Requirements**: All quality attributes across multiple dimensions
            4. **User Roles & Permissions**: Complete user hierarchy and detailed access control needs
            5. **Data Requirements**: All data entities, relationships, and governance requirements
            6. **Integration Requirements**: All external systems and data exchange needs
            7. **Business Rules**: All logic, constraints, and domain-specific rules
            8. **Risks & Gaps**: Identify risks, ambiguities, and missing information
            9. **Dependencies**: Capture relationships and dependencies between requirements

            {format_instructions}

            **Output Requirements:**
            Generate ONLY a valid JSON object with the following structure:
            {{
                "project_overview": {{
                    "project_name": "string",
                    "description": "string",
                    "objectives": ["array of main objectives"],
                    "scope": "string",
                    "business_context": "string",
                    "stakeholders": ["array of key stakeholders"]
                }},
                "functional_requirements": [
                    {{
                        "id": "string",
                        "category": "string",
                        "description": "string",
                        "priority": "High/Medium/Low",
                        "source": "Explicit/Implicit", 
                        "acceptance_criteria": ["array of criteria"],
                        "dependencies": ["IDs of dependent requirements"]
                    }}
                ],
                "non_functional_requirements": {{
                    "performance": ["array of performance requirements"],
                    "security": ["array of security requirements"],
                    "scalability": ["array of scalability requirements"],
                    "usability": ["array of usability requirements"],
                    "reliability": ["array of reliability requirements"],
                    "compliance": ["array of compliance requirements"],
                    "compatibility": ["array of compatibility requirements"],
                    "maintainability": ["array of maintainability requirements"]
                }},
                "user_roles": [
                    {{
                        "role_name": "string",
                        "description": "string",
                        "permissions": ["array of permissions"],
                        "user_stories": ["array of key user stories/journeys"]
                    }}
                ],
                "data_requirements": [
                    {{
                        "entity": "string",
                        "description": "string",
                        "attributes": ["array of key attributes with data types"],
                        "relationships": ["array of relationships to other entities"],
                        "volume_estimates": "string describing expected data volumes",
                        "retention_policy": "string describing data retention needs"
                    }}
                ],
                "integration_requirements": [
                    {{
                        "system": "string",
                        "type": "API/Database/File/etc",
                        "description": "string",
                        "data_flow": "Inbound/Outbound/Bidirectional",
                        "frequency": "Real-time/Batch/Daily/etc",
                        "criticality": "High/Medium/Low"
                    }}
                ],
                "business_rules": [
                    {{
                        "rule_id": "string",
                        "description": "string",
                        "condition": "string",
                        "action": "string",
                        "exceptions": ["array of exception cases"]
                    }}
                ],
                "constraints": [
                    {{
                        "type": "Technical/Business/Legal/etc",
                        "description": "string",
                        "impact": "string"
                    }}
                ],
                "risks_and_gaps": [
                    {{
                        "type": "Risk/Gap/Ambiguity/Inconsistency",
                        "description": "string",
                        "affected_areas": ["array of affected requirement IDs or areas"],
                        "severity": "High/Medium/Low",
                        "recommendation": "string with suggested mitigation or clarification"
                    }}
                ],
                "quality_assessment": {{
                    "completeness_score": "number between 1-10",
                    "clarity_score": "number between 1-10", 
                    "consistency_score": "number between 1-10",
                    "testability_score": "number between 1-10",
                    "overall_quality": "number between 1-10",
                    "improvement_recommendations": ["array of recommendations to improve BRD quality"]
                }}
            }}

            --- BRD ---
            {brd_text}
            --- END BRD ---
            """,
            input_variables=["brd_text"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()},
        )
    
    def get_default_structure(self) -> Dict[str, Any]:
        """Define enhanced default structure for BRD analysis response."""
        return {
            "project_overview": {
                "project_name": "Unknown Project",
                "description": "No description available",
                "objectives": [],
                "scope": "Not specified",
                "business_context": "Not provided",
                "stakeholders": []
            },
            "functional_requirements": [],
            "non_functional_requirements": {
                "performance": [],
                "security": [],
                "scalability": [],
                "usability": [],
                "reliability": [],
                "compliance": [],
                "compatibility": [],
                "maintainability": []
            },
            "user_roles": [],
            "data_requirements": [],
            "integration_requirements": [],
            "business_rules": [],
            "constraints": [],
            "risks_and_gaps": [],
            "quality_assessment": {
                "completeness_score": 0,
                "clarity_score": 0,
                "consistency_score": 0,
                "testability_score": 0,
                "overall_quality": 0,
                "improvement_recommendations": [
                    "Insufficient BRD data provided for analysis"
                ]
            }
        }
    
    def get_default_response(self) -> Dict[str, Any]:
        """Get enhanced default response when analysis fails completely."""
        default_structure = self.get_default_structure()
        default_structure["project_overview"]["project_name"] = "Analysis Failed"
        default_structure["project_overview"]["description"] = "BRD analysis encountered errors"
        default_structure["risks_and_gaps"].append({
            "type": "Gap",
            "description": "Analysis failure prevented complete extraction of requirements",
            "affected_areas": ["All"],
            "severity": "High",
            "recommendation": "Review BRD manually or provide more complete information"
        })
        return default_structure
    
    def run(self, raw_brd: str) -> Dict[str, Any]:
        """
        Analyze the BRD with comprehensive analysis, gap detection, and quality assessment.
        """
        self.log_start("Starting enhanced BRD analysis")
        self.log_info(f"Using temperature {self.temperature} for balanced analysis and extraction")
        
        # Validate input
        if not raw_brd:
            self.log_warning("Empty BRD provided")
            default_response = self.get_default_response()
            default_response["project_overview"]["description"] = "No BRD content provided"
            return default_response
        
        if len(raw_brd.strip()) < 100:
            self.log_warning("BRD content too short for meaningful analysis")
            default_response = self.get_default_response()
            default_response["project_overview"]["description"] = "BRD content insufficient for analysis"
            return default_response
        
        # Use RAG if available to enhance domain knowledge
        context = ""
        if self.rag_retriever:
            self.log_info("Retrieving relevant context from knowledge base")
            try:
                context = self.get_rag_context(raw_brd[:1000], max_docs=3)
                self.log_info(f"Retrieved {len(context.split())} words of context")
            except Exception as e:
                self.log_warning(f"RAG retrieval failed: {e}")
        
        try:
            # Execute LLM chain with inputs
            self.log_info("Executing deep BRD analysis")
            response = self.execute_with_monitoring(
                self.execute_llm_chain,
                {"brd_text": raw_brd}
            )
            
            # Enhanced validation of response structure
            required_keys = [
                "project_overview", "functional_requirements", "non_functional_requirements",
                "user_roles", "data_requirements", "integration_requirements", 
                "business_rules", "constraints", "risks_and_gaps", "quality_assessment"
            ]
            
            validated_response = self.validate_response_structure(response, required_keys)
            
            # Perform additional validation on response quality
            validated_response = self.enhance_response_quality(validated_response, raw_brd)
            
            # Log execution summary
            self.log_execution_summary(validated_response)
            
            return validated_response
            
        except Exception as e:
            self.log_error(f"BRD analysis failed completely: {e}")
            return self.get_default_response()
    
    def enhance_response_quality(self, response: Dict[str, Any], raw_brd: str) -> Dict[str, Any]:
        """Add additional quality checks and enhancements to the response."""
        # Ensure functional requirements have IDs
        if "functional_requirements" in response:
            for i, req in enumerate(response["functional_requirements"]):
                if "id" not in req or not req["id"]:
                    req["id"] = f"FR{i+1:03d}"
        
        # Check for missing acceptance criteria
        functional_reqs_without_criteria = 0
        if "functional_requirements" in response:
            for req in response["functional_requirements"]:
                if "acceptance_criteria" not in req or not req["acceptance_criteria"]:
                    functional_reqs_without_criteria += 1
                    req["acceptance_criteria"] = ["Criteria needs to be defined"]
        
        # If many requirements lack acceptance criteria, note it as a risk
        if functional_reqs_without_criteria > 0:
            if "risks_and_gaps" not in response:
                response["risks_and_gaps"] = []
            
            response["risks_and_gaps"].append({
                "type": "Gap",
                "description": f"{functional_reqs_without_criteria} functional requirements lack acceptance criteria",
                "affected_areas": ["Testability", "Quality Assurance"],
                "severity": "Medium",
                "recommendation": "Define clear acceptance criteria for all requirements"
            })
        
        # Ensure quality assessment has scores
        if "quality_assessment" not in response:
            response["quality_assessment"] = {
                "completeness_score": 5,
                "clarity_score": 5,
                "consistency_score": 5,
                "testability_score": 5,
                "overall_quality": 5,
                "improvement_recommendations": ["Auto-generated quality assessment"]
            }
        
        # Calculate word count to estimate BRD comprehensiveness
        word_count = len(raw_brd.split())
        if word_count < 500 and "quality_assessment" in response:
            if "improvement_recommendations" not in response["quality_assessment"]:
                response["quality_assessment"]["improvement_recommendations"] = []
            
            response["quality_assessment"]["improvement_recommendations"].append(
                "BRD appears brief. Consider expanding with more detailed requirements."
            )
        
        return response
    
    def validate_response_structure(self, response: Dict[str, Any], required_keys: List[str]) -> Dict[str, Any]:
        """Enhanced validation that maintains as much data as possible."""
        default_structure = self.get_default_structure()
        
        # If response is empty or not a dict, return default
        if not response or not isinstance(response, dict):
            self.log_warning("LLM returned invalid response structure")
            return default_structure
        
        # Create a validated response, merging with defaults for missing sections
        validated_response = {}
        
        for key in required_keys:
            if key not in response or not response[key]:
                self.log_warning(f"Missing {key} in response, using default")
                validated_response[key] = default_structure.get(key)
            else:
                validated_response[key] = response[key]
        
        # Include any extra keys that weren't in required_keys but were in response
        for key in response:
            if key not in required_keys:
                validated_response[key] = response[key]
        
        return validated_response
    
    def log_execution_summary(self, response: Dict[str, Any]):
        """Enhanced execution summary with quality metrics."""
        func_reqs = len(response.get("functional_requirements", []))
        user_roles = len(response.get("user_roles", []))
        data_entities = len(response.get("data_requirements", []))
        integrations = len(response.get("integration_requirements", []))
        business_rules = len(response.get("business_rules", []))
        risks = len(response.get("risks_and_gaps", []))
        
        project_name = response.get("project_overview", {}).get("project_name", "Unknown")
        
        # Quality assessment values
        quality = response.get("quality_assessment", {})
        completeness = quality.get("completeness_score", "N/A")
        clarity = quality.get("clarity_score", "N/A")
        overall = quality.get("overall_quality", "N/A")
        
        summary = (f"Analysis complete for '{project_name}' - {func_reqs} functional requirements, "
                 f"{user_roles} user roles, {data_entities} data entities, "
                 f"{integrations} integrations, {business_rules} business rules, "
                 f"{risks} risks/gaps identified")
        
        self.log_success(summary)
        
        quality_summary = f"BRD Quality Assessment - Completeness: {completeness}/10, " + \
                          f"Clarity: {clarity}/10, Overall: {overall}/10"
        
        self.log_info(quality_summary)
        
        # Detailed breakdown
        self.log_info(f"   Project: {project_name}")
        self.log_info(f"   Functional Requirements: {func_reqs}")
        self.log_info(f"   User Roles: {user_roles}")
        self.log_info(f"   Data Entities: {data_entities}")
        self.log_info(f"   Integrations: {integrations}")
        self.log_info(f"   Business Rules: {business_rules}")
        self.log_info(f"   Risks & Gaps: {risks}")
        
        # Log high severity risks for immediate attention
        high_severity_risks = [r for r in response.get("risks_and_gaps", []) 
                              if r.get("severity") == "High"]
        
        if high_severity_risks:
            self.log_warning(f"Found {len(high_severity_risks)} high-severity risks that need attention")
            for risk in high_severity_risks:
                self.log_warning(f"   HIGH RISK: {risk.get('description')}")