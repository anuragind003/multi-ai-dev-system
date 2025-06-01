import json
from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import PromptTemplate
from typing import Optional, Dict, Any, List
import monitoring
from .base_agent import BaseAgent

class TechStackAdvisorAgent(BaseAgent):
    """Enhanced Tech Stack Advisor Agent that recommends technology stack based solely on BRD analysis."""
    
    def __init__(self, llm: BaseLanguageModel, memory, rag_retriever: Optional[BaseRetriever] = None):
        super().__init__(llm, memory, "TechStackAdvisorAgent", temperature=0.2, rag_retriever=rag_retriever)
        
        self.prompt_template = PromptTemplate(
            template="""
            You are an expert Tech Stack Advisor AI.
            Your task is to recommend an optimal technology stack based on careful analysis of the provided Business Requirements Document (BRD).
            
            **Important**: Do NOT suggest technologies based on this prompt's examples. You must analyze the BRD requirements and select the most appropriate technologies based on their actual merits and fit for the specific project.
            
            {project_context}
            
            **Requirements Analysis:**
            Scale: {scale}
            Data Complexity: {data_complexity}
            Security Requirements: {security_level}
            Performance Needs: {performance_needs}
            Integration Points: {integration_points}
            
            Analyze the following BRD information carefully to extract:
            1. Scale and complexity requirements
            2. Performance needs
            3. Security requirements
            4. Data handling needs
            5. Integration requirements
            6. User experience expectations
            7. Deployment and hosting constraints
            
            **BRD Analysis:**
            {brd_analysis}
            
            {format_instructions}
            
            **Output Requirements:**
            Generate ONLY a valid JSON object with the following structure.
            Each recommendation must include specific reasoning tied to BRD requirements:
            
            {{
                "backend": {{
                    "language": "recommend most appropriate language based on BRD",
                    "framework": "recommend most appropriate framework based on BRD",
                    "reasoning": "detailed reasoning based on specific BRD requirements"
                }},
                "frontend": {{
                    "language": "recommend most appropriate language based on BRD",
                    "framework": "recommend most appropriate framework based on BRD",
                    "reasoning": "detailed reasoning based on specific BRD requirements"
                }},
                "database": {{
                    "type": "recommend most appropriate database based on BRD",
                    "reasoning": "detailed reasoning based on data requirements in the BRD"
                }},
                "architecture_pattern": "recommend most appropriate architecture pattern",
                "deployment_environment": {{
                    "platform": "recommend most appropriate platform based on BRD",
                    "containerization": "recommend appropriate containerization strategy",
                    "reasoning": "detailed reasoning based on specific BRD requirements"
                }},
                "key_libraries_tools": [
                    {{
                        "name": "specific library/tool name",
                        "category": "tool category",
                        "reasoning": "explain which specific BRD requirement this addresses"
                    }}
                ],
                "estimated_complexity": "Low/Medium/High based on BRD complexity",
                "overall_reasoning": "comprehensive explanation of how recommendations match BRD requirements"
            }}
            """,
            input_variables=["brd_analysis", "project_context", "scale", "data_complexity", 
                            "security_level", "performance_needs", "integration_points"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()}
        )
    
    def get_default_structure(self) -> Dict[str, Any]:
        """Define default structure for tech stack recommendation."""
        return {
            "backend": {
                "language": "Python",
                "framework": "Flask",
                "reasoning": "Default choice for balanced performance and development speed"
            },
            "frontend": {
                "language": "JavaScript",
                "framework": "React",
                "reasoning": "Default choice for responsive single-page applications"
            },
            "database": {
                "type": "PostgreSQL",
                "reasoning": "Default choice for reliable relational data storage"
            },
            "architecture_pattern": "Monolithic",
            "deployment_environment": {
                "platform": "AWS",
                "containerization": "Docker",
                "reasoning": "Default choice for scalable cloud deployment"
            },
            "key_libraries_tools": [
                {
                    "name": "SQLAlchemy",
                    "category": "ORM",
                    "reasoning": "Standard ORM for database interactions"
                },
                {
                    "name": "Jest",
                    "category": "Testing",
                    "reasoning": "Industry standard for frontend testing"
                }
            ],
            "estimated_complexity": "Medium",
            "overall_reasoning": "Default technology stack with balanced trade-offs suitable for typical web applications"
        }
    
    def get_default_response(self) -> Dict[str, Any]:
        """Get default response when recommendation fails."""
        default_structure = self.get_default_structure()
        return default_structure
    
    def extract_brd_requirements(self, brd_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key requirements from BRD analysis that influence tech stack decisions."""
        requirements = {
            "scale": "medium",  # default
            "data_complexity": "medium",  # default
            "security_level": "standard",  # default
            "performance_needs": "moderate",  # default
            "integration_points": [],
            "user_experience": "standard",
            "mobile_requirements": False,
            "regulatory_compliance": [],
            "budget_constraints": "medium"
        }
        
        try:
            # Extract scale and complexity from multiple sources
            if "project_overview" in brd_analysis:
                # Check scope
                scope = brd_analysis["project_overview"].get("scope", "").lower()
                if any(term in scope for term in ["enterprise", "large", "global", "high volume", "complex"]):
                    requirements["scale"] = "large"
                elif any(term in scope for term in ["small", "simple", "basic", "minimal"]):
                    requirements["scale"] = "small"
                    
                # Check objectives for scale indicators
                objectives = brd_analysis["project_overview"].get("objectives", [])
                if objectives and isinstance(objectives, list):
                    for obj in objectives:
                        if isinstance(obj, str):
                            if any(term in obj.lower() for term in ["scalable", "high volume", "enterprise", "global"]):
                                requirements["scale"] = "large"
                        
            # Extract data complexity from multiple sources
            if "data_requirements" in brd_analysis and brd_analysis["data_requirements"]:
                # Check number of entities
                data_entities = len(brd_analysis["data_requirements"])
                if data_entities > 10:
                    requirements["data_complexity"] = "high"
                elif data_entities <= 3:
                    requirements["data_complexity"] = "low"
            
                # Check for complex relationships
                complex_relations = 0
                for entity in brd_analysis["data_requirements"]:
                    if "relationships" in entity and isinstance(entity["relationships"], list):
                        complex_relations += len(entity["relationships"])
            
                if complex_relations > 15:
                    requirements["data_complexity"] = "high"
                    
            # Extract security requirements
            if "non_functional_requirements" in brd_analysis and "security" in brd_analysis["non_functional_requirements"]:
                security_reqs = brd_analysis["non_functional_requirements"]["security"]
                security_keywords = ["encryption", "compliance", "oauth", "2fa", "audit", "gdpr", "hipaa", "pci", 
                                    "sensitive", "confidential", "authentication", "authorization"]
                
                # Check for high security indicators
                if any(any(keyword in req.lower() for keyword in security_keywords) for req in security_reqs):
                    requirements["security_level"] = "high"
                    
                # Extract specific compliance requirements
                compliance_terms = ["gdpr", "hipaa", "pci", "sox", "iso27001", "ccpa", "ferpa"]
                for req in security_reqs:
                    for term in compliance_terms:
                        if term.lower() in req.lower():
                            requirements["regulatory_compliance"].append(term.upper())
            
            # Extract integration points
            if "integration_requirements" in brd_analysis:
                for integration in brd_analysis["integration_requirements"]:
                    if "system" in integration:
                        requirements["integration_points"].append(integration["system"])
                        
                    # Check for real-time integration needs
                    if "frequency" in integration and "real-time" in integration["frequency"].lower():
                        requirements["performance_needs"] = "high"
            
            # Extract performance needs
            if "non_functional_requirements" in brd_analysis and "performance" in brd_analysis["non_functional_requirements"]:
                perf_reqs = brd_analysis["non_functional_requirements"]["performance"]
                perf_keywords = ["real-time", "low latency", "high throughput", "millions", "thousands", "concurrent", "fast"]
                
                if any(any(keyword in req.lower() for keyword in perf_keywords) for req in perf_reqs):
                    requirements["performance_needs"] = "high"
            
            # Check for mobile requirements
            if "functional_requirements" in brd_analysis:
                for req in brd_analysis["functional_requirements"]:
                    if "description" in req and isinstance(req["description"], str):
                        if any(term in req["description"].lower() for term in ["mobile", "ios", "android", "app", "smartphone"]):
                            requirements["mobile_requirements"] = True
            
            # Extract budget constraints if available
            if "constraints" in brd_analysis:
                for constraint in brd_analysis["constraints"]:
                    if "type" in constraint and "description" in constraint:
                        if "budget" in constraint["type"].lower() or "cost" in constraint["type"].lower():
                            description = constraint["description"].lower()
                            if any(term in description for term in ["limited", "tight", "constrained", "low"]):
                                requirements["budget_constraints"] = "low"
                            elif any(term in description for term in ["high", "generous", "unlimited", "substantial"]):
                                requirements["budget_constraints"] = "high"
        
            self.log_info(f"Extracted requirements: {json.dumps(requirements, indent=2)}")
            return requirements
            
        except Exception as e:
            self.log_error(f"Error extracting requirements: {e}")
            return requirements
    
    def run(self, brd_analysis: Dict[str, Any], project_context: str = "") -> Dict[str, Any]:
        """
        Generate technology stack recommendations based on BRD analysis and optional project context.
        """
        self.log_start("Starting tech stack analysis based on BRD requirements")
        
        # Validate input
        if not brd_analysis or not isinstance(brd_analysis, dict):
            self.log_warning("Invalid BRD analysis input - using default recommendations")
            return self.get_default_response()
        
        try:
            # Extract key requirements from BRD
            requirements = self.extract_brd_requirements(brd_analysis)
            
            # Add requirements to execution context
            self.log_info(f"Identified key requirements - Scale: {requirements['scale']}, " +
                         f"Data complexity: {requirements['data_complexity']}, " +
                         f"Security: {requirements['security_level']}, " +
                         f"Performance: {requirements['performance_needs']}")
            
            # Check if RAG context would be helpful
            rag_context = ""
            if self.rag_retriever:
                query = f"technology stack for {requirements['scale']} scale application " + \
                        f"with {requirements['data_complexity']} data complexity " + \
                        f"and {requirements['security_level']} security requirements"
                rag_context = self.get_rag_context(query)
                if project_context:
                    project_context = f"{project_context}\n\nAdditional context: {rag_context}"
                else:
                    project_context = f"Additional context: {rag_context}"
            
            # Execute LLM chain with BRD analysis and extracted requirements
            response = self.execute_with_monitoring(
                self.execute_llm_chain,
                {
                    "brd_analysis": json.dumps(brd_analysis, indent=2),
                    "project_context": project_context,
                    "scale": requirements["scale"],
                    "data_complexity": requirements["data_complexity"],
                    "security_level": requirements["security_level"],
                    "performance_needs": requirements["performance_needs"],
                    "integration_points": ", ".join(requirements["integration_points"]) if requirements["integration_points"] else "None specified"
                }
            )
            
            # Validate response structure
            required_keys = [
                "backend", "frontend", "database", "architecture_pattern", 
                "deployment_environment", "key_libraries_tools", 
                "estimated_complexity", "overall_reasoning"
            ]
            
            validated_response = self.validate_response_structure(response, required_keys)
            
            # Validate tech stack alignment with requirements
            validated_response = self.validate_tech_stack_alignment(validated_response, requirements)
            
            # Log execution summary
            self.log_execution_summary(validated_response)
            
            return validated_response
            
        except Exception as e:
            self.log_error(f"Tech stack recommendation failed: {e}")
            return self.get_default_response()
    
    def validate_response_structure(self, response: Dict[str, Any], required_keys: List[str]) -> Dict[str, Any]:
        """Validates and ensures the response has all required keys."""
        default_structure = self.get_default_structure()
        
        # Create a new response with defaults for missing fields
        validated_response = {}
        
        for key in required_keys:
            if key not in response or not response[key]:
                self.log_warning(f"Missing {key} in response, using default")
                validated_response[key] = default_structure.get(key)
            else:
                validated_response[key] = response[key]
        
        return validated_response
    
    def log_execution_summary(self, response: Dict[str, Any]):
        """Log detailed execution summary for tech stack recommendation."""
        backend_lang = response.get("backend", {}).get("language", "Not specified")
        backend_framework = response.get("backend", {}).get("framework", "Not specified")
        database = response.get("database", {}).get("type", "Not specified")
        frontend_framework = response.get("frontend", {}).get("framework", "Not specified")
        architecture = response.get("architecture_pattern", "Not specified")
        complexity = response.get("estimated_complexity", "Unknown")
        
        summary = (f"Stack: {backend_lang}/{backend_framework} backend, {database} database, "
                 f"{frontend_framework} frontend, {architecture} architecture, {complexity} complexity")
        
        self.log_success(f"Tech stack recommendation complete: {summary}")
    
    def validate_tech_stack_alignment(self, response: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that the recommended tech stack aligns with the extracted requirements.
        If not, add appropriate warnings and annotations.
        """
        tech_issues = []
        
        # Check if high-security requirements are properly addressed
        if requirements["security_level"] == "high":
            backend = response.get("backend", {})
            security_addressed = False
            
            # Look for security mentions in the reasoning
            if "reasoning" in backend and any(kw in backend["reasoning"].lower() for kw in [
                "secur", "encrypt", "auth", "protect", "complian", "gdpr", "hipaa", "pci"
            ]):
                security_addressed = True
            
            if not security_addressed:
                tech_issues.append("Security requirements not fully addressed in backend selection")
                self.log_warning("Backend recommendation doesn't address high security requirements")
        
        # Check if high performance requirements are properly addressed
        if requirements["performance_needs"] == "high":
            perf_addressed = False
            
            # Check backend reasoning for performance mentions
            if "backend" in response and "reasoning" in response["backend"]:
                if any(kw in response["backend"]["reasoning"].lower() for kw in [
                    "perform", "scale", "fast", "latency", "throughput", "concurrent", "real-time"
                ]):
                    perf_addressed = True
            
            # Check database reasoning for performance mentions
            if "database" in response and "reasoning" in response["database"]:
                if any(kw in response["database"]["reasoning"].lower() for kw in [
                    "perform", "scale", "fast", "latency", "throughput", "concurrent", "real-time"
                ]):
                    perf_addressed = True
            
            if not perf_addressed:
                tech_issues.append("High performance requirements not fully addressed in technology selections")
                self.log_warning("Tech recommendations don't address high performance requirements")
        
        # Check if data complexity is properly addressed
        if requirements["data_complexity"] == "high":
            db_type = response.get("database", {}).get("type", "").lower()
            db_reasoning = response.get("database", {}).get("reasoning", "").lower()
            
            if not any(db in db_type for db in ["sql", "postgres", "oracle", "relational"]) and \
               not ("complex" in db_reasoning and "data" in db_reasoning):
                tech_issues.append("Complex data requirements may not be fully addressed by database selection")
                self.log_warning("Database recommendation may not address high data complexity")
        
        # Add validation issues to response if found
        if tech_issues:
            if "validation_issues" not in response:
                response["validation_issues"] = []
            
            response["validation_issues"].extend(tech_issues)
        
        return response