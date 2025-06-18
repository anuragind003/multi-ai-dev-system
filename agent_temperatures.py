"""
Centralized temperature configuration for all agents.
This allows easy tuning of agent behavior from one location.
"""

# Agent temperature settings with rationale
AGENT_TEMPERATURES = {
    # Analysis and planning agents
    "BRD Analyst Agent": {
        "temperature": 0.3,
        "rationale": "Creative task requiring synthesis of business requirements"
    },
    "Tech Stack Advisor Agent": {
        "temperature": 0.2,
        "rationale": "Analytical task requiring precision in technology selection"
    },
    "System Designer Agent": {
        "temperature": 0.2,
        "rationale": "Analytical task with defined architecture patterns"
    },
    "Project Analyzer Agent": {
        "temperature": 0.3,
        "rationale": "Balance between analysis and creative problem-solving"
    },
    "Timeline Estimator Agent": {
        "temperature": 0.2,
        "rationale": "Requires flexibility in timeline estimation"
    },
    "Risk Assessor Agent": {
        "temperature": 0.2,
        "rationale": "Analytical task focused on risk identification"
    },
    "Plan Compiler Agent": {
        "temperature": 0.2,
        "rationale": "Synthesizes plans from multiple sources"
    },
    
    # Code generation agents
    "Architecture Generator Agent": {
        "temperature": 0.1,
        "rationale": "Code generation requiring consistency and precision"
    },
    "Database Generator Agent": {
        "temperature": 0.1,
        "rationale": "Schema generation requiring precision"
    },
    "Backend Generator Agent": {
        "temperature": 0.1,
        "rationale": "Code generation requiring consistency and precision"
    },
    "Frontend Generator Agent": {
        "temperature": 0.1,
        "rationale": "Code generation requiring consistency and precision"
    },
    "Integration Generator Agent": {
        "temperature": 0.1,
        "rationale": "Code generation requiring consistency and precision"
    },
    "Code Optimizer Agent": {
        "temperature": 0.1,
        "rationale": "Code refactoring requiring deterministic output"
    },
    
    # Testing and validation agents
    "Test Case Generator Agent": {
        "temperature": 0.2,
        "rationale": "Balances coverage with creative test scenarios"
    },
    "Code Quality Agent": {
        "temperature": 0.1,
        "rationale": "Analysis task requiring precision in issue detection"
    },
    "Test Validation Agent": {
        "temperature": 0.1,
        "rationale": "Analytical task requiring precise test evaluation"    },
    "Code Generator Agent": {
        "temperature": 0.1,
        "rationale": "Deterministic code generation requiring consistency"
    },
    "Code Generation Agent": {
        "temperature": 0.1,
        "rationale": "Deterministic code generation requiring consistency"
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
    """
    return {agent_name: config["temperature"] for agent_name, config in AGENT_TEMPERATURES.items()}

def print_temperature_summary():
    """Print summary of all agent temperature settings."""
    print("\n🌡️  Agent Temperature Configuration:")
    print("=" * 60)
    for agent_name, config in AGENT_TEMPERATURES.items():
        temp = config["temperature"]
        rationale = config["rationale"]
        print(f"  {agent_name:30} | {temp:3.1f} | {rationale}")
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

def get_default_temperatures() -> dict:
    """
    Returns the default temperature settings for all AI agents in the system.
    
    This function implements our temperature strategy:
    - Analytical tasks (0.1-0.2): Code quality, test validation, tech recommendations
    - Creative tasks (0.3-0.4): BRD analysis, planning, test case generation
    - Code generation (0.1): Deterministic, consistent code output
    
    Returns:
        dict: A dictionary mapping agent names to their optimal temperature settings
    """
    return {
        # Analytical agents (lower temperature for precision)
        "Tech Stack Advisor Agent": 0.2,
        "Code Quality Agent": 0.1,
        "Test Validation Agent": 0.1,
        "Risk Assessor Agent": 0.2,      # ADDED: Missing agent
        
        # Planning and analysis agents (balanced temperatures)
        "Project Analyzer Agent": 0.2,    # ADDED: Missing agent
        "Timeline Estimator Agent": 0.2,  # ADDED: Missing agent
        "Plan Compiler Agent": 0.2,       # ADDED: Missing agent
        
        # Creative agents (higher temperature for exploration)
        "BRD Analyst Agent": 0.3,
        "Planning Agent": 0.4,
        "Test Case Generator Agent": 0.2,
        "System Designer Agent": 0.3,
          # Code generation agents (lowest temperature for consistency)
        "Code Generator Agent": 0.1,
        "Code Generation Agent": 0.1,  # Added the essential agent that was missing
        "Architecture Generator Agent": 0.1,
        "Database Generator Agent": 0.1,
        "Backend Generator Agent": 0.1,
        "Frontend Generator Agent": 0.1,
        "Integration Generator Agent": 0.1,
        "Code Optimizer Agent": 0.1,
        
        # Default for any other agent
        "default": 0.2
    }

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