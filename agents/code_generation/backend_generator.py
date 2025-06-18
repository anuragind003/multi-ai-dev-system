"""
Backend Generator Agent - Specialized in generating complete backend codebase
with models, controllers, services, and configurations.
"""

import json
import os
import time
import hashlib
from typing import Dict, Any, List, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

# Ensure correct import paths
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.retrievers import BaseRetriever

# MODIFIED: Fix import paths - use absolute imports instead of relative imports
import os
import sys
# Add project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import proper dependencies including model classes
from agents.code_generation.base_code_generator import BaseCodeGeneratorAgent
import monitoring
from tools.code_execution_tool import CodeExecutionTool
from message_bus import MessageBus
from tools.code_generation_utils import parse_llm_output_into_files
from agents.code_generation.models import GeneratedFile, CodeGenerationOutput

# Setup logger
import logging
logger = logging.getLogger(__name__)

@dataclass
class ComponentMetadata:
    """Metadata for tracking generated components and their dependencies"""
    name: str
    type: str
    file_path: str
    dependencies: List[str] = None
    status: str = "pending"
    execution_time: float = 0.0
    error: Optional[str] = None
    token_usage: Dict[str, int] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.token_usage is None:
            self.token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "file_path": self.file_path,
            "dependencies": self.dependencies,
            "status": self.status,
            "execution_time": self.execution_time,
            "error": self.error,
            "token_usage": self.token_usage
        }

class BackendGeneratorAgent(BaseCodeGeneratorAgent):
    """
    Enhanced Backend Generator Agent with comprehensive code generation capability.
    Generates a complete backend codebase in a single step including models, API endpoints, 
    business logic, and configuration files.
    """
    
    def __init__(self, llm: BaseLanguageModel, memory, 
                 temperature: float,
                 output_dir: str, 
                 code_execution_tool: CodeExecutionTool,
                 rag_retriever: Optional[BaseRetriever] = None,
                 message_bus: Optional[MessageBus] = None):
        """Initialize Backend Generator Agent."""
        
        # Call super().__init__ with all required parameters
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="Backend Generator Agent",
            temperature=temperature,
            output_dir=output_dir,
            code_execution_tool=code_execution_tool,
            rag_retriever=rag_retriever,
            message_bus=message_bus
        )
        
        # Initialize comprehensive prompt template
        self._initialize_prompt_templates()
        
        # Component tracking with dependencies
        self.component_registry = {}
        
        # Performance metrics
        self.generated_files_count = 0
        self.successful_files_count = 0
        self.token_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
        
        # Initialize successful compilations tracking
        self.successful_compilations = set()
        
        # Subscribe to relevant events if message bus available
        self._setup_message_subscriptions()
        
        # Initialize the component state store
        self.component_state = {
            "models": {},
            "api_endpoints": {},
            "business_logic": {},
            "generated_files": [],
            "execution_timeline": []
        }

        # Maximum tokens and context limits for backend generation
        self.max_tokens = 8192
        self.max_context_chars = 2000
        self.max_rag_docs = 3

    def _initialize_prompt_templates(self):
        """Initialize a comprehensive prompt template for backend code generation."""
        
        multi_file_format = """
        CRITICAL OUTPUT FORMAT:
        You MUST provide your response as a single block of text. For each file you generate, 
        you MUST use the following format:

        ### FILE: path/to/your/file.ext
        ```filetype
        # The full content of the file goes here.
        # Make sure to include all necessary code and configuration.
        ```

        Continue this pattern for all files you need to generate. Your output should include:

        1. DATA MODELS - Create complete model files with fields, relationships, and validation
        2. API ENDPOINTS - Create controllers/routes with proper request handling and responses
        3. BUSINESS LOGIC - Create services implementing the core business functionality
        4. CONFIGURATION - Create necessary configuration files for the application

        Ensure each file follows best practices for the specified tech stack and implements
        proper error handling, validation, and security measures.
        """

        self.backend_generator_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""
                You are a Senior Backend Developer specializing in creating comprehensive, production-ready backend code.
                
                Your task is to generate a complete backend codebase with models, API endpoints, business logic, 
                and configurations. Follow the provided tech stack and system design exactly.
                
                Generate clean, well-structured code that follows language and framework best practices,
                with proper error handling, validation, security, and documentation.
            """),
            HumanMessage(content="""
                ## Project Requirements and Design
                
                REQUIREMENTS ANALYSIS:
                {requirements_summary}
                
                TECH STACK:
                {tech_stack_summary}
                
                SYSTEM DESIGN:
                {system_design_summary}
                
                ## Technical Details
                
                Full Tech Stack:
                {tech_stack_details}
                
                Full System Design:
                {system_design_details}
                
                Database Schema:
                {database_schema}
                
                ## Backend Components to Generate
                
                MODELS:
                {models_to_generate}
                
                API ENDPOINTS:
                {endpoints_to_generate}
                
                BUSINESS LOGIC:
                {business_logic_to_generate}
                
                CONFIGURATIONS:
                {configurations_to_generate}
                
                ## Best Practices and Guidance
                
                {tech_best_practices}
                
                {rag_context}
                
                {code_review_feedback}
                
                Follow this multi-file output format EXACTLY:
                {format_instructions}
            """)
        ])
        
        self.backend_generator_prompt = self.backend_generator_prompt.partial(format_instructions=multi_file_format)

    def _generate_code(self, llm: BaseLanguageModel, invoke_config: Dict, **kwargs) -> Dict:
        """
        Generate complete backend code including models, APIs, business logic, and configurations.
        
        Args:
            llm: Language model configured with appropriate temperature
            invoke_config: Configuration for LLM invocation
            **kwargs: Additional arguments including requirements_analysis, tech_stack, system_design, etc.
            
        Returns:
            Dictionary containing generated backend components conforming to CodeGenerationOutput
        """
        with monitoring.agent_trace_span(self.agent_name, "backend_generation"):
            self.log_info("Starting comprehensive backend generation process")
            start_time = time.time()
            
            # Extract and validate inputs
            requirements_analysis = kwargs.get('requirements_analysis', {})
            tech_stack = kwargs.get('tech_stack', {})
            system_design = kwargs.get('system_design', {})
            code_review_feedback = kwargs.get('code_review_feedback')
            database_schema = kwargs.get('database_schema', {})
            
            # Validate inputs
            if not isinstance(requirements_analysis, dict):
                self.log_warning("Invalid requirements analysis - using minimal requirements")
                requirements_analysis = {"requirements": ["Basic backend application required"]}
                
            if not isinstance(tech_stack, dict):
                self.log_warning("Invalid tech stack input - using default technology stack")
                tech_stack = self._create_default_tech_stack()
                
            if not isinstance(system_design, dict):
                self.log_warning("Invalid system design input - using minimal design")
                system_design = self._create_default_system_design()
            
            if code_review_feedback is not None and not isinstance(code_review_feedback, dict):
                self.log_warning("Invalid code review feedback format - ignoring feedback")
                code_review_feedback = None
            
            # Track if this is a revision based on feedback
            is_revision = code_review_feedback is not None
            generation_type = "revision" if is_revision else "initial generation"
            
            if is_revision:
                self.log_info(f"Starting backend code revision based on code review feedback")
            
            # Create output directory structure
            self._ensure_output_directories(tech_stack)
            
            try:
                # Extract models to generate
                models_to_generate = self._extract_model_names(system_design)
                models_to_generate_formatted = self._format_models_for_prompt(models_to_generate, system_design)
                
                # Extract API endpoints to generate
                endpoints_to_generate = self._extract_api_endpoints(system_design)
                endpoints_to_generate_formatted = self._format_endpoints_for_prompt(endpoints_to_generate)
                
                # Extract business logic components to generate
                business_logic_to_generate = self._extract_business_logic_components(system_design)
                business_logic_to_generate_formatted = self._format_business_logic_for_prompt(business_logic_to_generate)
                
                # Determine config files to generate
                config_files_to_generate = self._determine_config_files(tech_stack)
                config_files_to_generate_formatted = self._format_config_files_for_prompt(config_files_to_generate)
                
                # Create concise summaries for the prompt
                requirements_summary = self._create_requirements_summary(requirements_analysis)
                tech_stack_summary = self._create_tech_stack_summary(tech_stack)
                system_design_summary = self._create_system_design_summary(system_design)
                
                # Extract tech best practices
                backend_language = tech_stack.get("backend", {}).get("language", "").lower()
                backend_framework = tech_stack.get("backend", {}).get("framework", "").lower()
                tech_best_practices = self._get_tech_best_practices(backend_language, backend_framework)
                
                # Get RAG context for backend generation
                rag_context = self._get_backend_rag_context(backend_language, backend_framework)
                
                # Format code review feedback if available
                code_review_section = ""
                if is_revision and isinstance(code_review_feedback, dict):
                    code_review_section = "## Code Review Feedback to Address\n"
                    
                    if "critical_issues" in code_review_feedback:
                        code_review_section += "Critical Issues:\n"
                        for issue in code_review_feedback.get("critical_issues", []):
                            if isinstance(issue, dict) and "issue" in issue:
                                code_review_section += f"- {issue['issue']}\n"
                                if "fix" in issue:
                                    code_review_section += f"  Suggested fix: {issue['fix']}\n"
                    
                    if "suggestions" in code_review_feedback:
                        code_review_section += "\nSuggestions:\n"
                        for suggestion in code_review_feedback.get("suggestions", []):
                            code_review_section += f"- {suggestion}\n"
                
                # Store execution start in timeline
                self.component_state["execution_timeline"].append({
                    "phase": "backend_generation_start",
                    "start_time": datetime.now().isoformat(),
                    "generation_type": generation_type,
                    "models_count": len(models_to_generate),
                    "endpoints_count": len(endpoints_to_generate),
                    "business_logic_count": len(business_logic_to_generate),
                    "config_count": len(config_files_to_generate)
                })
                
                # Prepare prompt variables
                prompt_vars = {
                    "requirements_summary": requirements_summary,
                    "tech_stack_summary": tech_stack_summary,
                    "system_design_summary": system_design_summary,
                    "tech_stack_details": json.dumps(self._prune_tech_stack(tech_stack), indent=2),
                    "system_design_details": json.dumps(self._prune_system_design(system_design), indent=2),
                    "database_schema": json.dumps(database_schema, indent=2) if database_schema else "No database schema provided",
                    "models_to_generate": models_to_generate_formatted,
                    "endpoints_to_generate": endpoints_to_generate_formatted,
                    "business_logic_to_generate": business_logic_to_generate_formatted,
                    "configurations_to_generate": config_files_to_generate_formatted,
                    "tech_best_practices": tech_best_practices,
                    "rag_context": rag_context,
                    "code_review_feedback": code_review_section
                }
                
                # Prepare LLM with appropriate temperature
                adjusted_temp = self._get_adjusted_temperature(is_revision)
                binding_args = {
                    "temperature": adjusted_temp,
                    "max_tokens": self.max_tokens
                }
                llm_with_temp = llm.bind(**binding_args)
                
                # Update invoke config with context
                invoke_config.update({
                    "agent_context": f"{self.agent_name}:{generation_type}",
                    "temperature_used": adjusted_temp,
                    "model_name": getattr(llm, "model_name", "unknown"),
                    "is_revision": is_revision
                })
                
                # Generate all backend code with a single LLM call
                self.log_info(f"Generating backend code with temperature {adjusted_temp}")
                response = llm_with_temp.invoke(
                    self.backend_generator_prompt.format_messages(**prompt_vars),
                    config=invoke_config
                )
                
                # Extract content from response
                content = response.content if hasattr(response, 'content') else str(response)
                
                # Track token usage if available
                if hasattr(response, 'response_metadata') and 'token_usage' in response.response_metadata:
                    token_usage = response.response_metadata['token_usage']
                    self._update_token_usage(token_usage)
                
                # Store the activity with temperature metadata
                self.memory.store_agent_activity(
                    agent_name=self.agent_name,
                    activity_type="backend_generation",
                    prompt=str(self.backend_generator_prompt),  # Just template reference to save tokens
                    response=content[:1000] + "..." if len(content) > 1000 else content,
                    metadata={
                        "model_name": getattr(llm, "model_name", "unknown"), 
                        "temperature": adjusted_temp,
                        "is_revision": is_revision
                    }
                )
                
                # Parse the multi-file output
                generated_files = parse_llm_output_into_files(content)
                
                # Handle case where parsing fails
                if not generated_files:
                    self.log_warning("Failed to parse multi-file output, attempting to salvage content")
                    # Generate minimal files as fallback
                    generated_files = self._create_default_backend_files(
                        tech_stack_summary, backend_language, backend_framework
                    )
                
                # Track successful files
                successful_files = 0
                
                # Process and save each generated file
                for file in generated_files:
                    try:
                        # Determine full file path
                        file_path = file.file_path
                        full_path = os.path.join(self.output_dir, file_path)
                        
                        # Create directories if they don't exist
                        os.makedirs(os.path.dirname(full_path), exist_ok=True)
                        
                        # Write file to disk
                        with open(full_path, 'w', encoding='utf-8') as f:
                            f.write(file.content)
                        
                        # Mark as success
                        file.status = "success"
                        successful_files += 1
                        self.successful_files_count += 1
                        
                    except Exception as e:
                        self.log_error(f"Error saving file {file.file_path}: {str(e)}")
                        file.status = "error"
                        file.error_message = str(e)
                
                self.generated_files_count = len(generated_files)
                
                # Update timeline with completion
                self.component_state["execution_timeline"].append({
                    "phase": "backend_generation_complete",
                    "end_time": datetime.now().isoformat(),
                    "duration": time.time() - start_time,
                    "total_files": len(generated_files),
                    "successful_files": successful_files
                })
                
                # Create categorized file tracking
                model_files = [f for f in generated_files if "model" in f.file_path.lower()]
                api_files = [f for f in generated_files if any(x in f.file_path.lower() for x in ["controller", "route", "api"])]
                business_logic_files = [f for f in generated_files if any(x in f.file_path.lower() for x in ["service", "logic", "manager"])]
                config_files = [f for f in generated_files if any(x in f.file_path.lower() for x in ["config", "settings", "env"])]
                other_files = [f for f in generated_files if f not in model_files + api_files + business_logic_files + config_files]
                
                # Create statistics for metadata
                generation_stats = {
                    "total_time": time.time() - start_time,
                    "generated_files_count": self.generated_files_count,
                    "successful_files_count": self.successful_files_count,
                    "success_rate": self.successful_files_count / self.generated_files_count if self.generated_files_count > 0 else 0,
                    "token_usage": self.token_usage,
                    "model_files_count": len(model_files),
                    "api_files_count": len(api_files),
                    "business_logic_files_count": len(business_logic_files),
                    "config_files_count": len(config_files),
                    "other_files_count": len(other_files),
                    "is_revision": is_revision
                }
                
                # Create final output using CodeGenerationOutput Pydantic model
                output = CodeGenerationOutput(
                    generated_files=generated_files,
                    summary=f"Generated {len(generated_files)} backend files with {successful_files} successful files",
                    status="success" if successful_files > 0 else "error",
                    metadata={
                        "generation_stats": generation_stats,
                        "models_count": len(models_to_generate),
                        "endpoints_count": len(endpoints_to_generate),
                        "business_logic_count": len(business_logic_to_generate),
                        "config_count": len(config_files_to_generate),
                        "is_revision": is_revision,
                        "agent": self.agent_name,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                # Create categorized output for detailed insights
                detailed_output = {
                    "models": {model: {"files": [f.dict() for f in model_files if model.lower() in f.file_path.lower()]} for model in models_to_generate},
                    "api_endpoints": {endpoint: {"files": [f.dict() for f in api_files if endpoint.lower() in f.file_path.lower()]} for endpoint in endpoints_to_generate},
                    "business_logic": {component: {"files": [f.dict() for f in business_logic_files if component.lower() in f.file_path.lower()]} for component in business_logic_to_generate},
                    "configurations": {config: {"files": [f.dict() for f in config_files if config.lower() in f.file_path.lower()]} for config in config_files_to_generate},
                    "backend_generation_output": output.dict()
                }
                
                self.log_success(f"Backend {generation_type} completed: {successful_files}/{len(generated_files)} successful files")
                
                # Return combined output
                return detailed_output
                
            except Exception as e:
                self.log_error(f"Backend {generation_type} failed: {str(e)}")
                import traceback
                
                # Create error output using CodeGenerationOutput for consistent handling
                error_output = CodeGenerationOutput(
                    generated_files=[],
                    summary=f"Backend generation failed: {str(e)}",
                    status="error",
                    metadata={
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                        "is_revision": is_revision,
                        "agent": self.agent_name,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                return {
                    "models": {},
                    "api_endpoints": {},
                    "business_logic": {},
                    "configurations": {},
                    "backend_generation_output": error_output.dict(),
                    "error": str(e)
                }
    
    def _create_default_backend_files(self, tech_stack_summary: str, language: str, framework: str) -> List[GeneratedFile]:
        """
        Create default backend files when generation fails.
        
        Args:
            tech_stack_summary: Summary of the tech stack
            language: Programming language
            framework: Backend framework
            
        Returns:
            List of GeneratedFile objects with default content
        """
        default_files = []
        
        # Create README file
        readme_content = f"""# Backend Application

## Tech Stack
{tech_stack_summary}

## Setup Instructions
1. Clone this repository
2. Install dependencies
3. Configure environment variables
4. Run the application

Generated by Backend Generator Agent (default template)
"""

        # Create basic model file
        model_extension = "py" if language.lower() == "python" else "js" if language.lower() in ["javascript", "node.js"] else "java"
        model_content = self._get_default_model_content(language, framework)
        
        # Create basic controller file
        controller_extension = model_extension
        controller_content = self._get_default_controller_content(language, framework)
        
        # Create basic service file
        service_extension = model_extension
        service_content = self._get_default_service_content(language, framework)
        
        # Create configuration file
        config_extension = "py" if language.lower() == "python" else "js" if language.lower() in ["javascript", "node.js"] else "properties"
        config_content = self._get_default_config_content(language, framework)
        
        # Add all default files
        default_files.extend([
            GeneratedFile(
                file_path="README.md",
                content=readme_content,
                purpose="Project documentation",
                status="generated"
            ),
            GeneratedFile(
                file_path=f"models/user.{model_extension}",
                content=model_content,
                purpose="Default user model",
                status="generated"
            ),
            GeneratedFile(
                file_path=f"controllers/user_controller.{controller_extension}",
                content=controller_content,
                purpose="Default user controller",
                status="generated"
            ),
            GeneratedFile(
                file_path=f"services/user_service.{service_extension}",
                content=service_content,
                purpose="Default user service",
                status="generated"
            ),
            GeneratedFile(
                file_path=f"config/config.{config_extension}",
                content=config_content,
                purpose="Default application configuration",
                status="generated"
            )
        ])
        
        return default_files
    
    def _get_default_model_content(self, language: str, framework: str) -> str:
        """Get default model content based on language and framework."""
        if language.lower() == "python":
            if framework.lower() == "django":
                return """from django.db import models

class User(models.Model):
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.username
"""
            else:  # Default to Flask/SQLAlchemy
                return """from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=func.now())
"""
        elif language.lower() in ["javascript", "typescript", "node.js"]:
            return """const mongoose = require('mongoose');

const userSchema = new mongoose.Schema({
  username: {
    type: String,
    required: true,
    unique: true
  },
  email: {
    type: String,
    required: true,
    unique: true
  },
  createdAt: {
    type: Date,
    default: Date.now
  }
});

module.exports = mongoose.model('User', userSchema);
"""
        else:  # Default to Java
            return """package com.example.models;

import java.time.LocalDateTime;
import javax.persistence.*;

@Entity
@Table(name = "users")
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(unique = true)
    private String username;
    
    @Column(unique = true)
    private String email;
    
    private LocalDateTime createdAt;
    
    // Getters and setters
    public Long getId() {
        return id;
    }
    
    public void setId(Long id) {
        this.id = id;
    }
    
    public String getUsername() {
        return username;
    }
    
    public void setUsername(String username) {
        this.username = username;
    }
    
    public String getEmail() {
        return email;
    }
    
    public void setEmail(String email) {
        this.email = email;
    }
    
    public LocalDateTime getCreatedAt() {
        return createdAt;
    }
    
    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }
}
"""
    
    def _get_default_controller_content(self, language: str, framework: str) -> str:
        """Get default controller content based on language and framework."""
        if language.lower() == "python":
            if framework.lower() == "django":
                return """from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404
from .models import User

class UserView(View):
    def get(self, request, user_id=None):
        if user_id:
            user = get_object_or_404(User, id=user_id)
            return JsonResponse({
                'id': user.id,
                'username': user.username,
                'email': user.email
            })
        else:
            users = User.objects.all()
            return JsonResponse({
                'users': [{'id': user.id, 'username': user.username} for user in users]
            })
"""
            else:  # Default to Flask
                return """from flask import Blueprint, jsonify, request
from models.user import User
from database import db_session

user_bp = Blueprint('user', __name__)

@user_bp.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify({
        'users': [{'id': user.id, 'username': user.username} for user in users]
    })

@user_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email
    })
"""
        elif language.lower() in ["javascript", "typescript", "node.js"]:
            return """const express = require('express');
const router = express.Router();
const User = require('../models/user');

// Get all users
router.get('/users', async (req, res) => {
  try {
    const users = await User.find({}, 'username email');
    res.json({ users });
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});

// Get one user
router.get('/users/:id', async (req, res) => {
  try {
    const user = await User.findById(req.params.id);
    if (!user) {
      return res.status(404).json({ message: 'User not found' });
    }
    res.json(user);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});

module.exports = router;
"""
        else:  # Default to Java Spring
            return """package com.example.controllers;

import com.example.models.User;
import com.example.services.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/users")
public class UserController {
    
    @Autowired
    private UserService userService;
    
    @GetMapping
    public ResponseEntity<List<User>> getAllUsers() {
        return ResponseEntity.ok(userService.getAllUsers());
    }
    
    @GetMapping("/{id}")
    public ResponseEntity<User> getUserById(@PathVariable Long id) {
        return userService.getUserById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }
}
"""
    
    def _get_default_service_content(self, language: str, framework: str) -> str:
        """Get default service content based on language and framework."""
        if language.lower() == "python":
            if framework.lower() == "django":
                return """from .models import User

class UserService:
    @staticmethod
    def get_all_users():
        return User.objects.all()
    
    @staticmethod
    def get_user_by_id(user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
    
    @staticmethod
    def create_user(username, email):
        user = User(username=username, email=email)
        user.save()
        return user
"""
            else:  # Default to Flask
                return """from models.user import User
from database import db_session

class UserService:
    @staticmethod
    def get_all_users():
        return User.query.all()
    
    @staticmethod
    def get_user_by_id(user_id):
        return User.query.get(user_id)
    
    @staticmethod
    def create_user(username, email):
        user = User(username=username, email=email)
        db_session.add(user)
        db_session.commit()
        return user
"""
        elif language.lower() in ["javascript", "typescript", "node.js"]:
            return """const User = require('../models/user');

class UserService {
  async getAllUsers() {
    return await User.find({});
  }
  
  async getUserById(userId) {
    return await User.findById(userId);
  }
  
  async createUser(userData) {
    const user = new User(userData);
    return await user.save();
  }
}

module.exports = new UserService();
"""
        else:  # Default to Java Spring
            return """package com.example.services;

import com.example.models.User;
import com.example.repositories.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class UserService {
    
    @Autowired
    private UserRepository userRepository;
    
    public List<User> getAllUsers() {
        return userRepository.findAll();
    }
    
    public Optional<User> getUserById(Long id) {
        return userRepository.findById(id);
    }
    
    public User createUser(User user) {
        return userRepository.save(user);
    }
}
"""
    
    def _get_default_config_content(self, language: str, framework: str) -> str:
        """Get default configuration content based on language and framework."""
        if language.lower() == "python":
            if framework.lower() == "django":
                return """# Django settings
DEBUG = True
SECRET_KEY = 'development-secret-key-change-in-production'
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Database settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    }
}

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'app'
]

# Rest Framework settings
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ]
}
"""
            else:  # Default to Flask
                return """import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'development-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False

class DevelopmentConfig(Config):
    DEBUG = True
    
class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'
    
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
"""
        elif language.lower() in ["javascript", "typescript", "node.js"]:
            return """// Configuration settings
module.exports = {
  development: {
    port: process.env.PORT || 3000,
    mongoURI: process.env.MONGO_URI || 'mongodb://localhost:27017/dev_db',
    jwtSecret: process.env.JWT_SECRET || 'dev-secret',
    nodeEnv: 'development'
  },
  test: {
    port: process.env.PORT || 3000,
    mongoURI: process.env.MONGO_URI || 'mongodb://localhost:27017/test_db',
    jwtSecret: process.env.JWT_SECRET || 'test-secret',
    nodeEnv: 'test'
  },
  production: {
    port: process.env.PORT || 3000,
    mongoURI: process.env.MONGO_URI,
    jwtSecret: process.env.JWT_SECRET,
    nodeEnv: 'production'
  }
};
"""
        else:  # Default to Java
            return """# Application Properties

# Server settings
server.port=8080
server.servlet.context-path=/api

# Database settings
spring.datasource.url=jdbc:h2:mem:testdb
spring.datasource.driverClassName=org.h2.Driver
spring.datasource.username=sa
spring.datasource.password=password
spring.jpa.database-platform=org.hibernate.dialect.H2Dialect
spring.jpa.hibernate.ddl-auto=update

# Logging settings
logging.level.root=INFO
logging.level.com.example=DEBUG

# Security settings
security.jwt.token.secret-key=secret-key-for-development
security.jwt.token.expire-length=3600000
"""
    
    def _ensure_output_directories(self, tech_stack: Dict[str, Any]):
        """Ensure all necessary output directories exist"""
        backend_language = tech_stack.get("backend", {}).get("language", "").lower()
        backend_framework = tech_stack.get("backend", {}).get("framework", "").lower()
        
        # Create common directories based on tech stack
        directories = [
            "models",
            "controllers",
            "services",
            "config"
        ]
        
        # Create framework-specific directories
        if backend_framework == "django":
            directories.extend(["apps", "migrations", "templates"])
        elif backend_framework == "flask":
            directories.extend(["blueprints", "templates", "static"])
        elif backend_framework == "express":
            directories.extend(["routes", "middleware", "public"])
        
        # Create all directories
        for directory in directories:
            dir_path = os.path.join(self.output_dir, directory)
            os.makedirs(dir_path, exist_ok=True)
        
        self.log_info(f"Created output directory structure with {len(directories)} directories")
    
    def _extract_model_names(self, system_design: Dict[str, Any]) -> List[str]:
        """Extract model names from system design specifications."""
        models = []
        
        try:
            # Check for models in database schema
            if "database_schema" in system_design and isinstance(system_design["database_schema"], dict):
                db_schema = system_design["database_schema"]
                if "tables" in db_schema and isinstance(db_schema["tables"], list):
                    for table in db_schema["tables"]:
                        if isinstance(table, dict) and "name" in table:
                            models.append(table["name"])
        
            # Also check direct model definitions if available
            if "models" in system_design and isinstance(system_design["models"], list):
                for model in system_design["models"]:
                    if isinstance(model, dict) and "name" in model:
                        model_name = model["name"]
                        if model_name not in models:  # Avoid duplicates
                            models.append(model_name)
            
            # Check for entities in domain model
            if "domain_model" in system_design and isinstance(system_design["domain_model"], dict):
                if "entities" in system_design["domain_model"] and isinstance(system_design["domain_model"]["entities"], list):
                    for entity in system_design["domain_model"]["entities"]:
                        if isinstance(entity, dict) and "name" in entity:
                            entity_name = entity["name"]
                            if entity_name not in models:  # Avoid duplicates
                                models.append(entity_name)
            
            # Ensure we always have at least basic models
            if not models:
                return ["User", "Product"]
                
            return models
        
        except Exception as e:
            self.log_warning(f"Error extracting model names: {e}")
            # Return a minimal set of generic models as fallback
            return ["User", "Product", "Order"]
    
    def _extract_api_endpoints(self, system_design: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Extract API endpoint specifications from system design."""
        endpoints = {}
        
        try:
            if "api_endpoints" in system_design:
                api_endpoints = system_design["api_endpoints"]
                if isinstance(api_endpoints, list):
                    for endpoint in api_endpoints:
                        if isinstance(endpoint, dict) and "name" in endpoint:
                            endpoints[endpoint["name"]] = endpoint
                elif isinstance(api_endpoints, dict):
                    for name, endpoint in api_endpoints.items():
                        if isinstance(endpoint, dict):
                            endpoint["name"] = name
                            endpoints[name] = endpoint
            
            # If no endpoints found, try to infer from models
            if not endpoints and "models" in system_design:
                models = system_design["models"]
                if isinstance(models, list):
                    for model in models:
                        if isinstance(model, dict) and "name" in model:
                            model_name = model["name"]
                            # Create standard CRUD endpoints for each model
                            endpoints[f"get{model_name}List"] = {
                                "name": f"get{model_name}List",
                                "path": f"/api/{model_name.lower()}s",
                                "method": "GET",
                                "description": f"Get list of {model_name}s"
                            }
                            endpoints[f"get{model_name}"] = {
                                "name": f"get{model_name}",
                                "path": f"/api/{model_name.lower()}s/{{id}}",
                                "method": "GET",
                                "description": f"Get {model_name} by ID"
                            }
                            endpoints[f"create{model_name}"] = {
                                "name": f"create{model_name}",
                                "path": f"/api/{model_name.lower()}s",
                                "method": "POST",
                                "description": f"Create new {model_name}"
                            }
                            endpoints[f"update{model_name}"] = {
                                "name": f"update{model_name}",
                                "path": f"/api/{model_name.lower()}s/{{id}}",
                                "method": "PUT",
                                "description": f"Update {model_name}"
                            }
                            endpoints[f"delete{model_name}"] = {
                                "name": f"delete{model_name}",
                                "path": f"/api/{model_name.lower()}s/{{id}}",
                                "method": "DELETE",
                                "description": f"Delete {model_name}"
                            }
            
            return endpoints
            
        except Exception as e:
            self.log_warning(f"Error extracting API endpoints: {e}")
            return {}
    
    def _extract_business_logic_components(self, system_design: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Extract business logic components from system design."""
        components = {}
        
        try:
            # Check direct business logic definitions
            if "business_logic" in system_design:
                business_logic = system_design["business_logic"]
                if isinstance(business_logic, list):
                    for component in business_logic:
                        if isinstance(component, dict) and "name" in component:
                            components[component["name"]] = component
                elif isinstance(business_logic, dict):
                    for name, component in business_logic.items():
                        if isinstance(component, dict):
                            component["name"] = name
                            components[name] = component
            
            # If no components found, try to infer from other parts
            if not components:
                # Create service components for each model
                models = self._extract_model_names(system_design)
                for model in models:
                    service_name = f"{model}Service"
                    components[service_name] = {
                        "name": service_name,
                        "description": f"Business logic for {model}",
                        "rules": [f"Validate {model} data"],
                        "dependencies": [model]
                    }
                    
                # Create utility components if there are business rules
                if "business_rules" in system_design:
                    components["BusinessRuleEngine"] = {
                        "name": "BusinessRuleEngine",
                        "description": "Core business rule processing engine",
                        "rules": system_design["business_rules"],
                        "dependencies": []
                    }
                    
            return components
            
        except Exception as e:
            self.log_warning(f"Error extracting business logic components: {e}")
            return {}
    
    def _determine_config_files(self, tech_stack: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Determine which configuration files to generate based on tech stack."""
        configs = {}
        
        try:
            backend_language = tech_stack.get("backend", {}).get("language", "").lower()
            backend_framework = tech_stack.get("backend", {}).get("framework", "").lower()
            
            # Add main configuration file
            if backend_language == "python":
                if backend_framework == "django":
                    configs["settings"] = {
                        "name": "settings",
                        "path": "config/settings.py",
                        "description": "Django settings configuration"
                    }
                elif backend_framework == "flask":
                    configs["config"] = {
                        "name": "config",
                        "path": "config/config.py",
                        "description": "Flask application configuration"
                    }
            elif backend_language in ["javascript", "typescript", "node.js"]:
                configs["config"] = {
                    "name": "config",
                    "path": "config/config.js",
                    "description": "Application configuration"
                }
                configs["package"] = {
                    "name": "package",
                    "path": "package.json",
                    "description": "NPM package configuration"
                }
            elif backend_language == "java":
                if backend_framework == "spring":
                    configs["application"] = {
                        "name": "application",
                        "path": "src/main/resources/application.properties",
                        "description": "Spring application properties"
                    }
                    configs["pom"] = {
                        "name": "pom",
                        "path": "pom.xml",
                        "description": "Maven project configuration"
                    }
            
            # Add environment configuration
            configs["env"] = {
                "name": "env",
                "path": ".env.example",
                "description": "Environment variable example file"
            }
            
            # Add Docker configuration if applicable
            if tech_stack.get("deployment", {}).get("containerization", "") == "Docker":
                configs["dockerfile"] = {
                    "name": "dockerfile",
                    "path": "Dockerfile",
                    "description": "Docker container configuration"
                }
                configs["dockercompose"] = {
                    "name": "dockercompose",
                    "path": "docker-compose.yml",
                    "description": "Docker Compose service configuration"
                }
            
            return configs
            
        except Exception as e:
            self.log_warning(f"Error determining configuration files: {e}")
            return {
                "config": {
                    "name": "config",
                    "path": "config/config.js",
                    "description": "Default application configuration"
                },
                "env": {
                    "name": "env",
                    "path": ".env.example",
                    "description": "Environment variable example file"
                }
            }
    
    def _format_models_for_prompt(self, models: List[str], system_design: Dict[str, Any]) -> str:
        """Format model names and details for the prompt."""
        result = []
        
        # Find model details in system design
        for model_name in models:
            # Try to find details for this model
            model_details = {}
            
            # Check in data model
            if "data_model" in system_design and "entities" in system_design["data_model"]:
                for entity in system_design["data_model"]["entities"]:
                    if isinstance(entity, dict) and entity.get("name") == model_name:
                        model_details = entity
                        break
            
            # Check in database schema
            if not model_details and "database_schema" in system_design and "tables" in system_design["database_schema"]:
                for table in system_design["database_schema"]["tables"]:
                    if isinstance(table, dict) and table.get("name") == model_name:
                        model_details = table
                        break
            
            # Add model name and any details found
            if model_details:
                description = model_details.get("description", f"Model for {model_name}")
                fields_info = ""
                
                # Add fields if available
                if "fields" in model_details and isinstance(model_details["fields"], list):
                    fields_info = "\n  Fields: " + ", ".join([
                        f"{f['name']} ({f['type']})" for f in model_details["fields"][:5] 
                        if isinstance(f, dict) and "name" in f and "type" in f
                    ])
                
                # Add relationships if available
                relationships_info = ""
                if "relationships" in model_details and isinstance(model_details["relationships"], list):
                    relationships_info = "\n  Relationships: " + ", ".join([
                        f"{r['type']} with {r['related_entity']}" for r in model_details["relationships"][:3]
                        if isinstance(r, dict) and "type" in r and "related_entity" in r
                    ])
                
                result.append(f"- {model_name}: {description}{fields_info}{relationships_info}")
            else:
                # Just add the name if no details found
                result.append(f"- {model_name}")
        
        return "\n".join(result)
    
    def _format_endpoints_for_prompt(self, endpoints: Dict[str, Dict[str, Any]]) -> str:
        """Format API endpoint details for the prompt."""
        result = []
        
        for name, endpoint in endpoints.items():
            path = endpoint.get("path", f"/api/{name}")
            method = endpoint.get("method", "GET")
            description = endpoint.get("description", f"API endpoint for {name}")
            
            result.append(f"- {name}: {method} {path} - {description}")
        
        return "\n".join(result)
    
    def _format_business_logic_for_prompt(self, components: Dict[str, Dict[str, Any]]) -> str:
        """Format business logic components for the prompt."""
        result = []
        
        for name, component in components.items():
            description = component.get("description", f"Business logic for {name}")
            
            # Add rules if available
            rules_info = ""
            if "rules" in component and isinstance(component["rules"], list):
                rules = component["rules"][:3]  # Limit to 3 rules for prompt
                if rules:
                    rules_info = "\n  Rules: " + ", ".join(rules)
            
            # Add dependencies if available
            deps_info = ""
            if "dependencies" in component and isinstance(component["dependencies"], list):
                dependencies = component["dependencies"]
                if dependencies:
                    deps_info = f"\n  Dependencies: {', '.join(dependencies)}"
            
            result.append(f"- {name}: {description}{rules_info}{deps_info}")
        
        return "\n".join(result)
    
    def _format_config_files_for_prompt(self, configs: Dict[str, Dict[str, Any]]) -> str:
        """Format configuration files for the prompt."""
        result = []
        
        for name, config in configs.items():
            path = config.get("path", f"config/{name}")
            description = config.get("description", f"Configuration for {name}")
            
            result.append(f"- {name}: {path} - {description}")
        
        return "\n".join(result)
    
    def _create_requirements_summary(self, requirements_analysis: Dict[str, Any]) -> str:
        """Create a concise summary of requirements for the prompt."""
        summary_parts = []
        
        # Extract key requirements
        if "requirements" in requirements_analysis:
            reqs = requirements_analysis["requirements"]
            if isinstance(reqs, list):
                summary_parts.append("Key Requirements:")
                for i, req in enumerate(reqs[:5]):  # Limit to 5 requirements
                    summary_parts.append(f"- {req}")
                if len(reqs) > 5:
                    summary_parts.append(f"- Plus {len(reqs) - 5} more requirements")
        
        # Extract functional requirements
        if "functional_requirements" in requirements_analysis:
            func_reqs = requirements_analysis["functional_requirements"]
            if isinstance(func_reqs, list):
                summary_parts.append("\nFunctional Requirements:")
                for i, req in enumerate(func_reqs[:5]):  # Limit to 5
                    if isinstance(req, dict) and "description" in req:
                        summary_parts.append(f"- {req['description']}")
                    elif isinstance(req, str):
                        summary_parts.append(f"- {req}")
                if len(func_reqs) > 5:
                    summary_parts.append(f"- Plus {len(func_reqs) - 5} more functional requirements")
        
        # If no requirements found, return a default summary
        if not summary_parts:
            return "Standard web application with user management and data processing capabilities."
        
        return "\n".join(summary_parts)
    
    def _create_tech_stack_summary(self, tech_stack: Dict[str, Any]) -> str:
        """Create a concise summary of the tech stack for the prompt."""
        components = []
        
        # Extract backend
        if "backend" in tech_stack:
            backend = tech_stack["backend"]
            if isinstance(backend, dict):
                language = backend.get("language", "")
                framework = backend.get("framework", "")
                if language and framework:
                    components.append(f"{language} with {framework} (backend)")
                elif language:
                    components.append(f"{language} (backend)")
            elif isinstance(backend, list) and len(backend) > 0:
                first_item = backend[0]
                if isinstance(first_item, dict) and "name" in first_item:
                    components.append(f"{first_item['name']} (backend)")
                elif isinstance(first_item, str):
                    components.append(f"{first_item} (backend)")
        
        # Extract database
        if "database" in tech_stack:
            database = tech_stack["database"]
            if isinstance(database, dict):
                db_type = database.get("type", database.get("name", ""))
                if db_type:
                    components.append(f"{db_type} (database)")
            elif isinstance(database, list) and len(database) > 0:
                first_item = database[0]
                if isinstance(first_item, dict) and "name" in first_item:
                    components.append(f"{first_item['name']} (database)")
                elif isinstance(first_item, str):
                    components.append(f"{first_item} (database)")
        
        # Extract architecture pattern
        if "architecture_pattern" in tech_stack:
            pattern = tech_stack["architecture_pattern"]
            components.append(f"{pattern} architecture")
        
        # Fallback if no tech stack found
        if not components:
            return "Standard web backend with REST API architecture"
        
        return ", ".join(components)
    
    def _create_system_design_summary(self, system_design: Dict[str, Any]) -> str:
        """Create a concise summary of the system design for the prompt."""
        summary_parts = []
        
        # Extract description if available
        if "description" in system_design:
            summary_parts.append(system_design["description"])
        
        # Extract architecture information
        if "architecture" in system_design:
            arch = system_design["architecture"]
            if isinstance(arch, dict):
                if "description" in arch:
                    summary_parts.append(f"Architecture: {arch['description']}")
                if "pattern" in arch:
                    summary_parts.append(f"Pattern: {arch['pattern']}")
        
        # Extract key components
        if "components" in system_design:
            components = system_design["components"]
            if isinstance(components, list) and len(components) > 0:
                summary_parts.append("Key Components:")
                for component in components[:5]:  # Limit to 5
                    if isinstance(component, dict) and "name" in component:
                        name = component["name"]
                        desc = component.get("description", "")
                        summary_parts.append(f"- {name}: {desc}")
            elif isinstance(components, dict):
                summary_parts.append("Key Components:")
                count = 0
                for name, details in components.items():
                    if count >= 5:  # Limit to 5
                        break
                    if isinstance(details, dict) and "description" in details:
                        summary_parts.append(f"- {name}: {details['description']}")
                    else:
                        summary_parts.append(f"- {name}")
                    count += 1
        
        # Fallback if no system design found
        if not summary_parts:
            return "Standard web backend with API and database layers"
        
        return "\n".join(summary_parts)
    
    def _get_tech_best_practices(self, language: str, framework: str) -> str:
        """Get best practices for a specific technology stack."""
        best_practices = []
        
        # Language-specific best practices
        if language == "python":
            best_practices.extend([
                "Use type hints for better code clarity",
                "Follow PEP 8 style guidelines",
                "Use docstrings for all functions and classes"
            ])
        elif language in ["javascript", "typescript"]:
            best_practices.extend([
                "Use const/let instead of var",
                "Use async/await for asynchronous code",
                "Follow ESLint configurations"
            ])
        elif language == "java":
            best_practices.extend([
                "Follow Java naming conventions",
                "Use proper encapsulation",
                "Implement appropriate exception handling"
            ])
            
        # Framework-specific best practices
        if framework == "django":
            best_practices.extend([
                "Use Django model managers for query logic",
                "Keep views thin and models fat",
                "Use Django forms for validation"
            ])
        elif framework == "flask":
            best_practices.extend([
                "Use Blueprints for modular applications",
                "Implement proper error handling",
                "Use Flask extensions for common needs"
            ])
        elif framework == "express":
            best_practices.extend([
                "Separate routes and controllers",
                "Use middleware for cross-cutting concerns",
                "Implement proper error middleware"
            ])
        elif framework == "spring":
            best_practices.extend([
                "Follow Spring best practices for dependency injection",
                "Use Spring Data for database operations",
                "Implement proper exception handling with @ControllerAdvice"
            ])
        
        # General backend best practices
        best_practices.extend([
            "Implement proper input validation",
            "Return appropriate HTTP status codes",
            "Handle errors gracefully with proper messages",
            "Use consistent error response format",
            "Document API endpoints with examples",
            "Implement proper logging for debugging and auditing",
            "Follow the Single Responsibility Principle",
            "Implement proper authentication and authorization"
        ])
            
        # Limit to top practices and join with newlines
        return "Best Practices to Follow:\n- " + "\n- ".join(best_practices[:10])
    
    def _get_backend_rag_context(self, language: str, framework: str) -> str:
        """Get RAG context for backend code generation."""
        if not self.rag_retriever:
            return ""
            
        try:
            # Create targeted queries for better RAG results
            queries = [
                f"{language} {framework} backend best practices",
                f"{framework} project structure example",
                f"{language} {framework} error handling patterns"
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
            
            if combined_context:
                return "## Expert Knowledge\n\n" + "\n\n".join(combined_context)
            return ""
            
        except Exception as e:
            self.log_warning(f"Error retrieving RAG context: {e}")
            return ""
    
    def _prune_tech_stack(self, tech_stack: Dict[str, Any]) -> Dict[str, Any]:
        """Prune tech stack to focus on backend-relevant aspects."""
        if not isinstance(tech_stack, dict):
            return {}
            
        # Keep only backend-relevant keys
        relevant_keys = ["backend", "database", "architecture_pattern", "orm", "api"]
        pruned_stack = {}
        
        for key in relevant_keys:
            if key in tech_stack:
                pruned_stack[key] = tech_stack[key]
                
        return pruned_stack
    

    def _prune_system_design(self, system_design: Dict[str, Any]) -> Dict[str, Any]:
        """Prune system design to focus on backend-relevant aspects."""
        if not isinstance(system_design, dict):
            return {}
            
        # Keep only backend-relevant keys
        relevant_keys = [
            "architecture", "backend", "database_schema", "api_design", 
            "data_model", "models", "api_endpoints", "business_logic",
            "components", "entities", "relationships", "authentication",
            "authorization"
        ]
        pruned_design = {}
        
        for key in relevant_keys:
            if key in system_design:
                pruned_design[key] = system_design[key]
                
        return pruned_design
    
    def _create_default_tech_stack(self) -> Dict[str, Any]:
        """Create a default tech stack when none is provided."""
        return {
            "backend": {
                "language": "Python",
                "framework": "FastAPI"
            },
            "database": {
                "type": "PostgreSQL"
            },
            "architecture_pattern": "RESTful API"
        }
    
    def _create_default_system_design(self) -> Dict[str, Any]:
        """Create a default system design when none is provided."""
        return {
            "architecture": {
                "description": "Standard 3-tier architecture",
                "pattern": "RESTful API"
            },
            "models": [
                {
                    "name": "User",
                    "fields": [
                        {"name": "id", "type": "uuid", "primary_key": True},
                        {"name": "username", "type": "string", "unique": True},
                        {"name": "email", "type": "string", "unique": True},
                        {"name": "password_hash", "type": "string"},
                        {"name": "is_active", "type": "boolean"},
                        {"name": "created_at", "type": "datetime"}
                    ]
                },
                {
                    "name": "Product",
                    "fields": [
                        {"name": "id", "type": "uuid", "primary_key": True},
                        {"name": "name", "type": "string"},
                        {"name": "description", "type": "text"},
                        {"name": "price", "type": "decimal"},
                        {"name": "created_at", "type": "datetime"}
                    ]
                }
            ],
            "api_endpoints": [
                {
                    "name": "getUserList",
                    "path": "/api/users",
                    "method": "GET",
                    "description": "Get all users"
                },
                {
                    "name": "getUser",
                    "path": "/api/users/{id}",
                    "method": "GET",
                    "description": "Get user by ID"
                },
                {
                    "name": "createUser",
                    "path": "/api/users",
                    "method": "POST",
                    "description": "Create a new user"
                }
            ]
        }
    
    def _get_adjusted_temperature(self, is_revision: bool) -> float:
        """
        Adjust temperature based on whether this is initial generation or revision.
        
        Args:
            is_revision: Whether this is a revision based on feedback
            
        Returns:
            Adjusted temperature value
        """
        # Use a lower temperature for initial code generation (more deterministic)
        initial_temp = max(0.1, min(self.temperature, 0.2))
        
        # Use slightly higher temperature for revisions to encourage creative fixes
        revision_temp = max(0.2, min(self.temperature + 0.1, 0.3))
        
        return revision_temp if is_revision else initial_temp
    
    def _update_token_usage(self, token_usage: Dict[str, int]) -> None:
        """
        Update token usage tracking metrics.
        
        Args:
            token_usage: Token usage dictionary from LLM response
        """
        if not isinstance(token_usage, dict):
            return
            
        # Update token counts
        self.token_usage["prompt_tokens"] += token_usage.get("prompt_tokens", 0)
        self.token_usage["completion_tokens"] += token_usage.get("completion_tokens", 0)
        self.token_usage["total_tokens"] += token_usage.get("total_tokens", 0)
    
    def _setup_message_subscriptions(self) -> None:
        """Setup message bus subscriptions if available."""
        if not self.message_bus:
            return
            
        # Subscribe to database generation completed events
        self.message_bus.subscribe(
            "database.generated", 
            self._handle_database_generation_complete
        )
        
        # Subscribe to code review feedback events
        self.message_bus.subscribe(
            "code_review.feedback.backend", 
            self._handle_code_review_feedback
        )
    
    def _handle_database_generation_complete(self, data: Dict[str, Any]) -> None:
        """
        Handle database generation complete event.
        
        Args:
            data: Event data containing database generation results
        """
        self.log_info("Received database generation complete event")
        
        # Store database schema reference for later use
        if "schema" in data:
            self.component_state["database_schema"] = data["schema"]
    
    def _handle_code_review_feedback(self, data: Dict[str, Any]) -> None:
        """
        Handle code review feedback event.
        
        Args:
            data: Event data containing code review feedback
        """
        self.log_info("Received code review feedback for backend")
        
        # Store feedback for use in next generation
        if "feedback" in data:
            self.component_state["latest_feedback"] = data["feedback"]
        
