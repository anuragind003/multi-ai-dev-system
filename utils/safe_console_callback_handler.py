"""
Safe Console Callback Handler for LangChain Agents
Prevents I/O errors when stdout/stderr are closed or unavailable.
Enhanced to show detailed tool outputs for better debugging.
"""

import logging
import json
from typing import Dict, Any, List
from langchain.callbacks.base import BaseCallbackHandler
from .windows_safe_console import safe_print

class SafeConsoleCallbackHandler(BaseCallbackHandler):
    """A safe console callback handler that shows detailed tool outputs without I/O errors."""
    
    def __init__(self, show_detailed_outputs: bool = True, max_output_length: int = 2000):
        super().__init__()
        self.step_count = 0
        self.show_detailed_outputs = show_detailed_outputs
        self.max_output_length = max_output_length
    
    def safe_print(self, message: str, prefix: str = ""):
        """Safely print messages without crashing on I/O errors."""
        formatted_message = f"{prefix}{message}" if prefix else message
        # Use the Windows-safe console utility
        safe_print(formatted_message)
    
    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs) -> None:
        """Called when a chain starts running."""
        self.safe_print(f"\n[AGENT START] Agent is analyzing and planning...")
        if inputs and self.show_detailed_outputs:
            input_preview = str(inputs)[:200] + "..." if len(str(inputs)) > 200 else str(inputs)
            self.safe_print(f"   [INPUT] Input: {input_preview}")
    
    def on_agent_action(self, action, **kwargs) -> None:
        """Called when an agent action is taken."""
        self.step_count += 1
        tool_name = action.tool if hasattr(action, 'tool') else str(action)
        tool_input = action.tool_input if hasattr(action, 'tool_input') else ""
        
        self.safe_print(f"\n[STEP {self.step_count}] Calling tool: '{tool_name}'")
        
        if tool_input and self.show_detailed_outputs:
            # Try to format JSON inputs nicely
            try:
                if isinstance(tool_input, str):
                    # Try to parse as JSON for better formatting
                    try:
                        parsed_input = json.loads(tool_input)
                        formatted_input = json.dumps(parsed_input, indent=2)[:500]
                        self.safe_print(f"   [TOOL INPUT] Tool Input (JSON):\n{formatted_input}")
                    except:
                        # Not JSON, show as regular string
                        display_input = tool_input[:500] + "..." if len(tool_input) > 500 else tool_input
                        self.safe_print(f"   [TOOL INPUT] Tool Input: {display_input}")
                elif isinstance(tool_input, dict):
                    formatted_input = json.dumps(tool_input, indent=2, default=str)[:500]
                    self.safe_print(f"   [TOOL INPUT] Tool Input (Dict):\n{formatted_input}")
                else:
                    display_input = str(tool_input)[:500] + "..." if len(str(tool_input)) > 500 else str(tool_input)
                    self.safe_print(f"   [TOOL INPUT] Tool Input: {display_input}")
            except Exception as e:
                self.safe_print(f"   [TOOL INPUT] Tool Input: {str(tool_input)[:200]}...")
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        """Called when a tool starts."""
        tool_name = serialized.get("name", "unknown")
        self.safe_print(f"   [EXECUTING] Starting tool: {tool_name}")
    
    def on_tool_end(self, output: str, **kwargs) -> None:
        """Called when a tool finishes."""
        self.safe_print(f"   [TOOL COMPLETED] Tool finished execution")
        
        if self.show_detailed_outputs and output:
            # Show detailed tool output
            try:
                # Try to parse and format JSON outputs
                if output.strip().startswith('{') or output.strip().startswith('['):
                    try:
                        parsed_output = json.loads(output)
                        formatted_output = json.dumps(parsed_output, indent=2, default=str)
                        
                        if len(formatted_output) <= self.max_output_length:
                            self.safe_print(f"   [TOOL OUTPUT] Tool Output (JSON):\n{formatted_output}")
                        else:
                            # Show truncated version
                            truncated = formatted_output[:self.max_output_length] + "\n   ... (output truncated)"
                            self.safe_print(f"   [TOOL OUTPUT] Tool Output (JSON - truncated):\n{truncated}")
                    except json.JSONDecodeError:
                        # Not valid JSON, treat as text
                        if len(output) <= self.max_output_length:
                            self.safe_print(f"   [TOOL OUTPUT] Tool Output:\n{output}")
                        else:
                            truncated = output[:self.max_output_length] + "\n   ... (output truncated)"
                            self.safe_print(f"   [TOOL OUTPUT] Tool Output (truncated):\n{truncated}")
                else:
                    # Regular text output
                    if len(output) <= self.max_output_length:
                        self.safe_print(f"   [TOOL OUTPUT] Tool Output:\n{output}")
                    else:
                        truncated = output[:self.max_output_length] + "\n   ... (output truncated)"
                        self.safe_print(f"   [TOOL OUTPUT] Tool Output (truncated):\n{truncated}")
                        
            except Exception as e:
                # Fallback for any formatting errors
                display_output = output[:500] + "..." if len(output) > 500 else output
                self.safe_print(f"   [TOOL OUTPUT] Tool Output: {display_output}")
        else:
            # Just show a summary if detailed output is disabled
            summary = output[:100] + "..." if len(output) > 100 else output
            self.safe_print(f"   [TOOL RESULT] Tool Result: {summary}")
    
    def on_tool_error(self, error: Exception, **kwargs) -> None:
        """Called when a tool encounters an error."""
        self.safe_print(f"   [TOOL ERROR] Tool Error: {str(error)[:300]}")
    
    def on_agent_finish(self, finish, **kwargs) -> None:
        """Called when an agent finishes."""
        self.safe_print(f"\n[AGENT COMPLETED] Analysis finished successfully!")
        
        if self.show_detailed_outputs and hasattr(finish, 'return_values'):
            try:
                final_output = finish.return_values
                if isinstance(final_output, dict) and final_output:
                    formatted_final = json.dumps(final_output, indent=2, default=str)
                    if len(formatted_final) <= self.max_output_length:
                        self.safe_print(f"   [FINAL RESULT] Final Result:\n{formatted_final}")
                    else:
                        truncated = formatted_final[:self.max_output_length] + "\n   ... (result truncated)"
                        self.safe_print(f"   [FINAL RESULT] Final Result (truncated):\n{truncated}")
            except Exception as e:
                self.safe_print(f"   [FINAL RESULT] Final Result: {str(finish.return_values)[:200]}...")
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """Called when LLM starts."""
        self.safe_print(f"   [LLM] LLM thinking and reasoning...")
    
    def on_llm_end(self, response, **kwargs) -> None:
        """Called when LLM finishes."""
        self.safe_print(f"   [LLM] LLM completed reasoning")
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs) -> None:
        """Called when a chain ends."""
        self.safe_print(f"   [CHAIN] Chain execution completed")
        
        if self.show_detailed_outputs and outputs:
            try:
                formatted_outputs = json.dumps(outputs, indent=2, default=str)
                if len(formatted_outputs) <= 300:
                    self.safe_print(f"   [CHAIN OUTPUTS] Chain Outputs: {formatted_outputs}")
            except:
                pass
    
    def on_chain_error(self, error: Exception, **kwargs) -> None:
        """Called when a chain encounters an error."""
        self.safe_print(f"   [CHAIN ERROR] Chain Error: {str(error)[:300]}")


# Convenience factory functions
def create_detailed_callback(max_output_length: int = 2000) -> SafeConsoleCallbackHandler:
    """Create a callback handler that shows detailed tool outputs."""
    return SafeConsoleCallbackHandler(show_detailed_outputs=True, max_output_length=max_output_length)

def create_summary_callback() -> SafeConsoleCallbackHandler:
    """Create a callback handler that shows only summaries."""
    return SafeConsoleCallbackHandler(show_detailed_outputs=False, max_output_length=100) 