"""
Integration patch to update existing monitoring.py to use the enhanced logging system
"""

def patch_monitoring():
    """Patch the existing monitoring module to use enhanced logging."""
    
    # Import both systems
    import monitoring
    from enhanced_logging_system import (
        log_agent_activity as enhanced_log_agent_activity,
        log_api_call as enhanced_log_api_call,
        log_workflow_event,
        log_error,
        get_logging_system
    )
    
    # Store original functions for fallback
    original_log_agent_activity = monitoring.log_agent_activity
    original_log_api_call_realtime = monitoring.log_api_call_realtime
    original_log_global = monitoring.log_global
    
    # Replace monitoring functions with enhanced versions
    def patched_log_agent_activity(agent_name: str, message: str, level: str = "INFO", metadata=None):
        """Enhanced agent activity logging with fallback."""
        try:
            enhanced_log_agent_activity(agent_name, message, level, metadata)
        except Exception as e:
            # Fallback to original if enhanced logging fails
            print(f"Enhanced logging failed: {e}, falling back to original")
            original_log_agent_activity(agent_name, message, level, metadata)
    
    def patched_log_api_call(model: str, call_type: str, input_preview: str, 
                           output_preview: str = "", duration: float = 0.0,
                           success: bool = True, error_msg: str = "",
                           temperature=None, agent_context: str = ""):
        """Enhanced API call logging with fallback."""
        try:
            metadata = {
                "input_preview": input_preview[:100],
                "output_preview": output_preview[:100],
                "temperature": temperature,
                "agent_context": agent_context
            }
            enhanced_log_api_call(model, call_type, duration, success, error_msg, metadata)
        except Exception as e:
            # Fallback to original
            print(f"Enhanced API logging failed: {e}, falling back to original")
            original_log_api_call_realtime(model, call_type, input_preview, output_preview,
                                         duration, success, error_msg, temperature, agent_context)
    
    def patched_log_global(message: str, level: str = "INFO"):
        """Enhanced global logging with fallback."""
        try:
            log_workflow_event(message, level)
        except Exception as e:
            # Fallback to original
            print(f"Enhanced global logging failed: {e}, falling back to original")
            original_log_global(message, level)
    
    # Monkey patch the monitoring module
    monitoring.log_agent_activity = patched_log_agent_activity
    monitoring.log_api_call_realtime = patched_log_api_call
    monitoring.log_global = patched_log_global
    
    print("✅ Enhanced logging system integrated with existing monitoring")

if __name__ == "__main__":
    patch_monitoring()
