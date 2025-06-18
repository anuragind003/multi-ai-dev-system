import os
import json
import hashlib
from typing import Dict, Any, Optional
import logging
import re

class SimpleResponseCache:
    """Simple file-based cache for LLM responses to reduce API calls"""
    
    def __init__(self):
        self.cache_dir = os.path.join("cache", "llm_responses")
        self.enabled = os.getenv("MAISD_ENABLE_CACHING", "true").lower() == "true"
        
        # Create cache directory if it doesn't exist
        if self.enabled and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_key(self, prompt: str, temperature: float, model: str) -> str:
        """Generate a unique cache key based on semantic content, not exact text"""
        # Normalize prompt to increase cache hits
        normalized_prompt = self._normalize_prompt(prompt)
        input_str = f"{normalized_prompt}|{temperature}|{model}"
        return hashlib.md5(input_str.encode()).hexdigest()

    def _normalize_prompt(self, prompt: str) -> str:
        """Normalize prompt to increase cache hit rate"""
        # Remove extra whitespace
        normalized = ' '.join(prompt.split())
        
        if os.environ.get("MAISD_EMERGENCY_MODE") == "true":
            # SUPER aggressive normalization for emergency mode
            # Strip all non-essential formatting and keep only core instructions
            normalized = re.sub(r'You are.*?\.', '', normalized)
            normalized = re.sub(r'\s+', ' ', normalized)
            normalized = re.sub(r'\d+', 'N', normalized)
            normalized = re.sub(r'[^\w\s\.]', '', normalized)
            # Get first 200 chars and last 200 chars only - skips middle content
            if len(normalized) > 400:
                normalized = normalized[:200] + "..." + normalized[-200:]
        elif os.environ.get("MAISD_REDUCED_CALLS") == "true":
            # Somewhat aggressive normalization for reduced calls mode
            normalized = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', 'DATE', normalized)
            normalized = re.sub(r'\b\d{2}:\d{2}:\d{2}\b', 'TIME', normalized)
            normalized = re.sub(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', 'UUID', normalized)
            normalized = re.sub(r'var_\d+', 'var_X', normalized)
            normalized = re.sub(r'temp_\d+', 'temp_X', normalized)
    
        # Truncate for hashing
        if len(normalized) > 10000:
            normalized = normalized[:10000]
            
        return normalized
    
    def get_cached_response(self, prompt: str, temperature: float, model: str) -> Optional[str]:
        """Retrieve cached response if it exists"""
        if not self.enabled:
            return None
            
        cache_key = self._get_cache_key(prompt, temperature, model)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                    logging.debug(f"Cache hit for prompt: {prompt[:50]}...")
                    return cached_data["response"]
            except Exception as e:
                logging.warning(f"Failed to read cache: {e}")
                
        return None
    
    def cache_response(self, prompt: str, temperature: float, model: str, response: str) -> None:
        """Cache response for future use"""
        if not self.enabled:
            return
            
        cache_key = self._get_cache_key(prompt, temperature, model)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    "prompt": prompt,
                    "temperature": temperature,
                    "model": model,
                    "response": response
                }, f)
            logging.debug(f"Cached response for prompt: {prompt[:50]}...")
        except Exception as e:
            logging.warning(f"Failed to write cache: {e}")

# Global cache instance
response_cache = SimpleResponseCache()