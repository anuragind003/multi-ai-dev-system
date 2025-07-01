"""
MCP-Compatible Agent Wrapper for Native LangGraph MCP Support
Provides properly typed agents that can be exposed via the /mcp endpoint.
"""

from typing_extensions import TypedDict
from typing import Optional, Dict, Any, List
from langgraph.graph import StateGraph, START, END
import json
import logging

logger = logging.getLogger(__name__)

# Input schemas for MCP exposure
class BRDAnalysisInput(TypedDict):
    """Input schema for BRD analysis via MCP."""
    brd_content: str
    analysis_type: Optional[str]  # "comprehensive", "quick", "technical"

class TechStackInput(TypedDict):
    """Input schema for tech stack recommendation via MCP."""
    project_requirements: str
    target_platform: Optional[str]  # "web", "mobile", "desktop", "api"
    complexity_level: Optional[str]  # "simple", "medium", "complex"

class CodeGenerationInput(TypedDict):
    """Input schema for code generation via MCP."""
    project_specification: str
    tech_stack: str
    output_format: Optional[str]  # "full", "skeleton", "documentation"

class WorkflowInput(TypedDict):
    """Input schema for complete workflow via MCP."""
    brd_content: str
    project_type: Optional[str]  # "web_app", "api", "mobile_app", "desktop_app"
    development_approach: Optional[str]  # "phased", "iterative", "basic"

# Output schemas for MCP exposure
class BRDAnalysisOutput(TypedDict):
    """Output schema for BRD analysis results."""
    analysis_summary: str
    technical_requirements: Dict[str, Any]
    business_objectives: List[str]
    success_criteria: List[str]
    recommended_approach: str

class TechStackOutput(TypedDict):
    """Output schema for tech stack recommendations."""
    recommended_stack: Dict[str, str]
    rationale: str
    alternatives: List[Dict[str, str]]
    implementation_notes: str

class CodeGenerationOutput(TypedDict):
    """Output schema for code generation results."""
    generated_files: Dict[str, str]
    project_structure: str
    setup_instructions: str
    next_steps: List[str]

class WorkflowOutput(TypedDict):
    """Output schema for complete workflow results."""
    brd_analysis: BRDAnalysisOutput
    tech_stack: TechStackOutput
    code_generation: CodeGenerationOutput
    project_summary: str

# Combined state schemas
class BRDAnalysisState(BRDAnalysisInput, BRDAnalysisOutput):
    pass

class TechStackState(TechStackInput, TechStackOutput):
    pass

class CodeGenerationState(CodeGenerationInput, CodeGenerationOutput):
    pass

class WorkflowState(WorkflowInput, WorkflowOutput):
    pass

# Agent nodes for MCP
async def brd_analysis_node(state: BRDAnalysisInput) -> BRDAnalysisOutput:
    """BRD analysis node for MCP exposure."""
    try:
        # Import your existing BRD analyst
        from agents.brd_analyst_react import BRDAnalystReActAgent
        from config import get_llm, get_shared_memory
        
        # Initialize agent
        llm = get_llm(temperature=0.3)  # Creative temperature for BRD analysis
        memory = get_shared_memory()
        agent = BRDAnalystReActAgent(llm, memory, temperature=0.3)
        
        # Perform analysis
        analysis_type = state.get("analysis_type", "comprehensive")
        analysis_result = await agent.analyze(state["brd_content"])
        
        # Structure output for MCP
        return {
            "analysis_summary": analysis_result.get("summary", ""),
            "technical_requirements": analysis_result.get("technical_requirements", {}),
            "business_objectives": analysis_result.get("business_objectives", []),
            "success_criteria": analysis_result.get("success_criteria", []),
            "recommended_approach": analysis_result.get("recommended_approach", "")
        }
        
    except Exception as e:
        logger.error(f"BRD analysis failed: {e}")
        return {
            "analysis_summary": f"Analysis failed: {str(e)}",
            "technical_requirements": {},
            "business_objectives": [],
            "success_criteria": [],
            "recommended_approach": "Manual analysis required"
        }

async def tech_stack_node(state: TechStackInput) -> TechStackOutput:
    """Tech stack recommendation node for MCP exposure."""
    try:
        # Import your existing tech stack advisor
        from agents.tech_stack_advisor_react import TechStackAdvisorReActAgent
        from config import get_llm, get_shared_memory
        
        # Initialize agent
        llm = get_llm(temperature=0.2)  # Analytical temperature
        memory = get_shared_memory()
        agent = TechStackAdvisorReActAgent(llm, memory, temperature=0.2)
        
        # Get recommendation
        platform = state.get("target_platform", "web")
        complexity = state.get("complexity_level", "medium")
        
        recommendation = await agent.recommend_stack(
            state["project_requirements"],
            platform=platform,
            complexity=complexity
        )
        
        return {
            "recommended_stack": recommendation.get("stack", {}),
            "rationale": recommendation.get("rationale", ""),
            "alternatives": recommendation.get("alternatives", []),
            "implementation_notes": recommendation.get("notes", "")
        }
        
    except Exception as e:
        logger.error(f"Tech stack recommendation failed: {e}")
        return {
            "recommended_stack": {},
            "rationale": f"Recommendation failed: {str(e)}",
            "alternatives": [],
            "implementation_notes": "Manual tech stack selection required"
        }

async def code_generation_node(state: CodeGenerationInput) -> CodeGenerationOutput:
    """Code generation node for MCP exposure."""
    try:
        # Import your existing code generators
        from agents.code_generation.architecture_generator import ArchitectureGenerator
        from agents.code_generation.backend_orchestrator import BackendOrchestratorAgent
        from config import get_llm, get_shared_memory
        
        # Initialize agents
        llm = get_llm(temperature=0.1)  # Deterministic for code generation
        memory = get_shared_memory()
        
        arch_gen = ArchitectureGenerator(llm, memory, temperature=0.1)
        backend_gen = BackendOrchestratorAgent(llm, memory, temperature=0.1)
        
        # Generate code
        output_format = state.get("output_format", "full")
        
        # Parse tech stack
        tech_stack = json.loads(state["tech_stack"]) if isinstance(state["tech_stack"], str) else state["tech_stack"]
        
        # Generate architecture
        architecture = await arch_gen.generate_architecture(
            state["project_specification"],
            tech_stack
        )
        
        # Generate backend code
        generated_code = await backend_gen.generate_backend(
            architecture,
            tech_stack
        )
        
        return {
            "generated_files": generated_code.get("files", {}),
            "project_structure": generated_code.get("structure", ""),
            "setup_instructions": generated_code.get("setup", ""),
            "next_steps": generated_code.get("next_steps", [])
        }
        
    except Exception as e:
        logger.error(f"Code generation failed: {e}")
        return {
            "generated_files": {},
            "project_structure": f"Generation failed: {str(e)}",
            "setup_instructions": "Manual setup required",
            "next_steps": ["Review error and try again"]
        }

async def complete_workflow_node(state: WorkflowInput) -> WorkflowOutput:
    """Complete development workflow node for MCP exposure."""
    try:
        # Run BRD analysis
        brd_result = await brd_analysis_node({
            "brd_content": state["brd_content"],
            "analysis_type": "comprehensive"
        })
        
        # Run tech stack recommendation
        tech_result = await tech_stack_node({
            "project_requirements": brd_result["analysis_summary"],
            "target_platform": state.get("project_type", "web"),
            "complexity_level": "medium"
        })
        
        # Run code generation
        code_result = await code_generation_node({
            "project_specification": brd_result["analysis_summary"],
            "tech_stack": json.dumps(tech_result["recommended_stack"]),
            "output_format": "full"
        })
        
        return {
            "brd_analysis": brd_result,
            "tech_stack": tech_result,
            "code_generation": code_result,
            "project_summary": f"Generated {state.get('project_type', 'web')} project with {len(code_result['generated_files'])} files"
        }
        
    except Exception as e:
        logger.error(f"Complete workflow failed: {e}")
        return {
            "brd_analysis": {
                "analysis_summary": f"Workflow failed: {str(e)}",
                "technical_requirements": {},
                "business_objectives": [],
                "success_criteria": [],
                "recommended_approach": ""
            },
            "tech_stack": {
                "recommended_stack": {},
                "rationale": "",
                "alternatives": [],
                "implementation_notes": ""
            },
            "code_generation": {
                "generated_files": {},
                "project_structure": "",
                "setup_instructions": "",
                "next_steps": []
            },
            "project_summary": "Workflow execution failed"
        }

# MCP-compatible graph builders
def create_brd_analysis_agent():
    """Create BRD analysis agent for MCP exposure."""
    builder = StateGraph(BRDAnalysisState, input=BRDAnalysisInput, output=BRDAnalysisOutput)
    builder.add_node("analyze", brd_analysis_node)
    builder.add_edge(START, "analyze")
    builder.add_edge("analyze", END)
    return builder.compile()

def create_tech_stack_agent():
    """Create tech stack recommendation agent for MCP exposure."""
    builder = StateGraph(TechStackState, input=TechStackInput, output=TechStackOutput)
    builder.add_node("recommend", tech_stack_node)
    builder.add_edge(START, "recommend")
    builder.add_edge("recommend", END)
    return builder.compile()

def create_code_generation_agent():
    """Create code generation agent for MCP exposure."""
    builder = StateGraph(CodeGenerationState, input=CodeGenerationInput, output=CodeGenerationOutput)
    builder.add_node("generate", code_generation_node)
    builder.add_edge(START, "generate")
    builder.add_edge("generate", END)
    return builder.compile()

def create_complete_workflow_agent():
    """Create complete development workflow agent for MCP exposure."""
    builder = StateGraph(WorkflowState, input=WorkflowInput, output=WorkflowOutput)
    builder.add_node("workflow", complete_workflow_node)
    builder.add_edge(START, "workflow")
    builder.add_edge("workflow", END)
    return builder.compile()

# Test function
async def test_mcp_agents():
    """Test MCP-compatible agents."""
    # Test BRD analysis
    brd_agent = create_brd_analysis_agent()
    brd_result = await brd_agent.ainvoke({
        "brd_content": "Build a task management web application with user authentication and real-time updates.",
        "analysis_type": "comprehensive"
    })
    print("BRD Analysis Result:", brd_result)
    
    # Test tech stack
    tech_agent = create_tech_stack_agent()
    tech_result = await tech_agent.ainvoke({
        "project_requirements": "Task management web app with real-time features",
        "target_platform": "web",
        "complexity_level": "medium"
    })
    print("Tech Stack Result:", tech_result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_mcp_agents()) 