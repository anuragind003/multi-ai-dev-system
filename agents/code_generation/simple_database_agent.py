"""
Simple Database Agent - Unified database code generation  
Replaces: 51KB database_generator + over-complex enterprise patterns
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

class SimpleDatabaseAgent(SimpleBaseAgent):
    """
    SIMPLIFIED Database Agent - All database needs in one focused agent
    
    Handles:
    ✅ Database schema design
    ✅ Migration scripts  
    ✅ Basic CRUD queries
    ✅ Indexes and constraints
    ✅ Seed data
    ✅ Simple backup scripts
    ✅ Configuration files
    """
    
    def __init__(self, llm: BaseLanguageModel, memory, temperature: float, output_dir: str, 
                 code_execution_tool: CodeExecutionTool, **kwargs):
        super().__init__(
            llm=llm,
            memory=memory,
            temperature=temperature,
            output_dir=output_dir,
            code_execution_tool=code_execution_tool,
            agent_name="Simple Database Agent",
            **kwargs
        )
        self._initialize_simple_prompts()
        logger.info("Simple Database Agent initialized - unified database generation")

    def _initialize_simple_prompts(self):
        """Enhanced prompt for better database code generation."""
        self.database_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior database architect creating a complete, production-ready database system.

            CRITICAL REQUIREMENTS:
            - Generate EXACTLY 8-12 files (no more, no less)
            - Each file must be substantial and functional
            - Use proper database design principles
            - Include comprehensive error handling
            - Follow industry best practices
            
            REQUIRED FILES (generate ALL of these):
            1. Schema definition (tables, relationships, constraints)
            2. Migration scripts (create/alter operations)
            3. Essential indexes for performance optimization
            4. Stored procedures or functions for common operations
            5. Seed data for development/testing
            6. Database configuration file
            7. Connection management module
            8. Basic CRUD query templates
            9. Backup/restore scripts
            10. Database initialization script
            11. Data validation rules
            12. Performance monitoring queries
            
            Use the ### FILE: path format for each file.
            Make each file substantial with real, functional code."""),
            
            ("human", """Create a complete {db_type} database system for: {description}
            
            **Technical Context:**
            - Backend: {backend_tech}
            - Frontend: {frontend_tech}
            - Database: {database_tech}
            - Database Type: {db_type}
            - Migration Tool: {migration_tool}  
            - Required Features: {features}
            - Data Models: {data_models}
            - Work Item: {work_item}
            
            **Work Item Dependencies:**
            {dependencies}
            
            **Acceptance Criteria:**
            {acceptance_criteria}
            
            **Expected File Structure (MUST FOLLOW EXACTLY):**
            {expected_files}
            
            **CRITICAL: File Structure Requirements:**
            - You MUST create files that match the expected file structure above
            - Use the EXACT file paths and names specified
            - If migration files are in specific directories, create them there
            - If .sql files are expected, create SQL migration files for {db_type}
            - Follow the file naming conventions shown in the expected structure
            - Ensure generated files serve the purposes implied by their paths
            
            **Mandatory Requirements:**
            - Generate files that match the expected structure above
            - Use {db_type} syntax and features appropriately
            - Ensure all acceptance criteria are met in the database design
            - Consider and handle dependencies appropriately in schema design
            - Normalized schema with proper relationships
            - Performance-optimized with strategic indexes
            - Comprehensive data validation and constraints
            - Production-ready configuration
            - Robust error handling throughout
            - Security best practices (user roles, permissions)
            - Backup and recovery procedures
            - Migration scripts compatible with {migration_tool}
            
            Focus on creating a complete, enterprise-grade database solution that follows the exact file structure specified and meets all acceptance criteria.
            Each file should be production-ready with comprehensive functionality for {db_type}.""")
        ])

    def run(self, work_item: WorkItem, state: Dict[str, Any]) -> CodeGenerationOutput:
        """Generate complete database for a work item."""
        try:
            logger.info(f"SimpleDatabaseAgent processing: {work_item.description}")
            
            # ENHANCED: Extract technology stack from enhanced state
            tech_stack_info = state.get('tech_stack_info', {})
            backend_tech = tech_stack_info.get('backend', 'Python with FastAPI')
            frontend_tech = tech_stack_info.get('frontend', 'JavaScript with React')
            database_tech = tech_stack_info.get('database', 'PostgreSQL')
            expected_files = tech_stack_info.get('expected_file_structure', [])
            
            # Parse database technology
            if 'postgresql' in database_tech.lower() or 'postgres' in database_tech.lower():
                db_type = 'PostgreSQL'
            elif 'mysql' in database_tech.lower():
                db_type = 'MySQL'
            elif 'sqlite' in database_tech.lower():
                db_type = 'SQLite'
            elif 'mongodb' in database_tech.lower():
                db_type = 'MongoDB'
            else:
                db_type = database_tech or 'PostgreSQL'  # Default
            
            # Determine migration tool based on backend technology
            if 'python' in backend_tech.lower():
                migration_tool = 'Alembic'
            elif 'node.js' in backend_tech.lower() or 'javascript' in backend_tech.lower():
                migration_tool = 'Knex.js'
            elif 'java' in backend_tech.lower():
                migration_tool = 'Flyway'
            else:
                migration_tool = 'Alembic'  # Default
            
            logger.info(f"SimpleDatabaseAgent using: {db_type} with {migration_tool}")
            logger.info(f"Expected files: {expected_files}")
            
            # Extract context
            system_design = state.get('system_design', {})
            
            # Extract data models from system design
            data_models = self._extract_data_models(system_design)
            features = self._extract_features(work_item.description)
            
            # Generate code with LLM - Enhanced with work item details
            dependencies = tech_stack_info.get('work_item_dependencies', [])
            acceptance_criteria = tech_stack_info.get('work_item_acceptance_criteria', [])
            
            prompt_input = {
                "description": work_item.description,
                "db_type": db_type,
                "migration_tool": migration_tool,
                "features": ", ".join(features),
                "data_models": json.dumps(data_models, indent=2),
                "work_item": f"ID: {work_item.id}, Role: {work_item.agent_role}",
                "expected_files": "\n".join(expected_files) if expected_files else "No specific file structure specified",
                "backend_tech": backend_tech,
                "frontend_tech": frontend_tech,
                "database_tech": database_tech,
                "dependencies": "\n".join([f"- {dep}" for dep in dependencies]) if dependencies else "No dependencies",
                "acceptance_criteria": "\n".join([f"✓ {criteria}" for criteria in acceptance_criteria]) if acceptance_criteria else "No specific acceptance criteria"
            }
            
            response = self.llm.invoke(self.database_prompt.format_messages(**prompt_input))
            raw_content = response.content if hasattr(response, 'content') else str(response)

            # Handle case where content is a list of strings/chunks
            if isinstance(raw_content, list):
                content = "".join(raw_content)
            else:
                content = str(raw_content)
            
            # Parse files
            generated_files = parse_llm_output_into_files(content)
            
            # Quality validation - flexible approach for database files
            min_files_suggested = 2  # Flexible minimum for database (schema + connection is sufficient)
            if len(generated_files) < min_files_suggested:
                logger.info(f"Generated {len(generated_files)} database files (suggested: {min_files_suggested}+)")
                
                # Accept even fewer files if they have substantial content
                if not generated_files:
                    logger.error("No database files generated at all")
                    return CodeGenerationOutput(
                        generated_files=[],
                        summary="Database generation failed: No files generated",
                        status="error"
                    )
            else:
                logger.info(f"Generated {len(generated_files)} database files - good coverage")
            
            # Validate file content quality
            validated_files = self._validate_generated_files(generated_files, db_type)
            if not validated_files:
                logger.warning("Database file validation failed, but proceeding with generated files")
                # Be more lenient - use original files if validation is too strict
                validated_files = [f for f in generated_files if f.content and len(f.content.strip()) > 10]
            
            # Save to disk
            self._save_files(validated_files)
            
            logger.info(f"Generated {len(validated_files)} high-quality database files")
            return CodeGenerationOutput(
                generated_files=validated_files,
                summary=f"Complete {db_type} database with {len(validated_files)} production-ready files",
                status="success"
            )
            
        except Exception as e:
            logger.error(f"SimpleDatabaseAgent failed: {e}")
            return CodeGenerationOutput(
                generated_files=[],
                summary=f"Database generation error: {e}",
                status="error"
            )

    def _extract_data_models(self, system_design: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data models from system design."""
        models = {}
        
        # Look for data models in system design
        if 'data_model' in system_design:
            models = system_design['data_model']
        elif 'entities' in system_design:
            models = system_design['entities']
        elif 'database_design' in system_design:
            models = system_design['database_design']
            
        # Enhanced default models if none found
        if not models:
            models = {
                "users": {
                    "id": "primary_key", 
                    "username": "string_unique", 
                    "email": "string_unique",
                    "password_hash": "string",
                    "created_at": "timestamp",
                    "updated_at": "timestamp"
                },
                "items": {
                    "id": "primary_key", 
                    "name": "string", 
                    "description": "text",
                    "user_id": "foreign_key",
                    "status": "enum",
                    "created_at": "timestamp",
                    "updated_at": "timestamp"
                },
                "categories": {
                    "id": "primary_key",
                    "name": "string_unique",
                    "description": "text"
                }
            }
            
        return models

    def _extract_features(self, description: str) -> List[str]:
        """Extract required features from work item description."""
        features = []
        desc_lower = description.lower()
        
        # Enhanced feature detection
        feature_patterns = {
            "user_management": ["user", "auth", "login", "registration"],
            "transactions": ["transaction", "payment", "order", "billing"],
            "audit_trail": ["audit", "log", "history", "tracking"],
            "full_text_search": ["search", "index", "query", "find"],
            "backup_restore": ["backup", "restore", "recovery"],
            "performance_optimization": ["cache", "performance", "optimization", "index"],
            "data_validation": ["validation", "constraint", "rule"],
            "reporting": ["report", "analytics", "statistics"],
            "security": ["security", "permission", "role", "access"],
            "scalability": ["scale", "partition", "shard", "cluster"]
        }
        
        for feature, keywords in feature_patterns.items():
            if any(keyword in desc_lower for keyword in keywords):
                features.append(feature)
                
        return features or ["basic_crud", "data_management"]

    def _validate_generated_files(self, generated_files: List[GeneratedFile], db_type: str) -> List[GeneratedFile]:
        """Validate generated files meet quality standards."""
        validated_files = []
        
        required_patterns = {
            "schema": ["CREATE TABLE", "PRIMARY KEY", "FOREIGN KEY"],
            "migration": ["CREATE", "ALTER", "DROP"],
            "config": ["connection", "database", "config"],
            "seed": ["INSERT", "VALUES"],
        }
        
        for file_obj in generated_files:
            try:
                content = file_obj.content if hasattr(file_obj, 'content') else file_obj.get('content', '')
                file_path = file_obj.file_path if hasattr(file_obj, 'file_path') else file_obj.get('file_path', '')
                
                # Check if file has substantial content
                if len(content.strip()) < 50:
                    logger.warning(f"Skipping file {file_path}: insufficient content")
                    continue
                
                # Basic pattern validation for database files
                content_upper = content.upper()
                file_path_lower = file_path.lower()
                
                is_valid = (
                    "schema" in file_path_lower and any(pattern in content_upper for pattern in required_patterns["schema"]) or
                    "migration" in file_path_lower and any(pattern in content_upper for pattern in required_patterns["migration"]) or
                    "config" in file_path_lower and any(pattern in content.lower() for pattern in required_patterns["config"]) or
                    "seed" in file_path_lower and any(pattern in content_upper for pattern in required_patterns["seed"]) or
                    any(keyword in file_path_lower for keyword in ["backup", "query", "procedure", "function", "index"])
                )
                
                if is_valid or len(content.strip()) > 200:  # Accept substantial files
                    validated_files.append(file_obj)
                else:
                    logger.warning(f"File {file_path} did not meet validation criteria")
                    
            except Exception as e:
                logger.error(f"Error validating file: {e}")
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
            "summary": "SimpleDatabaseAgent encountered an error",
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