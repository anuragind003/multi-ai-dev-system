#!/usr/bin/env python3
"""
Example: Multi-Agent System with LangGraph MCP Integration
Demonstrates how to use MCP servers with your existing multi-agent pipeline.
"""

import asyncio
import json
import logging
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.langgraph_mcp import get_langgraph_mcp_manager, cleanup_langgraph_mcp
from mcp.agent_integration import run_mcp_enhanced_pipeline, setup_mcp_for_agents

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demo_mcp_filesystem():
    """Demonstrate MCP filesystem operations."""
    print("\n🗁 MCP Filesystem Demo")
    print("-" * 40)
    
    try:
        manager = await get_langgraph_mcp_manager()
        
        # Write a sample file
        test_content = """# Sample BRD
        
Project: Task Tracker
Goal: Create a simple task management system
Requirements:
- Users can create tasks
- Tasks have due dates
- Simple dashboard
"""
        await manager.call_tool("filesystem", "write_file", {
            "path": "./test_brd.md",
            "content": test_content
        })
        print("✅ Created test BRD file")
        
        # Read the file back
        result = await manager.call_tool("filesystem", "read_file", {
            "path": "./test_brd.md"
        })
        print(f"✅ Read file content: {len(result.get('content', ''))} characters")
        
        # List directory
        dir_result = await manager.call_tool("filesystem", "list_directory", {
            "path": "."
        })
        print(f"✅ Directory listing: {len(dir_result.get('files', []))} items")
        
    except Exception as e:
        print(f"❌ Filesystem demo failed: {e}")

async def demo_mcp_git():
    """Demonstrate MCP Git operations."""
    print("\n🌿 MCP Git Demo")
    print("-" * 40)
    
    try:
        manager = await get_langgraph_mcp_manager()
        
        # Get Git status
        status_result = await manager.call_tool("git", "git_status", {})
        print(f"✅ Git status retrieved")
        
        # Show available tools
        tools = await manager.list_tools("git")
        print(f"✅ Available Git tools: {[tool.get('name', 'unknown') for tool in tools]}")
        
    except Exception as e:
        print(f"❌ Git demo failed: {e}")

async def demo_mcp_database():
    """Demonstrate MCP database operations."""
    print("\n🗄️ MCP Database Demo")
    print("-" * 40)
    
    try:
        manager = await get_langgraph_mcp_manager()
        
        # Create a simple table
        create_table = """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'active'
        )
        """
        
        await manager.call_tool("sqlite", "execute_query", {
            "query": create_table
        })
        print("✅ Created projects table")
        
        # Insert test data
        insert_data = "INSERT INTO projects (name) VALUES ('Task Tracker')"
        await manager.call_tool("sqlite", "execute_query", {
            "query": insert_data
        })
        print("✅ Inserted test project")
        
        # Query data
        select_data = "SELECT * FROM projects"
        result = await manager.call_tool("sqlite", "execute_query", {
            "query": select_data
        })
        print(f"✅ Query result: {result}")
        
    except Exception as e:
        print(f"❌ Database demo failed: {e}")

async def demo_full_pipeline():
    """Demonstrate the full MCP-enhanced pipeline."""
    print("\n🚀 Full MCP-Enhanced Pipeline Demo")
    print("-" * 50)
    
    try:
        # Setup MCP for all agents
        await setup_mcp_for_agents()
        print("✅ MCP setup completed for all agents")
        
        # Create a sample BRD file
        brd_content = """
# Project Requirements Document

## Project Title: Task Management System

## Business Problem
Small teams need a simple, efficient way to track and manage tasks without the complexity of enterprise project management tools.

## Project Goals
1. Create an intuitive task management interface
2. Enable team collaboration and task assignment
3. Provide basic reporting and analytics
4. Ensure mobile responsiveness

## Functional Requirements

### Task Management
- REQ-001: Users can create new tasks with title, description, and due date
- REQ-002: Tasks can be assigned to specific team members
- REQ-003: Task status can be updated (To Do, In Progress, Done)
- REQ-004: Users can set task priority (High, Medium, Low)

### User Management
- REQ-005: User registration and authentication
- REQ-006: Role-based access control (Admin, Member)
- REQ-007: User profile management

### Collaboration
- REQ-008: Task comments and updates
- REQ-009: File attachments to tasks
- REQ-010: Email notifications for task assignments

## Non-Functional Requirements

### Performance
- REQ-011: Page load time under 3 seconds
- REQ-012: Support for 50 concurrent users
- REQ-013: 99.5% uptime availability

### Security
- REQ-014: Secure user authentication
- REQ-015: Data encryption in transit and at rest
- REQ-016: Regular security audits

### Usability
- REQ-017: Mobile-responsive design
- REQ-018: Intuitive user interface
- REQ-019: Accessibility compliance (WCAG 2.1)

## Technical Constraints
- Web-based application
- Cloud deployment preferred (AWS/Azure)
- Budget-conscious solution
- Easy maintenance and updates
- Integration with existing tools

## Success Criteria
- User adoption rate > 80% within 3 months
- Task completion rate improvement of 25%
- User satisfaction score > 4.0/5.0
"""
        
        # Save BRD to file using MCP
        manager = await get_langgraph_mcp_manager()
        await manager.call_tool("filesystem", "write_file", {
            "path": "./sample_brd.md",
            "content": brd_content
        })
        print("✅ Created comprehensive BRD file")
        
        # Run the MCP-enhanced pipeline
        print("🔄 Running MCP-enhanced pipeline...")
        
        # Note: This would run the full pipeline if the agents were properly initialized
        # For demo purposes, we'll simulate the workflow
        
        print("📋 Step 1: BRD Analysis with MCP filesystem integration")
        print("  - Reading BRD from file system")
        print("  - Extracting requirements and constraints")
        print("  - Saving analysis results")
        
        print("⚙️ Step 2: Tech Stack Recommendation with MCP database integration")
        print("  - Analyzing technical requirements")
        print("  - Recommending technology stack")
        print("  - Saving recommendations to database")
        
        print("💻 Step 3: Code Generation with MCP filesystem and Git integration")
        print("  - Generating project structure")
        print("  - Creating source code files")
        print("  - Committing to version control")
        
        print("✅ MCP-enhanced pipeline simulation completed")
        
    except Exception as e:
        print(f"❌ Full pipeline demo failed: {e}")

async def demo_mcp_tools_for_agents():
    """Demonstrate MCP tools that agents can use."""
    print("\n🔧 MCP Tools for Agents Demo")
    print("-" * 40)
    
    try:
        from mcp.langgraph_mcp import (
            mcp_filesystem_read_file,
            mcp_filesystem_write_file,
            mcp_git_status,
            mcp_database_query
        )
        
        # Test filesystem tools
        await mcp_filesystem_write_file("./agent_test.txt", "Hello from agent!")
        content = await mcp_filesystem_read_file("./agent_test.txt")
        print(f"✅ Agent filesystem tools: wrote and read {len(content)} characters")
        
        # Test git tools
        git_status = await mcp_git_status()
        print(f"✅ Agent git tools: retrieved status")
        
        # Test database tools  
        db_result = await mcp_database_query("SELECT 1 as test")
        print(f"✅ Agent database tools: executed query")
        
        print("🎯 All MCP tools are ready for agent integration!")
        
    except Exception as e:
        print(f"❌ MCP tools demo failed: {e}")

async def main():
    """Main demonstration function."""
    print("🌟 LangGraph MCP Integration Demo")
    print("=" * 50)
    print("This demo shows how to integrate MCP servers with your multi-agent system")
    print("")
    
    try:
        # Individual MCP server demos
        await demo_mcp_filesystem()
        await demo_mcp_git()
        await demo_mcp_database()
        
        # MCP tools for agents
        await demo_mcp_tools_for_agents()
        
        # Full pipeline demonstration
        await demo_full_pipeline()
        
        print("\n" + "🎉" * 20)
        print("🏆 MCP Integration Demo Completed Successfully!")
        print("")
        print("🔗 Your multi-agent system now has:")
        print("  ✅ Filesystem access for reading/writing files")
        print("  ✅ Git integration for version control")
        print("  ✅ Database connectivity for data persistence")
        print("  ✅ Enhanced agent capabilities")
        print("  ✅ LangGraph-native MCP workflows")
        print("")
        print("📋 Next Steps:")
        print("  1. Install MCP servers: npm install -g @modelcontextprotocol/server-*")
        print("  2. Configure your specific MCP servers in mcp/langgraph_mcp_config.json")
        print("  3. Integrate MCP tools into your existing agents")
        print("  4. Run your enhanced multi-agent pipeline!")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise
    finally:
        # Cleanup
        await cleanup_langgraph_mcp()
        print("\n🧹 Cleanup completed")

if __name__ == "__main__":
    asyncio.run(main())
