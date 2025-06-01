"""
Base Agent class for the Multi-AI Development System.
Provides common functionality for all specialized agents including LLM interaction,
error handling, monitoring, and standardized logging.
"""

import time
import json
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

import monitoring

class BaseAgent(ABC):
    """
    Abstract base class for all AI agents in the system.
    Provides standardized LLM interaction, error handling, and monitoring.
    """
    
    def __init__(
        self, 
        llm: BaseLanguageModel, 
        memory, 
        agent_name: str,
        temperature: float = 0.2,
        rag_retriever: Optional[BaseRetriever] = None
    ):
        self.llm = llm  # Store the original TrackedChatModel instance
        self.memory = memory
        self.agent_name = agent_name
        self.temperature = temperature  # Store the agent's specific temperature
        self.rag_retriever = rag_retriever
        
        # FIXED: Remove direct temperature binding here.
        # The LLM instance passed (self.llm) is already a TrackedChatModel from get_llm().
        # We will apply the specific temperature using .bind() when creating the chain in execute_llm_chain.
        # self.llm_with_temp = self.llm.bind(temperature=self.temperature)  # REMOVED
        
        # Execution tracking
        self.execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_execution_time": 0.0,
            "last_execution_time": 0.0,
            "last_execution_status": "not_started"
        }
        
        # Initialize JSON parser without OutputFixingParser to avoid dependency issues
        self.json_parser = JsonOutputParser()
        
        # Initialize prompt template (will be set by subclasses)
        self.prompt_template = None
    
    def log_start(self, message: str):
        """Log start of agent execution."""
        monitoring.log_agent_activity(self.agent_name, message, "START")
    
    def log_info(self, message: str):
        """Log informational message."""
        monitoring.log_agent_activity(self.agent_name, message, "INFO")
    
    def log_success(self, message: str):
        """Log successful completion."""
        monitoring.log_agent_activity(self.agent_name, message, "SUCCESS")
    
    def log_warning(self, message: str):
        """Log warning message."""
        monitoring.log_agent_activity(self.agent_name, message, "WARNING")
    
    def log_error(self, message: str):
        """Log error message."""
        monitoring.log_agent_activity(self.agent_name, message, "ERROR")
    
    def execute_with_monitoring(self, func, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute agent function with monitoring and error handling.
        No duplicate logging - all logging goes through self.log_* methods.
        """
        start_time = time.time()
        
        try:
            self.log_start("Starting execution")
            
            # Update execution stats
            self.execution_stats["total_executions"] += 1
            
            # Execute the main function
            result = func(*args, **kwargs)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            self.execution_stats["last_execution_time"] = execution_time
            self.execution_stats["total_execution_time"] += execution_time
            self.execution_stats["successful_executions"] += 1
            self.execution_stats["last_execution_status"] = "success"
            
            self.log_success(f"Completed successfully in {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            # Calculate execution time even for failures
            execution_time = time.time() - start_time
            self.execution_stats["last_execution_time"] = execution_time
            self.execution_stats["total_execution_time"] += execution_time
            self.execution_stats["failed_executions"] += 1
            self.execution_stats["last_execution_status"] = "error"
            
            self.log_error(f"Execution failed after {execution_time:.2f}s: {e}")
            
            # Return default response instead of raising
            return self.get_default_response()
    
    def execute_llm_chain(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute LLM chain with inputs and return parsed JSON response.
        FIXED: Apply temperature binding at execution time, not init time.
        """
        if not self.prompt_template:
            raise ValueError(f"{self.agent_name} prompt template not initialized")
        
        try:
            self.log_info(f"Executing LLM chain with temperature {self.temperature}")
            
            # FIXED: Create the chain, binding the agent's specific temperature here.
            # This is the crucial change: self.llm is the original TrackedChatModel.
            chain = self.prompt_template | self.llm.bind(temperature=self.temperature)
            
            # Execute with monitoring context
            response = chain.invoke(
                inputs,
                config={"agent_context": self.agent_name}
            )
            
            # Parse JSON response
            try:
                if hasattr(response, 'content'):
                    response_text = response.content
                else:
                    response_text = str(response)
                
                # Clean and parse JSON
                cleaned_response = self._clean_json_response(response_text)
                parsed_response = json.loads(cleaned_response)
                
                self.log_info("LLM response successfully parsed")
                return parsed_response
                
            except json.JSONDecodeError as e:
                self.log_warning(f"JSON parsing failed, attempting repair: {e}")
                
                # Use our own JSON repair logic
                try:
                    fixed_response = self._attempt_json_repair(response_text)
                    self.log_info("JSON response successfully repaired and parsed")
                    return fixed_response
                        
                except Exception as repair_error:
                    self.log_error(f"JSON repair also failed: {repair_error}")
                    return self.get_default_response()
                    
        except Exception as e:
            self.log_error(f"LLM chain execution failed: {e}")
            return self.get_default_response()
    
    def _clean_json_response(self, response_text: str) -> str:
        """Clean common JSON formatting issues from LLM responses."""
        # Remove common prefixes/suffixes
        cleaned = response_text.strip()
        
        # Remove markdown code blocks
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        # Find JSON object boundaries
        start_idx = cleaned.find('{')
        end_idx = cleaned.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            cleaned = cleaned[start_idx:end_idx + 1]
        
        return cleaned.strip()
    
    def _attempt_json_repair(self, response_text: str) -> Dict[str, Any]:
        """
        ENHANCED: Attempt to repair malformed JSON responses using multiple strategies.
        No longer depends on OutputFixingParser - uses our own repair logic.
        """
        # Strategy 1: Try to extract JSON from the response
        cleaned = self._clean_json_response(response_text)
        
        # Strategy 2: Try to fix common JSON issues
        try:
            # Fix trailing commas
            import re
            fixed = re.sub(r',(\s*[}\]])', r'\1', cleaned)
            
            # Fix unquoted keys (basic case)
            fixed = re.sub(r'(\w+):', r'"\1":', fixed)
            
            # Fix single quotes to double quotes
            fixed = fixed.replace("'", '"')
            
            parsed = json.loads(fixed)
            return parsed
            
        except json.JSONDecodeError:
            pass
        
        # Strategy 3: Try to use JsonOutputParser as fallback
        try:
            # Use the standard JsonOutputParser
            parsed = self.json_parser.parse(response_text)
            if isinstance(parsed, dict):
                return parsed
            else:
                # If it's not a dict, wrap it
                return {"content": parsed}
                
        except Exception as e:
            self.log_error(f"JsonOutputParser also failed: {e}")
        
        # Strategy 4: Extract any JSON-like structure using regex
        try:
            import re
            # Look for JSON object patterns
            json_pattern = r'\{[^{}]*\}'
            matches = re.findall(json_pattern, response_text, re.DOTALL)
            
            for match in matches:
                try:
                    parsed = json.loads(match)
                    if isinstance(parsed, dict) and parsed:  # Non-empty dict
                        return parsed
                except json.JSONDecodeError:
                    continue
                    
        except Exception:
            pass
        
        # Strategy 5: Last resort - create a structured response from text
        self.log_warning("All JSON repair strategies failed, creating structured response from text")
        
        # Try to extract meaningful content
        lines = response_text.strip().split('\n')
        content_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
        
        return {
            "content": ' '.join(content_lines) if content_lines else response_text,
            "raw_response": response_text,
            "parsing_status": "manual_extraction",
            "agent": self.agent_name
        }
    
    def get_rag_context(self, query: str, max_docs: int = 3) -> str:
        """
        Get relevant context from RAG retriever if available.
        
        Args:
            query: Search query for RAG retrieval
            max_docs: Maximum number of documents to retrieve
            
        Returns:
            str: Formatted RAG context or empty string if unavailable
        """
        if not self.rag_retriever:
            return ""
        
        try:
            # Replace deprecated get_relevant_documents with invoke
            docs = self.rag_retriever.invoke(query)
            
            # Handle different return types from invoke()
            if isinstance(docs, dict) and "documents" in docs:
                # Some retrievers return {"documents": [...]}
                docs_list = docs["documents"]
            elif isinstance(docs, list):
                # Some return the documents directly
                docs_list = docs
            else:
                self.log_warning(f"Unexpected RAG retriever response format: {type(docs)}")
                return ""
                
            if not docs_list:
                return ""
            
            # Limit documents and format context
            relevant_docs = docs_list[:max_docs]
            context_parts = []
            
            for i, doc in enumerate(relevant_docs, 1):
                content = doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content
                context_parts.append(f"Context {i}: {content}")
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            self.log_warning(f"RAG context retrieval failed: {e}")
            return ""
    
    def validate_response_structure(self, response: Dict[str, Any], required_keys: List[str]) -> Dict[str, Any]:
        """
        Validate that the response contains all required keys.
        Returns the response with missing keys filled with defaults.
        """
        validated_response = response.copy()
        missing_keys = []
        
        for key in required_keys:
            if key not in validated_response:
                missing_keys.append(key)
                # Add default empty structure
                validated_response[key] = self._get_default_value_for_key(key)
        
        if missing_keys:
            self.log_warning(f"Response missing keys: {missing_keys}, added defaults")
        
        return validated_response
    
    def _get_default_value_for_key(self, key: str) -> Any:
        """Get appropriate default value based on key name patterns."""
        if key.endswith('_requirements') or key.endswith('_rules') or key.endswith('_points'):
            return []
        elif key.endswith('_design') or key.endswith('_overview') or key.endswith('_analysis'):
            return {}
        elif 'modules' in key or 'tools' in key or 'considerations' in key:
            return []
        else:
            return ""
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics for this agent."""
        return self.execution_stats.copy()
    
    def reset_execution_stats(self):
        """Reset execution statistics."""
        self.execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_execution_time": 0.0,
            "last_execution_time": 0.0,
            "last_execution_status": "not_started"
        }
    
    @abstractmethod
    def get_default_response(self) -> Dict[str, Any]:
        """Get default response when agent execution fails."""
        pass
    
    @abstractmethod
    def run(self, *args, **kwargs) -> Dict[str, Any]:
        """Main execution method for the agent."""
        pass