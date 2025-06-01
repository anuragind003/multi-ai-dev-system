"""
Centralized temperature configuration for all agents.
This allows easy tuning of agent behavior from one location.
"""

# Agent temperature settings with rationale
AGENT_TEMPERATURES = {
    # Analytical Agents (Low Temperature for Consistency)
    "brd_analyst": {
        "temperature": 0.3,
        "rationale": "Balanced analysis and extraction while maintaining structure"
    },
    "tech_stack_advisor": {
        "temperature": 0.2, 
        "rationale": "Precise technical recommendations based on established patterns"
    },
    "system_designer": {
        "temperature": 0.2,
        "rationale": "Structured architectural decisions following industry standards"
    },
    "code_generation": {
        "temperature": 0.1,
        "rationale": "Deterministic, consistent code following patterns"
    },
    "code_quality_agent": {
        "temperature": 0.1,
        "rationale": "Objective, factual quality assessment"
    },
    "test_validation_agent": {
        "temperature": 0.1,
        "rationale": "Factual test result analysis and reporting"
    },
    "base_agent": {
        "temperature": 0.2,
        "rationale": "Default base agent for general tasks"
    },
    
    # Creative Agents (Higher Temperature for Innovation)
    "planning_agent": {
        "temperature": 0.4,
        "rationale": "Creative planning and timeline estimation"
    },
    "test_case_generator": {
        "temperature": 0.2,
        "rationale": "Creative test scenarios while maintaining structure"
    }
}

def get_agent_temperature(agent_name: str) -> float:
    """Get temperature for a specific agent."""
    config = AGENT_TEMPERATURES.get(agent_name)
    if config:
        return config["temperature"]
    
    # Default temperature if agent not configured
    print(f"Warning: No temperature configured for agent '{agent_name}', using default 0.2")
    return 0.2

def get_temperature_rationale(agent_name: str) -> str:
    """Get rationale for an agent's temperature setting."""
    config = AGENT_TEMPERATURES.get(agent_name)
    if config:
        return config["rationale"]
    return "Default temperature setting"

def list_agent_temperatures() -> dict:
    """
    Return a dictionary of agent names and their temperature values.
    This function was missing and causing the import error.
    """
    return {agent_name: config["temperature"] for agent_name, config in AGENT_TEMPERATURES.items()}

def print_temperature_summary():
    """Print summary of all agent temperature settings."""
    print("\n🌡️  Agent Temperature Configuration:")
    print("=" * 60)
    for agent_name, config in AGENT_TEMPERATURES.items():
        temp = config["temperature"]
        rationale = config["rationale"]
        print(f"  {agent_name:20} | {temp:3.1f} | {rationale}")
    print("=" * 60)

def validate_agent_temperatures():
    """Validate that all temperature values are within acceptable ranges."""
    issues = []
    
    for agent_name, config in AGENT_TEMPERATURES.items():
        temp = config["temperature"]
        
        if not isinstance(temp, (int, float)):
            issues.append(f"{agent_name}: Temperature must be a number, got {type(temp)}")
        elif temp < 0.0 or temp > 2.0:
            issues.append(f"{agent_name}: Temperature {temp} is outside recommended range (0.0-2.0)")
        elif temp > 1.0:
            issues.append(f"{agent_name}: Temperature {temp} is high - may cause unpredictable outputs")
    
    return issues

# Add this for backward compatibility with health_check.py
def get_simple_temperatures_dict():
    """Return simplified dict for compatibility with health check."""
    return {agent_name: config["temperature"] for agent_name, config in AGENT_TEMPERATURES.items()}

# Validate temperatures on import
_validation_issues = validate_agent_temperatures()
if _validation_issues:
    print("⚠️  Agent temperature validation issues:")
    for issue in _validation_issues:
        print(f"   - {issue}")