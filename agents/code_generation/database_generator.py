"""
Database Generator Agent - Specialized in generating database schemas, migrations, and queries.
"""

import json
import os
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate

from agents.code_generation.base_code_generator import BaseCodeGeneratorAgent
from agents.code_generation.models import GeneratedFile, CodeGenerationOutput
from tools.code_generation_utils import parse_llm_output_into_files

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
        
        Be thorough and include all necessary files to fully implement the database layer.
        """

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system",
             "You are a database expert specializing in schema design, migrations, and query optimization. "
             "Your task is to generate all necessary database files based on system design and tech stack. "
             "The files should be production-ready, follow best practices, include proper indexes, "
             "and be optimized for performance. Use appropriate parameterization to prevent SQL injection."),
            ("human",
             "Generate a complete set of database artifacts for a {db_type} database using {migration_tool} for migrations. "
             
             "## Project Context\n"
             "Tech Stack: {tech_stack_info}\n\n"
             "System Design: {system_design}\n\n"
             "Data Model: {data_model}\n\n"
             
             "## Requirements\n"
             "1. Schema Definition: Create a complete database schema with tables/collections, columns, "
             "constraints, indexes, and proper relationships.\n"
             "2. Migrations: Generate migration files for schema creation with both up and down migrations.\n"
             "3. Queries: Create optimized query templates for common CRUD operations and important business "
             "operations identified in the system design.\n"
             "4. ORM Models: If appropriate for the tech stack, include ORM model definitions.\n\n"
             
             "## Best Practices\n"
             "{rag_context}\n\n"
             
             "{code_review_feedback}\n\n"
             
             "Follow this multi-file output format EXACTLY:\n{format_instructions}")
        ])
        
        self.prompt_template = self.prompt_template.partial(format_instructions=multi_file_format)

    def _generate_code(self, llm: BaseLanguageModel, invoke_config: Dict, **kwargs) -> Dict[str, Any]:
        """
        Generate all database artifacts in a single step using a comprehensive prompt.
        
        Args:
            llm: Language model to use for generation
            invoke_config: Configuration for LLM invocation
            **kwargs: Additional arguments including tech_stack, system_design, etc.
            
        Returns:
            Dictionary conforming to the CodeGenerationOutput model
        """
        self.log_info("Starting comprehensive database code generation")
        start_time = time.time()
        
        # Extract required inputs with validation
        tech_stack = kwargs.get('tech_stack', {})
        system_design = kwargs.get('system_design', {})
        requirements_analysis = kwargs.get('requirements_analysis', {})
        code_review_feedback = kwargs.get('code_review_feedback')
        
        # Track if this is a revision based on feedback
        is_revision = code_review_feedback is not None
        generation_type = "revision" if is_revision else "initial generation"
        
        try:
            # Validate inputs with defaults
            if not isinstance(tech_stack, dict):
                self.log_warning("Invalid tech stack - using default")
                tech_stack = self._create_default_tech_stack()
                
            if not isinstance(system_design, dict):
                self.log_warning("Invalid system design - using default")
                system_design = self._create_default_system_design()
            
            # Extract database type from tech stack
            db_type = self._extract_database_type(tech_stack)
            self.log_info(f"Using database type: {db_type}")
            
            # Determine migration tool based on tech stack
            migration_tool = self._determine_migration_tool(tech_stack)
            self.log_info(f"Using migration tool: {migration_tool}")
            
            # Extract data model from system design
            data_model = self._extract_data_model(system_design)
            
            # Prune system design to focus on database-relevant aspects
            pruned_design = self._prune_system_design_for_db(system_design)
            
            # Get RAG context for database best practices
            rag_context = self._get_database_rag_context(db_type)
            
            # Format tech stack for prompt
            tech_stack_info = json.dumps(tech_stack, indent=2)
            
            # Prepare code review feedback section if available
            code_review_section = ""
            if is_revision and isinstance(code_review_feedback, dict):
                code_review_section = "## Code Review Feedback to Address\n"
                
                if "critical_issues" in code_review_feedback:
                    code_review_section += "Critical Issues:\n"
                    for issue in code_review_feedback["critical_issues"]:
                        if isinstance(issue, dict):
                            code_review_section += f"- {issue.get('issue', '')}\n"
                            if issue.get('fix'):
                                code_review_section += f"  Suggested fix: {issue['fix']}\n"
                
                if "suggestions" in code_review_feedback:
                    code_review_section += "Suggestions:\n"
                    for suggestion in code_review_feedback["suggestions"]:
                        code_review_section += f"- {suggestion}\n"
            
            # Create the prompt with all necessary inputs
            prompt = self.prompt_template.format(
                db_type=db_type,
                migration_tool=migration_tool,
                tech_stack_info=tech_stack_info,
                system_design=json.dumps(pruned_design, indent=2),
                data_model=json.dumps(data_model, indent=2),
                rag_context=rag_context,
                code_review_feedback=code_review_section
            )
            
            # Set up temperature for the generation
            adjusted_temp = self._get_complexity_based_temperature(
                db_type, 
                self._estimate_schema_complexity(system_design)
            )
            
            # Use binding pattern for temperature
            llm_with_temp = llm.bind(
                temperature=adjusted_temp,
                max_tokens=self.max_tokens
            )
            
            # Add monitoring context
            invoke_config["agent_context"] = f"{self.agent_name}:{db_type}_generation"
            invoke_config["temperature_used"] = adjusted_temp
            invoke_config["is_revision"] = is_revision
            
            # Execute LLM call to generate all database artifacts
            self.log_info(f"Generating {db_type} database artifacts with temperature {adjusted_temp}")
            response = llm_with_temp.invoke(
                prompt,
                config=invoke_config
            )
            
            # Extract content from response
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Record activity in memory
            self.memory.store_agent_activity(
                agent_name=self.agent_name,
                activity_type="database_generation",
                prompt=str(prompt),
                response=content[:1000] + "..." if len(content) > 1000 else content,
                metadata={
                    "db_type": db_type, 
                    "temperature": adjusted_temp,
                    "is_revision": is_revision
                }
            )
            
            # Parse the multi-file output
            generated_files = parse_llm_output_into_files(content)
            
            # Handle case where parsing fails
            if not generated_files:
                self.log_warning("Failed to parse multi-file output, attempting alternate parsing")
                # Try to salvage content as a single schema file
                schema_content = self._extract_code_blocks(content)
                schema_file_path = f"db/schema.{self._get_file_extension_for_db(db_type)}"
                
                if schema_content:
                    generated_files = [
                        GeneratedFile(
                            file_path=schema_file_path,
                            content=schema_content,
                            purpose="Database schema definition",
                            status="generated"
                        )
                    ]
            
            # Set all files to success (validation could be added in the future)
            for file in generated_files:
                file.status = "success"
            
            # Create structured output
            output = CodeGenerationOutput(
                generated_files=generated_files,
                summary=f"Generated {len(generated_files)} database artifacts for {db_type} using {migration_tool}",
                status="success" if generated_files else "error",
                metadata={
                    "db_type": db_type,
                    "migration_tool": migration_tool,
                    "is_revision": is_revision,
                    "generation_type": generation_type,
                    "file_count": len(generated_files),
                    "agent": self.agent_name,
                    "temperature_used": adjusted_temp,
                    "execution_time": time.time() - start_time
                }
            )
            
            # Log success message
            self.log_success(
                f"Database {generation_type} complete: {len(generated_files)} files generated"
            )
            
            # Save files to disk
            self._save_files(generated_files)
            
            # Publish event if message bus is available
            if self.message_bus:
                self.message_bus.publish("database.generated", {
                    "db_type": db_type,
                    "file_count": len(generated_files),
                    "is_revision": is_revision,
                    "status": "success"
                })
            
            # Return as dictionary
            return output.dict()
            
        except Exception as e:
            self.log_error(f"Database generation failed: {str(e)}", exc_info=True)
            # Return error output using the standardized format
            error_output = CodeGenerationOutput(
                generated_files=[],
                summary=f"Error generating database code: {str(e)}",
                status="error",
                metadata={
                    "error": str(e),
                    "db_type": db_type if 'db_type' in locals() else "unknown",
                    "agent": self.agent_name,
                    "timestamp": datetime.now().isoformat()
                }
            )
            return error_output.dict()
    
    # --- Helper methods for database generation ---
    
    def _extract_database_type(self, tech_stack: Dict[str, Any]) -> str:
        """Extract database type from tech stack with sensible defaults."""
        db_type = "postgresql"  # Default to PostgreSQL
        
        try:
            if "database" in tech_stack:
                db_info = tech_stack["database"]
                if isinstance(db_info, dict) and "type" in db_info:
                    db_type = db_info["type"].lower()
                elif isinstance(db_info, list) and len(db_info) > 0:
                    first_db = db_info[0]
                    if isinstance(first_db, dict) and "name" in first_db:
                        db_type = first_db["name"].lower()
                    elif isinstance(first_db, str):
                        db_type = first_db.lower()
        except Exception as e:
            self.log_warning(f"Error extracting database type: {e}")
            
        return db_type
    
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
                f"{db_type} data modeling patterns"
            ]
            
            combined_context = []
            for query in queries:
                try:
                    docs = self.rag_retriever.get_relevant_documents(query)
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
        """Get appropriate file extension for database type."""
        extensions = {
            "postgresql": "sql",
            "mysql": "sql",
            "sqlite": "sql",
            "mariadb": "sql",
            "oracle": "sql",
            "sql server": "sql",
            "mongodb": "js",
            "cosmosdb": "js",
            "dynamodb": "json",
            "cassandra": "cql",
            "neo4j": "cypher"
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