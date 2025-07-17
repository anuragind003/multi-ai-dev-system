"""
Enhanced error handling and monitoring utilities for code generation pipeline.
This module provides robust error handling, monitoring, and recovery mechanisms.
"""

import logging
import time
import traceback
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels for monitoring and alerting."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ErrorReport:
    """Structured error report for tracking and monitoring."""
    timestamp: float
    module: str
    error_type: str
    error_message: str
    severity: ErrorSeverity
    context: Dict[str, Any]
    stack_trace: Optional[str] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False

class CodeGenerationErrorHandler:
    """Enhanced error handler for code generation pipeline."""
    
    def __init__(self):
        self.error_history: List[ErrorReport] = []
        self.error_patterns: Dict[str, int] = {}
        self.circuit_breaker_threshold = 3
        self.circuit_breaker_window = 300  # 5 minutes
    
    def handle_llm_parsing_error(self, llm_output: str, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle LLM output parsing errors with recovery strategies."""
        
        error_report = ErrorReport(
            timestamp=time.time(),
            module="LLM_Parsing",
            error_type=type(error).__name__,
            error_message=str(error),
            severity=ErrorSeverity.HIGH,
            context={
                "output_length": len(llm_output) if llm_output else 0,
                "work_item_id": context.get("work_item_id", "unknown"),
                "agent_role": context.get("agent_role", "unknown"),
                **context
            },
            stack_trace=traceback.format_exc()
        )
        
        self.error_history.append(error_report)
        self._update_error_patterns(error_report)
        
        logger.error(f"LLM Parsing Error: {error_report.error_message}")
        logger.debug(f"Context: {error_report.context}")
        
        # Attempt recovery strategies
        recovery_result = self._attempt_parsing_recovery(llm_output, error_report)
        
        if recovery_result:
            error_report.recovery_attempted = True
            error_report.recovery_successful = True
            logger.info(f"Successfully recovered from parsing error using strategy: {recovery_result.get('strategy')}")
            return recovery_result
        else:
            error_report.recovery_attempted = True
            error_report.recovery_successful = False
            logger.warning("Failed to recover from parsing error")
            return self._create_emergency_response(error_report)
    
    def handle_code_generation_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code generation errors with fallback strategies."""
        
        error_report = ErrorReport(
            timestamp=time.time(),
            module="Code_Generation",
            error_type=type(error).__name__,
            error_message=str(error),
            severity=ErrorSeverity.HIGH,
            context=context,
            stack_trace=traceback.format_exc()
        )
        
        self.error_history.append(error_report)
        self._update_error_patterns(error_report)
        
        logger.error(f"Code Generation Error: {error_report.error_message}")
        
        # Check for circuit breaker activation
        if self._should_activate_circuit_breaker():
            error_report.severity = ErrorSeverity.CRITICAL
            logger.critical("Circuit breaker activated due to repeated errors")
            return self._create_circuit_breaker_response(error_report)
        
        return self._create_error_response(error_report)
    
    def validate_generated_files(self, files: List[Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate generated files with detailed error reporting."""
        
        validation_result = {
            "valid_files": [],
            "invalid_files": [],
            "validation_errors": [],
            "total_files": len(files) if files else 0
        }
        
        if not files:
            error_report = ErrorReport(
                timestamp=time.time(),
                module="File_Validation",
                error_type="NoFilesGenerated",
                error_message="No files were generated",
                severity=ErrorSeverity.MEDIUM,
                context=context
            )
            self.error_history.append(error_report)
            validation_result["validation_errors"].append("No files generated")
            return validation_result
        
        for i, file_obj in enumerate(files):
            try:
                file_validation = self._validate_single_file(file_obj, i, context)
                
                if file_validation["is_valid"]:
                    validation_result["valid_files"].append(file_validation["file_data"])
                else:
                    validation_result["invalid_files"].append({
                        "index": i,
                        "errors": file_validation["errors"]
                    })
                    validation_result["validation_errors"].extend(file_validation["errors"])
            
            except Exception as e:
                error_msg = f"Error validating file {i}: {str(e)}"
                validation_result["invalid_files"].append({"index": i, "errors": [error_msg]})
                validation_result["validation_errors"].append(error_msg)
                
                error_report = ErrorReport(
                    timestamp=time.time(),
                    module="File_Validation",
                    error_type="ValidationException",
                    error_message=error_msg,
                    severity=ErrorSeverity.MEDIUM,
                    context={**context, "file_index": i}
                )
                self.error_history.append(error_report)
        
        # Log validation summary
        valid_count = len(validation_result["valid_files"])
        invalid_count = len(validation_result["invalid_files"])
        
        if valid_count > 0:
            logger.info(f"File validation: {valid_count} valid, {invalid_count} invalid")
        else:
            logger.warning(f"File validation: No valid files found out of {validation_result['total_files']}")
        
        return validation_result
    
    def _validate_single_file(self, file_obj: Any, index: int, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single generated file."""
        
        validation_result = {
            "is_valid": False,
            "file_data": None,
            "errors": []
        }
        
        try:
            # Convert to dictionary
            if hasattr(file_obj, 'model_dump'):
                file_dict = file_obj.model_dump()
            elif hasattr(file_obj, 'dict'):
                file_dict = file_obj.dict()
            elif isinstance(file_obj, dict):
                file_dict = file_obj
            else:
                validation_result["errors"].append(f"Invalid file object type: {type(file_obj)}")
                return validation_result
            
            # Check required fields
            required_fields = ['file_path', 'content']
            missing_fields = [field for field in required_fields if not file_dict.get(field)]
            
            if missing_fields:
                validation_result["errors"].append(f"Missing required fields: {missing_fields}")
                return validation_result
            
            # Validate file path
            file_path = file_dict.get('file_path', '')
            if not self._is_valid_file_path(file_path):
                validation_result["errors"].append(f"Invalid file path: '{file_path}'")
                return validation_result
            
            # Validate content
            content = str(file_dict.get('content', ''))
            if len(content.strip()) < 10:
                validation_result["errors"].append(f"Content too short: {len(content)} characters")
                return validation_result
            
            # Check for common content issues
            if '```' in content and content.count('```') % 2 != 0:
                validation_result["errors"].append("Unmatched code block markers in content")
            
            # File is valid
            validation_result["is_valid"] = True
            validation_result["file_data"] = file_dict
            
        except Exception as e:
            validation_result["errors"].append(f"Validation exception: {str(e)}")
        
        return validation_result
    
    def _is_valid_file_path(self, file_path: str) -> bool:
        """Check if a file path is valid."""
        if not file_path or len(file_path) < 3:
            return False
        
        # Must have an extension
        if '.' not in file_path:
            return False
        
        # Check for valid characters
        import re
        if not re.match(r'^[a-zA-Z0-9_/.-]+$', file_path):
            return False
        
        return True
    
    def _attempt_parsing_recovery(self, llm_output: str, error_report: ErrorReport) -> Optional[Dict[str, Any]]:
        """Attempt to recover from parsing errors using fallback strategies."""
        
        if not llm_output:
            return None
        
        try:
            # Strategy 1: Use the enhanced parser
            from tools.code_generation_utils import parse_llm_output_into_files
            
            logger.info("Attempting recovery using enhanced parser")
            files = parse_llm_output_into_files(llm_output)
            
            if files:
                return {
                    "strategy": "enhanced_parser",
                    "generated_files": [file.model_dump() if hasattr(file, 'model_dump') else file for file in files],
                    "status": "recovered"
                }
        
        except Exception as e:
            logger.warning(f"Enhanced parser recovery failed: {e}")
        
        # Strategy 2: Emergency content extraction
        try:
            logger.info("Attempting emergency content extraction")
            emergency_files = self._emergency_content_extraction(llm_output)
            
            if emergency_files:
                return {
                    "strategy": "emergency_extraction",
                    "generated_files": emergency_files,
                    "status": "recovered"
                }
        
        except Exception as e:
            logger.warning(f"Emergency extraction failed: {e}")
        
        return None
    
    def _emergency_content_extraction(self, llm_output: str) -> List[Dict[str, Any]]:
        """Emergency content extraction when all parsing fails."""
        
        files = []
        
        # Look for substantial code blocks
        import re
        code_blocks = re.findall(r'```[a-zA-Z]*\s*\n(.*?)(?=\n```|$)', llm_output, re.DOTALL)
        
        for i, content in enumerate(code_blocks):
            content = content.strip()
            if len(content) > 50:  # Substantial content
                files.append({
                    "file_path": f"emergency_file_{i}.txt",
                    "content": content,
                    "purpose": f"Emergency extracted content {i}",
                    "status": "emergency_recovery"
                })
        
        return files
    
    def _update_error_patterns(self, error_report: ErrorReport):
        """Update error pattern tracking for circuit breaker logic."""
        pattern_key = f"{error_report.module}_{error_report.error_type}"
        self.error_patterns[pattern_key] = self.error_patterns.get(pattern_key, 0) + 1
    
    def _should_activate_circuit_breaker(self) -> bool:
        """Determine if circuit breaker should be activated."""
        current_time = time.time()
        recent_errors = [
            err for err in self.error_history
            if current_time - err.timestamp < self.circuit_breaker_window
        ]
        
        return len(recent_errors) >= self.circuit_breaker_threshold
    
    def _create_emergency_response(self, error_report: ErrorReport) -> Dict[str, Any]:
        """Create emergency response when recovery fails."""
        return {
            "status": "error",
            "error": error_report.error_message,
            "error_type": error_report.error_type,
            "severity": error_report.severity.value,
            "generated_files": [],
            "recovery_attempted": error_report.recovery_attempted,
            "timestamp": error_report.timestamp
        }
    
    def _create_error_response(self, error_report: ErrorReport) -> Dict[str, Any]:
        """Create standard error response."""
        return {
            "status": "error",
            "error": error_report.error_message,
            "error_type": error_report.error_type,
            "generated_files": [],
            "context": error_report.context,
            "timestamp": error_report.timestamp
        }
    
    def _create_circuit_breaker_response(self, error_report: ErrorReport) -> Dict[str, Any]:
        """Create circuit breaker response."""
        return {
            "status": "circuit_breaker_activated",
            "error": "Too many errors detected, circuit breaker activated",
            "original_error": error_report.error_message,
            "generated_files": [],
            "circuit_breaker": True,
            "timestamp": error_report.timestamp
        }
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors for monitoring."""
        current_time = time.time()
        recent_errors = [
            err for err in self.error_history
            if current_time - err.timestamp < 3600  # Last hour
        ]
        
        return {
            "total_errors": len(self.error_history),
            "recent_errors": len(recent_errors),
            "error_patterns": dict(self.error_patterns),
            "severity_breakdown": {
                severity.value: len([err for err in recent_errors if err.severity == severity])
                for severity in ErrorSeverity
            },
            "circuit_breaker_status": self._should_activate_circuit_breaker()
        }

# Global error handler instance
_global_error_handler = CodeGenerationErrorHandler()

def get_error_handler() -> CodeGenerationErrorHandler:
    """Get the global error handler instance."""
    return _global_error_handler
