"""
Enhanced Hybrid Validation System for Multi-Agent Development System

This module provides progressive validation that gracefully handles various input formats
from ReAct agents, especially JSON strings that should be dictionaries.

Key Features:
- 3-layer progressive validation (Strict → Tolerant → Permissive)
- JSON string detection and parsing
- Confidence scoring and validation metrics
- ReAct agent input preprocessing
- Comprehensive error recovery
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Union, Type, Callable
from pydantic import BaseModel, ValidationError, Field
from dataclasses import dataclass
from enum import Enum
import copy

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Validation strictness levels in order of preference."""
    STRICT = "strict"           # Full Pydantic validation with exact types
    TOLERANT = "tolerant"       # Pydantic with type coercion and cleaning
    PERMISSIVE = "permissive"   # Schema-guided extraction with fallbacks
    FALLBACK = "fallback"       # Best-effort keyword extraction

@dataclass
class HybridValidationResult:
    """Result of hybrid validation with detailed metadata."""
    success: bool
    data: Dict[str, Any]
    level_used: ValidationLevel
    errors: List[str]
    warnings: List[str]
    confidence_score: float  # 0.0 to 1.0
    processing_notes: List[str]  # Detailed processing information

class ReactInputPreprocessor:
    """Handles preprocessing of ReAct agent inputs that are often JSON strings."""
    
    @staticmethod
    def detect_and_parse_json_string(input_data: Any) -> Any:
        """Detect and parse JSON strings from ReAct agents."""
        if isinstance(input_data, str):
            # Check if string looks like JSON
            stripped = input_data.strip()
            if ((stripped.startswith('{') and stripped.endswith('}')) or
                (stripped.startswith('[') and stripped.endswith(']'))):
                try:
                    parsed = json.loads(stripped)
                    logger.debug(f"Successfully parsed JSON string: {type(parsed)}")
                    return parsed
                except json.JSONDecodeError as e:
                    logger.debug(f"JSON parsing failed: {e}")
                    # Try to fix common JSON issues
                    return ReactInputPreprocessor._fix_malformed_json(stripped)
        return input_data
    
    @staticmethod
    def _fix_malformed_json(json_str: str) -> Any:
        """Attempt to fix common JSON formatting issues."""
        try:
            # Fix single quotes to double quotes
            fixed = json_str.replace("'", '"')
            
            # Fix unquoted keys (common in Python dict format)
            fixed = re.sub(r'(\w+):', r'"\1":', fixed)
            
            # Fix trailing commas
            fixed = re.sub(r',(\s*[}\]])', r'\1', fixed)
            
            return json.loads(fixed)
        except:
            logger.debug("Could not fix malformed JSON")
            return json_str

class HybridValidator:
    """
    Progressive validation system that handles multiple input formats gracefully.
    Designed specifically for ReAct agents that often pass JSON strings instead of dicts.
    """
    
    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        self.logger = logger_instance or logger
        self.preprocessor = ReactInputPreprocessor()
        self.stats = {
            "strict_successes": 0,
            "tolerant_successes": 0,
            "permissive_successes": 0,
            "fallback_successes": 0,
            "total_failures": 0
        }
    
    def validate_progressive(
        self, 
        raw_input: Any, 
        pydantic_model: Type[BaseModel],
        required_fields: List[str],
        fallback_extractors: Optional[List[Callable]] = None,
        context: str = ""
    ) -> HybridValidationResult:
        """
        Progressive validation with multiple fallback levels.
        
        Args:
            raw_input: The input to validate (could be JSON string, dict, etc.)
            pydantic_model: Pydantic model for validation
            required_fields: List of required field names
            fallback_extractors: Optional custom extraction functions
            context: Context string for better error messages
        
        Returns:
            HybridValidationResult with validation outcome and metadata
        """
        processing_notes = []
        
        # Preprocess ReAct agent inputs (especially JSON strings)
        preprocessed_input = self.preprocessor.detect_and_parse_json_string(raw_input)
        if preprocessed_input != raw_input:
            processing_notes.append("Preprocessed JSON string from ReAct agent")
        
        # Level 1: STRICT Validation
        result = self._try_strict_validation(preprocessed_input, pydantic_model, processing_notes)
        if result.success:
            self.stats["strict_successes"] += 1
            return result
        
        # Level 2: TOLERANT Validation
        result = self._try_tolerant_validation(preprocessed_input, pydantic_model, processing_notes)
        if result.success:
            self.stats["tolerant_successes"] += 1
            return result
        
        # Level 3: PERMISSIVE Validation
        result = self._try_permissive_validation(
            preprocessed_input, pydantic_model, required_fields, processing_notes
        )
        if result.success:
            self.stats["permissive_successes"] += 1
            return result
        
        # Level 4: FALLBACK Validation
        result = self._try_fallback_validation(
            preprocessed_input, required_fields, fallback_extractors, processing_notes
        )
        if result.success:
            self.stats["fallback_successes"] += 1
            return result
        
        # All levels failed
        self.stats["total_failures"] += 1
        return HybridValidationResult(
            success=False,
            data={},
            level_used=ValidationLevel.FALLBACK,
            errors=[f"All validation levels failed for {context}"],
            warnings=[],
            confidence_score=0.0,
            processing_notes=processing_notes
        )
    
    def _try_strict_validation(
        self, input_data: Any, pydantic_model: Type[BaseModel], notes: List[str]
    ) -> HybridValidationResult:
        """Level 1: Try exact Pydantic validation."""
        try:
            if isinstance(input_data, dict):
                validated = pydantic_model(**input_data)
                notes.append("STRICT validation successful")
                return HybridValidationResult(
                    success=True,
                    data=validated.dict(),
                    level_used=ValidationLevel.STRICT,
                    errors=[],
                    warnings=[],
                    confidence_score=1.0,
                    processing_notes=notes.copy()
                )
        except ValidationError as e:
            self.logger.debug(f"STRICT validation failed: {e}")
        except Exception as e:
            self.logger.debug(f"STRICT validation error: {e}")
        
        return HybridValidationResult(
            success=False, data={}, level_used=ValidationLevel.STRICT,
            errors=[], warnings=[], confidence_score=0.0, processing_notes=notes.copy()
        )
    
    def _try_tolerant_validation(
        self, input_data: Any, pydantic_model: Type[BaseModel], notes: List[str]
    ) -> HybridValidationResult:
        """Level 2: Try with type coercion and cleaning."""
        try:
            cleaned_input = self._clean_and_coerce_input(input_data, pydantic_model)
            if cleaned_input:
                validated = pydantic_model(**cleaned_input)
                notes.append("TOLERANT validation successful with cleaning")
                return HybridValidationResult(
                    success=True,
                    data=validated.dict(),
                    level_used=ValidationLevel.TOLERANT,
                    errors=[],
                    warnings=[f"Input required cleaning for fields: {list(cleaned_input.keys())}"],
                    confidence_score=0.8,
                    processing_notes=notes.copy()
                )
        except Exception as e:
            self.logger.debug(f"TOLERANT validation failed: {e}")
        
        return HybridValidationResult(
            success=False, data={}, level_used=ValidationLevel.TOLERANT,
            errors=[], warnings=[], confidence_score=0.0, processing_notes=notes.copy()
        )
    
    def _try_permissive_validation(
        self, input_data: Any, pydantic_model: Type[BaseModel], 
        required_fields: List[str], notes: List[str]
    ) -> HybridValidationResult:
        """Level 3: Schema-guided extraction with field mapping."""
        try:
            extracted = self._extract_using_schema(input_data, pydantic_model, required_fields)
            if extracted and self._has_required_fields(extracted, required_fields):
                notes.append("PERMISSIVE validation using schema-guided extraction")
                return HybridValidationResult(
                    success=True,
                    data=extracted,
                    level_used=ValidationLevel.PERMISSIVE,
                    errors=[],
                    warnings=["Used schema-guided extraction - verify results"],
                    confidence_score=0.6,
                    processing_notes=notes.copy()
                )
        except Exception as e:
            self.logger.debug(f"PERMISSIVE validation failed: {e}")
        
        return HybridValidationResult(
            success=False, data={}, level_used=ValidationLevel.PERMISSIVE,
            errors=[], warnings=[], confidence_score=0.0, processing_notes=notes.copy()
        )
    
    def _try_fallback_validation(
        self, input_data: Any, required_fields: List[str], 
        fallback_extractors: Optional[List[Callable]], notes: List[str]
    ) -> HybridValidationResult:
        """Level 4: Best-effort extraction with custom extractors."""
        try:
            fallback_data = self._fallback_extraction(input_data, required_fields, fallback_extractors)
            if fallback_data:
                notes.append("FALLBACK validation using custom extractors")
                return HybridValidationResult(
                    success=True,
                    data=fallback_data,
                    level_used=ValidationLevel.FALLBACK,
                    errors=[],
                    warnings=["Used fallback extraction - verify results carefully"],
                    confidence_score=0.3,
                    processing_notes=notes.copy()
                )
        except Exception as e:
            self.logger.debug(f"FALLBACK validation failed: {e}")
        
        return HybridValidationResult(
            success=False, data={}, level_used=ValidationLevel.FALLBACK,
            errors=[], warnings=[], confidence_score=0.0, processing_notes=notes.copy()
        )
    
    def _clean_and_coerce_input(self, input_data: Any, pydantic_model: Type[BaseModel]) -> Dict[str, Any]:
        """Clean and coerce input data for tolerant validation."""
        if not isinstance(input_data, dict):
            return {}
        
        cleaned = {}
        model_fields = pydantic_model.__fields__
        
        for field_name, value in input_data.items():
            if field_name in model_fields:
                field_info = model_fields[field_name]
                
                # Type coercion based on field type
                if hasattr(field_info, 'type_'):
                    expected_type = field_info.type_
                    
                    # Handle common type coercions
                    if expected_type == list and isinstance(value, str):
                        # Try to parse comma-separated string as list
                        cleaned[field_name] = [item.strip() for item in value.split(',')]
                    elif expected_type == str and not isinstance(value, str):
                        cleaned[field_name] = str(value)
                    elif expected_type in [int, float] and isinstance(value, str):
                        try:
                            cleaned[field_name] = expected_type(value)
                        except ValueError:
                            continue
                    else:
                        cleaned[field_name] = value
                else:
                    cleaned[field_name] = value
        
        return cleaned
    
    def _extract_using_schema(
        self, input_data: Any, pydantic_model: Type[BaseModel], required_fields: List[str]
    ) -> Dict[str, Any]:
        """Extract data using schema information."""
        extracted = {}
        
        # Get model field information
        model_fields = getattr(pydantic_model, '__fields__', {})
        
        if isinstance(input_data, dict):
            # Direct field mapping
            for field_name in required_fields:
                if field_name in input_data:
                    extracted[field_name] = input_data[field_name]
                else:
                    # Try case-insensitive matching
                    for key, value in input_data.items():
                        if key.lower() == field_name.lower():
                            extracted[field_name] = value
                            break
        
        elif isinstance(input_data, str):
            # Extract from text using field names as keywords
            text = input_data.lower()
            for field_name in required_fields:
                # Look for patterns like "field_name: value" or "field_name = value"
                patterns = [
                    rf'{field_name.lower()}\s*[:=]\s*([^\n,;]+)',
                    rf'"{field_name}"\s*[:=]\s*([^\n,;]+)',
                    rf"'{field_name}'\s*[:=]\s*([^\n,;]+)"
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, text)
                    if match:
                        value = match.group(1).strip()
                        # Try to parse as JSON if it looks like a list/dict
                        if value.startswith('[') or value.startswith('{'):
                            try:
                                extracted[field_name] = json.loads(value)
                            except:
                                extracted[field_name] = value
                        else:
                            extracted[field_name] = value
                        break
        
        return extracted
    
    def _fallback_extraction(
        self, input_data: Any, required_fields: List[str], 
        fallback_extractors: Optional[List[Callable]]
    ) -> Dict[str, Any]:
        """Last resort extraction using custom extractors."""
        fallback_data = {}
        
        # Try custom extractors first
        if fallback_extractors:
            for extractor in fallback_extractors:
                try:
                    result = extractor(input_data)
                    if isinstance(result, dict):
                        fallback_data.update(result)
                except Exception as e:
                    self.logger.debug(f"Custom extractor failed: {e}")
        
        # If still missing required fields, use keyword-based extraction
        missing_fields = [f for f in required_fields if f not in fallback_data]
        if missing_fields:
            keyword_extracted = self._keyword_based_extraction(input_data, missing_fields)
            fallback_data.update(keyword_extracted)
        
        return fallback_data
    
    def _keyword_based_extraction(self, input_data: Any, field_names: List[str]) -> Dict[str, Any]:
        """Extract based on common keywords and patterns."""
        extracted = {}
        text = str(input_data).lower()
        
        # Common extraction patterns for different field types
        extraction_patterns = {
            'section_titles': r'(?:sections?|titles?|headings?)[:\s]*([^\n]+)',
            'requirements': r'(?:requirements?|specs?|specifications?)[:\s]*([^\n]+)',
            'goals': r'(?:goals?|objectives?|aims?)[:\s]*([^\n]+)',
            'constraints': r'(?:constraints?|limitations?|restrictions?)[:\s]*([^\n]+)',
            'assumptions': r'(?:assumptions?|premises?)[:\s]*([^\n]+)',
        }
        
        for field_name in field_names:
            if field_name.lower() in extraction_patterns:
                pattern = extraction_patterns[field_name.lower()]
                match = re.search(pattern, text)
                if match:
                    value = match.group(1).strip()
                    # If it looks like a list, split by commas
                    if ',' in value:
                        extracted[field_name] = [item.strip() for item in value.split(',')]
                    else:
                        extracted[field_name] = [value]
        
        return extracted
    
    def _has_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> bool:
        """Check if data has all required fields with non-empty values."""
        for field in required_fields:
            if field not in data or not data[field]:
                return False
        return True
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation performance statistics."""
        total = sum(self.stats.values())
        if total == 0:
            return {"message": "No validations performed yet"}
        
        return {
            "total_validations": total,
            "success_rate": (total - self.stats["total_failures"]) / total,
            "level_distribution": {
                level: count / total for level, count in self.stats.items()
            },
            "recommendations": self._get_optimization_recommendations()
        }
    
    def _get_optimization_recommendations(self) -> List[str]:
        """Generate recommendations based on validation patterns."""
        recommendations = []
        total = sum(self.stats.values())
        
        if total == 0:
            return ["No data available for recommendations"]
        
        strict_rate = self.stats["strict_successes"] / total
        failure_rate = self.stats["total_failures"] / total
        
        if strict_rate < 0.5:
            recommendations.append("Consider improving input format consistency in ReAct agents")
        
        if failure_rate > 0.1:
            recommendations.append("Add more fallback extractors for better coverage")
        
        if self.stats["fallback_successes"] > self.stats["strict_successes"]:
            recommendations.append("Review agent prompt engineering to improve output structure")
        
        return recommendations 