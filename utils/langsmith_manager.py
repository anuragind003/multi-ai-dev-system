import os
import time
import logging
from typing import Dict, Any, Optional
from contextlib import contextmanager
from langsmith import Client

class LangSmithManager:
    """
    Manager for LangSmith integration providing tracing and evaluation capabilities
    optimized for multi-agent temperature-controlled workflows.
    """
    
    def __init__(self, project_name: str = "Multi-AI-Dev-System"):
        """Initialize LangSmith manager with project settings."""
        self.project_name = project_name
        self.logger = logging.getLogger("LangSmithManager")
        self._client = None
        self.enabled = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        self.api_key = os.getenv("LANGSMITH_API_KEY")
        
        # Try to initialize client
        if self.enabled and self.api_key:
            try:
                self._client = Client()
                self.logger.info(f"LangSmith initialized for project: {project_name}")
            except Exception as e:
                self.logger.error(f"Failed to initialize LangSmith client: {e}")
                self.enabled = False
    
    @property
    def client(self) -> Optional[Client]:
        """Get the LangSmith client if available."""
        return self._client
    
    @contextmanager
    def trace(self, name: str, agent_type: str, temperature: float, metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager for tracing agent executions with temperature information.
        
        Optimized for tracking temperature-controlled agents (0.1-0.4 temperature range)
        according to system guidelines.
        
        Args:
            name: Name of the trace span
            agent_type: Type of agent (BRD Analyst, Tech Stack Advisor, etc.)
            temperature: Temperature setting for this agent (0.1-0.4)
            metadata: Additional metadata to include
        """
        if not self.enabled or not self._client:
            # Fall back to simple logging if LangSmith is disabled
            print(f"🔍 Agent: {agent_type} ({name}) with temp={temperature}")
            start_time = time.time()
            try:
                yield
            finally:
                execution_time = time.time() - start_time
                print(f"✓ Completed: {agent_type} in {execution_time:.2f}s")
            return
        
        # Prepare metadata with temperature strategy info
        trace_metadata = {
            "agent_type": agent_type,
            "temperature": temperature,
            "temperature_category": self._categorize_temperature(temperature),
            **(metadata or {})
        }
        
        try:
            # Create run through the Python Client API
            with self._client.new_run(
                name=name,
                run_type="chain",
                project_name=self.project_name,
                metadata=trace_metadata,
            ) as run:
                start_time = time.time()
                try:
                    yield run
                    execution_time = time.time() - start_time
                    run.end(outputs={"execution_time": execution_time})
                except Exception as e:
                    execution_time = time.time() - start_time
                    run.end(
                        error=str(e),
                        outputs={
                            "execution_time": execution_time,
                            "error": str(e),
                            "status": "failed"
                        }
                    )
                    raise
        except Exception as e:
            self.logger.error(f"LangSmith trace error: {e}")
            # Continue execution even if tracing fails
            yield
    
    def _categorize_temperature(self, temperature: float) -> str:
        """Categorize temperature according to project guidelines."""
        if temperature <= 0.1:
            return "code_generation"
        elif temperature <= 0.2:
            return "analytical"
        elif temperature <= 0.4:
            return "creative"
        else:
            return "other"
    
    def log_dataset_example(self, 
                           inputs: Dict[str, Any],
                           outputs: Dict[str, Any], 
                           dataset_name: str,
                           agent_type: str) -> Optional[str]:
        """Log an example to a LangSmith dataset for future evaluation."""
        if not self.enabled or not self._client:
            return None
            
        try:
            # Check if dataset exists, create if not
            datasets = self._client.list_datasets(project_name=self.project_name)
            dataset_exists = any(d.name == dataset_name for d in datasets)
            
            if not dataset_exists:
                self._client.create_dataset(
                    dataset_name=dataset_name,
                    description=f"Examples for {agent_type} agent evaluation"
                )
            
            # Create the example
            example = self._client.create_example(
                inputs=inputs,
                outputs=outputs,
                dataset_name=dataset_name
            )
            
            return example.id
        except Exception as e:
            self.logger.error(f"Failed to log dataset example: {e}")
            return None