"""
MCP Tools for Multi-AI Development System.
Provides LangChain tools that connect to MCP servers for database, filesystem, IDE, and other operations.
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from .server_manager import get_mcp_manager, MCPResponse

logger = logging.getLogger(__name__)

# Pydantic models for tool inputs
class FileSystemInput(BaseModel):
    """Input for filesystem operations."""
    operation: str = Field(description="Operation: read, write, list, create_dir, delete")
    path: str = Field(description="File or directory path")
    content: Optional[str] = Field(default=None, description="Content for write operations")
    recursive: bool = Field(default=False, description="Recursive operation for directories")

class DatabaseInput(BaseModel):
    """Input for database operations."""
    operation: str = Field(description="Operation: query, execute, schema, tables")
    query: Optional[str] = Field(default=None, description="SQL query to execute")
    table: Optional[str] = Field(default=None, description="Table name for specific operations")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Query parameters")

class GitInput(BaseModel):
    """Input for Git operations."""
    operation: str = Field(description="Operation: status, add, commit, push, pull, branch, log")
    files: Optional[List[str]] = Field(default=None, description="Files for add/commit operations")
    message: Optional[str] = Field(default=None, description="Commit message")
    branch: Optional[str] = Field(default=None, description="Branch name")

class BrowserInput(BaseModel):
    """Input for browser automation."""
    operation: str = Field(description="Operation: navigate, click, type, screenshot, get_text")
    url: Optional[str] = Field(default=None, description="URL to navigate to")
    selector: Optional[str] = Field(default=None, description="CSS selector for element operations")
    text: Optional[str] = Field(default=None, description="Text to type")

# Filesystem Tools
@tool
async def mcp_filesystem_read_file(**kwargs) -> str:
    """Read a file using MCP filesystem server."""
    try:
        # Handle input from tool_input or direct parameters
        if 'tool_input' in kwargs:
            params = kwargs['tool_input']
        else:
            params = kwargs
        
        path = params.get('path', '')
        if not path:
            return "Error: No file path provided"
        
        mcp_manager = await get_mcp_manager()
        response = await mcp_manager.send_request(
            "filesystem",
            "files/read",
            {"path": path}
        )
        
        if response.error:
            return f"Error reading file: {response.error}"
        
        return response.result.get("content", "")
        
    except Exception as e:
        logger.error(f"Error in mcp_filesystem_read_file: {e}")
        return f"Error: {str(e)}"

@tool
async def mcp_filesystem_write_file(**kwargs) -> str:
    """Write content to a file using MCP filesystem server."""
    try:
        if 'tool_input' in kwargs:
            params = kwargs['tool_input']
        else:
            params = kwargs
        
        path = params.get('path', '')
        content = params.get('content', '')
        
        if not path:
            return "Error: No file path provided"
        
        mcp_manager = await get_mcp_manager()
        response = await mcp_manager.send_request(
            "filesystem",
            "files/write",
            {"path": path, "content": content}
        )
        
        if response.error:
            return f"Error writing file: {response.error}"
        
        return f"Successfully wrote to {path}"
        
    except Exception as e:
        logger.error(f"Error in mcp_filesystem_write_file: {e}")
        return f"Error: {str(e)}"

@tool
async def mcp_filesystem_list_directory(**kwargs) -> str:
    """List directory contents using MCP filesystem server."""
    try:
        if 'tool_input' in kwargs:
            params = kwargs['tool_input']
        else:
            params = kwargs
        
        path = params.get('path', '.')
        
        mcp_manager = await get_mcp_manager()
        response = await mcp_manager.send_request(
            "filesystem",
            "files/list",
            {"path": path}
        )
        
        if response.error:
            return f"Error listing directory: {response.error}"
        
        files = response.result.get("files", [])
        return json.dumps(files, indent=2)
        
    except Exception as e:
        logger.error(f"Error in mcp_filesystem_list_directory: {e}")
        return f"Error: {str(e)}"

@tool
async def mcp_filesystem_create_directory(**kwargs) -> str:
    """Create a directory using MCP filesystem server."""
    try:
        if 'tool_input' in kwargs:
            params = kwargs['tool_input']
        else:
            params = kwargs
        
        path = params.get('path', '')
        if not path:
            return "Error: No directory path provided"
        
        mcp_manager = await get_mcp_manager()
        response = await mcp_manager.send_request(
            "filesystem",
            "files/create_directory",
            {"path": path}
        )
        
        if response.error:
            return f"Error creating directory: {response.error}"
        
        return f"Successfully created directory: {path}"
        
    except Exception as e:
        logger.error(f"Error in mcp_filesystem_create_directory: {e}")
        return f"Error: {str(e)}"

# Database Tools
@tool
async def mcp_database_query(**kwargs) -> str:
    """Execute a database query using MCP database server."""
    try:
        if 'tool_input' in kwargs:
            params = kwargs['tool_input']
        else:
            params = kwargs
        
        query = params.get('query', '')
        parameters = params.get('parameters', {})
        
        if not query:
            return "Error: No SQL query provided"
        
        mcp_manager = await get_mcp_manager()
        response = await mcp_manager.send_request(
            "sqlite",
            "query",
            {"sql": query, "params": parameters}
        )
        
        if response.error:
            return f"Error executing query: {response.error}"
        
        result = response.result
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error in mcp_database_query: {e}")
        return f"Error: {str(e)}"

@tool
async def mcp_database_get_schema(**kwargs) -> str:
    """Get database schema using MCP database server."""
    try:
        mcp_manager = await get_mcp_manager()
        response = await mcp_manager.send_request(
            "sqlite",
            "schema",
            {}
        )
        
        if response.error:
            return f"Error getting schema: {response.error}"
        
        schema = response.result
        return json.dumps(schema, indent=2)
        
    except Exception as e:
        logger.error(f"Error in mcp_database_get_schema: {e}")
        return f"Error: {str(e)}"

# Git Tools
@tool
async def mcp_git_status(**kwargs) -> str:
    """Get Git status using MCP Git server."""
    try:
        mcp_manager = await get_mcp_manager()
        response = await mcp_manager.send_request(
            "git",
            "status",
            {}
        )
        
        if response.error:
            return f"Error getting Git status: {response.error}"
        
        status = response.result
        return json.dumps(status, indent=2)
        
    except Exception as e:
        logger.error(f"Error in mcp_git_status: {e}")
        return f"Error: {str(e)}"

@tool
async def mcp_git_add_files(**kwargs) -> str:
    """Add files to Git using MCP Git server."""
    try:
        if 'tool_input' in kwargs:
            params = kwargs['tool_input']
        else:
            params = kwargs
        
        files = params.get('files', [])
        if not files:
            return "Error: No files specified"
        
        mcp_manager = await get_mcp_manager()
        response = await mcp_manager.send_request(
            "git",
            "add",
            {"files": files}
        )
        
        if response.error:
            return f"Error adding files: {response.error}"
        
        return f"Successfully added files: {', '.join(files)}"
        
    except Exception as e:
        logger.error(f"Error in mcp_git_add_files: {e}")
        return f"Error: {str(e)}"

@tool
async def mcp_git_commit(**kwargs) -> str:
    """Commit changes using MCP Git server."""
    try:
        if 'tool_input' in kwargs:
            params = kwargs['tool_input']
        else:
            params = kwargs
        
        message = params.get('message', 'Automated commit')
        
        mcp_manager = await get_mcp_manager()
        response = await mcp_manager.send_request(
            "git",
            "commit",
            {"message": message}
        )
        
        if response.error:
            return f"Error committing: {response.error}"
        
        result = response.result
        return f"Commit successful: {result.get('hash', 'unknown')}"
        
    except Exception as e:
        logger.error(f"Error in mcp_git_commit: {e}")
        return f"Error: {str(e)}"

# Browser Tools
@tool
async def mcp_browser_navigate(**kwargs) -> str:
    """Navigate to a URL using MCP browser server."""
    try:
        if 'tool_input' in kwargs:
            params = kwargs['tool_input']
        else:
            params = kwargs
        
        url = params.get('url', '')
        if not url:
            return "Error: No URL provided"
        
        mcp_manager = await get_mcp_manager()
        response = await mcp_manager.send_request(
            "browser",
            "navigate",
            {"url": url}
        )
        
        if response.error:
            return f"Error navigating: {response.error}"
        
        return f"Successfully navigated to: {url}"
        
    except Exception as e:
        logger.error(f"Error in mcp_browser_navigate: {e}")
        return f"Error: {str(e)}"

@tool
async def mcp_browser_screenshot(**kwargs) -> str:
    """Take a screenshot using MCP browser server."""
    try:
        if 'tool_input' in kwargs:
            params = kwargs['tool_input']
        else:
            params = kwargs
        
        filename = params.get('filename', f'screenshot_{int(asyncio.get_event_loop().time())}.png')
        
        mcp_manager = await get_mcp_manager()
        response = await mcp_manager.send_request(
            "browser",
            "screenshot",
            {"filename": filename}
        )
        
        if response.error:
            return f"Error taking screenshot: {response.error}"
        
        return f"Screenshot saved as: {filename}"
        
    except Exception as e:
        logger.error(f"Error in mcp_browser_screenshot: {e}")
        return f"Error: {str(e)}"

# Utility Tools
@tool
async def mcp_server_status(**kwargs) -> str:
    """Get status of all MCP servers."""
    try:
        mcp_manager = await get_mcp_manager()
        stats = mcp_manager.get_server_stats()
        return json.dumps(stats, indent=2)
        
    except Exception as e:
        logger.error(f"Error in mcp_server_status: {e}")
        return f"Error: {str(e)}"

@tool
async def mcp_start_server(**kwargs) -> str:
    """Start a specific MCP server."""
    try:
        if 'tool_input' in kwargs:
            params = kwargs['tool_input']
        else:
            params = kwargs
        
        server_name = params.get('server_name', '')
        if not server_name:
            return "Error: No server name provided"
        
        mcp_manager = await get_mcp_manager()
        success = await mcp_manager.start_server(server_name)
        
        if success:
            return f"Successfully started MCP server: {server_name}"
        else:
            return f"Failed to start MCP server: {server_name}"
        
    except Exception as e:
        logger.error(f"Error in mcp_start_server: {e}")
        return f"Error: {str(e)}"

@tool
async def mcp_stop_server(**kwargs) -> str:
    """Stop a specific MCP server."""
    try:
        if 'tool_input' in kwargs:
            params = kwargs['tool_input']
        else:
            params = kwargs
        
        server_name = params.get('server_name', '')
        if not server_name:
            return "Error: No server name provided"
        
        mcp_manager = await get_mcp_manager()
        success = await mcp_manager.stop_server(server_name)
        
        if success:
            return f"Successfully stopped MCP server: {server_name}"
        else:
            return f"Failed to stop MCP server: {server_name}"
        
    except Exception as e:
        logger.error(f"Error in mcp_stop_server: {e}")
        return f"Error: {str(e)}"

# Get all MCP tools
def get_mcp_tools():
    """Get all MCP tools for use with agents."""
    return [
        # Filesystem tools
        mcp_filesystem_read_file,
        mcp_filesystem_write_file,
        mcp_filesystem_list_directory,
        mcp_filesystem_create_directory,
        
        # Database tools
        mcp_database_query,
        mcp_database_get_schema,
        
        # Git tools
        mcp_git_status,
        mcp_git_add_files,
        mcp_git_commit,
        
        # Browser tools
        mcp_browser_navigate,
        mcp_browser_screenshot,
        
        # Utility tools
        mcp_server_status,
        mcp_start_server,
        mcp_stop_server,
    ]
