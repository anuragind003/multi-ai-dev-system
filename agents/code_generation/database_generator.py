"""
Database Generator Agent - Specialized in generating database schemas, migrations, and queries.
"""

import json
import os
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

from agents.code_generation.base_code_generator import BaseCodeGeneratorAgent
from models.data_contracts import GeneratedFile, CodeGenerationOutput, WorkItem
from tools.code_generation_utils import parse_llm_output_into_files

# Enhanced memory and RAG imports
from enhanced_memory_manager import create_memory_manager, EnhancedSharedProjectMemory
from rag_manager import get_rag_manager

logger = logging.getLogger(__name__)

class DatabaseGeneratorAgent(BaseCodeGeneratorAgent):
    """
    Specializes in generating all database-related artifacts in a single, structured step.
    Produces complete schema definitions, migrations, and optimized queries.
    """
    
    def __init__(self, llm, memory, 
                 temperature: float = 0.1,
                 output_dir="./output/database", 
                 code_execution_tool=None,
                 rag_retriever=None,
                 message_bus=None):
        
        # Initialize the base code generator with all parameters
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Database Generator Agent",
            temperature=temperature,
            output_dir=output_dir,
            code_execution_tool=code_execution_tool,
            rag_retriever=rag_retriever,
            message_bus=message_bus
        )
        
        # Enhanced memory is already initialized in BaseCodeGeneratorAgent
        # Initialize RAG context if not already done by parent
        if not hasattr(self, 'rag_manager'):
            self.rag_manager = get_rag_manager()
            if self.rag_manager:
                self.logger.info("RAG manager available for enhanced database generation")
            else:
                self.logger.warning("RAG manager not available - proceeding with basic database generation")
        
        # Maximum tokens and context limits
        self.max_tokens = 8192  # Adequate for multi-file generation
        self.max_context_chars = 2000
        self.max_rag_docs = 3
        
        # Initialize comprehensive prompt template
        self._initialize_prompt_templates()
    
    def _initialize_prompt_templates(self):
        """Initialize a single comprehensive prompt template for all database artifacts."""
        
        multi_file_format = """
        CRITICAL OUTPUT FORMAT:
        You MUST provide your response as a single block of text. For each file you generate, 
        you MUST use the following format:

        ### FILE: path/to/your/file.ext
        ```filetype
        # The full content of the file goes here
        ```

        Continue this pattern for all files. Generate the following types of files:
        1. Schema definition files (SQL or NoSQL schema depending on the database type)
        2. Migration files with up/down scripts
        3. Query files with optimized CRUD operations
        4. Any necessary ORM model definitions if appropriate
        5. Performance monitoring and optimization scripts
        6. Security and backup configurations
        7. Database testing and validation scripts
        8. DevOps and deployment configurations
        Be thorough and include all necessary files to fully implement the database layer.
        """
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system",
             "You are an expert database architect specializing in enterprise-grade database implementations. "
             "Your task is to generate PRODUCTION-READY, ENTERPRISE-SCALE database systems with comprehensive "
             "security, monitoring, performance optimization, and operational excellence.\n\n"
             
             "**MANDATORY ENTERPRISE REQUIREMENTS:**\n"
             "You MUST include ALL of the following in every database implementation:\n\n"
             
             "1. **SECURITY & COMPLIANCE:**\n"
             "   - Row-Level Security (RLS) policies and roles\n"
             "   - Column-level encryption for sensitive data\n"
             "   - Audit trails with immutable logging\n"
             "   - Access control matrices and user roles\n"
             "   - Data masking for non-production environments\n"
             "   - Security vulnerability scanning scripts\n"
             "   - Compliance validation (GDPR, HIPAA, SOX, PCI-DSS)\n\n"
             
             "2. **PERFORMANCE & SCALABILITY:**\n"
             "   - Advanced indexing strategies (partial, functional, covering)\n"
             "   - Query performance monitoring and optimization\n"
             "   - Connection pooling and resource management\n"
             "   - Database partitioning and sharding strategies\n"
             "   - Read replicas and load balancing configuration\n"
             "   - Query plan analysis and optimization scripts\n"
             "   - Performance benchmarking and load testing\n\n"
             
             "3. **MONITORING & OBSERVABILITY:**\n"
             "   - Comprehensive database monitoring dashboards\n"
             "   - Real-time performance metrics collection\n"
             "   - Automated alerting for critical thresholds\n"
             "   - Slow query logging and analysis\n"
             "   - Resource utilization monitoring\n"
             "   - Database health checks and diagnostics\n"
             "   - Business metrics and KPI tracking\n\n"
             
             "4. **BACKUP & DISASTER RECOVERY:**\n"
             "   - Automated backup strategies (full, incremental, differential)\n"
             "   - Point-in-time recovery procedures\n"
             "   - Cross-region backup replication\n"
             "   - Disaster recovery testing and validation\n"
             "   - Data corruption detection and repair\n"
             "   - Backup encryption and security\n"
             "   - Recovery time objective (RTO) optimization\n\n"
             
             "5. **DATA GOVERNANCE & QUALITY:**\n"
             "   - Data validation rules and constraints\n"
             "   - Data lineage and metadata management\n"
             "   - Data quality monitoring and reporting\n"
             "   - Schema evolution and migration strategies\n"
             "   - Data retention and archival policies\n"
             "   - Data catalog and documentation\n"
             "   - Referential integrity enforcement\n\n"
             
             "6. **DEVOPS & AUTOMATION:**\n"
             "   - Infrastructure as Code (Terraform, CloudFormation)\n"
             "   - CI/CD pipeline integration for database changes\n"
             "   - Automated testing frameworks for database logic\n"
             "   - Environment provisioning and configuration\n"
             "   - Database schema version control\n"
             "   - Deployment automation and rollback procedures\n"
             "   - Configuration management and secrets handling\n\n"
             
             "**DOMAIN AND DATABASE AWARENESS:**\n"
             "- Healthcare: HIPAA compliance, audit trails, data encryption, patient privacy patterns\n"
             "- Financial: PCI-DSS compliance, transaction integrity, fraud detection, secure payment data\n"
             "- IoT: Time-series optimization, device data patterns, real-time ingestion, edge data handling\n"
             "- E-commerce: Product catalogs, inventory tracking, cart optimization, order management\n"
             "- Analytics: OLAP patterns, data warehousing, aggregation tables, reporting optimization\n"
             "- Real-time: Streaming data, cache patterns, session management, low-latency access\n\n"
             
             "**DATABASE-SPECIFIC PATTERNS:**\n"
             "- PostgreSQL/MySQL: ACID transactions, normalized schemas, foreign keys, advanced indexing\n"
             "- MongoDB: Document schemas, embedded vs referenced data, compound indexes, aggregation pipelines\n"
             "- Redis: Key-value patterns, data structures, expiration policies, pub/sub patterns\n"
             "- InfluxDB: Time-series schemas, retention policies, continuous queries, measurement organization\n"
             "- Neo4j: Graph relationships, node properties, path queries, graph algorithms\n"
             "- Cassandra: Partition keys, clustering columns, materialized views, time-based data\n\n"
             
             "Generate enterprise-grade database implementations that are immediately deployable to production "
             "with comprehensive security, monitoring, and operational excellence built-in."),
            ("human",
             "Generate a COMPLETE ENTERPRISE-GRADE database implementation for **{db_type}** with **{migration_tool}** "
             "for migrations, optimized for the **{project_domain}** domain. This must be immediately deployable "
             "to production with enterprise security, monitoring, and operational excellence.\n\n"
             
             "## Project Context\n"
             "Domain: {project_domain}\n"
             "Tech Stack: {tech_stack_info}\n"
             "System Design: {system_design}\n"
             "Data Model: {data_model}\n\n"
             
             "## MANDATORY ENTERPRISE REQUIREMENTS\n"
             "You MUST generate ALL of the following categories of files:\n\n"
             
             "### 1. **CORE SCHEMA & MIGRATIONS**\n"
             "   - Complete database schema with all entities, relationships, and constraints\n"
             "   - Migration scripts with proper up/down migration support\n"
             "   - Data seeding scripts for initial setup and testing\n"
             "   - Schema validation and consistency checks\n"
             "   - Index creation optimized for query patterns\n\n"
             
             "### 2. **SECURITY & COMPLIANCE**\n"
             "   - Row-Level Security (RLS) policies for data access control\n"
             "   - User roles and permissions matrix\n"
             "   - Audit trail tables and triggers for all data changes\n"
             "   - Data encryption configuration (at-rest and in-transit)\n"
             "   - Compliance validation scripts for {project_domain} regulations\n"
             "   - Security vulnerability assessment queries\n"
             "   - Data masking scripts for non-production environments\n\n"
             
             "### 3. **PERFORMANCE & OPTIMIZATION**\n"
             "   - Advanced indexing strategies (covering, partial, functional indexes)\n"
             "   - Query optimization and performance tuning scripts\n"
             "   - Database partitioning and sharding configuration\n"
             "   - Connection pooling and resource management setup\n"
             "   - Slow query analysis and monitoring\n"
             "   - Performance benchmarking and load testing scripts\n"
             "   - Query plan analysis tools\n\n"
             
             "### 4. **MONITORING & OBSERVABILITY**\n"
             "   - Database monitoring dashboard configuration\n"
             "   - Real-time metrics collection scripts\n"
             "   - Automated alerting rules for critical thresholds\n"
             "   - Health check and diagnostic queries\n"
             "   - Resource utilization monitoring\n"
             "   - Business metrics and KPI tracking queries\n"
             "   - Log analysis and reporting tools\n\n"
             
             "### 5. **BACKUP & DISASTER RECOVERY**\n"
             "   - Automated backup scripts (full, incremental, differential)\n"
             "   - Point-in-time recovery procedures and scripts\n"
             "   - Disaster recovery testing and validation\n"
             "   - Cross-region backup replication configuration\n"
             "   - Data corruption detection and repair procedures\n"
             "   - Backup verification and integrity checking\n"
             "   - Recovery time optimization strategies\n\n"
             
             "### 6. **DATA GOVERNANCE & QUALITY**\n"
             "   - Data validation rules and constraint enforcement\n"
             "   - Data quality monitoring and reporting queries\n"
             "   - Data lineage tracking and metadata management\n"
             "   - Schema evolution and migration strategies\n"
             "   - Data retention and archival policies\n"
             "   - Referential integrity validation scripts\n"
             "   - Data catalog and documentation generation\n\n"
             
             "### 7. **DEVOPS & AUTOMATION**\n"
             "   - Infrastructure as Code (Terraform/CloudFormation) templates\n"
             "   - CI/CD pipeline configuration for database changes\n"
             "   - Automated testing framework for database logic\n"
             "   - Environment provisioning and configuration scripts\n"
             "   - Database schema version control integration\n"
             "   - Deployment automation and rollback procedures\n"
             "   - Configuration management and secrets handling\n\n"
             
             "### 8. **OPERATIONAL QUERIES & PROCEDURES**\n"
             "   - Optimized CRUD operations for all entities\n"
             "   - Domain-specific business logic queries\n"
             "   - Reporting and analytics query templates\n"
             "   - Maintenance and housekeeping procedures\n"
             "   - Data migration and ETL scripts\n"
             "   - Performance troubleshooting queries\n"
             "   - Administrative and operational procedures\n\n"
             
             "## Domain-Specific Requirements\n"
             "{domain_specific_requirements}\n\n"
             
             "## Best Practices Context\n"
             "{rag_context}\n\n"
             
             "{code_review_feedback}\n\n"
             
             "## OUTPUT REQUIREMENTS\n"
             "Generate a MINIMUM of 20+ files covering all enterprise requirements above. "
             "Include proper file organization with directories for different concerns "
             "(schema/, migrations/, security/, monitoring/, backup/, etc.). "
             "Each file must be production-ready with comprehensive documentation.\n\n"
             
             "Follow this multi-file output format EXACTLY:\n{format_instructions}")
        ])
        
        self.prompt_template = self.prompt_template.partial(format_instructions=multi_file_format)

    def _create_prompt_template(self) -> PromptTemplate:
        """Creates the prompt template for the agent."""
        prompt_string = """
        You are a world-class database engineer. Your task is to write clean, efficient, and well-documented database schemas, migrations, and queries.
        You must follow all instructions precisely. The scripts you generate will be part of a larger project.

        {rag_context}

        **Technology Stack:**
        - Database Management System: {database_management_system}
        - ORM/Query Builder: {orm}

        **Work Item:**
        - Description: {work_item_description}
        - File Path: {file_path}
        - Example Snippet (for reference):
        ```
        {example_code_snippet}
        ```

        **Instructions:**
        1.  Generate the complete SQL/script for the file specified in `File Path`.
        2.  You MUST also generate the corresponding test data or a validation script.
        3.  Format your response clearly, separating the implementation script and test script with the specified tags.

        **Output Format:**
        Provide your response in the following format, and do not include any other text or explanations.

        [CODE]
        ```sql
        -- Your generated database script here
        ```
        [/CODE]

        [TESTS]
        ```sql
        -- Your generated test data or validation script here
        ```
        [/TESTS]
        """
        return PromptTemplate(
            template=prompt_string,
            input_variables=[
                "work_item_description",
                "file_path",
                "database_management_system",
                "orm",
                "example_code_snippet",
                "rag_context"
            ],
        )

    def _generate_code(self, llm, invoke_config, work_item: WorkItem, tech_stack: dict) -> dict:
        """
        Generates database-related code or scripts.
        """
        prompt_template = self._create_prompt_template()
        chain = prompt_template | llm

        query = f"Task: {work_item.description}\nFile to be created/modified: {work_item.file_path}"
        rag_context = self._get_rag_context(query)

        logger.info(f"Running DatabaseGeneratorAgent for work item: {work_item.description}")
        
        try:
            result = chain.invoke({
                "work_item_description": work_item.description,
                "file_path": work_item.file_path,
                "database_management_system": tech_stack.get("database", "PostgreSQL"),
                "orm": tech_stack.get("orm", "SQLAlchemy"),
                "example_code_snippet": work_item.example or "No example provided.",
                "rag_context": rag_context,
            })
            
            logger.info(f"DatabaseGeneratorAgent completed for work item: {work_item.description}")
            
            parsed_output = self._parse_output(result.content)
            files = self._create_files_from_parsed_output(parsed_output, work_item)

            return CodeGenerationOutput(
                files=files,
                summary=f"Successfully generated database scripts for: {work_item.description}"
            ).dict()

        except Exception as e:
            logger.error(f"Error running DatabaseGeneratorAgent: {e}", exc_info=True)
            return self.get_default_response()
            
    def _parse_output(self, llm_output: str) -> dict:
        """Parses the LLM's output to extract the implementation and test code."""
        code = llm_output.split("[CODE]")[1].split("[/CODE]")[0].strip()
        test_code = llm_output.split("[TESTS]")[1].split("[/TESTS]")[0].strip()

        code = code.replace("```sql", "").replace("```", "").strip()
        test_code = test_code.replace("```sql", "").replace("```", "").strip()
        
        return {"code": code, "test_code": test_code}

    def _create_files_from_parsed_output(self, parsed_output: dict, work_item: WorkItem) -> list[GeneratedFile]:
        """Creates a list of GeneratedFile objects from the parsed LLM output."""
        files = []
        
        if parsed_output.get("code"):
            files.append(GeneratedFile(file_path=work_item.file_path, content=parsed_output["code"]))
        
        if parsed_output.get("test_code"):
            test_file_path = self._get_test_file_path(work_item.file_path)
            files.append(GeneratedFile(file_path=test_file_path, content=parsed_output["test_code"]))
            
        return files

    def _get_test_file_path(self, file_path_str: str) -> str:
        """Derives a conventional test file path from a source file path."""
        p = Path(file_path_str)
        # e.g., 'db/migrations/001_create_users.sql' -> 'tests/db/001_test_data.sql'
        test_filename = f"{p.stem}_test_data{p.suffix}"
        
        new_path = p.parent.parent / 'tests' / p.parent.name / test_filename
        return str(new_path)

    # --- Helper methods for database generation ---
    
    def _extract_database_type(self, tech_stack: Dict[str, Any]) -> str:
        """Extract database type from tech stack with intelligent domain-aware defaults."""
        try:
            # First, try to extract from tech stack recommendations
            if "database" in tech_stack:
                db_info = tech_stack["database"]
                if isinstance(db_info, dict):
                    # Handle different database info formats
                    db_type = (db_info.get("primary") or 
                              db_info.get("type") or 
                              db_info.get("name") or 
                              db_info.get("technology"))
                    if db_type:
                        return db_type.lower()
                elif isinstance(db_info, list) and len(db_info) > 0:
                    first_db = db_info[0]
                    if isinstance(first_db, dict):
                        db_type = (first_db.get("name") or 
                                  first_db.get("type") or 
                                  first_db.get("technology"))
                        if db_type:
                            return db_type.lower()
                    elif isinstance(first_db, str):
                        return first_db.lower()
                elif isinstance(db_info, str):
                    return db_info.lower()
            
            # Fallback: Intelligent domain-aware default selection
            return self._get_domain_appropriate_database(tech_stack)
            
        except Exception as e:
            self.log_warning(f"Error extracting database type: {e}")
            return self._get_domain_appropriate_database(tech_stack)
    
    def _get_domain_appropriate_database(self, tech_stack: Dict[str, Any]) -> str:
        """Get domain-appropriate database based on project context."""
        try:
            # Try to detect domain from various sources
            domain = self._detect_project_domain(tech_stack)
            
            # Domain-specific database recommendations
            domain_databases = {
                "healthcare": "postgresql",  # ACID compliance, audit trails
                "financial": "postgresql",   # Transaction integrity, ACID
                "iot": "influxdb",          # Time-series data
                "ecommerce": "postgresql",   # Transaction support, JSON
                "analytics": "clickhouse",   # Analytics workloads
                "realtime": "redis",        # Real-time data
                "content": "mongodb",       # Document storage
                "social": "neo4j",          # Graph relationships
                "startup": "sqlite",        # Simple, lightweight
                "enterprise": "postgresql"  # Mature, scalable
            }
            
            return domain_databases.get(domain, "postgresql")
            
        except Exception as e:
            self.log_warning(f"Error determining domain-appropriate database: {e}")
            return "postgresql"  # Conservative fallback
    
    def _detect_project_domain(self, tech_stack: Dict[str, Any]) -> str:
        """Detect project domain from tech stack and context."""
        try:
            # Check for domain hints in tech stack
            if isinstance(tech_stack, dict):
                domain = tech_stack.get("domain") or tech_stack.get("project_domain")
                if domain:
                    return domain.lower()
                
                # Look for domain indicators in project context
                project_name = tech_stack.get("project_name", "").lower()
                requirements = str(tech_stack.get("requirements", "")).lower()
                
                # Domain detection keywords
                if any(keyword in project_name or keyword in requirements 
                       for keyword in ["patient", "medical", "health", "hospital"]):
                    return "healthcare"
                elif any(keyword in project_name or keyword in requirements 
                         for keyword in ["payment", "bank", "finance", "trading"]):
                    return "financial"
                elif any(keyword in project_name or keyword in requirements 
                         for keyword in ["device", "sensor", "iot", "telemetry"]):
                    return "iot"
                elif any(keyword in project_name or keyword in requirements 
                         for keyword in ["shop", "cart", "product", "ecommerce"]):
                    return "ecommerce"
                elif any(keyword in project_name or keyword in requirements 
                         for keyword in ["analytics", "data", "report"]):
                    return "analytics"
                elif any(keyword in project_name or keyword in requirements 
                         for keyword in ["real-time", "live", "streaming"]):
                    return "realtime"
                elif any(keyword in project_name or keyword in requirements 
                         for keyword in ["content", "cms", "blog", "article"]):
                    return "content"
                elif any(keyword in project_name or keyword in requirements 
                         for keyword in ["social", "network", "friend", "follow"]):
                    return "social"
            
            return "generic"
            
        except Exception:
            return "generic"
    
    def _determine_migration_tool(self, tech_stack: Dict[str, Any]) -> str:
        """Determine which migration tool to use based on tech stack."""
        try:
            # Default to a generic migration approach
            migration_tool = "SQL migrations"
            
            # Check backend framework to determine migration tool
            if "backend" in tech_stack and tech_stack["backend"]:
                backend = tech_stack["backend"]
                
                # Handle backend as either list or object
                if isinstance(backend, list) and len(backend) > 0:
                    first_backend = backend[0]
                    if isinstance(first_backend, dict):
                        backend_name = first_backend.get("name", "").lower()
                    else:
                        backend_name = str(first_backend).lower()
                        
                    # Map backend frameworks to migration tools
                    if "django" in backend_name:
                        migration_tool = "Django migrations"
                    elif "flask" in backend_name:
                        migration_tool = "Alembic"
                    elif "express" in backend_name or "node" in backend_name:
                        migration_tool = "Sequelize"
                    elif "spring" in backend_name:
                        migration_tool = "Flyway"
                    elif "rails" in backend_name:
                        migration_tool = "ActiveRecord migrations"
                    elif "laravel" in backend_name:
                        migration_tool = "Laravel migrations"
                elif isinstance(backend, dict):
                    backend_name = backend.get("framework", "").lower()
                    if "django" in backend_name:
                        migration_tool = "Django migrations"
                    elif "flask" in backend_name:
                        migration_tool = "Alembic"
                    elif "express" in backend_name or "node" in backend_name:
                        migration_tool = "Sequelize"
                    elif "spring" in backend_name:
                        migration_tool = "Flyway"
                    elif "rails" in backend_name:
                        migration_tool = "ActiveRecord migrations"
                    elif "laravel" in backend_name:
                        migration_tool = "Laravel migrations"
                        
            # Check if there's an explicit ORM or migration tool mentioned
            if "orm" in tech_stack:
                orm = tech_stack["orm"]
                if isinstance(orm, str):
                    orm = orm.lower()
                    if "sequelize" in orm:
                        migration_tool = "Sequelize migrations"
                    elif "prisma" in orm:
                        migration_tool = "Prisma migrations"
                    elif "typeorm" in orm:
                        migration_tool = "TypeORM migrations"
                    elif "sqlalchemy" in orm:
                        migration_tool = "Alembic"
                elif isinstance(orm, dict) and "name" in orm:
                    orm_name = orm["name"].lower()
                    if "sequelize" in orm_name:
                        migration_tool = "Sequelize migrations"
                    elif "prisma" in orm_name:
                        migration_tool = "Prisma migrations"
                    elif "typeorm" in orm_name:
                        migration_tool = "TypeORM migrations"
                    elif "sqlalchemy" in orm_name:
                        migration_tool = "Alembic"
                        
        except Exception as e:
            self.log_warning(f"Error determining migration tool: {e}. Using default.")
            migration_tool = "SQL migrations"
            
        return migration_tool
    
    def _extract_data_model(self, system_design: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data model information from the system design."""
        data_model = {}
        
        try:
            # Look for data_model in different possible locations
            if "data_model" in system_design:
                data_model = system_design["data_model"]
            elif "database" in system_design:
                data_model = system_design["database"]
            elif "data_entities" in system_design:
                data_model = {"entities": system_design["data_entities"]}
            elif "entities" in system_design:
                data_model = {"entities": system_design["entities"]}
            elif "database_schema" in system_design:
                data_model = system_design["database_schema"]
            elif "modules" in system_design:
                # Try to find data model in modules
                modules = system_design["modules"]
                for module in modules:
                    if isinstance(module, dict) and "name" in module:
                        if module["name"].lower() in ["database", "data", "data model", "datamodel"]:
                            data_model = module
                            break
        except Exception as e:
            self.log_warning(f"Error extracting data model: {e}")
            
        return data_model
    
    def _prune_system_design_for_db(self, system_design: Dict[str, Any]) -> Dict[str, Any]:
        """Prune system design to only include database-relevant parts."""
        relevant_keys = [
            "data_model", "database", "data_entities", "entities", "relationships", 
            "database_design", "schema", "tables", "collections"
        ]
        
        pruned_design = {}
        
        for key in relevant_keys:
            if key in system_design:
                pruned_design[key] = system_design[key]
        
        # Add API endpoints for context if available
        if "api_design" in system_design and "endpoints" in system_design["api_design"]:
            pruned_design["api_endpoints"] = system_design["api_design"]["endpoints"]
        
        return pruned_design
    
    def _get_database_rag_context(self, db_type: str) -> str:
        """Get RAG context specific to database implementation."""
        if not self.rag_retriever:
            return ""
        
        try:
            # Create targeted queries for better RAG results
            queries = [
                f"{db_type} database schema best practices",
                f"{db_type} indexing and query optimization",
                f"{db_type} data modeling patterns"            ]
            
            combined_context = []
            for query in queries:
                try:
                    docs = self.rag_retriever.invoke(query)
                    if docs:
                        context = "\n\n".join([doc.page_content for doc in docs[:self.max_rag_docs]])
                        combined_context.append(f"# {query.title()}\n{context}")
                except Exception as e:
                    self.log_warning(f"Error retrieving RAG for '{query}': {e}")
            
            return "\n\n".join(combined_context)
            
        except Exception as e:
            self.log_warning(f"Error retrieving RAG context: {e}")
            return ""
    
    def _extract_code_blocks(self, content: str) -> str:
        """Extract code blocks from LLM response content."""
        if "```" not in content:
            return content
            
        code_blocks = []
        in_block = False
        current_block = []
        
        for line in content.split("\n"):
            if line.startswith("```"):
                if not in_block:
                    in_block = True
                    # Skip the opening backticks line
                    continue
                else:
                    in_block = False
                    if current_block:
                        code_blocks.append("\n".join(current_block))
                        current_block = []
                    continue
            
            if in_block:
                current_block.append(line)        
        return "\n\n".join(code_blocks)
    
    def _get_file_extension_for_db(self, db_type: str) -> str:
        """Get appropriate file extension for database type with comprehensive support."""
        extensions = {
            # SQL Databases
            "postgresql": "sql",
            "mysql": "sql", 
            "sqlite": "sql",
            "mariadb": "sql",
            "oracle": "sql",
            "sql server": "sql",
            "sqlserver": "sql",
            "mssql": "sql",
            "h2": "sql",
            "hsqldb": "sql",
            
            # NoSQL Document Databases
            "mongodb": "js",
            "cosmosdb": "js",
            "couchdb": "js",
            "documentdb": "js",
            
            # Key-Value Stores
            "redis": "txt",
            "dynamodb": "json",
            "cassandra": "cql",
            "scylladb": "cql",
            
            # Graph Databases
            "neo4j": "cypher",
            "arangodb": "js",
            "orientdb": "sql",
            
            # Time-Series Databases
            "influxdb": "flux",
            "timescaledb": "sql",
            "prometheus": "promql",
            
            # Analytics Databases
            "clickhouse": "sql",
            "bigquery": "sql",
            "snowflake": "sql",
            "redshift": "sql",
            
            # Multi-Model
            "arangodb": "js",
            "orientdb": "sql"
        }
        
        return extensions.get(db_type.lower(), "sql")
    
    def _estimate_schema_complexity(self, system_design: Dict[str, Any]) -> str:
        """Estimate schema complexity based on entity count and relationships."""
        try:
            # Get entities from various possible locations
            entities = []
            if "data_entities" in system_design:
                entities = system_design["data_entities"]
            elif "entities" in system_design:
                entities = system_design["entities"]
            elif "data_model" in system_design and "entities" in system_design["data_model"]:
                entities = system_design["data_model"]["entities"]
            
            # Count entities and relationships
            entity_count = len(entities) if isinstance(entities, list) else 0
            relationship_count = 0
            complex_rel_count = 0
            
            # Analyze relationships
            for entity in entities:
                if isinstance(entity, dict) and "relationships" in entity:
                    rels = entity["relationships"]
                    relationship_count += len(rels) if isinstance(rels, list) else 0;
                    
                    # Check for complex relationships
                    for rel in rels if isinstance(rels, list) else []:
                        if isinstance(rel, dict) and "type" in rel:
                            rel_type = rel["type"].lower() if isinstance(rel["type"], str) else ""
                            if "many-to-many" in rel_type:
                                complex_rel_count += 1
            
            # Determine complexity level
            if entity_count <= 5 and complex_rel_count == 0:
                return "low"
            elif entity_count >= 12 or complex_rel_count >= 3:
                return "high"
            else:
                return "medium"
                
        except Exception as e:
            self.log_warning(f"Error estimating schema complexity: {e}")
            return "medium"  # Default to medium complexity
    
    def _get_complexity_based_temperature(self, db_type: str, complexity: str) -> float:
        """Adjust temperature based on database type and schema complexity."""
        # Base temperature - very low for database generation
        base_temp = 0.1
        
        # NoSQL databases might benefit from slightly higher temperature
        if db_type.lower() in ["mongodb", "cosmosdb", "dynamodb", "cassandra"]:
            base_temp += 0.05
            
        # Adjust for complexity
        if complexity == "high":
            base_temp += 0.05  # Slightly more creative for complex schemas
        elif complexity == "low":
            base_temp -= 0.02  # Even more deterministic for simple schemas
            
        # Ensure temperature stays in reasonable range
        return max(0.05, min(base_temp, 0.25))
    
    def _create_default_tech_stack(self) -> Dict[str, Any]:
        """Create default tech stack when input is invalid."""
        return {
            "database": {
                "type": "postgresql",
                "version": "14"
            },
            "backend": {
                "language": "Python",
                "framework": "FastAPI"
            }
        }
        
    def _create_default_system_design(self) -> Dict[str, Any]:
        """Create default system design when input is invalid."""
        return {
            "data_entities": [
                {
                    "name": "User",
                    "attributes": [
                        {"name": "id", "type": "uuid", "primary_key": True},
                        {"name": "username", "type": "string", "unique": True},
                        {"name": "email", "type": "string"},
                        {"name": "created_at", "type": "timestamp"}
                    ]
                },
                {
                    "name": "Profile",
                    "attributes": [
                        {"name": "id", "type": "uuid", "primary_key": True},
                        {"name": "user_id", "type": "uuid", "foreign_key": "User.id"},
                        {"name": "name", "type": "string"},
                        {"name": "bio", "type": "text"}
                    ],
                    "relationships": [
                        {"entity": "User", "type": "one-to-one"}
                    ]
                }
            ]
        }
    
    def _get_domain_specific_requirements(self, domain: str) -> str:
        """Get domain-specific database requirements and patterns."""
        domain_requirements = {
            "healthcare": """
**Healthcare Domain Requirements:**
- HIPAA compliance: Include audit tables, data encryption fields, access logging
- Patient data privacy: Separate PII into secure tables with access controls
- Medical data integrity: Add data validation constraints for medical values
- Audit trails: Create audit tables for all patient data modifications
- Data retention: Include soft delete patterns and data archival strategies
- Security: Implement row-level security and column-level encryption
""",
            "financial": """
**Financial Domain Requirements:**
- PCI-DSS compliance: Secure payment data storage with tokenization
- Transaction integrity: ACID compliance, double-entry bookkeeping patterns
- Fraud detection: Include transaction scoring and anomaly detection fields
- Regulatory compliance: Add fields for SOX compliance and financial reporting
- Audit trails: Complete transaction audit logs with immutable records
- Security: Multi-layer encryption, secure key management, access controls
""",
            "iot": """
**IoT Domain Requirements:**
- Time-series optimization: Partition by time, optimize for time-based queries
- Device data patterns: Include device metadata, sensor readings, telemetry
- Real-time ingestion: Optimize for high-frequency data insertion
- Data retention: Implement time-based data archival and compression
- Scalability: Design for horizontal scaling and data partitioning
- Edge data: Consider offline synchronization and data batching patterns
""",
            "ecommerce": """
**E-commerce Domain Requirements:**
- **Product Management**: Optimized product search, category hierarchies, variants, pricing tiers, inventory tracking
- **Order Processing**: ACID-compliant order transactions, payment processing, fraud detection, order state management
- **Customer Experience**: User profiles, wish lists, reviews, recommendations, purchase history analytics
- **Inventory & Fulfillment**: Multi-warehouse inventory, real-time stock tracking, reservation systems, supplier management
- **Security & Compliance**: PCI-DSS compliance for payments, fraud detection algorithms, secure customer data storage
- **Performance & Scale**: Read-heavy optimization, search indexing, caching for product catalogs, traffic spike handling
- **Analytics & Reporting**: Sales analytics, customer behavior tracking, inventory reports, financial reconciliation
- **Business Intelligence**: Revenue tracking, conversion analytics, A/B testing data, marketing attribution
""",
            "analytics": """
**Analytics Domain Requirements:**
- OLAP patterns: Star/snowflake schemas, fact and dimension tables
- Data warehousing: ETL optimization, aggregation tables, data marts
- Reporting: Pre-computed metrics, materialized views, query optimization
- Data lineage: Track data transformations and source attribution
- Performance: Columnstore indexes, partitioning, query acceleration
- Scalability: Design for large data volumes and complex analytical queries
""",
            "realtime": """
**Real-time Domain Requirements:**
- Low latency: Optimize for quick reads/writes, minimal joins
- Caching patterns: Redis integration, session management, temporary data
- Streaming data: Design for continuous data ingestion and processing
- Session management: User state tracking, real-time updates
- Performance: In-memory patterns, connection pooling, query optimization
- Scalability: Horizontal scaling, load distribution, replication strategies
""",
            "generic": """
**General Requirements:**
- Follow database best practices for the selected database type
- Include proper indexing strategies for common query patterns
- Implement basic security measures and access controls
- Design for maintainability and future scalability
- Include standard CRUD operations and common business queries
"""
        }
        
        return domain_requirements.get(domain, domain_requirements["generic"])

    def run(self, work_item: WorkItem, tech_stack: dict) -> dict:
        """
        Runs the agent to generate database-related code or scripts.
        """
        prompt_template = self._create_prompt_template()
        chain = self._create_chain(prompt_template)

        # Get RAG context
        query = f"Task: {work_item.description}\nFile to be created/modified: {work_item.file_path}"
        rag_context = self._get_rag_context(query)

        logger.info(f"Running DatabaseGeneratorAgent for work item: {work_item.description}")
        
        try:
            result = chain.invoke({
                "work_item_description": work_item.description,
                "file_path": work_item.file_path,
                "database_management_system": tech_stack.get("database", "PostgreSQL"),
                "orm": tech_stack.get("orm", "SQLAlchemy"),
                "example_code_snippet": work_item.example or "No example provided.",
                "rag_context": rag_context,
            })
            
            logger.info(f"DatabaseGeneratorAgent completed for work item: {work_item.description}")
            return self._parse_output(result['text'])

        except Exception as e:
            logger.error(f"Error running DatabaseGeneratorAgent: {e}", exc_info=True)
            return {
                "code": f"-- Error generating code: {e}",
                "test_code": f"-- Error generating test code: {e}"
            }
            
    def _parse_output(self, llm_output: str) -> dict:
        # Implementation of _parse_output method
        pass

    def _create_chain(self, prompt_template):
        # Implementation of _create_chain method
        pass

    def _get_rag_context(self, query: str) -> str:
        # Implementation of _get_rag_context method
        pass