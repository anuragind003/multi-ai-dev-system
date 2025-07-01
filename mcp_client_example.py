"""
Example MCP Client for Multi-AI Development System
Demonstrates how to use the exposed agents via MCP protocol.
"""

import asyncio
import json
from typing import Dict, Any

# Install required dependencies:
# pip install langchain-mcp-adapters

async def connect_to_mcp_server():
    """Connect to the MCP server and use the exposed agents."""
    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
        from langchain_mcp_adapters.tools import load_mcp_tools
        from langgraph.prebuilt import create_react_agent
        
        # Configure server connection
        server_params = {
            "url": "http://localhost:3001/mcp",  # Your LangGraph dev server
            "headers": {
                # Add authentication if needed
                # "X-Api-Key": "your_api_key_here"
            }
        }
        
        print("🔌 Connecting to Multi-AI Development System MCP endpoint...")
        
        async with streamablehttp_client(**server_params) as (read, write, _):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()
                print("✅ Connected to MCP server")
                
                # Load available tools (your agents exposed as MCP tools)
                tools = await load_mcp_tools(session)
                print(f"📚 Loaded {len(tools)} MCP tools:")
                
                for tool in tools:
                    print(f"  - {tool.name}: {tool.description}")
                
                # Create a React agent that can use your MCP-exposed agents
                agent = create_react_agent("openai:gpt-4", tools)
                
                # Example 1: Use BRD Analysis
                print("\n🔍 Example 1: BRD Analysis")
                brd_response = await agent.ainvoke({
                    "messages": [
                        "Analyze this BRD: 'Build a task management web application with user authentication, real-time notifications, and collaborative features. Users should be able to create projects, assign tasks, set deadlines, and track progress.'"
                    ]
                })
                print("BRD Analysis Result:", brd_response["messages"][-1].content)
                
                # Example 2: Tech Stack Recommendation
                print("\n⚡ Example 2: Tech Stack Recommendation")
                tech_response = await agent.ainvoke({
                    "messages": [
                        "Recommend a technology stack for a medium complexity web application with real-time features and collaborative editing capabilities."
                    ]
                })
                print("Tech Stack Result:", tech_response["messages"][-1].content)
                
                # Example 3: Complete Workflow
                print("\n🚀 Example 3: Complete Development Workflow")
                workflow_response = await agent.ainvoke({
                    "messages": [
                        "Execute the complete development workflow for: 'E-commerce platform with user authentication, product catalog, shopping cart, payment integration, and order management. Target platform: web application.'"
                    ]
                })
                print("Complete Workflow Result:", workflow_response["messages"][-1].content)
                
    except Exception as e:
        print(f"❌ Error connecting to MCP server: {e}")
        print("Make sure your LangGraph server is running on localhost:3001")

async def direct_tool_usage_example():
    """Example of directly using the MCP tools without React agent."""
    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
        
        server_params = {
            "url": "http://localhost:3001/mcp",
            "headers": {}
        }
        
        async with streamablehttp_client(**server_params) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # List available tools
                tools_result = await session.list_tools()
                print(f"Available tools: {[tool.name for tool in tools_result.tools]}")
                
                # Call BRD analysis tool directly
                brd_result = await session.call_tool(
                    "brd_analysis_mcp",
                    {
                        "brd_content": "Build a social media platform with user profiles, posts, comments, and real-time messaging.",
                        "analysis_type": "comprehensive"
                    }
                )
                print("Direct BRD Analysis:", brd_result.content)
                
                # Call tech stack tool directly
                tech_result = await session.call_tool(
                    "tech_stack_mcp",
                    {
                        "project_requirements": "Social media platform with real-time messaging",
                        "target_platform": "web", 
                        "complexity_level": "complex"
                    }
                )
                print("Direct Tech Stack:", tech_result.content)
                
    except Exception as e:
        print(f"❌ Error in direct tool usage: {e}")

async def test_local_agents():
    """Test the agents locally before MCP exposure."""
    try:
        from mcp_agent_wrapper import (
            create_brd_analysis_agent,
            create_tech_stack_agent,
            create_complete_workflow_agent
        )
        
        print("🧪 Testing agents locally...")
        
        # Test BRD analysis agent
        brd_agent = create_brd_analysis_agent()
        brd_result = await brd_agent.ainvoke({
            "brd_content": "Build a project management tool with team collaboration features, task tracking, file sharing, and reporting capabilities.",
            "analysis_type": "comprehensive"
        })
        print("✅ BRD Analysis Test:", brd_result["analysis_summary"][:100] + "...")
        
        # Test tech stack agent
        tech_agent = create_tech_stack_agent()
        tech_result = await tech_agent.ainvoke({
            "project_requirements": "Project management tool with collaboration features",
            "target_platform": "web",
            "complexity_level": "medium"
        })
        print("✅ Tech Stack Test:", tech_result["rationale"][:100] + "...")
        
        # Test complete workflow
        workflow_agent = create_complete_workflow_agent()
        workflow_result = await workflow_agent.ainvoke({
            "brd_content": "Simple blog application with user authentication and content management.",
            "project_type": "web_app",
            "development_approach": "basic"
        })
        print("✅ Complete Workflow Test:", workflow_result["project_summary"])
        
    except Exception as e:
        print(f"❌ Error testing local agents: {e}")
        import traceback
        traceback.print_exc()

def print_mcp_usage_instructions():
    """Print instructions for using the MCP-exposed agents."""
    print("""
🎯 Multi-AI Development System MCP Usage Guide

1. Start your LangGraph server:
   cd multi_ai_dev_system
   langgraph dev

2. Your agents are now available as MCP tools at:
   http://localhost:3001/mcp

3. Available MCP Tools:
   - brd_analysis_mcp: Analyze Business Requirements Documents
   - tech_stack_mcp: Get technology stack recommendations  
   - code_generation_mcp: Generate project code and structure
   - complete_workflow_mcp: Run end-to-end development workflow

4. Connect from any MCP-compatible client:
   - Claude Desktop (with MCP configuration)
   - Custom applications using langchain-mcp-adapters
   - Direct MCP client connections

5. Example MCP configuration for Claude Desktop:
   {
     "mcpServers": {
       "multi-ai-dev": {
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-streamable-http"],
         "env": {
           "MCP_SERVER_URL": "http://localhost:3001/mcp"
         }
       }
     }
   }

6. Authentication (if enabled):
   Add X-Api-Key header with your LangGraph API key
""")

async def main():
    """Main execution function."""
    print("🤖 Multi-AI Development System MCP Client Example\n")
    
    choice = input("Choose option:\n1. Test local agents\n2. Connect to MCP server\n3. Direct tool usage\n4. Show usage instructions\nEnter choice (1-4): ")
    
    if choice == "1":
        await test_local_agents()
    elif choice == "2":
        await connect_to_mcp_server()
    elif choice == "3":
        await direct_tool_usage_example()
    elif choice == "4":
        print_mcp_usage_instructions()
    else:
        print("Invalid choice. Running local test...")
        await test_local_agents()

if __name__ == "__main__":
    asyncio.run(main()) 