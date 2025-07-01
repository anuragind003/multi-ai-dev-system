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
        
    def _safe_async_run(self, coro):
        """Safely run async code from sync callback"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, schedule the coroutine
                asyncio.create_task(coro)
            else:
                loop.run_until_complete(coro)
        except Exception as e:
            logger.error(f"Error in WebSocket callback: {e}")
    
    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> Any:
        """Called when LLM starts generating"""
        self.step_count += 1
        message = f"[STEP {self.step_count}] {self.agent_name} is thinking..."
        print(f"🤔 {message}")
        
        from multi_ai_dev_system.app.websocket_manager import websocket_manager
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
                
                from multi_ai_dev_system.app.websocket_manager import websocket_manager
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
        
        from multi_ai_dev_system.app.websocket_manager import websocket_manager
        self._safe_async_run(
            websocket_manager.send_error(self.session_id, error_msg, self.agent_name)
        )
    
    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> Any:
        """Called when a tool starts executing"""
        tool_name = serialized.get("name", "Unknown Tool")
        message = f"[STEP {self.step_count}] Using tool: {tool_name}"
        print(f"🔧 {message}")
        print(f"   Input: {input_str}")
        
        from multi_ai_dev_system.app.websocket_manager import websocket_manager
        self._safe_async_run(
            websocket_manager.send_agent_action(
                self.session_id, self.agent_name, tool_name, input_str
            )
        )
    
    def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        """Called when a tool finishes executing"""
        message = f"[STEP {self.step_count}] Tool completed"
        print(f"✅ {message}")
        print(f"   Output: {output[:200]}{'...' if len(output) > 200 else ''}")
        
        # Get tool name from kwargs if available
        tool_name = kwargs.get("name", "Unknown Tool")
        
        from multi_ai_dev_system.app.websocket_manager import websocket_manager
        self._safe_async_run(
            websocket_manager.send_tool_result(
                self.session_id, self.agent_name, tool_name, output
            )
        )
    
    def on_tool_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> Any:
        """Called when a tool encounters an error"""
        error_msg = f"Tool Error in {self.agent_name}: {str(error)}"
        print(f"❌ {error_msg}")
        
        from multi_ai_dev_system.app.websocket_manager import websocket_manager
        self._safe_async_run(
            websocket_manager.send_error(self.session_id, error_msg, self.agent_name)
        )
    
    def on_text(self, text: str, **kwargs: Any) -> Any:
        """Called when agent outputs text"""
        # Filter out some verbose intermediate outputs
        if any(skip in text.lower() for skip in ["entering new", "finished chain", "entering new agentexecutor"]):
            return
            
        print(f"💭 {self.agent_name}: {text}")
        
        from multi_ai_dev_system.app.websocket_manager import websocket_manager
        self._safe_async_run(
            websocket_manager.send_agent_thinking(
                self.session_id, self.agent_name, text
            )
        )
    
    def on_agent_action(self, action: Any, **kwargs: Any) -> Any:
        """Called when agent decides on an action"""
        tool_name = action.tool if hasattr(action, 'tool') else str(action)
        tool_input = action.tool_input if hasattr(action, 'tool_input') else ""
        
        message = f"[STEP {self.step_count}] {self.agent_name} decided to use: {tool_name}"
        print(f"🎯 {message}")
        
        from multi_ai_dev_system.app.websocket_manager import websocket_manager
        self._safe_async_run(
            websocket_manager.send_agent_action(
                self.session_id, self.agent_name, tool_name, str(tool_input)
            )
        )
    
    def on_agent_finish(self, finish: Any, **kwargs: Any) -> Any:
        """Called when agent finishes"""
        message = f"{self.agent_name} completed successfully"
        print(f"🎉 {message}")
        
        result = {}
        if hasattr(finish, 'return_values'):
            result = finish.return_values
        elif hasattr(finish, 'output'):
            result = {"output": finish.output}
        
        from multi_ai_dev_system.app.websocket_manager import websocket_manager
        self._safe_async_run(
            websocket_manager.send_agent_completed(
                self.session_id, self.agent_name, result
            )
        )
    
    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> Any:
        """Called when a chain starts"""
        chain_name = serialized.get("name", "Unknown Chain")
        if chain_name != "AgentExecutor":  # Avoid spam from executor
            message = f"Starting {chain_name}"
            print(f"🔄 {message}")
            
            from multi_ai_dev_system.app.websocket_manager import websocket_manager
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
        
        from multi_ai_dev_system.app.websocket_manager import websocket_manager
        self._safe_async_run(
            websocket_manager.send_error(self.session_id, error_msg, self.agent_name)
        )


def create_websocket_callback(session_id: str = None, agent_name: str = "Agent") -> WebSocketCallbackHandler:
    """
    Factory function to create a WebSocket callback handler
    """
    return WebSocketCallbackHandler(session_id=session_id, agent_name=agent_name) 