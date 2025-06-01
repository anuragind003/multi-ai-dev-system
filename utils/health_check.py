from typing import Dict, Any
import os
import sys
from pathlib import Path
import monitoring
from config import get_llm, get_embedding_model
from agent_temperatures import AGENT_TEMPERATURES, print_temperature_summary, get_simple_temperatures_dict

def check_system_health() -> Dict[str, Any]:
    """Comprehensive system health check."""
    health_report = {
        "status": "healthy",
        "checks": {},
        "warnings": [],
        "errors": []
    }
    
    # Check Python version
    python_version = sys.version_info
    if python_version < (3, 8):
        health_report["errors"].append(f"Python {python_version} is too old. Requires Python 3.8+")
        health_report["status"] = "unhealthy"
    else:
        health_report["checks"]["python_version"] = f"{python_version.major}.{python_version.minor}.{python_version.micro}"
    
    # Check environment variables
    required_env_vars = ["GEMINI_API_KEY", "LLM_PROVIDER"]
    missing_env_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_env_vars:
        health_report["errors"].extend([f"Missing environment variable: {var}" for var in missing_env_vars])
        health_report["status"] = "unhealthy"
    else:
        health_report["checks"]["environment"] = "All required environment variables present"
    
    # Check directories
    required_dirs = ["output", "brds", "agents", "tools"]
    missing_dirs = [dir_name for dir_name in required_dirs if not os.path.exists(dir_name)]
    if missing_dirs:
        health_report["warnings"].extend([f"Missing directory: {dir_name}" for dir_name in missing_dirs])
    else:
        health_report["checks"]["directories"] = "All required directories exist"
    
    # Check LLM connectivity
    try:
        llm = get_llm()
        test_response = llm.invoke("Test connection")
        health_report["checks"]["llm_connection"] = "LLM connection successful"
    except Exception as e:
        health_report["errors"].append(f"LLM connection failed: {e}")
        health_report["status"] = "unhealthy"
    
    # Check embeddings
    try:
        embeddings = get_embedding_model()
        test_embedding = embeddings.embed_query("test")
        health_report["checks"]["embeddings"] = f"Embeddings working (dimension: {len(test_embedding)})"
    except Exception as e:
        health_report["warnings"].append(f"Embeddings issue: {e}")
    
    # Check agent temperature configuration
    agent_files = [f for f in os.listdir("agents") if f.endswith(".py") and f != "__init__.py"]
    agent_names = [f[:-3] for f in agent_files]  # Remove .py extension

    # Use the simple temperatures dict for compatibility
    simple_temps = get_simple_temperatures_dict()
    unconfigured_agents = [name for name in agent_names if name not in simple_temps]
    if unconfigured_agents:
        health_report["warnings"].extend([f"Agent temperature not configured: {name}" for name in unconfigured_agents])

    health_report["checks"]["agent_temperatures"] = f"{len(simple_temps)} agents configured"
    
    return health_report

def run_startup_checks():
    """Run all startup checks and print results."""
    print("🔍 Running System Health Check...")
    print("=" * 50)
    
    health = check_system_health()
    
    # Print checks
    for check_name, result in health["checks"].items():
        print(f"✅ {check_name}: {result}")
    
    # Print warnings
    for warning in health["warnings"]:
        print(f"⚠️  WARNING: {warning}")
    
    # Print errors
    for error in health["errors"]:
        print(f"❌ ERROR: {error}")
    
    print("=" * 50)
    print(f"Overall Status: {'✅ HEALTHY' if health['status'] == 'healthy' else '❌ UNHEALTHY'}")
    
    if health["status"] == "unhealthy":
        print("⚠️  Please fix the errors above before running the system.")
        return False
    
    # Print temperature configuration
    print_temperature_summary()
    
    return True

if __name__ == "__main__":
    success = run_startup_checks()
    sys.exit(0 if success else 1)