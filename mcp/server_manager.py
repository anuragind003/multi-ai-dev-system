"""
MCP (Model Context Protocol) Server Manager for Multi-AI Development System.
Provides secure connections to databases, IDEs, file systems, and external tools.
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime

import httpx
import websockets
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class MCPServerType(Enum):
    """Types of MCP servers supported."""
    DATABASE = "database"
    FILESYSTEM = "filesystem"
    IDE = "ide"
    GIT = "git"
    DOCKER = "docker"
    API = "api"
    BROWSER = "browser"
    TERMINAL = "terminal"

@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    name: str
    server_type: MCPServerType
    command: List[str]
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    working_dir: Optional[str] = None
    timeout: int = 30
    auto_restart: bool = True
    enabled: bool = True
    port: Optional[int] = None
    protocol: str = "stdio"  # stdio, http, websocket

class MCPRequest(BaseModel):
    """Standard MCP request format."""
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)
    id: Optional[Union[str, int]] = None

class MCPResponse(BaseModel):
    """Standard MCP response format."""
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None

class MCPServerProcess:
    """Manages a single MCP server process."""
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.start_time: Optional[datetime] = None
        self.request_count = 0
        self.error_count = 0
        
    async def start(self) -> bool:
        """Start the MCP server process."""
        try:
            if self.is_running:
                logger.warning(f"MCP server {self.config.name} is already running")
                return True
                
            logger.info(f"Starting MCP server: {self.config.name}")
            
            # Prepare environment
            env = os.environ.copy()
            env.update(self.config.env)
            
            # Build command
            full_command = self.config.command + self.config.args
            
            # Start process
            self.process = subprocess.Popen(
                full_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=self.config.working_dir,
                text=True,
                bufsize=0
            )
            
            # Wait a moment to see if process starts successfully
            await asyncio.sleep(0.5)
            
            if self.process.poll() is None:
                self.is_running = True
                self.start_time = datetime.now()
                logger.info(f"MCP server {self.config.name} started successfully (PID: {self.process.pid})")
                return True
            else:
                stderr_output = self.process.stderr.read() if self.process.stderr else ""
                logger.error(f"MCP server {self.config.name} failed to start: {stderr_output}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting MCP server {self.config.name}: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the MCP server process."""
        try:
            if not self.is_running or not self.process:
                return True
                
            logger.info(f"Stopping MCP server: {self.config.name}")
            
            # Try graceful shutdown first
            self.process.terminate()
            
            # Wait for graceful shutdown
            try:
                await asyncio.wait_for(
                    asyncio.create_task(self._wait_for_process()),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                # Force kill if graceful shutdown fails
                logger.warning(f"Force killing MCP server: {self.config.name}")
                self.process.kill()
                await self._wait_for_process()
            
            self.is_running = False
            self.start_time = None
            logger.info(f"MCP server {self.config.name} stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping MCP server {self.config.name}: {e}")
            return False
    
    async def _wait_for_process(self):
        """Wait for process to terminate."""
        while self.process and self.process.poll() is None:
            await asyncio.sleep(0.1)
    
    async def send_request(self, request: MCPRequest) -> MCPResponse:
        """Send a request to the MCP server."""
        try:
            if not self.is_running or not self.process:
                raise Exception(f"MCP server {self.config.name} is not running")
            
            # Serialize request
            request_data = request.json() + "\n"
            
            # Send request
            self.process.stdin.write(request_data)
            self.process.stdin.flush()
            
            # Read response
            response_line = self.process.stdout.readline()
            if not response_line:
                raise Exception("No response received from MCP server")
            
            # Parse response
            response_data = json.loads(response_line.strip())
            response = MCPResponse(**response_data)
            
            self.request_count += 1
            
            if response.error:
                self.error_count += 1
                logger.error(f"MCP server {self.config.name} returned error: {response.error}")
            
            return response
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Error sending request to MCP server {self.config.name}: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        uptime = None
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "name": self.config.name,
            "type": self.config.server_type.value,
            "is_running": self.is_running,
            "pid": self.process.pid if self.process else None,
            "uptime_seconds": uptime,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.request_count, 1)
        }

class MCPServerManager:
    """Manages multiple MCP servers for the multi-agent system."""
    
    def __init__(self):
        self.servers: Dict[str, MCPServerProcess] = {}
        self.config_file = Path("mcp_servers.json")
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize the MCP server manager."""
        try:
            logger.info("Initializing MCP Server Manager")
            
            # Load server configurations
            await self.load_configurations()
            
            # Start enabled servers
            await self.start_all_enabled_servers()
            
            self.is_initialized = True
            logger.info("MCP Server Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP Server Manager: {e}")
            raise
    
    async def load_configurations(self):
        """Load MCP server configurations from file."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    configs_data = json.load(f)
                
                for config_data in configs_data.get("servers", []):
                    config = MCPServerConfig(
                        name=config_data["name"],
                        server_type=MCPServerType(config_data["server_type"]),
                        command=config_data["command"],
                        args=config_data.get("args", []),
                        env=config_data.get("env", {}),
                        working_dir=config_data.get("working_dir"),
                        timeout=config_data.get("timeout", 30),
                        auto_restart=config_data.get("auto_restart", True),
                        enabled=config_data.get("enabled", True),
                        port=config_data.get("port"),
                        protocol=config_data.get("protocol", "stdio")
                    )
                    
                    self.servers[config.name] = MCPServerProcess(config)
                    logger.info(f"Loaded MCP server config: {config.name}")
            else:
                # Create default configuration file
                await self.create_default_config()
                
        except Exception as e:
            logger.error(f"Error loading MCP configurations: {e}")
            raise
    
    async def create_default_config(self):
        """Create default MCP server configuration file."""
        default_config = {
            "servers": [
                {
                    "name": "filesystem",
                    "server_type": "filesystem",
                    "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem"],
                    "args": ["."],
                    "enabled": True,
                    "env": {},
                    "timeout": 30,
                    "auto_restart": True
                },
                {
                    "name": "git",
                    "server_type": "git",
                    "command": ["npx", "-y", "@modelcontextprotocol/server-git"],
                    "args": ["--repository", "."],
                    "enabled": True,
                    "env": {},
                    "timeout": 30,
                    "auto_restart": True
                },
                {
                    "name": "sqlite",
                    "server_type": "database",
                    "command": ["npx", "-y", "@modelcontextprotocol/server-sqlite"],
                    "args": ["--db-path", "./data/project.db"],
                    "enabled": False,
                    "env": {},
                    "timeout": 30,
                    "auto_restart": True
                },
                {
                    "name": "browser",
                    "server_type": "browser",
                    "command": ["npx", "-y", "@modelcontextprotocol/server-puppeteer"],
                    "enabled": False,
                    "env": {},
                    "timeout": 30,
                    "auto_restart": True
                }
            ]
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        logger.info(f"Created default MCP configuration: {self.config_file}")
    
    async def start_all_enabled_servers(self):
        """Start all enabled MCP servers."""
        for name, server in self.servers.items():
            if server.config.enabled:
                await server.start()
    
    async def start_server(self, name: str) -> bool:
        """Start a specific MCP server."""
        if name in self.servers:
            return await self.servers[name].start()
        else:
            logger.error(f"MCP server {name} not found")
            return False
    
    async def stop_server(self, name: str) -> bool:
        """Stop a specific MCP server."""
        if name in self.servers:
            return await self.servers[name].stop()
        else:
            logger.error(f"MCP server {name} not found")
            return False
    
    async def stop_all_servers(self):
        """Stop all MCP servers."""
        tasks = []
        for server in self.servers.values():
            if server.is_running:
                tasks.append(server.stop())
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def send_request(self, server_name: str, method: str, params: Dict[str, Any] = None) -> MCPResponse:
        """Send a request to a specific MCP server."""
        if server_name not in self.servers:
            raise Exception(f"MCP server {server_name} not found")
        
        server = self.servers[server_name]
        if not server.is_running:
            # Try to start the server if it's not running
            if server.config.auto_restart:
                logger.info(f"Auto-starting MCP server: {server_name}")
                await server.start()
            else:
                raise Exception(f"MCP server {server_name} is not running")
        
        request = MCPRequest(
            method=method,
            params=params or {},
            id=f"{server_name}_{int(time.time() * 1000)}"
        )
        
        return await server.send_request(request)
    
    def get_server_stats(self) -> Dict[str, Any]:
        """Get statistics for all servers."""
        return {
            "total_servers": len(self.servers),
            "running_servers": sum(1 for s in self.servers.values() if s.is_running),
            "servers": {name: server.get_stats() for name, server in self.servers.items()}
        }
    
    def get_available_servers(self) -> List[str]:
        """Get list of available server names."""
        return list(self.servers.keys())
    
    def get_running_servers(self) -> List[str]:
        """Get list of running server names."""
        return [name for name, server in self.servers.items() if server.is_running]
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all servers."""
        health_status = {}
        
        for name, server in self.servers.items():
            try:
                if server.is_running:
                    # Send a simple ping request
                    response = await self.send_request(name, "ping")
                    health_status[name] = response.error is None
                else:
                    health_status[name] = False
            except Exception:
                health_status[name] = False
        
        return health_status
    
    async def cleanup(self):
        """Cleanup all MCP servers."""
        logger.info("Cleaning up MCP servers")
        await self.stop_all_servers()

# Global MCP server manager instance
_mcp_manager: Optional[MCPServerManager] = None

async def get_mcp_manager() -> MCPServerManager:
    """Get the global MCP server manager instance."""
    global _mcp_manager
    
    if _mcp_manager is None:
        _mcp_manager = MCPServerManager()
        await _mcp_manager.initialize()
    
    return _mcp_manager

async def cleanup_mcp():
    """Cleanup MCP resources on shutdown."""
    global _mcp_manager
    
    if _mcp_manager:
        await _mcp_manager.cleanup()
        _mcp_manager = None
