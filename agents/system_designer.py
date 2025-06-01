import json
from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import PromptTemplate
from typing import Optional, Dict, Any, List
import monitoring
from .base_agent import BaseAgent

class SystemDesignerAgent(BaseAgent):
    """Enhanced System Designer Agent with comprehensive validation, architectural patterns,
    consistency checking, UML descriptions, and detailed component specifications."""
    
    def __init__(self, llm: BaseLanguageModel, memory, rag_retriever: Optional[BaseRetriever] = None):
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="System Designer Agent",
            temperature=0.2,  # Low for structured architectural decisions
            rag_retriever=rag_retriever
        )
        
        # Initialize prompt template
        self.prompt_template = PromptTemplate(
            template="""
            You are an expert System Designer and Software Architect AI with extensive experience in enterprise software design.
            Your task is to create a comprehensive system design based on the BRD analysis and recommended technology stack.

            **IMPORTANT**: Do NOT default to architecture patterns mentioned in this prompt.
            Your design must be specifically tailored to the provided tech stack recommendation and BRD requirements.
            If the tech stack recommends a specific architecture pattern, your design should align with it.

            **BRD Analysis:**
            {brd_analysis}

            **Recommended Technology Stack:**
            {tech_stack}

            **Design Instructions:**
            Create a detailed system design that includes:
            1. Overall architecture pattern (Microservices, Monolith, Event-Driven, etc.) with justification
            2. Main system modules/components with their responsibilities and relationships
            3. Database schema design optimized for the selected database technology
            4. API design following RESTful/GraphQL best practices with detailed endpoints
            5. Comprehensive security architecture including authentication, authorization, data protection
            6. Detailed data flow diagrams (described textually) covering all key processes
            7. Integration patterns for external systems
            8. Performance optimization strategies specific to the selected tech stack
            9. Scalability architecture with specific implementation details
            10. Deployment architecture with containerization and orchestration
            11. Textual UML descriptions for key components

            **Architectural Considerations:**
            - Ensure your design aligns with the recommended technology stack
            - Apply appropriate design patterns where beneficial
            - Incorporate fault tolerance and error handling
            - Consider observability (logging, monitoring, tracing)
            - Design for maintainability and future extensibility
            - Include appropriate caching strategies
            - Define clear boundaries between components

            {format_instructions}

            **Output Requirements:**
            Generate ONLY a valid JSON object with the following structure:
            {{
                "architecture_overview": {{
                    "pattern": "string - architectural pattern name",
                    "description": "string - detailed description of the architecture",
                    "justification": "string - why this architecture was chosen",
                    "key_principles": ["array of architectural principles applied"]
                }},
                "main_modules": [
                    {{
                        "name": "string - module name",
                        "purpose": "string - detailed description of module's responsibility",
                        "components": ["array of subcomponents"],
                        "dependencies": ["array of modules this depends on"],
                        "interfaces": ["array of interfaces exposed"]
                    }}
                ],
                "database_design": {{
                    "schema_type": "string - relational/document/graph/etc.",
                    "optimization_strategy": "string - specific optimizations for chosen database",
                    "tables": [
                        {{
                            "name": "string - table/collection name",
                            "purpose": "string - what this table stores",
                            "key_fields": [
                                {{
                                    "name": "string - field name",
                                    "type": "string - data type",
                                    "constraints": "string - any constraints",
                                    "description": "string - purpose of this field" 
                                }}
                            ],
                            "relationships": [
                                {{
                                    "related_to": "string - related table name",
                                    "relationship_type": "string - one-to-many, many-to-many, etc.",
                                    "implementation": "string - how relationship is implemented"
                                }}
                            ]
                        }}
                    ],
                    "indexes": [
                        {{
                            "table": "string - table name",
                            "fields": ["array of field names"],
                            "type": "string - index type",
                            "purpose": "string - why this index is needed"
                        }}
                    ],
                    "constraints": ["array of important constraints"],
                    "migration_strategy": "string - how schema changes will be handled"
                }},
                "api_design": {{
                    "style": "string - REST/GraphQL/gRPC/etc.",
                    "base_url": "string - API base URL pattern",
                    "versioning_strategy": "string - how API versioning is handled",
                    "authentication": "string - Auth method (JWT, OAuth, etc.)",
                    "rate_limiting": "string - rate limiting strategy",
                    "endpoints": [
                        {{
                            "method": "GET/POST/PUT/DELETE",
                            "path": "string - endpoint path",
                            "purpose": "string - what this endpoint does",
                            "request_format": {{
                                "content_type": "string - e.g. application/json",
                                "schema": "string - description of request schema"
                            }},
                            "response_format": {{
                                "content_type": "string - e.g. application/json",
                                "schema": "string - description of response schema",
                                "status_codes": ["array of possible status codes with meaning"]
                            }},
                            "authentication_required": true/false,
                            "permissions_required": ["array of permissions needed"]
                        }}
                    ],
                    "error_handling": "string - standard error response format"
                }},
                "security_design": {{
                    "authentication_method": "string",
                    "authorization_strategy": "string",
                    "data_encryption": {{
                        "at_rest": "string - encryption for stored data",
                        "in_transit": "string - encryption for data in transit",
                        "in_use": "string - encryption for data in use (if applicable)"
                    }},
                    "security_measures": [
                        {{
                            "category": "string - e.g. Input Validation, Access Control",
                            "measures": ["array of specific security measures"],
                            "implementation": "string - how it's implemented"
                        }}
                    ],
                    "compliance_considerations": ["array of compliance requirements addressed"]
                }},
                "data_flow": [
                    {{
                        "process": "string - process name",
                        "description": "string - overall process description",
                        "steps": [
                            {{
                                "step": "string - step description",
                                "component": "string - which component handles this",
                                "input": "string - input data",
                                "output": "string - output data",
                                "error_handling": "string - how errors are handled"
                            }}
                        ],
                        "uml_sequence_description": "string - textual description of sequence diagram"
                    }}
                ],
                "integration_points": [
                    {{
                        "system": "string - external system name",
                        "integration_method": "string - how we integrate",
                        "integration_pattern": "string - e.g. API Gateway, Message Queue",
                        "data_exchanged": "string - what data is exchanged",
                        "frequency": "string - how often",
                        "error_handling": "string - how integration errors are handled",
                        "fallback_strategy": "string - what happens if integration fails"
                    }}
                ],
                "performance_design": {{
                    "caching_strategy": {{
                        "approach": "string - e.g. Redis, in-memory, CDN",
                        "cache_invalidation": "string - how cache is kept fresh",
                        "cached_resources": ["array of resources to be cached"]
                    }},
                    "optimization_techniques": [
                        {{
                            "technique": "string - optimization technique name",
                            "target_area": "string - what is being optimized",
                            "implementation": "string - how it's implemented"
                        }}
                    ],
                    "bottleneck_mitigations": ["array of potential bottlenecks and mitigations"]
                }},
                "scalability_architecture": {{
                    "scaling_approach": "string - horizontal/vertical/hybrid",
                    "statelessness_strategy": "string - how state is managed for scalability",
                    "data_partitioning": "string - how data is partitioned",
                    "load_balancing": "string - load balancing strategy",
                    "auto_scaling_policy": "string - when/how resources scale"
                }},
                "deployment_architecture": {{
                    "environments": ["array of environments - dev, staging, prod"],
                    "containerization": {{
                        "approach": "string - e.g. Docker, containerd",
                        "orchestration": "string - e.g. Kubernetes, ECS"
                    }},
                    "ci_cd_pipeline": {{
                        "tools": ["array of CI/CD tools"],
                        "stages": ["array of pipeline stages"],
                        "deployment_strategy": "string - e.g. blue-green, canary"
                    }}
                }},
                "file_structure": [
                    {{
                        "directory": "string - directory name",
                        "purpose": "string - what goes in this directory",
                        "key_files": [
                            {{
                                "filename": "string - filename",
                                "purpose": "string - what this file does",
                                "content_description": "string - brief description of content"
                            }}
                        ]
                    }}
                ],
                "observability_design": {{
                    "logging": "string - logging approach",
                    "monitoring": "string - monitoring strategy",
                    "alerting": "string - alerting mechanisms",
                    "key_metrics": ["array of important metrics to track"]
                }},
                "design_patterns_used": [
                    {{
                        "pattern": "string - design pattern name",
                        "purpose": "string - why this pattern is used",
                        "implementation_location": "string - where it's implemented"
                    }}
                ],
                "cross_cutting_concerns": [
                    {{
                        "concern": "string - e.g. logging, error handling",
                        "approach": "string - how it's addressed across the system"
                    }}
                ],
                "design_risks_mitigations": [
                    {{
                        "risk": "string - potential design risk",
                        "impact": "string - potential impact",
                        "mitigation": "string - how it's mitigated"
                    }}
                ]
            }}

            Output ONLY the JSON object. Do not include any explanatory text outside the JSON.
            """,
            input_variables=["brd_analysis", "tech_stack"],
            partial_variables={"format_instructions": self.json_parser.get_format_instructions()},
        )
    
    def get_default_structure(self) -> Dict[str, Any]:
        """Define comprehensive default structure for system design."""
        return {
            "architecture_overview": {
                "pattern": "Layered Architecture with Microservices",
                "description": "A hybrid architecture combining a layered approach for the core application with microservices for specialized functionality",
                "justification": "Provides a balance between development simplicity and scalability of critical components",
                "key_principles": ["Separation of concerns", "Loose coupling", "High cohesion", "Single responsibility"]
            },
            "main_modules": [
                {
                    "name": "User Management",
                    "purpose": "Handles user authentication, authorization, and profile management",
                    "components": ["Authentication Service", "User Profile Service", "Permission Manager"],
                    "dependencies": [],
                    "interfaces": ["AuthAPI", "UserProfileAPI"]
                },
                {
                    "name": "Core Business Logic",
                    "purpose": "Implements primary business rules and workflows",
                    "components": ["Business Rules Engine", "Workflow Processor", "Domain Services"],
                    "dependencies": ["User Management"],
                    "interfaces": ["BusinessAPI", "WorkflowAPI"]
                },
                {
                    "name": "Data Access Layer",
                    "purpose": "Provides abstracted data access with ORM integration",
                    "components": ["Repository Implementations", "Data Mappers", "Query Services"],
                    "dependencies": [],
                    "interfaces": ["RepositoryInterfaces"]
                }
            ],
            "database_design": {
                "schema_type": "Relational with read replicas",
                "optimization_strategy": "Denormalization for read-heavy tables, vertical partitioning for large tables",
                "tables": [
                    {
                        "name": "users",
                        "purpose": "Store user account information",
                        "key_fields": [
                            {
                                "name": "id",
                                "type": "UUID",
                                "constraints": "PRIMARY KEY",
                                "description": "Unique user identifier"
                            },
                            {
                                "name": "username",
                                "type": "VARCHAR(50)",
                                "constraints": "UNIQUE NOT NULL",
                                "description": "User login name"
                            },
                            {
                                "name": "email",
                                "type": "VARCHAR(100)",
                                "constraints": "UNIQUE NOT NULL",
                                "description": "User email for notifications and recovery"
                            },
                            {
                                "name": "password_hash",
                                "type": "VARCHAR(255)",
                                "constraints": "NOT NULL",
                                "description": "Bcrypt hashed password"
                            }
                        ],
                        "relationships": [
                            {
                                "related_to": "user_roles",
                                "relationship_type": "one-to-many",
                                "implementation": "Foreign key from user_roles to users"
                            }
                        ]
                    }
                ],
                "indexes": [
                    {
                        "table": "users",
                        "fields": ["email"],
                        "type": "BTREE",
                        "purpose": "Fast lookup during login"
                    },
                    {
                        "table": "users",
                        "fields": ["username"],
                        "type": "BTREE",
                        "purpose": "Fast lookup during login"
                    }
                ],
                "constraints": ["Referential integrity for all relationships", "Check constraints for data validation"],
                "migration_strategy": "Versioned migrations with backward compatibility for one version"
            },
            "api_design": {
                "style": "RESTful API with resource-based endpoints",
                "base_url": "/api/v1",
                "versioning_strategy": "URL-based versioning (e.g., /api/v1/, /api/v2/)",
                "authentication": "JWT Bearer Token with refresh tokens",
                "rate_limiting": "Token bucket algorithm with client IP and API key limits",
                "endpoints": [
                    {
                        "method": "POST",
                        "path": "/auth/login",
                        "purpose": "User authentication",
                        "request_format": {
                            "content_type": "application/json",
                            "schema": "{ username: string, password: string }"
                        },
                        "response_format": {
                            "content_type": "application/json",
                            "schema": "{ access_token: string, refresh_token: string, user: UserObject }",
                            "status_codes": ["200 OK", "401 Unauthorized", "429 Too Many Requests"]
                        },
                        "authentication_required": False,
                        "permissions_required": []
                    }
                ],
                "error_handling": "Standardized error responses with error codes, messages, and request IDs"
            },
            "security_design": {
                "authentication_method": "JWT with refresh tokens, PKCE for SPA flows",
                "authorization_strategy": "Role-based access control (RBAC) with attribute-based refinements",
                "data_encryption": {
                    "at_rest": "AES-256 encryption for sensitive database fields",
                    "in_transit": "TLS 1.3 for all HTTP traffic",
                    "in_use": "Memory protection techniques for sensitive data"
                },
                "security_measures": [
                    {
                        "category": "Input Validation",
                        "measures": ["Schema validation", "Sanitization", "Parameterized queries"],
                        "implementation": "Centralized validation middleware"
                    },
                    {
                        "category": "Access Control",
                        "measures": ["Token validation", "Permission checks", "Rate limiting"],
                        "implementation": "AuthZ middleware in API gateway"
                    }
                ],
                "compliance_considerations": ["GDPR data handling", "OWASP Top 10 mitigations"]
            },
            "data_flow": [
                {
                    "process": "User Authentication",
                    "description": "Process for authenticating users and issuing access tokens",
                    "steps": [
                        {
                            "step": "Submit login credentials",
                            "component": "Authentication Controller",
                            "input": "Username/password",
                            "output": "Validated credentials",
                            "error_handling": "Return 401 for invalid credentials"
                        },
                        {
                            "step": "Verify credentials",
                            "component": "Authentication Service",
                            "input": "Validated credentials",
                            "output": "User identity",
                            "error_handling": "Log failed attempts, implement rate limiting"
                        },
                        {
                            "step": "Generate tokens",
                            "component": "Token Service",
                            "input": "User identity",
                            "output": "JWT access and refresh tokens",
                            "error_handling": "Log token generation failures"
                        },
                        {
                            "step": "Return tokens",
                            "component": "Authentication Controller",
                            "input": "JWT tokens + user profile",
                            "output": "HTTP response with tokens and user data",
                            "error_handling": "Return 500 with request ID for server errors"
                        }
                    ],
                    "uml_sequence_description": "Client->AuthController: Login request with credentials; AuthController->AuthService: Validate credentials; AuthService->Database: Query user record; Database->AuthService: Return user data; AuthService->TokenService: Generate JWT; TokenService->AuthService: Return tokens; AuthService->AuthController: User data and tokens; AuthController->Client: 200 OK with tokens and user data"
                }
            ],
            "integration_points": [
                {
                    "system": "Email Service",
                    "integration_method": "REST API",
                    "integration_pattern": "Asynchronous messaging with retry",
                    "data_exchanged": "Email templates and recipient information",
                    "frequency": "On-demand",
                    "error_handling": "Retry with exponential backoff",
                    "fallback_strategy": "Queue messages for later delivery"
                }
            ],
            "performance_design": {
                "caching_strategy": {
                    "approach": "Redis for application cache, CDN for static assets",
                    "cache_invalidation": "Time-based expiration with manual invalidation API",
                    "cached_resources": ["User permissions", "Frequently accessed reference data", "API responses"]
                },
                "optimization_techniques": [
                    {
                        "technique": "Query optimization",
                        "target_area": "Database queries",
                        "implementation": "Optimized indexes, query tuning, read replicas"
                    },
                    {
                        "technique": "Connection pooling",
                        "target_area": "Database connections",
                        "implementation": "Configured connection pool with appropriate sizing"
                    }
                ],
                "bottleneck_mitigations": [
                    "Horizontal scaling for API servers",
                    "Database read replicas for read-heavy operations",
                    "Asynchronous processing for long-running tasks"
                ]
            },
            "scalability_architecture": {
                "scaling_approach": "Horizontal scaling with stateless services",
                "statelessness_strategy": "External session store using Redis",
                "data_partitioning": "Vertical partitioning by feature domain, sharding for high-volume tables",
                "load_balancing": "Layer 7 load balancing with sticky sessions where needed",
                "auto_scaling_policy": "CPU utilization threshold with pre-provisioned capacity for predictable loads"
            },
            "deployment_architecture": {
                "environments": ["Development", "Testing", "Staging", "Production"],
                "containerization": {
                    "approach": "Docker containers for all services",
                    "orchestration": "Kubernetes for container orchestration"
                },
                "ci_cd_pipeline": {
                    "tools": ["GitHub Actions", "ArgoCD", "SonarQube"],
                    "stages": ["Build", "Test", "Security Scan", "Deploy to Dev", "Integration Tests", "Deploy to Staging", "Performance Tests", "Deploy to Production"],
                    "deployment_strategy": "Blue-green deployment for zero downtime"
                }
            },
            "file_structure": [
                {
                    "directory": "src/core",
                    "purpose": "Core business logic and domain models",
                    "key_files": [
                        {
                            "filename": "models.py",
                            "purpose": "Domain model definitions",
                            "content_description": "Contains domain entity classes with validation"
                        },
                        {
                            "filename": "services.py",
                            "purpose": "Business logic services",
                            "content_description": "Service classes that implement business rules"
                        }
                    ]
                }
            ],
            "observability_design": {
                "logging": "Structured logging with correlation IDs across services",
                "monitoring": "Prometheus metrics with Grafana dashboards",
                "alerting": "Alert rules with escalation policies and on-call rotation",
                "key_metrics": ["Request latency", "Error rates", "System resource usage", "Business KPIs"]
            },
            "design_patterns_used": [
                {
                    "pattern": "Repository Pattern",
                    "purpose": "Abstract data access from business logic",
                    "implementation_location": "Data access layer"
                },
                {
                    "pattern": "Factory Pattern",
                    "purpose": "Dynamic creation of service instances",
                    "implementation_location": "Service initialization"
                }
            ],
            "cross_cutting_concerns": [
                {
                    "concern": "Logging",
                    "approach": "Centralized logging configuration with context enrichment middleware"
                },
                {
                    "concern": "Error Handling",
                    "approach": "Global exception middleware with standardized error responses"
                }
            ],
            "design_risks_mitigations": [
                {
                    "risk": "Database performance under high load",
                    "impact": "Increased latency and potential system failures",
                    "mitigation": "Implement read replicas, connection pooling, and query optimization"
                },
                {
                    "risk": "Security vulnerabilities in authentication",
                    "impact": "Unauthorized access to sensitive data",
                    "mitigation": "Regular security audits, proper token management, and secure coding practices"
                }
            ]
        }
    
    def get_default_response(self) -> Dict[str, Any]:
        """Get default response when design fails."""
        default_structure = self.get_default_structure()
        default_structure["architecture_overview"]["description"] = "Basic layered architecture (generated due to design error)"
        default_structure["design_risks_mitigations"].append({
            "risk": "Incomplete system design",
            "impact": "Potential implementation gaps",
            "mitigation": "Conduct detailed design review before implementation"
        })
        return default_structure
    
    def run(self, brd_analysis: Dict[str, Any], tech_stack_recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create comprehensive system design with enhanced validation and consistency checks.
        """
        self.log_start("Starting comprehensive system design creation")
        self.log_info("Using temperature 0.2 for structured architectural decisions")
        
        # Validate inputs
        if not brd_analysis or not isinstance(brd_analysis, dict):
            self.log_warning("Invalid BRD analysis input - using default design")
            return self.get_default_response()
        
        if not tech_stack_recommendation or not isinstance(tech_stack_recommendation, dict):
            self.log_warning("Invalid tech stack input - using default design")
            return self.get_default_response()
        
        try:
            # Use RAG for architectural patterns if available
            arch_context = ""
            if self.rag_retriever:
                tech_backend = tech_stack_recommendation.get("backend", {}).get("language", "")
                tech_frontend = tech_stack_recommendation.get("frontend", {}).get("language", "")
                tech_db = tech_stack_recommendation.get("database", {}).get("type", "")
                arch_pattern = tech_stack_recommendation.get("architecture_pattern", "")
                
                query = f"system design architecture patterns for {tech_backend} {tech_frontend} {tech_db} {arch_pattern}"
                arch_context = self.get_rag_context(query, max_docs=3)
                self.log_info("Retrieved architectural patterns context from knowledge base")
            
            # Execute LLM chain with enhanced context
            self.log_info("Generating comprehensive system design")
            
            response = self.execute_with_monitoring(
                self.execute_llm_chain,
                {
                    "brd_analysis": json.dumps(brd_analysis, indent=2),
                    "tech_stack": json.dumps(tech_stack_recommendation, indent=2)
                }
            )
            
            # Validate response structure
            required_keys = [
                "architecture_overview", "main_modules", "database_design", 
                "api_design", "security_design", "data_flow", "integration_points",
                "performance_design", "scalability_architecture", "deployment_architecture",
                "file_structure", "observability_design"
            ]
            
            validated_response = self.validate_response_structure(response, required_keys)
            
            # Perform additional consistency checks
            validated_response = self.verify_design_consistency(validated_response, tech_stack_recommendation)
            
            # Log execution summary
            self.log_execution_summary(validated_response)
            
            return validated_response
            
        except Exception as e:
            self.log_error(f"System design generation failed: {e}")
            return self.get_default_response()
    
    def verify_design_consistency(self, design: Dict[str, Any], tech_stack: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify consistency between system design and tech stack recommendations.
        Add warnings and corrections where needed.
        """
        try:
            # Initialize list for consistency issues
            if "design_risks_mitigations" not in design:
                design["design_risks_mitigations"] = []
            
            # Check database consistency
            db_type_tech_stack = tech_stack.get("database", {}).get("type", "").lower()
            db_schema_type = design.get("database_design", {}).get("schema_type", "").lower()
            
            # Simple check for major inconsistency (e.g., MongoDB recommended but SQL schema designed)
            if "mongo" in db_type_tech_stack and "relation" in db_schema_type:
                self.log_warning("Database inconsistency: MongoDB recommended but relational schema designed")
                design["design_risks_mitigations"].append({
                    "risk": "Database technology mismatch",
                    "impact": "Implementation challenges with NoSQL vs relational schema",
                    "mitigation": "Review database design to align with MongoDB document structure"
                })
            
            # Check architecture pattern consistency
            arch_pattern_tech_stack = tech_stack.get("architecture_pattern", "").lower()
            arch_pattern_design = design.get("architecture_overview", {}).get("pattern", "").lower()
            
            if ("micro" in arch_pattern_tech_stack and "mono" in arch_pattern_design) or \
               ("mono" in arch_pattern_tech_stack and "micro" in arch_pattern_design):
                self.log_warning("Architecture pattern inconsistency detected")
                design["design_risks_mitigations"].append({
                    "risk": "Architecture pattern mismatch",
                    "impact": "Inconsistent system organization leading to development challenges",
                    "mitigation": "Align system design with recommended architecture pattern or justify deviation"
                })
            
            # Check frontend framework consistency
            frontend_tech_stack = tech_stack.get("frontend", {}).get("framework", "").lower()
            frontend_in_design = False
            
            # Check if frontend framework appears in file structure or modules
            for directory in design.get("file_structure", []):
                if "front" in directory.get("directory", "").lower() or frontend_tech_stack in directory.get("directory", "").lower():
                    frontend_in_design = True
                    break
            
            if not frontend_in_design:
                self.log_info("Adding frontend structure to align with tech stack recommendation")
                # Add frontend directory to file structure if missing
                design["file_structure"].append({
                    "directory": f"src/frontend-{frontend_tech_stack}",
                    "purpose": f"Frontend implementation using {frontend_tech_stack}",
                    "key_files": [
                        {
                            "filename": "index.js",
                            "purpose": "Main entry point",
                            "content_description": "Application initialization and routing setup"
                        },
                        {
                            "filename": "components/",
                            "purpose": "UI component directory",
                            "content_description": "Reusable UI components"
                        }
                    ]
                })
            
            return design
            
        except Exception as e:
            self.log_warning(f"Design consistency check failed: {e}")
            return design
    
    def validate_response_structure(self, response: Dict[str, Any], required_keys: List[str]) -> Dict[str, Any]:
        """Enhanced validation with detailed checks and default values."""
        default_structure = self.get_default_structure()
        
        # If response is empty or not a dict, return default
        if not response or not isinstance(response, dict):
            self.log_warning("Invalid response structure received from LLM")
            return default_structure
        
        # Create a validated response with defaults for missing sections
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