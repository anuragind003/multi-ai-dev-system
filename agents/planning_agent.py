import json
import datetime
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.retrievers import BaseRetriever
from typing import Optional, Dict, Any, List, Tuple
import monitoring
from .base_agent import BaseAgent

class PlanningAgent(BaseAgent):
    """Enhanced Planning Agent with comprehensive project planning capabilities, 
    critical path analysis, resource optimization, and agile methodology integration."""
    
    def __init__(self, llm: BaseLanguageModel, memory, rag_retriever: Optional[BaseRetriever] = None):
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Planning Agent",
            temperature=0.4,  # Creative temperature for planning while maintaining structure
            rag_retriever=rag_retriever
        )
        
        # Initialize main planning prompt template
        self.prompt_template = PromptTemplate(
            template="""
            You are an expert Project Manager and Software Development Planning specialist.
            Your task is to create a comprehensive implementation plan based on the BRD analysis, recommended tech stack, and system design.

            **BRD Analysis:**
            {brd_analysis}

            **Tech Stack Recommendation:**
            {tech_stack_recommendation}

            **System Design:**
            {system_design}

            **Project Constraints:**
            {project_constraints}

            **RAG Context (relevant planning knowledge):**
            {rag_context}

            **Instructions:**
            Create a detailed implementation plan that includes:
            1. Development phases and milestones with clear timeline estimates
            2. Granular task breakdown with dependencies and effort estimates
            3. Resource allocation optimization and team structure recommendations
            4. Critical path analysis with dependency resolution
            5. Comprehensive risk assessment with quantified impact and probability
            6. Quality assurance plan with measurable criteria
            7. Deployment strategy with rollback contingencies
            8. Agile sprint planning if appropriate for the project

            {format_instructions}

            **Output Requirements:**
            Generate a JSON object with:
            {{
                "project_overview": {{
                    "estimated_duration": "string - Total project duration",
                    "team_size": "string - Recommended team size",
                    "complexity_level": "Low/Medium/High",
                    "critical_path": ["array of critical milestones"],
                    "delivery_date": "string - Expected delivery date",
                    "methodology": "string - Recommended development methodology",
                    "key_constraints": ["array of major constraints affecting the plan"]
                }},
                "development_phases": [
                    {{
                        "phase_name": "string",
                        "phase_id": "string - unique identifier",
                        "start_date": "string - estimated start date",
                        "end_date": "string - estimated end date",
                        "duration": "string",
                        "objectives": ["array of phase objectives"],
                        "deliverables": ["array of expected deliverables"],
                        "dependencies": ["array of dependencies"],
                        "risk_level": "Low/Medium/High",
                        "key_milestones": ["array of important milestones"]
                    }}
                ],
                "task_breakdown": [
                    {{
                        "task_id": "string",
                        "phase_id": "string - associated phase",
                        "task_name": "string",
                        "description": "string",
                        "estimated_effort": "string - hours/days",
                        "priority": "High/Medium/Low",
                        "assigned_role": "string",
                        "dependencies": ["array of task dependencies"],
                        "complexity": "Low/Medium/High",
                        "acceptance_criteria": ["array of criteria to consider task complete"]
                    }}
                ],
                "resource_plan": {{
                    "roles_required": [
                        {{
                            "role": "string - role title",
                            "quantity": "number - how many needed",
                            "skills": ["array of required skills"],
                            "allocation_percentage": "number - allocation percentage",
                            "key_responsibilities": ["array of responsibilities"]
                        }}
                    ],
                    "team_structure": "string - team organization approach",
                    "external_dependencies": ["array of external dependencies"],
                    "resource_constraints": "string - any resource limitations",
                    "onboarding_requirements": "string - specific onboarding needs"
                }},
                "risk_assessment": [
                    {{
                        "risk_id": "string - unique identifier",
                        "category": "string - risk category",
                        "description": "string - risk description",
                        "impact": "High/Medium/Low",
                        "probability": "High/Medium/Low",
                        "severity": "number - combined impact and probability score (1-10)",
                        "mitigation": "string - mitigation strategy",
                        "contingency": "string - contingency plan",
                        "owner": "string - role responsible for monitoring this risk"
                    }}
                ],
                "quality_plan": {{
                    "testing_strategy": "string",
                    "code_review_process": "string",
                    "quality_gates": ["array of quality checkpoints"],
                    "acceptance_criteria": ["array of project acceptance criteria"],
                    "metrics": ["array of quality metrics to track"],
                    "testing_tools": ["array of recommended testing tools"],
                    "performance_benchmarks": "string - performance targets"
                }},
                "deployment_plan": {{
                    "deployment_strategy": "string",
                    "environments": ["array of required environments"],
                    "rollback_plan": "string",
                    "deployment_phases": ["array of deployment steps"],
                    "post_deployment_monitoring": "string",
                    "required_approvals": ["array of approval checkpoints"],
                    "release_notes_template": "string - template for release notes"
                }},
                "sprint_planning": [
                    {{
                        "sprint_number": "number",
                        "duration": "string - typically 1-4 weeks",
                        "start_date": "string - estimated start date",
                        "end_date": "string - estimated end date",
                        "goals": ["array of sprint goals"],
                        "key_deliverables": ["array of planned deliverables"],
                        "task_ids": ["array of task IDs planned for this sprint"]
                    }}
                ],
                "timeline_visualization": {{
                    "critical_path_sequence": ["array of tasks forming the critical path"],
                    "major_milestones": [
                        {{
                            "name": "string - milestone name",
                            "date": "string - estimated date",
                            "description": "string",
                            "dependencies": ["array of dependencies"]
                        }}
                    ],
                    "key_dependencies": ["array of critical dependencies that could affect timeline"]
                }}
            }}

            Output ONLY the JSON object. Do not include any explanatory text outside the JSON.
            """,
            input_variables=["brd_analysis", "tech_stack_recommendation", "system_design", 
                            "project_constraints", "rag_context"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()},
        )
        
        # Additional template for dependency analysis
        self.dependency_analysis_template = PromptTemplate(
            template="""
            You are an expert Project Planner specializing in Critical Path Analysis.
            Review the provided task breakdown and identify the critical path and key dependencies.

            **Task Breakdown:**
            {task_breakdown}

            {format_instructions}

            Generate a JSON object with:
            {{
                "critical_path": ["array of task IDs in critical path order"],
                "critical_dependencies": [
                    {{
                        "task_id": "string",
                        "blockers": ["array of task IDs blocking this task"],
                        "impact_level": "High/Medium/Low",
                        "risk_to_timeline": "string explanation"
                    }}
                ],
                "recommended_parallel_work": ["array of tasks that could be done in parallel"],
                "timeline_bottlenecks": ["array of potential bottlenecks"]
            }}
            """,
            input_variables=["task_breakdown"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()},
        )
        
        # Risk assessment template
        self.risk_assessment_template = PromptTemplate(
            template="""
            You are an expert Risk Manager specializing in software development projects.
            Based on the project information, create a comprehensive risk assessment and mitigation plan.

            **Project Overview:**
            {project_overview}

            **Tech Stack:**
            {tech_stack}

            **System Design:**
            {system_design_summary}

            {format_instructions}

            Generate a JSON object with:
            {{
                "risk_assessment": [
                    {{
                        "risk_id": "RISK-001",
                        "category": "Technical/Resource/Schedule/External/Requirements",
                        "description": "detailed risk description",
                        "triggers": ["events that might trigger this risk"],
                        "early_warning_signs": ["indicators to watch for"],
                        "impact": "High/Medium/Low",
                        "probability": "High/Medium/Low",
                        "severity": "1-10 numeric score",
                        "mitigation": "preventive measures",
                        "contingency": "what to do if risk materializes",
                        "owner": "role responsible for this risk"
                    }}
                ],
                "risk_matrix": {{
                    "high_impact_high_probability": ["risk_ids in this category"],
                    "high_impact_medium_probability": ["risk_ids in this category"],
                    "high_impact_low_probability": ["risk_ids in this category"],
                    "medium_impact_high_probability": ["risk_ids in this category"],
                    "medium_impact_medium_probability": ["risk_ids in this category"],
                    "medium_impact_low_probability": ["risk_ids in this category"],
                    "low_impact_high_probability": ["risk_ids in this category"],
                    "low_impact_medium_probability": ["risk_ids in this category"],
                    "low_impact_low_probability": ["risk_ids in this category"]
                }},
                "top_risks": ["most critical risk_ids to monitor"]
            }}
            """,
            input_variables=["project_overview", "tech_stack", "system_design_summary"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()},
        )

    def get_default_structure(self) -> Dict[str, Any]:
        """Define comprehensive default structure for implementation plan."""
        today = datetime.datetime.now()
        phase1_start = today + datetime.timedelta(days=7)
        phase2_start = today + datetime.timedelta(days=21)
        phase3_start = today + datetime.timedelta(days=49)
        phase4_start = today + datetime.timedelta(days=63)
        end_date = today + datetime.timedelta(days=77)
        
        date_format = "%Y-%m-%d"
        
        return {
            "project_overview": {
                "estimated_duration": "8-12 weeks",
                "team_size": "3-5 developers",
                "complexity_level": "Medium",
                "critical_path": ["Requirements Analysis", "Core Development", "Testing", "Deployment"],
                "delivery_date": end_date.strftime(date_format),
                "methodology": "Agile with 2-week sprints",
                "key_constraints": ["Timeline", "Budget", "Available expertise"]
            },
            "development_phases": [
                {
                    "phase_name": "Planning & Setup",
                    "phase_id": "PHASE-1",
                    "start_date": today.strftime(date_format),
                    "end_date": phase1_start.strftime(date_format),
                    "duration": "1-2 weeks",
                    "objectives": ["Environment setup", "Requirements clarification", "Team onboarding"],
                    "deliverables": ["Development environment", "Technical specification", "Sprint plan"],
                    "dependencies": [],
                    "risk_level": "Low",
                    "key_milestones": ["Environment ready", "Requirements approved"]
                },
                {
                    "phase_name": "Core Development",
                    "phase_id": "PHASE-2",
                    "start_date": phase1_start.strftime(date_format),
                    "end_date": phase2_start.strftime(date_format),
                    "duration": "4-6 weeks",
                    "objectives": ["Implement core features", "Database setup", "API development"],
                    "deliverables": ["Working application", "Database schema", "API documentation"],
                    "dependencies": ["PHASE-1"],
                    "risk_level": "Medium",
                    "key_milestones": ["Database schema approved", "Core features implemented"]
                },
                {
                    "phase_name": "Testing & QA",
                    "phase_id": "PHASE-3",
                    "start_date": phase2_start.strftime(date_format),
                    "end_date": phase3_start.strftime(date_format),
                    "duration": "2-3 weeks",
                    "objectives": ["Quality assurance", "Bug fixing", "Performance testing"],
                    "deliverables": ["Test reports", "Bug-free application", "Performance benchmarks"],
                    "dependencies": ["PHASE-2"],
                    "risk_level": "Medium",
                    "key_milestones": ["Test plan approved", "Critical bugs resolved"]
                },
                {
                    "phase_name": "Deployment",
                    "phase_id": "PHASE-4",
                    "start_date": phase3_start.strftime(date_format),
                    "end_date": phase4_start.strftime(date_format),
                    "duration": "1-2 weeks",
                    "objectives": ["Production deployment", "Go-live", "Knowledge transfer"],
                    "deliverables": ["Live application", "Documentation", "Support handover"],
                    "dependencies": ["PHASE-3"],
                    "risk_level": "High",
                    "key_milestones": ["Production environment ready", "Go-live approval"]
                }
            ],
            "task_breakdown": [
                {
                    "task_id": "TASK-001",
                    "phase_id": "PHASE-1",
                    "task_name": "Project Setup",
                    "description": "Initialize development environment and project structure",
                    "estimated_effort": "2-3 days",
                    "priority": "High",
                    "assigned_role": "Lead Developer",
                    "dependencies": [],
                    "complexity": "Low",
                    "acceptance_criteria": ["Repository created", "CI/CD pipeline configured", "Development environment documented"]
                },
                {
                    "task_id": "TASK-002",
                    "phase_id": "PHASE-1",
                    "task_name": "Requirements Workshop",
                    "description": "Conduct requirements gathering workshop with stakeholders",
                    "estimated_effort": "1-2 days",
                    "priority": "High",
                    "assigned_role": "Business Analyst",
                    "dependencies": [],
                    "complexity": "Medium",
                    "acceptance_criteria": ["All stakeholder inputs captured", "Requirements documented", "Priorities aligned"]
                },
                {
                    "task_id": "TASK-003",
                    "phase_id": "PHASE-2",
                    "task_name": "Database Schema Design",
                    "description": "Design and implement database schema",
                    "estimated_effort": "3-5 days",
                    "priority": "High",
                    "assigned_role": "Database Engineer",
                    "dependencies": ["TASK-001"],
                    "complexity": "Medium",
                    "acceptance_criteria": ["Schema design document approved", "Database migrations created", "Data model tested"]
                }
            ],
            "resource_plan": {
                "roles_required": [
                    {
                        "role": "Lead Developer",
                        "quantity": 1,
                        "skills": ["Architecture", "System Design", "Code Review", "DevOps"],
                        "allocation_percentage": 100,
                        "key_responsibilities": ["Technical leadership", "Architecture decisions", "Code quality"]
                    },
                    {
                        "role": "Backend Developer",
                        "quantity": 2,
                        "skills": ["API Development", "Database", "Testing"],
                        "allocation_percentage": 100,
                        "key_responsibilities": ["Backend implementation", "API development", "Database interactions"]
                    },
                    {
                        "role": "Frontend Developer",
                        "quantity": 1,
                        "skills": ["UI Development", "UX Design", "Frontend Testing"],
                        "allocation_percentage": 100,
                        "key_responsibilities": ["Frontend implementation", "UI/UX realization", "Client-side logic"]
                    },
                    {
                        "role": "QA Engineer",
                        "quantity": 1,
                        "skills": ["Test Planning", "Automated Testing", "Performance Testing"],
                        "allocation_percentage": 80,
                        "key_responsibilities": ["Test planning", "Test execution", "Quality reporting"]
                    }
                ],
                "team_structure": "Agile team with cross-functional skills",
                "external_dependencies": ["Cloud Infrastructure", "Third-party APIs", "Design Assets"],
                "resource_constraints": "Limited DevOps expertise available",
                "onboarding_requirements": "All team members require 2-3 days project onboarding"
            },
            "risk_assessment": [
                {
                    "risk_id": "RISK-001",
                    "category": "Requirements",
                    "description": "Requirements changes during development",
                    "impact": "Medium",
                    "probability": "Medium",
                    "severity": 6,
                    "mitigation": "Agile methodology with regular stakeholder reviews",
                    "contingency": "Change control process with impact assessment",
                    "owner": "Project Manager"
                },
                {
                    "risk_id": "RISK-002",
                    "category": "Technical",
                    "description": "Technical complexity underestimation",
                    "impact": "High",
                    "probability": "Medium",
                    "severity": 8,
                    "mitigation": "Detailed technical analysis and proof of concepts",
                    "contingency": "Additional technical resources and expertise",
                    "owner": "Lead Developer"
                },
                {
                    "risk_id": "RISK-003",
                    "category": "Resource",
                    "description": "Key team member unavailability",
                    "impact": "Medium",
                    "probability": "Low",
                    "severity": 4,
                    "mitigation": "Cross-training and documentation",
                    "contingency": "Backup resource identification and knowledge sharing",
                    "owner": "Project Manager"
                }
            ],
            "quality_plan": {
                "testing_strategy": "Comprehensive testing including unit, integration, and acceptance tests",
                "code_review_process": "Peer review for all code changes with mandatory approval",
                "quality_gates": ["Code review approval", "All tests passing", "Security scan clear", "Performance benchmarks met"],
                "acceptance_criteria": ["Functional requirements met", "Non-functional requirements met", "Documentation complete"],
                "metrics": ["Code coverage", "Bug density", "Technical debt", "Performance metrics"],
                "testing_tools": ["Jest", "Cypress", "JMeter", "SonarQube"],
                "performance_benchmarks": "Response time under 500ms for 95% of API requests"
            },
            "deployment_plan": {
                "deployment_strategy": "Blue-green deployment with gradual rollout",
                "environments": ["Development", "Testing", "Staging", "Production"],
                "rollback_plan": "Automated rollback trigger based on error threshold",
                "deployment_phases": ["Deploy to staging", "Smoke testing", "Gradual production rollout", "Monitor"],
                "post_deployment_monitoring": "24-hour heightened monitoring period",
                "required_approvals": ["QA sign-off", "Security sign-off", "Product Owner sign-off"],
                "release_notes_template": "# Release Notes\n## New Features\n## Bug Fixes\n## Known Issues"
            },
            "sprint_planning": [
                {
                    "sprint_number": 1,
                    "duration": "2 weeks",
                    "start_date": today.strftime(date_format),
                    "end_date": (today + datetime.timedelta(days=14)).strftime(date_format),
                    "goals": ["Environment setup", "Core architecture"],
                    "key_deliverables": ["Development environment", "Project structure", "DB schema design"],
                    "task_ids": ["TASK-001", "TASK-002", "TASK-003"]
                },
                {
                    "sprint_number": 2,
                    "duration": "2 weeks",
                    "start_date": (today + datetime.timedelta(days=14)).strftime(date_format),
                    "end_date": (today + datetime.timedelta(days=28)).strftime(date_format),
                    "goals": ["Core backend features"],
                    "key_deliverables": ["API foundation", "Data models", "Authentication"],
                    "task_ids": ["TASK-004", "TASK-005", "TASK-006"]
                }
            ],
            "timeline_visualization": {
                "critical_path_sequence": ["TASK-001", "TASK-003", "TASK-006", "TASK-010", "TASK-015"],
                "major_milestones": [
                    {
                        "name": "Project Kickoff",
                        "date": today.strftime(date_format),
                        "description": "Official project start",
                        "dependencies": []
                    },
                    {
                        "name": "Alpha Release",
                        "date": phase2_start.strftime(date_format),
                        "description": "Core functionality available for internal testing",
                        "dependencies": ["TASK-006", "TASK-007"]
                    },
                    {
                        "name": "Beta Release",
                        "date": phase3_start.strftime(date_format),
                        "description": "Feature complete version for QA and stakeholder review",
                        "dependencies": ["TASK-010", "TASK-011"]
                    },
                    {
                        "name": "Production Launch",
                        "date": end_date.strftime(date_format),
                        "description": "Public release of the application",
                        "dependencies": ["TASK-015", "TASK-016"]
                    }
                ],
                "key_dependencies": ["Database schema must be finalized before API development", 
                                    "API endpoints must be complete before frontend integration",
                                    "Performance testing requires all core features to be implemented"]
            }
        }

    def get_default_response(self) -> Dict[str, Any]:
        """Get enhanced default response when planning fails."""
        default_structure = self.get_default_structure()
        default_structure["project_overview"]["estimated_duration"] = "Planning analysis failed - manual review required"
        default_structure["risk_assessment"].append({
            "risk_id": "RISK-999",
            "category": "Process",
            "description": "Planning agent failure - plan may be incomplete or inaccurate",
            "impact": "High",
            "probability": "High",
            "severity": 9,
            "mitigation": "Manual review and correction of the plan",
            "contingency": "Full planning session with human experts",
            "owner": "Project Manager"
        })
        return default_structure

    def run(self, brd_analysis: Dict[str, Any], tech_stack_recommendation: Dict[str, Any], 
           system_design: Dict[str, Any], project_constraints: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create comprehensive implementation plan with enhanced validation,
        critical path analysis and resource optimization.
        """
        self.log_start("Starting enhanced implementation planning")
        
        # Set temperature for this creative planning task
        llm_with_temp = self.llm.bind(temperature=0.4)
        
        # Initialize default constraints if none provided
        if not project_constraints:
            project_constraints = {
                "timeline": "Standard",
                "budget": "Medium",
                "quality_requirements": "High",
                "team_expertise": "Mixed",
                "stakeholder_availability": "Limited"
            }
            self.log_info("Using default project constraints")
        
        # Validate inputs
        if not all([brd_analysis, tech_stack_recommendation, system_design]):
            self.log_warning("Missing required inputs for planning")
            return self.get_default_response()
        
        # Validate input types
        if not all([isinstance(brd_analysis, dict), 
                   isinstance(tech_stack_recommendation, dict), 
                   isinstance(system_design, dict)]):
            self.log_warning("Invalid input types for planning")
            return self.get_default_response()

        try:
            # Get RAG context with specific planning knowledge
            backend_stack = tech_stack_recommendation.get('backend', {}).get('framework', '')
            architecture = tech_stack_recommendation.get('architecture_pattern', '')
            complexity = self._assess_project_complexity(brd_analysis, system_design)
            
            rag_query = (f"software project planning {backend_stack} {architecture} " 
                        f"{complexity} complexity best practices timeline estimation")
            
            rag_context = self.get_rag_context(rag_query)
            self.log_info(f"Retrieved planning knowledge for {backend_stack} with {complexity} complexity")
            
            # Format project constraints for the prompt
            constraints_str = json.dumps(project_constraints, indent=2) if project_constraints else "{}"
            
            # Execute LLM chain to generate base implementation plan
            self.log_info("Generating comprehensive implementation plan")
            base_plan = self.execute_with_monitoring(
                lambda kwargs: llm_with_temp.invoke(self.prompt_template.format(**kwargs)),
                {
                    "brd_analysis": json.dumps(brd_analysis, indent=2),
                    "tech_stack_recommendation": json.dumps(tech_stack_recommendation, indent=2),
                    "system_design": json.dumps(system_design, indent=2),
                    "project_constraints": constraints_str,
                    "rag_context": rag_context
                }
            )
            
            # Parse the response
            try:
                # First handle the response based on its type
                if hasattr(base_plan, 'content'):
                    content = base_plan.content
                    # Handle case where content is a list
                    if isinstance(content, list):
                        content = "\n".join(content) if all(isinstance(item, str) for item in content) else str(content)
                    plan_json = self.json_parser.parse(content)
                else:
                    # Handle case where base_plan itself might be a list
                    base_plan_str = base_plan
                    if isinstance(base_plan, list):
                        base_plan_str = "\n".join(base_plan) if all(isinstance(item, str) for item in base_plan) else str(base_plan)
                    plan_json = self.json_parser.parse(str(base_plan_str))
            except Exception as e:
                self.log_warning(f"Error parsing implementation plan: {e}")
                return self.get_default_response()
            
            # Validate response structure
            required_keys = [
                "project_overview", "development_phases", "task_breakdown",
                "resource_plan", "risk_assessment", "quality_plan", "deployment_plan"
            ]
            
            validated_plan = self.validate_response_structure(plan_json, required_keys)
            
            # Enhance the plan with additional analyses
            enhanced_plan = self._enhance_plan(validated_plan, brd_analysis, tech_stack_recommendation, system_design)
            
            # Perform consistency checks
            enhanced_plan = self._validate_plan_consistency(enhanced_plan)
            
            # Log execution summary
            self.log_execution_summary(enhanced_plan)
            
            return enhanced_plan
            
        except Exception as e:
            self.log_error(f"Implementation planning failed: {e}")
            import traceback
            self.log_error(traceback.format_exc())
            return self.get_default_response()

    def _enhance_plan(self, base_plan: Dict[str, Any], brd_analysis: Dict[str, Any], 
                    tech_stack: Dict[str, Any], system_design: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance the base plan with additional analyses and details."""
        try:
            # Only perform enhancements if we have a valid base plan
            if not base_plan or not isinstance(base_plan, dict):
                return base_plan
                
            self.log_info("Enhancing implementation plan with additional analyses")
            
            # Enhance with critical path and dependency analysis if we have task breakdown
            if "task_breakdown" in base_plan and base_plan["task_breakdown"]:
                task_breakdown = json.dumps(base_plan["task_breakdown"], indent=2)
                
                try:
                    # Use a lower temperature for this analytical task
                    llm_analytical = self.llm.bind(temperature=0.2)
                    
                    # Set the prompt template for dependency analysis
                    dependency_prompt = self.dependency_analysis_template.format(
                        task_breakdown=task_breakdown
                    )
                    
                    self.log_info("Performing dependency and critical path analysis")
                    dependency_response = llm_analytical.invoke(dependency_prompt)
                    
                    # Parse the response
                    if hasattr(dependency_response, 'content'):
                        dependency_analysis = self.json_parser.parse(dependency_response.content)
                    else:
                        dependency_analysis = self.json_parser.parse(str(dependency_response))
                    
                    # Update the plan with enhanced critical path information
                    if "critical_path" in dependency_analysis and dependency_analysis["critical_path"]:
                        base_plan["timeline_visualization"]["critical_path_sequence"] = dependency_analysis["critical_path"]
                        
                    if "critical_dependencies" in dependency_analysis:
                        base_plan["timeline_visualization"]["critical_dependencies"] = dependency_analysis["critical_dependencies"]
                        
                    if "recommended_parallel_work" in dependency_analysis:
                        base_plan["timeline_visualization"]["parallel_work_recommendations"] = dependency_analysis["recommended_parallel_work"]
                        
                    self.log_info("Added critical path and dependency analysis to plan")
                        
                except Exception as e:
                    self.log_warning(f"Error enhancing plan with dependency analysis: {e}")
            
            # Enhance with detailed risk assessment
            try:
                # Extract summary data for risk analysis
                project_overview = {
                    "name": brd_analysis.get("project_overview", {}).get("project_name", "Unknown"),
                    "description": brd_analysis.get("project_overview", {}).get("description", ""),
                    "complexity": base_plan.get("project_overview", {}).get("complexity_level", "Medium"),
                    "timeline": base_plan.get("project_overview", {}).get("estimated_duration", "Unknown")
                }
                
                tech_stack_summary = {
                    "backend": tech_stack.get("backend", {}).get("framework", "Unknown"),
                    "frontend": tech_stack.get("frontend", {}).get("framework", "Unknown"),
                    "database": tech_stack.get("database", {}).get("type", "Unknown"),
                    "architecture": tech_stack.get("architecture_pattern", "Unknown")
                }
                
                system_design_summary = {
                    "architecture": system_design.get("architecture_overview", {}).get("pattern", "Unknown"),
                    "components": len(system_design.get("main_modules", [])),
                    "integrations": len(system_design.get("integration_points", []))
                }
                
                # Use analytical temperature for risk assessment
                llm_analytical = self.llm.bind(temperature=0.2)
                
                # Set the prompt template for risk assessment
                risk_prompt = self.risk_assessment_template.format(
                    project_overview=json.dumps(project_overview, indent=2),
                    tech_stack=json.dumps(tech_stack_summary, indent=2),
                    system_design_summary=json.dumps(system_design_summary, indent=2)
                )
                
                self.log_info("Performing detailed risk assessment")
                risk_response = llm_analytical.invoke(risk_prompt)
                
                # Parse the response
                if hasattr(risk_response, 'content'):
                    risk_analysis = self.json_parser.parse(risk_response.content)
                else:
                    risk_analysis = self.json_parser.parse(str(risk_response))
                
                # Add risk matrix to the plan if available
                if "risk_matrix" in risk_analysis:
                    if "risk_assessment" not in base_plan:
                        base_plan["risk_assessment"] = []
                        
                    base_plan["risk_analysis"] = {
                        "risk_matrix": risk_analysis.get("risk_matrix", {}),
                        "top_risks": risk_analysis.get("top_risks", [])
                    }
                    
                    # Merge the risk assessments, preserving existing ones
                    existing_risk_ids = [r.get("risk_id") for r in base_plan["risk_assessment"] if "risk_id" in r]
                    
                    for risk in risk_analysis.get("risk_assessment", []):
                        if "risk_id" in risk and risk["risk_id"] not in existing_risk_ids:
                            base_plan["risk_assessment"].append(risk)
                
                # Add top risks directly to the plan overview for visibility
                top_risks = risk_analysis.get("top_risks", [])
                if top_risks:
                    base_plan["project_overview"]["top_risks"] = top_risks
                
                self.log_info("Enhanced plan with detailed risk assessment")
                    
            except Exception as e:
                self.log_warning(f"Error enhancing plan with risk assessment: {e}")
                
            return base_plan
                
        except Exception as e:
            self.log_warning(f"Error in plan enhancement: {e}")
            return base_plan

    def _validate_plan_consistency(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the internal consistency of the plan and fix any issues."""
        try:
            # Only proceed if we have a valid plan
            if not plan or not isinstance(plan, dict):
                return plan
                
            self.log_info("Validating plan consistency")
            
            # Check phase and task ID consistency
            phase_ids = set()
            if "development_phases" in plan:
                for phase in plan["development_phases"]:
                    if "phase_id" in phase:
                        phase_ids.add(phase["phase_id"])
            
            # Check that all tasks reference valid phases
            if "task_breakdown" in plan and plan["task_breakdown"]:
                for task in plan["task_breakdown"]:
                    if "phase_id" in task and task["phase_id"] not in phase_ids:
                        self.log_warning(f"Task {task.get('task_id', 'Unknown')} references non-existent phase {task['phase_id']}")
                        # Try to find a suitable phase
                        if phase_ids:
                            task["phase_id"] = list(phase_ids)[0]
                            self.log_info(f"Assigned task to phase {task['phase_id']}")
            
            # Check sprint planning task references
            task_ids = set()
            if "task_breakdown" in plan and plan["task_breakdown"]:
                for task in plan["task_breakdown"]:
                    if "task_id" in task:
                        task_ids.add(task["task_id"])
            
            if "sprint_planning" in plan and plan["sprint_planning"]:
                for sprint in plan["sprint_planning"]:
                    if "task_ids" in sprint:
                        valid_tasks = [task_id for task_id in sprint["task_ids"] if task_id in task_ids]
                        if len(valid_tasks) != len(sprint["task_ids"]):
                            self.log_warning(f"Sprint {sprint.get('sprint_number', 'Unknown')} references non-existent tasks")
                            sprint["task_ids"] = valid_tasks
            
            # Check critical path references valid tasks
            if "timeline_visualization" in plan and "critical_path_sequence" in plan["timeline_visualization"]:
                valid_critical_path = [task_id for task_id in plan["timeline_visualization"]["critical_path_sequence"] 
                                     if task_id in task_ids]
                
                if len(valid_critical_path) != len(plan["timeline_visualization"]["critical_path_sequence"]):
                    self.log_warning("Critical path references non-existent tasks, correcting")
                    plan["timeline_visualization"]["critical_path_sequence"] = valid_critical_path
            
            # Check timeline consistency
            self._check_timeline_consistency(plan)
            
            self.log_info("Plan consistency validation complete")
            return plan
                
        except Exception as e:
            self.log_warning(f"Error in plan consistency validation: {e}")
            return plan

    def _check_timeline_consistency(self, plan: Dict[str, Any]) -> None:
        """Check and fix timeline consistency issues in the plan."""
        try:
            # Check phase dates
            if "development_phases" in plan and len(plan["development_phases"]) > 1:
                phases = plan["development_phases"]
                # Sort phases by dependencies
                dependency_map = {phase["phase_id"]: phase.get("dependencies", []) for phase in phases if "phase_id" in phase}
                
                # Check for date inconsistencies
                for i in range(len(phases)):
                    phase = phases[i]
                    if "dependencies" in phase and phase["dependencies"]:
                        for dep_id in phase["dependencies"]:
                            # Find the dependent phase
                            dep_phase = next((p for p in phases if p.get("phase_id") == dep_id), None)
                            if dep_phase and "end_date" in dep_phase and "start_date" in phase:
                                # Parse dates for comparison
                                try:
                                    dep_end = datetime.datetime.strptime(dep_phase["end_date"], "%Y-%m-%d")
                                    phase_start = datetime.datetime.strptime(phase["start_date"], "%Y-%m-%d")
                                    
                                    if phase_start < dep_end:
                                        self.log_warning(f"Phase {phase['phase_id']} starts before dependency {dep_id} ends, adjusting")
                                        # Fix by setting start date to dependency end date
                                        phase["start_date"] = dep_phase["end_date"]
                                        
                                        # Also adjust end date
                                        if "end_date" in phase and "duration" in phase:
                                            # Parse duration (e.g., "2-3 weeks")
                                            duration_text = phase["duration"]
                                            duration_weeks = 0
                                            
                                            if "week" in duration_text.lower():
                                                # Extract numbers
                                                import re
                                                numbers = re.findall(r'\d+', duration_text)
                                                if numbers:
                                                    # Use the larger number if range is given
                                                    duration_weeks = int(numbers[-1])
                                            else:
                                                # Default to 2 weeks if unparseable
                                                duration_weeks = 2
                                                
                                            # Calculate new end date
                                            new_end = dep_end + datetime.timedelta(weeks=duration_weeks)
                                            phase["end_date"] = new_end.strftime("%Y-%m-%d")
                                except Exception:
                                    # Skip date parsing errors
                                    pass
        except Exception as e:
            self.log_warning(f"Error checking timeline consistency: {e}")

    def _assess_project_complexity(self, brd_analysis: Dict[str, Any], system_design: Dict[str, Any]) -> str:
        """Assess the complexity of the project based on BRD and system design."""
        try:
            # Default to medium complexity
            complexity = "Medium"
            
            # Count functional requirements
            func_reqs = len(brd_analysis.get("functional_requirements", []))
            
            # Count system components
            components = len(system_design.get("main_modules", []))
            
            # Count integrations
            integrations = len(system_design.get("integration_points", []))
            
            # Count data entities
            data_entities = len(brd_analysis.get("data_requirements", []))
            
            # Simple heuristic for complexity assessment
            complexity_score = 0
            
            if func_reqs > 30:
                complexity_score += 3
            elif func_reqs > 15:
                complexity_score += 2
            elif func_reqs > 5:
                complexity_score += 1
                
            if components > 10:
                complexity_score += 3
            elif components > 5:
                complexity_score += 2
            elif components > 3:
                complexity_score += 1
                
            if integrations > 5:
                complexity_score += 3
            elif integrations > 2:
                complexity_score += 2
            elif integrations > 0:
                complexity_score += 1
                
            if data_entities > 15:
                complexity_score += 3
            elif data_entities > 8:
                complexity_score += 2
            elif data_entities > 3:
                complexity_score += 1
                
            # Check for specific complexity indicators in non-functional requirements
            nfrs = brd_analysis.get("non_functional_requirements", {})
            
            # Security requirements can increase complexity
            security_reqs = nfrs.get("security", [])
            if security_reqs and any("compliance" in req.lower() or "encryption" in req.lower() 
                                  or "authentication" in req.lower() for req in security_reqs):
                complexity_score += 2
                
            # Performance requirements can increase complexity
            perf_reqs = nfrs.get("performance", [])
            if perf_reqs and any("real-time" in req.lower() or "high volume" in req.lower() 
                              or "low latency" in req.lower() for req in perf_reqs):
                complexity_score += 2
                
            # Determine final complexity
            if complexity_score >= 10:
                complexity = "High"
            elif complexity_score >= 5:
                complexity = "Medium"
            else:
                complexity = "Low"
                
            self.log_info(f"Assessed project complexity: {complexity} (score: {complexity_score})")
            return complexity
                
        except Exception as e:
            self.log_warning(f"Error assessing project complexity: {e}")
            return "Medium"  # Default to medium if assessment fails

    def log_execution_summary(self, response: Dict[str, Any]):
        """Enhanced execution summary with detailed metrics and critical path information."""
        phases = len(response.get("development_phases", []))
        tasks = len(response.get("task_breakdown", []))
        risks = len(response.get("risk_assessment", []))
        duration = response.get("project_overview", {}).get("estimated_duration", "Unknown")
        complexity = response.get("project_overview", {}).get("complexity_level", "Unknown")
        team_size = response.get("project_overview", {}).get("team_size", "Unknown")
        methodology = response.get("project_overview", {}).get("methodology", "Unknown")
        delivery_date = response.get("project_overview", {}).get("delivery_date", "Unknown")
        
        # Calculate high-priority risks
        high_risks = [risk for risk in response.get("risk_assessment", []) 
                     if risk.get("impact") == "High" and risk.get("probability") in ["High", "Medium"]]
        
        # Calculate critical path length
        critical_path = response.get("timeline_visualization", {}).get("critical_path_sequence", [])
        critical_path_length = len(critical_path)
        
        # Calculate sprint coverage
        sprints = response.get("sprint_planning", [])
        sprint_count = len(sprints)
        
        # Log enhanced summary for monitoring
        monitoring.log_agent_activity(
            self.agent_name,
            f"Planning complete - Duration: {duration}, Delivery: {delivery_date}, "
            f"Methodology: {methodology}, Complexity: {complexity}, "
            f"Team: {team_size}, {phases} phases, {tasks} tasks, {risks} risks, "
            f"{len(high_risks)} high risks, {critical_path_length} critical path items, {sprint_count} sprints",
            "SUCCESS"
        )
        
        # Log user-friendly summary
        self.log_success(f"Implementation plan created with {phases} phases and {tasks} tasks")
        self.log_info(f"   Duration: {duration} (Target delivery: {delivery_date})")
        self.log_info(f"   Methodology: {methodology}")
        self.log_info(f"   Complexity: {complexity}")
        self.log_info(f"   Team Size: {team_size}")
        self.log_info(f"   Phases: {phases}")
        self.log_info(f"   Tasks: {tasks}")
        self.log_info(f"   Risks Identified: {risks} ({len(high_risks)} high severity)")
        
        # Log key phases for visibility
        phases_list = response.get("development_phases", [])
        if phases_list:
            phase_names = [phase.get("phase_name", "Unknown") for phase in phases_list[:3]]
            phase_summary = ", ".join(phase_names)
            if len(phases_list) > 3:
                phase_summary += f" (+{len(phases_list) - 3} more)"
            self.log_info(f"   Key Phases: {phase_summary}")
        
        # Log critical path if available
        if critical_path:
            if len(critical_path) <= 3:
                cp_display = " → ".join(critical_path)
            else:
                cp_display = f"{critical_path[0]} → {critical_path[1]} → ... → {critical_path[-1]} ({len(critical_path)} items)"
            self.log_info(f"   Critical Path: {cp_display}")
            
        # Log sprint plan if available
        if sprints:
            sprint_duration = sprints[0].get("duration", "Unknown")
            sprint_summary = f"{sprint_count} sprints of {sprint_duration} planned"
            self.log_info(f"   Sprint Plan: {sprint_summary}")
        
        # Log top risks
        top_risks = response.get("risk_analysis", {}).get("top_risks", [])
        if top_risks:
            self.log_warning(f"   Top Risks: {', '.join(top_risks[:3])}")