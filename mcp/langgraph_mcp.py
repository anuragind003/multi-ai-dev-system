"""
LangGraph-native MCP (Model Context Protocol) Integration
Provides seamless MCP server integration within LangGraph workflows.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass
from enum import Enum

try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.sqlite import SqliteSaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    # Mock classes for when LangGraph isn't available
    class StateGraph:
        def __init__(self, state_class): pass
        def add_node(self, name, func): pass
        def add_edge(self, start, end): pass
        def add_conditional_edges(self, start, condition): pass
    START = "START"
    END = "END"
    SqliteSaver = None

try:
    from langchain_core.tools import tool
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    # Mock classes
    class BaseMessage: pass
    class HumanMessage: pass
    class AIMessage: pass
    def tool(func): return func

from pydantic import BaseModel, Field

# MCP imports
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    # Mock classes
    class ClientSession: pass
    class StdioServerParameters: pass
    stdio_client = None

logger = logging.getLogger(__name__)

class MCPServerType(Enum):
    """Types of MCP servers for LangGraph integration."""
    FILESYSTEM = "filesystem"
    DATABASE = "database"
    GIT = "git"
    IDE = "ide"
    BROWSER = "browser"
    TERMINAL = "terminal"
    API = "api"

@dataclass
class MCPServerConfig:
    """Configuration for MCP servers in LangGraph."""
    name: str
    server_type: MCPServerType
    command: str
    args: List[str]
    enabled: bool = True
    timeout: int = 30
    max_retries: int = 3

class MCPState(BaseModel):
    """State for MCP operations in LangGraph."""
    messages: List[BaseMessage] = Field(default_factory=list)
    mcp_servers: Dict[str, Any] = Field(default_factory=dict)
    current_operation: Optional[str] = None
    operation_results: Dict[str, Any] = Field(default_factory=dict)
    error_context: Optional[str] = None

class LangGraphMCPManager:
    """LangGraph-native MCP server manager."""
    
    def __init__(self):
        self.servers: Dict[str, MCPServerConfig] = {}
        self.active_sessions: Dict[str, ClientSession] = {}
        self.config_file = Path("mcp/langgraph_mcp_config.json")
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize MCP servers for LangGraph."""
        try:
            logger.info("Initializing LangGraph MCP Manager")
            
            # Ensure config directory exists
            self.config_file.parent.mkdir(exist_ok=True)
            
            # Load or create configuration
            await self.load_configuration()
            
            # Initialize enabled servers
            await self.initialize_servers()
            
            self.is_initialized = True
            logger.info("LangGraph MCP Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize LangGraph MCP Manager: {e}")
            raise
    
    async def load_configuration(self):
        """Load MCP configuration for LangGraph."""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
            
            for server_data in config_data.get("servers", []):
                config = MCPServerConfig(
                    name=server_data["name"],
                    server_type=MCPServerType(server_data["server_type"]),
                    command=server_data["command"],
                    args=server_data.get("args", []),
                    enabled=server_data.get("enabled", True),
                    timeout=server_data.get("timeout", 30),
                    max_retries=server_data.get("max_retries", 3)
                )
                self.servers[config.name] = config
        else:
            # Create default configuration
            await self.create_default_config()
    
    async def create_default_config(self):
        """Create default MCP configuration for LangGraph."""
        default_config = {
            "servers": [
                {
                    "name": "filesystem",
                    "server_type": "filesystem",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
                    "enabled": True
                },
                {
                    "name": "git",
                    "server_type": "git", 
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-git", "--repository", "."],
                    "enabled": True
                },
                {
                    "name": "sqlite",
                    "server_type": "database",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-sqlite", "--db-path", "./data/project.db"],
                    "enabled": False
                },
                {
                    "name": "browser",
                    "server_type": "browser",
                    "command": "npx", 
                    "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
                    "enabled": False
                }
            ]
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        logger.info(f"Created default LangGraph MCP configuration: {self.config_file}")
        
        # Load the newly created config
        await self.load_configuration()
    
    async def initialize_servers(self):
        """Initialize enabled MCP servers."""
        for name, config in self.servers.items():
            if config.enabled:
                try:
                    await self.connect_server(name)
                    logger.info(f"Successfully connected to MCP server: {name}")
                except Exception as e:
                    logger.error(f"Failed to connect to MCP server {name}: {e}")
    
    async def connect_server(self, server_name: str) -> bool:
        """Connect to a specific MCP server."""
        if server_name not in self.servers:
            logger.error(f"MCP server {server_name} not configured")
            return False
        
        config = self.servers[server_name]
        
        try:
            # Create server parameters
            server_params = StdioServerParameters(
                command=config.command,
                args=config.args
            )
            
            # Create and store client session
            async with stdio_client(server_params) as (read, write):
                session = ClientSession(read, write)
                await session.initialize()
                
                self.active_sessions[server_name] = session
                return True
                
        except Exception as e:
            logger.error(f"Error connecting to MCP server {server_name}: {e}")
            return False
    
    async def disconnect_server(self, server_name: str):
        """Disconnect from an MCP server."""
        if server_name in self.active_sessions:
            try:
                session = self.active_sessions[server_name]
                # Close session if it has a close method
                if hasattr(session, 'close'):
                    await session.close()
                del self.active_sessions[server_name]
                logger.info(f"Disconnected from MCP server: {server_name}")
            except Exception as e:
                logger.error(f"Error disconnecting from MCP server {server_name}: {e}")
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on an MCP server."""
        if server_name not in self.active_sessions:
            raise Exception(f"MCP server {server_name} not connected")
        
        session = self.active_sessions[server_name]
        
        try:
            # Call the tool
            result = await session.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            logger.error(f"Error calling tool {tool_name} on server {server_name}: {e}")
            raise
    
    async def list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """List available tools on an MCP server."""
        if server_name not in self.active_sessions:
            raise Exception(f"MCP server {server_name} not connected")
        
        session = self.active_sessions[server_name]
        
        try:
            tools = await session.list_tools()
            return tools.tools if hasattr(tools, 'tools') else []
        except Exception as e:
            logger.error(f"Error listing tools for server {server_name}: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup all MCP connections."""
        logger.info("Cleaning up LangGraph MCP connections")
        
        for server_name in list(self.active_sessions.keys()):
            await self.disconnect_server(server_name)

# LangGraph MCP Tools
@tool
async def mcp_filesystem_read_file(file_path: str) -> str:
    """Read a file using MCP filesystem server."""
    manager = await get_langgraph_mcp_manager()
    
    try:
        result = await manager.call_tool("filesystem", "read_file", {"path": file_path})
        return result.get("content", "")
    except Exception as e:
        logger.error(f"MCP filesystem read error: {e}")
        return f"Error reading file: {e}"

@tool
async def mcp_filesystem_write_file(file_path: str, content: str) -> str:
    """Write content to a file using MCP filesystem server."""
    manager = await get_langgraph_mcp_manager()
    
    try:
        result = await manager.call_tool("filesystem", "write_file", {
            "path": file_path,
            "content": content
        })
        return "File written successfully"
    except Exception as e:
        logger.error(f"MCP filesystem write error: {e}")
        return f"Error writing file: {e}"

@tool
async def mcp_filesystem_list_directory(directory_path: str) -> str:
    """List directory contents using MCP filesystem server."""
    manager = await get_langgraph_mcp_manager()
    
    try:
        result = await manager.call_tool("filesystem", "list_directory", {"path": directory_path})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"MCP filesystem list error: {e}")
        return f"Error listing directory: {e}"

@tool
async def mcp_git_status() -> str:
    """Get Git status using MCP git server."""
    manager = await get_langgraph_mcp_manager()
    
    try:
        result = await manager.call_tool("git", "git_status", {})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"MCP git status error: {e}")
        return f"Error getting git status: {e}"

@tool
async def mcp_git_commit(message: str, files: List[str] = None) -> str:
    """Commit changes using MCP git server."""
    manager = await get_langgraph_mcp_manager()
    
    try:
        arguments = {"message": message}
        if files:
            arguments["files"] = files
        
        result = await manager.call_tool("git", "git_commit", arguments)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"MCP git commit error: {e}")
        return f"Error committing changes: {e}"

@tool
async def mcp_database_query(query: str) -> str:
    """Execute database query using MCP database server."""
    manager = await get_langgraph_mcp_manager()
    
    try:
        result = await manager.call_tool("sqlite", "execute_query", {"query": query})
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"MCP database query error: {e}")
        return f"Error executing query: {e}"

# LangGraph MCP Node Functions
async def mcp_filesystem_node(state: MCPState) -> MCPState:
    """LangGraph node for filesystem operations."""
    try:
        # Extract the last message to understand the request
        if state.messages:
            last_message = state.messages[-1]
            
            # This is a simplified example - you'd parse the actual request
            if "read file" in last_message.content.lower():
                # Extract file path from message (simplified)
                file_path = "example.txt"  # You'd parse this from the message
                content = await mcp_filesystem_read_file(file_path)
                
                state.operation_results["filesystem"] = {
                    "operation": "read_file",
                    "file_path": file_path,
                    "content": content
                }
                
                # Add response message
                response = AIMessage(content=f"File content: {content}")
                state.messages.append(response)
        
        return state
        
    except Exception as e:
        state.error_context = f"Filesystem operation failed: {e}"
        return state

async def mcp_git_node(state: MCPState) -> MCPState:
    """LangGraph node for git operations."""
    try:
        if state.messages:
            last_message = state.messages[-1]
            
            if "git status" in last_message.content.lower():
                status = await mcp_git_status()
                
                state.operation_results["git"] = {
                    "operation": "status",
                    "result": status
                }
                
                response = AIMessage(content=f"Git status: {status}")
                state.messages.append(response)
        
        return state
        
    except Exception as e:
        state.error_context = f"Git operation failed: {e}"
        return state

async def mcp_database_node(state: MCPState) -> MCPState:
    """LangGraph node for database operations."""
    try:
        if state.messages:
            last_message = state.messages[-1]
            
            if "database query" in last_message.content.lower():
                # Extract query (simplified)
                query = "SELECT 1"  # You'd parse this from the message
                result = await mcp_database_query(query)
                
                state.operation_results["database"] = {
                    "operation": "query",
                    "query": query,
                    "result": result
                }
                
                response = AIMessage(content=f"Query result: {result}")
                state.messages.append(response)
        
        return state
        
    except Exception as e:
        state.error_context = f"Database operation failed: {e}"
        return state

def create_mcp_graph() -> StateGraph:
    """Create a LangGraph workflow with MCP integration."""
    workflow = StateGraph(MCPState)
    
    # Add MCP nodes
    workflow.add_node("filesystem", mcp_filesystem_node)
    workflow.add_node("git", mcp_git_node)
    workflow.add_node("database", mcp_database_node)
    
    # Add routing logic (simplified)
    def route_mcp_operation(state: MCPState):
        if state.messages:
            last_message = state.messages[-1].content.lower()
            
            if any(word in last_message for word in ["file", "directory", "folder"]):
                return "filesystem"
            elif any(word in last_message for word in ["git", "commit", "branch"]):
                return "git" 
            elif any(word in last_message for word in ["database", "query", "sql"]):
                return "database"
        
        return END
    
    # Set up the graph flow
    workflow.add_conditional_edges(START, route_mcp_operation)
    workflow.add_edge("filesystem", END)
    workflow.add_edge("git", END)
    workflow.add_edge("database", END)
    
    return workflow

# Global manager instance
_langgraph_mcp_manager: Optional[LangGraphMCPManager] = None

async def get_langgraph_mcp_manager() -> LangGraphMCPManager:
    """Get the global LangGraph MCP manager instance."""
    global _langgraph_mcp_manager
    
    if _langgraph_mcp_manager is None:
        _langgraph_mcp_manager = LangGraphMCPManager()
        await _langgraph_mcp_manager.initialize()
    
    return _langgraph_mcp_manager

def get_mcp_tools() -> List[Callable]:
    """Get all MCP tools for agent integration."""
    return [
        mcp_filesystem_read_file,
        mcp_filesystem_write_file,
        mcp_filesystem_list_directory,
        mcp_git_status,
        mcp_git_commit,
        mcp_database_query
    ]

async def cleanup_langgraph_mcp():
    """Cleanup LangGraph MCP resources."""
    global _langgraph_mcp_manager
    
    if _langgraph_mcp_manager:
        await _langgraph_mcp_manager.cleanup()
        _langgraph_mcp_manager = None
