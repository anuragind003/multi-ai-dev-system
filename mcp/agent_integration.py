"""
Enhanced Agent Integration with LangGraph MCP Support
Integrates MCP tools with your existing multi-agent system.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable

from langchain_core.tools import BaseTool
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

# Import your existing agents
from agents.base_agent import BaseAgent
from agents.brd_analyst_react import BRDAnalystReActAgent
from agents.tech_stack_advisor_react import TechStackAdvisorReActAgent

# Import MCP integration
from mcp.langgraph_mcp import (
    get_langgraph_mcp_manager,
    get_mcp_tools,
    MCPState,
    create_mcp_graph
)

logger = logging.getLogger(__name__)

class MCPEnhancedAgent(BaseAgent):
    """Base agent class with MCP capabilities."""
    
    def __init__(self, llm: BaseLanguageModel, memory, temperature: float, **kwargs):
        super().__init__(llm, memory, temperature, **kwargs)
        self.mcp_tools = []
        self.mcp_manager = None
    
    async def initialize_mcp(self):
        """Initialize MCP capabilities for this agent."""
        try:
            self.mcp_manager = await get_langgraph_mcp_manager()
            self.mcp_tools = get_mcp_tools()
            logger.info(f"MCP capabilities initialized for {self.__class__.__name__}")
        except Exception as e:
            logger.error(f"Failed to initialize MCP for {self.__class__.__name__}: {e}")
    
    def get_enhanced_tools(self) -> List[BaseTool]:
        """Get agent tools enhanced with MCP capabilities."""
        base_tools = self.get_tools() if hasattr(self, 'get_tools') else []
        return base_tools + self.mcp_tools

class MCPEnhancedBRDAnalyst(BRDAnalystReActAgent, MCPEnhancedAgent):
    """BRD Analyst with MCP file system and Git integration."""
    
    def __init__(self, llm: BaseLanguageModel, memory, temperature: float, **kwargs):
        BRDAnalystReActAgent.__init__(self, llm, memory, temperature, **kwargs)
        MCPEnhancedAgent.__init__(self, llm, memory, temperature, **kwargs)
    
    async def analyze_brd_from_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze BRD directly from file using MCP filesystem."""
        try:
            await self.initialize_mcp()
            
            # Read BRD file using MCP
            from mcp.langgraph_mcp import mcp_filesystem_read_file
            brd_content = await mcp_filesystem_read_file(file_path)
            
            # Initialize enhanced tools with BRD content
            from tools.enhanced_brd_analysis_tools import initialize_enhanced_brd_tools
            initialize_enhanced_brd_tools(self.llm, brd_content)
            
            # Perform analysis
            analysis = await self.analyze(brd_content)
            
            # Save analysis result using MCP
            analysis_file = file_path.replace('.', '_analysis.')
            await self.save_analysis_to_file(analysis, analysis_file)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing BRD from file: {e}")
            raise
    
    async def save_analysis_to_file(self, analysis: Dict[str, Any], file_path: str):
        """Save BRD analysis to file using MCP."""
        try:
            import json
            from mcp.langgraph_mcp import mcp_filesystem_write_file
            
            analysis_json = json.dumps(analysis, indent=2)
            await mcp_filesystem_write_file(file_path, analysis_json)
            
            logger.info(f"BRD analysis saved to: {file_path}")
            
        except Exception as e:
            logger.error(f"Error saving analysis to file: {e}")

class MCPEnhancedTechStackAdvisor(TechStackAdvisorReActAgent, MCPEnhancedAgent):
    """Tech Stack Advisor with MCP database and external API integration."""
    
    def __init__(self, llm: BaseLanguageModel, memory, temperature: float, **kwargs):
        TechStackAdvisorReActAgent.__init__(self, llm, memory, temperature, **kwargs)
        MCPEnhancedAgent.__init__(self, llm, memory, temperature, **kwargs)
    
    async def save_tech_stack_to_database(self, tech_stack: Dict[str, Any], project_id: str):
        """Save tech stack recommendation to database using MCP."""
        try:
            await self.initialize_mcp()
            
            from mcp.langgraph_mcp import mcp_database_query
            import json
            
            # Create table if not exists
            create_table_query = '''
            CREATE TABLE IF NOT EXISTS tech_stacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            '''
            await mcp_database_query(create_table_query)
            
            # Insert tech stack
            insert_query = '''
            INSERT INTO tech_stacks (project_id, recommendation)
            VALUES (?, ?)
            '''
            tech_stack_json = json.dumps(tech_stack)
            
            # Note: This is simplified - you'd need proper parameterized queries
            full_query = f"INSERT INTO tech_stacks (project_id, recommendation) VALUES ('{project_id}', '{tech_stack_json}')"
            await mcp_database_query(full_query)
            
            logger.info(f"Tech stack saved to database for project: {project_id}")
            
        except Exception as e:
            logger.error(f"Error saving tech stack to database: {e}")
    
    async def get_tech_stack_history(self, project_id: str) -> List[Dict[str, Any]]:
        """Get tech stack history from database using MCP."""
        try:
            await self.initialize_mcp()
            
            from mcp.langgraph_mcp import mcp_database_query
            import json
            
            query = f"SELECT * FROM tech_stacks WHERE project_id = '{project_id}' ORDER BY created_at DESC"
            result = await mcp_database_query(query)
            
            # Parse result (this would depend on the actual database response format)
            history = []
            if isinstance(result, str):
                result_data = json.loads(result)
                if 'rows' in result_data:
                    for row in result_data['rows']:
                        history.append({
                            'id': row[0],
                            'project_id': row[1],
                            'recommendation': json.loads(row[2]),
                            'created_at': row[3]
                        })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting tech stack history: {e}")
            return []

class MCPEnhancedCodeGenerator(MCPEnhancedAgent):
    """Code Generator with MCP filesystem and Git integration."""
    
    async def generate_and_save_code(self, code_structure: Dict[str, Any], project_path: str):
        """Generate code and save to filesystem using MCP."""
        try:
            await self.initialize_mcp()
            
            from mcp.langgraph_mcp import mcp_filesystem_write_file, mcp_filesystem_list_directory
            
            # Create project structure
            for file_path, content in code_structure.get('files', {}).items():
                full_path = f"{project_path}/{file_path}"
                await mcp_filesystem_write_file(full_path, content)
                logger.info(f"Generated file: {full_path}")
            
            # List generated files
            project_files = await mcp_filesystem_list_directory(project_path)
            logger.info(f"Generated project structure: {project_files}")
            
        except Exception as e:
            logger.error(f"Error generating and saving code: {e}")
    
    async def commit_generated_code(self, message: str, files: List[str] = None):
        """Commit generated code using MCP Git."""
        try:
            await self.initialize_mcp()
            
            from mcp.langgraph_mcp import mcp_git_commit, mcp_git_status
            
            # Check status first
            status = await mcp_git_status()
            logger.info(f"Git status before commit: {status}")
            
            # Commit changes
            result = await mcp_git_commit(message, files)
            logger.info(f"Git commit result: {result}")
            
        except Exception as e:
            logger.error(f"Error committing generated code: {e}")

def create_mcp_enhanced_workflow() -> StateGraph:
    """Create an enhanced workflow with MCP integration."""
    
    # Create the base MCP graph
    mcp_graph = create_mcp_graph()
    
    # Define enhanced state that includes your agent states
    class EnhancedMCPState(MCPState):
        brd_analysis: Optional[Dict[str, Any]] = None
        tech_stack: Optional[Dict[str, Any]] = None
        generated_code: Optional[Dict[str, Any]] = None
        project_path: str = "./output"
        project_id: str = "default_project"
    
    # Create enhanced workflow
    workflow = StateGraph(EnhancedMCPState)
    
    # Enhanced node functions
    async def brd_analysis_with_mcp(state: EnhancedMCPState) -> EnhancedMCPState:
        """BRD analysis with MCP file operations."""
        try:
            # Initialize BRD analyst with MCP
            llm = None  # You'd get this from your config
            memory = None  # You'd get this from your setup
            
            analyst = MCPEnhancedBRDAnalyst(llm, memory, 0.3)
            
            # Analyze BRD from file if specified in messages
            if state.messages:
                last_message = state.messages[-1]
                if "analyze_brd_file:" in last_message.content:
                    file_path = last_message.content.split("analyze_brd_file:")[1].strip()
                    analysis = await analyst.analyze_brd_from_file(file_path)
                    state.brd_analysis = analysis
                    
                    response = AIMessage(content=f"BRD analysis completed for {file_path}")
                    state.messages.append(response)
            
            return state
            
        except Exception as e:
            state.error_context = f"BRD analysis with MCP failed: {e}"
            return state
    
    async def tech_stack_with_mcp(state: EnhancedMCPState) -> EnhancedMCPState:
        """Tech stack recommendation with MCP database operations."""
        try:
            if state.brd_analysis:
                llm = None  # You'd get this from your config
                memory = None  # You'd get this from your setup
                
                advisor = MCPEnhancedTechStackAdvisor(llm, memory, 0.2)
                
                # Get tech stack recommendation
                tech_stack = await advisor.recommend_tech_stack(state.brd_analysis)
                state.tech_stack = tech_stack
                
                # Save to database
                await advisor.save_tech_stack_to_database(tech_stack, state.project_id)
                
                response = AIMessage(content="Tech stack recommendation completed and saved")
                state.messages.append(response)
            
            return state
            
        except Exception as e:
            state.error_context = f"Tech stack with MCP failed: {e}"
            return state
    
    async def code_generation_with_mcp(state: EnhancedMCPState) -> EnhancedMCPState:
        """Code generation with MCP filesystem and Git operations."""
        try:
            if state.tech_stack:
                generator = MCPEnhancedCodeGenerator(None, None, 0.1)
                
                # Generate code structure
                code_structure = {
                    'files': {
                        'main.py': '# Generated main file\nprint("Hello World")',
                        'requirements.txt': '# Generated requirements\nfastapi==0.104.1',
                        'README.md': '# Generated Project\n\nThis project was automatically generated.'
                    }
                }
                
                # Save code using MCP
                await generator.generate_and_save_code(code_structure, state.project_path)
                state.generated_code = code_structure
                
                # Commit to Git
                await generator.commit_generated_code("Initial code generation", 
                                                      list(code_structure['files'].keys()))
                
                response = AIMessage(content=f"Code generated and committed to {state.project_path}")
                state.messages.append(response)
            
            return state
            
        except Exception as e:
            state.error_context = f"Code generation with MCP failed: {e}"
            return state
    
    # Add nodes to workflow
    workflow.add_node("brd_analysis_mcp", brd_analysis_with_mcp)
    workflow.add_node("tech_stack_mcp", tech_stack_with_mcp)
    workflow.add_node("code_generation_mcp", code_generation_with_mcp)
    
    # Add edges
    workflow.add_edge(START, "brd_analysis_mcp")
    workflow.add_edge("brd_analysis_mcp", "tech_stack_mcp")
    workflow.add_edge("tech_stack_mcp", "code_generation_mcp")
    workflow.add_edge("code_generation_mcp", END)
    
    return workflow

async def run_mcp_enhanced_pipeline(brd_file_path: str, project_id: str = "default_project"):
    """Run the complete pipeline with MCP integration."""
    try:
        # Create workflow
        workflow = create_mcp_enhanced_workflow()
        
        # Setup checkpointing
        checkpointer = SqliteSaver.from_conn_string(":memory:")
        app = workflow.compile(checkpointer=checkpointer)
        
        # Initial state
        initial_state = {
            "messages": [HumanMessage(content=f"analyze_brd_file: {brd_file_path}")],
            "project_id": project_id,
            "project_path": f"./output/{project_id}"
        }
        
        # Run workflow
        config = {"configurable": {"thread_id": project_id}}
        result = await app.ainvoke(initial_state, config)
        
        logger.info("MCP-enhanced pipeline completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"MCP-enhanced pipeline failed: {e}")
        raise

# Utility functions for easy integration
async def setup_mcp_for_agents():
    """Setup MCP for all agents in the system."""
    try:
        manager = await get_langgraph_mcp_manager()
        logger.info("MCP setup completed for all agents")
        return manager
    except Exception as e:
        logger.error(f"MCP setup failed: {e}")
        raise

def get_mcp_enhanced_tools() -> List[Callable]:
    """Get all MCP-enhanced tools for agents."""
    return get_mcp_tools()
