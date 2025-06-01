from typing import Dict, List, Tuple
from ..config import get_llm
from ..agent_temperatures import AGENT_TEMPERATURES
from ..monitoring import log_global

def validate_temperature_management() -> Dict[str, bool]:
    """Validate temperature management across all agents."""
    results = {}
    
    try:
        llm = get_llm()
        
        for agent_name, expected_temp in AGENT_TEMPERATURES.items():
            try:
                # Test temperature binding
                if hasattr(llm, 'with_temperature'):
                    bound_llm = llm.with_temperature(expected_temp)
                else:
                    bound_llm = llm.bind(temperature=expected_temp)
                
                # Validate the binding
                actual_temp = getattr(bound_llm, 'temperature', None)
                
                if actual_temp is not None:
                    temp_match = abs(actual_temp - expected_temp) < 0.001
                    results[agent_name] = temp_match
                    
                    if not temp_match:
                        log_global(
                            f"Temperature mismatch for {agent_name}: expected {expected_temp}, got {actual_temp}",
                            "WARNING"
                        )
                else:
                    log_global(f"Could not verify temperature for {agent_name}", "WARNING")
                    results[agent_name] = False
                    
            except Exception as e:
                log_global(f"Temperature binding failed for {agent_name}: {e}", "ERROR")
                results[agent_name] = False
        
        # Log summary
        passed = sum(results.values())
        total = len(results)
        log_global(f"Temperature validation: {passed}/{total} agents passed")
        
        return results
        
    except Exception as e:
        log_global(f"Temperature validation failed: {e}", "ERROR")
        return {}

def get_temperature_summary() -> List[Tuple[str, float, bool]]:
    """Get a summary of temperature settings and their validation status."""
    validation_results = validate_temperature_management()
    
    summary = []
    for agent_name, temp in AGENT_TEMPERATURES.items():
        is_valid = validation_results.get(agent_name, False)
        summary.append((agent_name, temp, is_valid))
    
    return summary

def print_temperature_report():
    """Print a detailed temperature management report."""
    print("\n" + "="*60)
    print("TEMPERATURE MANAGEMENT REPORT")
    print("="*60)
    
    summary = get_temperature_summary()
    
    for agent_name, temp, is_valid in summary:
        status = "✅ VALID" if is_valid else "❌ INVALID"
        print(f"{agent_name:<30} | Temp: {temp:<4} | {status}")
    
    total_valid = sum(1 for _, _, valid in summary if valid)
    total_agents = len(summary)
    
    print("-"*60)
    print(f"Total: {total_valid}/{total_agents} agents with valid temperature binding")
    print("="*60)

if __name__ == "__main__":
    print_temperature_report()