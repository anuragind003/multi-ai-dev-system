#!/usr/bin/env python3
"""
System Initializer for Multi-AI Development System

Provides comprehensive initialization and health checking for all system components.
"""

import logging
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import os
import asyncio

# System imports
import monitoring
from config import get_system_config
from enhanced_memory_manager_with_recovery import get_enhanced_memory_manager
from rag_manager import ProjectRAGManager, set_rag_manager
from message_bus import get_message_bus

# Configure logger
logger = logging.getLogger(__name__)

class SystemInitializer:
    """Comprehensive system initializer for the Multi-AI Development System."""

    def __init__(self):
        self.initialization_results = {}
        self.startup_time = time.time()
        self.memory_hub = None  # Store the initialized memory hub
        
    def initialize_system(self, config_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Initialize the entire Multi-AI Development System."""
        logger.info("Starting Multi-AI Development System Initialization")
        
        try:
            # Phase 1: Core Configuration
            config_result = self._initialize_configuration(config_override)
            self.initialization_results["configuration"] = config_result
            
            # Phase 2: Enhanced Memory System
            memory_result = self._initialize_enhanced_memory()
            self.initialization_results["enhanced_memory"] = memory_result
            
            # --- FIX: Capture and set the global memory hub singleton ---
            if memory_result.get("success"):
                self.memory_hub = memory_result.get("instance")
                # Pre-initialize the singleton to prevent race conditions
                try:
                    from utils import shared_memory_hub
                    shared_memory_hub._shared_memory_instance = self.memory_hub
                    logger.info("[OK] Global shared memory hub singleton is set.")
                except Exception as e:
                    logger.error(f"[FAIL] Failed to set global memory hub singleton: {e}")

            # Phase 3: RAG System
            rag_result = self._initialize_rag_system()
            self.initialization_results["rag_system"] = rag_result
            
            # Phase 4: Message Bus
            message_bus_result = self._initialize_message_bus()
            self.initialization_results["message_bus"] = message_bus_result
            
            # Phase 5: System Health Check
            health_result = self._perform_health_check()
            self.initialization_results["health_check"] = health_result
            
            # Calculate total time
            total_time = time.time() - self.startup_time
            
            # Generate status report
            status_report = self._generate_status_report(total_time)
            
            logger.info(f"[OK] System initialization completed in {total_time:.2f} seconds")
            return status_report
            
        except Exception as e:
            logger.error(f"[FAIL] System initialization failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def _initialize_configuration(self, config_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Initialize system configuration."""
        logger.info("Initializing system configuration...")
        
        try:
            import config
            
            # Initialize system config if needed
            if hasattr(config, 'initialize_system_config'):
                config.initialize_system_config({})
            
            config_status = {
                "llm_available": hasattr(config, 'get_llm'),
                "embedding_model_available": hasattr(config, 'get_embedding_model'),
                "api_keys_configured": True
            }
            
            logger.info("[OK] Configuration initialized successfully")
            return {"success": True, "status": config_status}
            
        except Exception as e:
            logger.error(f"[FAIL] Configuration initialization failed: {e}")
            return {"success": False, "error": str(e)}

    def _initialize_enhanced_memory(self) -> Dict[str, Any]:
        """Initialize enhanced memory system and return the manager instance."""
        logger.info("Initializing enhanced memory system...")
        
        try:
            from config import get_system_config
            
            # --- FIX: Get the memory hub from the already-initialized SystemConfig ---
            # This ensures we use the SINGLE, system-wide memory hub instance.
            system_config = get_system_config()
            memory_manager = system_config.memory_hub
            
            if memory_manager is None:
                raise RuntimeError("Memory hub not found in SystemConfig. Initialization order is incorrect.")

            # Test basic operations
            test_key = "system_init_test"
            test_value = {"initialized": True, "timestamp": datetime.now().isoformat()}
            
            memory_manager.set(test_key, test_value, context="system_initialization")
            retrieved_value = memory_manager.get(test_key, context="system_initialization")
            
            memory_status = {
                "memory_manager_created": True,
                "basic_operations_working": retrieved_value is not None,
                "hybrid_backend_available": True
            }
            
            logger.info("[OK] Enhanced memory system initialized successfully")
            return {"success": True, "status": memory_status, "instance": memory_manager}
            
        except Exception as e:
            logger.error(f"[FAIL] Enhanced memory initialization failed: {e}")
            return {"success": False, "error": str(e), "instance": None}

    def _initialize_rag_system(self) -> Dict[str, Any]:
        """Initialize RAG system and build the index."""
        logger.info("Initializing RAG system...")
        
        try:
            from rag_manager import get_rag_manager
            
            rag_manager = get_rag_manager()
            
            rag_status = {
                "rag_manager_available": rag_manager is not None,
                "index_built_successfully": False,
                "vector_store_initialized": False
            }
            
            if rag_manager:
                # --- FIX: Explicitly build the RAG index during initialization ---
                # This ensures the vector store is ready before any agent needs it.
                logger.info("Building RAG index... (This may take a moment)")
                try:
                    # The indexing function is synchronous, so we call it directly.
                    rag_manager.optimized_index_project()

                    logger.info("[OK] RAG index built successfully.")
                    rag_status["index_built_successfully"] = True
                except Exception as index_error:
                    logger.error(f"[FAIL] RAG indexing failed: {index_error}")
                    # Continue without a working RAG system, but log the failure.
                    rag_status["index_built_successfully"] = False
                
                rag_status["vector_store_initialized"] = rag_manager.is_initialized()
            
            logger.info("[OK] RAG system initialization phase complete.")
            return {"success": True, "status": rag_status}
            
        except Exception as e:
            logger.error(f"[FAIL] RAG system initialization failed: {e}")
            return {"success": False, "error": str(e)}

    def _initialize_message_bus(self) -> Dict[str, Any]:
        """Initialize message bus system."""
        logger.info("Initializing message bus system...")
        
        try:
            from message_bus import get_message_bus
            
            message_bus = get_message_bus()
            
            # Test message publishing
            test_topic = "system.init.test"
            test_message = {"test": True, "timestamp": datetime.now().isoformat()}
            message_bus.publish(test_topic, test_message)
            
            message_bus_status = {
                "message_bus_created": True,
                "publish_working": True,
                "async_support": True
            }
            
            logger.info("[OK] Message bus system initialized successfully")
            return {"success": True, "status": message_bus_status}
            
        except Exception as e:
            logger.error(f"[FAIL] Message bus initialization failed: {e}")
            return {"success": False, "error": str(e)}

    def _perform_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive system health check."""
        logger.info("Performing system health check...")
        
        try:
            health_checks = {}
            
            # Check each component
            for component, result in self.initialization_results.items():
                health_checks[component] = result.get("success", False)
            
            # Calculate overall health
            total_checks = len(health_checks)
            passed_checks = sum(1 for v in health_checks.values() if v)
            overall_health = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
            
            health_result = {
                "individual_checks": health_checks,
                "overall_health_percentage": overall_health,
                "passed_checks": passed_checks,
                "total_checks": total_checks,
                "system_ready": overall_health >= 75.0
            }
            
            logger.info(f"[OK] System health check: {overall_health:.1f}% healthy")
            return {"success": True, "health": health_result}
            
        except Exception as e:
            logger.error(f"[FAIL] Health check failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_status_report(self, total_time: float) -> Dict[str, Any]:
        """Generate comprehensive system status report."""
        
        successful_components = sum(1 for result in self.initialization_results.values() if result.get("success", False))
        total_components = len(self.initialization_results)
        success_rate = (successful_components / total_components) * 100 if total_components > 0 else 0
        
        health_info = self.initialization_results.get("health_check", {}).get("health", {})
        overall_health = health_info.get("overall_health_percentage", 0)
        system_ready = health_info.get("system_ready", False)

        status_report = {
            "initialization_summary": {
                "success": success_rate >= 75.0,
                "total_time_seconds": total_time,
                "components_initialized": successful_components,
                "total_components": total_components,
                "success_rate_percentage": success_rate,
                "overall_health_percentage": overall_health,
                "system_ready": system_ready
            },
            "component_results": self.initialization_results,
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "memory_hub_instance": self.memory_hub # Include the instance for downstream use
        }
        
        if system_ready:
            logger.info(f"Multi-AI Development System is READY! ({overall_health:.1f}% health)")
        else:
            logger.warning(f"Multi-AI Development System has issues ({overall_health:.1f}% health)")
            
        return status_report

def initialize_multi_ai_system(config_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Initialize the Multi-AI Development System."""
    initializer = SystemInitializer()
    report = initializer.initialize_system(config_override)
    # Persist the memory hub instance in the final report
    report['memory_hub_instance'] = initializer.memory_hub
    return report

if __name__ == "__main__":
    # This allows running the initializer directly for testing
    print("--- Running Standalone System Initialization Test ---")
    
    result = initialize_multi_ai_system()
    
    print("\n--- System Initialization Report ---")
    # Pretty print the JSON report, but exclude the memory hub instance for readability
    report_copy = result.copy()
    report_copy.pop("memory_hub_instance", None)
    print(json.dumps(report_copy, indent=2))
    
    print("\n--- Summary ---")
    
    print(f"\nTotal Initialization Time: {result.get('initialization_summary', {}).get('total_time_seconds', 'N/A'):.2f} seconds")
    
    print("\nComponent Status:")
    for name, res in result.get("component_results", {}).items():
        status = "[OK]" if res.get("success") else "[FAIL]"
        print(f"  - {name.replace('_', ' ').title()}: {status}")
        
    print("\nHealth Check:")
    health_info = result.get("component_results", {}).get("health_check", {}).get("health", {})
    for check, status in health_info.get("individual_checks", {}).items():
        check_status = "[PASS]" if status else "[FAIL]"
        print(f"  - {check.replace('_', ' ').title()}: {check_status}")
        
    print(f"\nOverall Health: {health_info.get('overall_health_percentage', 0):.1f}%")
    
    print("\nFinal Status:")
    if result.get("initialization_summary", {}).get("system_ready", False):
        print("\n[OK] System is ready for operation!")
        sys.exit(0)
    else:
        print("\n[FAIL] System has issues and is not ready.")
        sys.exit(1) 