"""
WebSocket-aware callback handler for LangChain agents
Broadcasts agent reasoning steps to connected WebSocket clients
"""
from langchain.callbacks.base import BaseCallbackHandler
from typing import Any, Dict, List, Optional, Union
import asyncio
import logging
from datetime import datetime
import uuid
import json

from app.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

class WebSocketCallbackHandler(BaseCallbackHandler):
    """
    Callback handler that sends agent events to WebSocket clients
    while also providing console output for local debugging
    """
    
    def __init__(self, session_id: str = None, agent_name: str = "Unknown Agent"):
        super().__init__()
        self.session_id = session_id or str(uuid.uuid4())
        self.agent_name = agent_name
        self.step_count = 0
        
    def _serialize_for_log(self, data: Any) -> str:
        """Safely serialize data for logging, handling various types."""
        if isinstance(data, str):
            return data
        if isinstance(data, dict) or isinstance(data, list):
            try:
                return json.dumps(data, indent=2)
            except TypeError:
                return str(data) # Fallback for non-serializable objects
        return str(data)
    
    def _safe_async_run(self, coro):
        """Safely run async code from sync callback, managing event loops."""
        try:
            # Check if there's a running event loop in the current thread
            loop = asyncio.get_running_loop()
            # If so, schedule the coroutine to run on it
            loop.create_task(coro)
        except RuntimeError:
            # If there's no running loop, create a new one just for this coroutine.
            # This is common when callbacks are invoked from a synchronous context in a separate thread.
            asyncio.run(coro)
        except Exception as e:
            logger.error(f"Error in WebSocket callback: {e}")
    
    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> Any:
        """Called when LLM starts generating"""
        self.step_count += 1
        message = f"[STEP {self.step_count}] {self.agent_name} is thinking..."
        print(f"🤔 {message}")
        
        self._safe_async_run(
            websocket_manager.send_agent_thinking(
                self.session_id, self.agent_name, message
            )
        )
    
    def on_llm_end(self, response: Any, **kwargs: Any) -> Any:
        """Called when LLM finishes generating"""
        message = f"[STEP {self.step_count}] {self.agent_name} completed reasoning"
        print(f"✅ {message}")
        
        # Extract the actual response text
        if hasattr(response, 'generations') and response.generations:
            if hasattr(response.generations[0][0], 'text'):
                reasoning = response.generations[0][0].text
                
                self._safe_async_run(
                    websocket_manager.send_agent_thinking(
                        self.session_id, self.agent_name, f"Reasoning: {reasoning}"
                    )
                )
    
    def on_llm_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> Any:
        """Called when LLM encounters an error"""
        error_msg = f"LLM Error in {self.agent_name}: {str(error)}"
        print(f"❌ {error_msg}")
        
        self._safe_async_run(
            websocket_manager.send_error(self.session_id, error_msg, self.agent_name)
        )
    
    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> Any:
        """Called when a tool starts executing"""
        tool_name = serialized.get("name", "Unknown Tool")
        input_log = self._serialize_for_log(input_str)
        message = f"[STEP {self.step_count}] Using tool: {tool_name}"
        print(f"🔧 {message}")
        print(f"   Input: {input_log}")
        
        self._safe_async_run(
            websocket_manager.send_agent_action(
                self.session_id, self.agent_name, tool_name, f"INPUT: {input_log}"
            )
        )
    
    def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        """Called when a tool finishes executing"""
        output_log = self._serialize_for_log(output)
        message = f"[STEP {self.step_count}] Tool completed"
        print(f"✅ {message}")
        print(f"   Output: {output_log[:200]}{'...' if len(output_log) > 200 else ''}")
        
        # Get tool name from kwargs if available
        tool_name = kwargs.get("name", "Unknown Tool")
        
        self._safe_async_run(
            websocket_manager.send_tool_result(
                self.session_id, self.agent_name, tool_name, f"OUTPUT: {output_log}"
            )
        )
    
    def on_tool_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> Any:
        """Called when a tool encounters an error"""
        error_msg = f"Tool Error in {self.agent_name}: {str(error)}"
        print(f"❌ {error_msg}")
        
        self._safe_async_run(
            websocket_manager.send_error(self.session_id, error_msg, self.agent_name)
        )
    
    def on_text(self, text: str, **kwargs: Any) -> Any:
        """Called when agent outputs text"""
        # Filter out some verbose intermediate outputs
        if any(skip in text.lower() for skip in ["entering new", "finished chain", "entering new agentexecutor"]):
            return
            
        print(f"💭 {self.agent_name}: {text}")
        
        self._safe_async_run(
            websocket_manager.send_agent_thinking(
                self.session_id, self.agent_name, text
            )
        )
    
    def on_agent_action(self, action: Any, **kwargs: Any) -> Any:
        """Called when agent decides on an action"""
        tool_name = action.tool if hasattr(action, 'tool') else "Unknown Tool"
        tool_input = self._serialize_for_log(getattr(action, 'tool_input', ''))
        
        message = f"[STEP {self.step_count}] {self.agent_name} decided to use: {tool_name}"
        print(f"🎯 {message}")
        
        self._safe_async_run(
            websocket_manager.send_agent_action(
                self.session_id, self.agent_name, tool_name, tool_input
            )
        )
    
    def on_agent_finish(self, finish: Any, **kwargs: Any) -> Any:
        """Called when agent finishes"""
        message = f"{self.agent_name} completed successfully"
        print(f"🎉 {message}")
        
        result_log = self._serialize_for_log(getattr(finish, 'return_values', {}))
        
        self._safe_async_run(
            websocket_manager.send_agent_completed(
                self.session_id, self.agent_name, result_log
            )
        )
    
    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> Any:
        """Called when a chain starts"""
        if not serialized:
            # Silently return without warning - this is normal for some LangChain operations
            return
            
        chain_name = serialized.get("name", "Unknown Chain")
        if chain_name != "AgentExecutor":  # Avoid spam from executor
            message = f"Starting {chain_name}"
            print(f"🔄 {message}")
            
            self._safe_async_run(
                websocket_manager.send_workflow_status(
                    self.session_id, "chain_start", message, {"chain": chain_name}
                )
            )
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> Any:
        """Called when a chain ends"""
        # Only log significant chain completions
        pass
    
    def on_chain_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> Any:
        """Called when a chain encounters an error"""
        error_msg = f"Chain Error in {self.agent_name}: {str(error)}"
        print(f"❌ {error_msg}")
        
        self._safe_async_run(
            websocket_manager.send_error(self.session_id, error_msg, self.agent_name)
        )


def create_websocket_callback(session_id: str = None, agent_name: str = "Agent") -> WebSocketCallbackHandler:
    """
    Factory function to create a WebSocket callback handler
    """
    return WebSocketCallbackHandler(session_id=session_id, agent_name=agent_name) 