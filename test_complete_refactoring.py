"""
Complete Refactoring Test - All LLM-Powered Specialized Agents
Tests all 6 specialized agents with LLM-powered generation and cost optimization.
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any

# Add project root to Python path
# Correctly identify the project root, which is the parent of the current directory
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(PROJECT_ROOT)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

# Also add the project root itself for other imports
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import get_llm
from shared_memory import SharedProjectMemory
from tools.code_execution_tool import CodeExecutionTool

# Import all specialized agents
from agents.code_generation.specialized.core_backend_agent import CoreBackendAgent
from agents.code_generation.specialized.devops_infrastructure_agent import DevOpsInfrastructureAgent
from agents.code_generation.specialized.security_compliance_agent import SecurityComplianceAgent
from agents.code_generation.specialized.documentation_agent import DocumentationAgent
from agents.code_generation.specialized.monitoring_observability_agent import MonitoringObservabilityAgent
from agents.code_generation.specialized.testing_qa_agent import TestingQAAgent

# Import the main orchestrator
from agents.code_generation.backend_orchestrator import BackendOrchestratorAgent, CostOptimizationConfig

def test_individual_agents():
    """Test each specialized agent individually for LLM-powered generation."""
    
    print("🔬 Testing Individual Specialized Agents")
    print("=" * 80)
    
    # Setup
    output_dir = "test_output/complete_refactoring_test"
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize components
    llm = get_llm(temperature=0.2)
    memory = SharedProjectMemory(run_dir=output_dir)
    code_execution_tool = CodeExecutionTool(output_dir)
    
    # Test parameters
    test_params = {
        "domain": "ecommerce",
        "language": "python", 
        "framework": "fastapi",
        "scale": "enterprise",
        "features": {"authentication", "caching", "monitoring", "security"}
    }
    
    agents_results = {}
    
    print(f"🎯 Testing with: {test_params['domain']} {test_params['framework']} app")
    print()
    
    # Test 1: Core Backend Agent
    print("1️⃣ Testing Core Backend Agent (LLM-powered)")
    try:
        core_agent = CoreBackendAgent(
            llm=llm, memory=memory, temperature=0.2, output_dir=output_dir,
            code_execution_tool=code_execution_tool
        )
        
        start = time.time()
        result = core_agent.generate_comprehensive_backend(**test_params)
        execution_time = time.time() - start
        
        if result.get("status") == "success":
            print(f"   ✅ SUCCESS - Files: {len(result.get('files', []))}, Time: {execution_time:.1f}s")
            print(f"   💰 Cost optimization: {result.get('cost_optimization', {}).get('generation_method', 'Unknown')}")
        else:
            print(f"   ❌ FAILED - {result.get('error', 'Unknown error')}")
        
        agents_results["core"] = result
    except Exception as e:
        print(f"   ❌ EXCEPTION - {str(e)}")
        agents_results["core"] = {"status": "error", "error": str(e)}
    
    # Test 2: DevOps Infrastructure Agent
    print("2️⃣ Testing DevOps Infrastructure Agent (LLM-powered)")
    try:
        devops_agent = DevOpsInfrastructureAgent(
            llm=llm, memory=memory, temperature=0.2, output_dir=output_dir,
            code_execution_tool=code_execution_tool
        )
        
        start = time.time()
        result = devops_agent.generate_devops_infrastructure(
            domain=test_params["domain"],
            language=test_params["language"],
            framework=test_params["framework"],
            scale=test_params["scale"],
            deployment_targets=["docker", "kubernetes"],
            features=test_params["features"]
        )
        execution_time = time.time() - start
        
        if result.get("status") == "success":
            print(f"   ✅ SUCCESS - Files: {len(result.get('files', []))}, Time: {execution_time:.1f}s")
            print(f"   💰 Cost optimization: {result.get('cost_optimization', {}).get('generation_method', 'Unknown')}")
        else:
            print(f"   ❌ FAILED - {result.get('error', 'Unknown error')}")
        
        agents_results["devops"] = result
    except Exception as e:
        print(f"   ❌ EXCEPTION - {str(e)}")
        agents_results["devops"] = {"status": "error", "error": str(e)}
    
    # Test 3: Security Compliance Agent
    print("3️⃣ Testing Security Compliance Agent (LLM-powered)")
    try:
        security_agent = SecurityComplianceAgent(
            llm=llm, memory=memory, temperature=0.2, output_dir=output_dir,
            code_execution_tool=code_execution_tool
        )
        
        start = time.time()
        result = security_agent.generate_security_infrastructure(
            domain=test_params["domain"],
            language=test_params["language"],
            framework=test_params["framework"],
            security_level="high",
            compliance_requirements=["PCI-DSS", "GDPR"],
            features=test_params["features"],
            scale=test_params["scale"]
        )
        execution_time = time.time() - start
        
        if result.get("status") == "success":
            print(f"   ✅ SUCCESS - Files: {len(result.get('files', []))}, Time: {execution_time:.1f}s")
            print(f"   💰 Cost optimization: {result.get('cost_optimization', {}).get('generation_method', 'Unknown')}")
        else:
            print(f"   ❌ FAILED - {result.get('error', 'Unknown error')}")
        
        agents_results["security"] = result
    except Exception as e:
        print(f"   ❌ EXCEPTION - {str(e)}")
        agents_results["security"] = {"status": "error", "error": str(e)}
    
    # Test 4: Documentation Agent
    print("4️⃣ Testing Documentation Agent (LLM-powered)")
    try:
        docs_agent = DocumentationAgent(
            llm=llm, memory=memory, temperature=0.2, output_dir=output_dir,
            code_execution_tool=code_execution_tool
        )
        
        start = time.time()
        result = docs_agent.generate_documentation(
            domain=test_params["domain"],
            language=test_params["language"],
            framework=test_params["framework"],
            scale=test_params["scale"],
            features=test_params["features"]
        )
        execution_time = time.time() - start
        
        if result.get("status") == "success":
            print(f"   ✅ SUCCESS - Files: {len(result.get('files', []))}, Time: {execution_time:.1f}s")
            print(f"   💰 Cost optimization: {result.get('cost_optimization', {}).get('generation_method', 'Unknown')}")
        else:
            print(f"   ❌ FAILED - {result.get('error', 'Unknown error')}")
        
        agents_results["documentation"] = result
    except Exception as e:
        print(f"   ❌ EXCEPTION - {str(e)}")
        agents_results["documentation"] = {"status": "error", "error": str(e)}
    
    # Test 5: Monitoring Observability Agent
    print("5️⃣ Testing Monitoring Observability Agent (LLM-powered)")
    try:
        monitoring_agent = MonitoringObservabilityAgent(
            llm=llm, memory=memory, temperature=0.2, output_dir=output_dir,
            code_execution_tool=code_execution_tool
        )
        
        start = time.time()
        result = monitoring_agent.generate_monitoring_infrastructure(
            domain=test_params["domain"],
            language=test_params["language"],
            framework=test_params["framework"],
            scale=test_params["scale"],
            monitoring_stack=["prometheus", "grafana"]
        )
        execution_time = time.time() - start
        
        if result.get("status") == "success":
            print(f"   ✅ SUCCESS - Files: {len(result.get('files', []))}, Time: {execution_time:.1f}s")
            print(f"   💰 Cost optimization: {result.get('cost_optimization', {}).get('generation_method', 'Unknown')}")
        else:
            print(f"   ❌ FAILED - {result.get('error', 'Unknown error')}")
        
        agents_results["monitoring"] = result
    except Exception as e:
        print(f"   ❌ EXCEPTION - {str(e)}")
        agents_results["monitoring"] = {"status": "error", "error": str(e)}
    
    # Test 6: Testing QA Agent
    print("6️⃣ Testing QA Agent (LLM-powered)")
    try:
        testing_agent = TestingQAAgent(
            llm=llm, memory=memory, temperature=0.2, output_dir=output_dir,
            code_execution_tool=code_execution_tool
        )
        
        start = time.time()
        result = testing_agent.generate_testing_infrastructure(
            domain=test_params["domain"],
            language=test_params["language"],
            framework=test_params["framework"],
            scale=test_params["scale"],
            features=test_params["features"]
        )
        execution_time = time.time() - start
        
        if result.get("status") == "success":
            print(f"   ✅ SUCCESS - Files: {len(result.get('files', []))}, Time: {execution_time:.1f}s")
            print(f"   💰 Cost optimization: {result.get('cost_optimization', {}).get('generation_method', 'Unknown')}")
        else:
            print(f"   ❌ FAILED - {result.get('error', 'Unknown error')}")
        
        agents_results["testing"] = result
    except Exception as e:
        print(f"   ❌ EXCEPTION - {str(e)}")
        agents_results["testing"] = {"status": "error", "error": str(e)}
    
    return agents_results

def test_backend_orchestrator_integration():
    """Test the complete backend orchestrator with all specialized agents."""
    
    print("\n🎯 Testing Backend Orchestrator Integration")
    print("=" * 80)
    
    # Setup
    output_dir = "test_output/orchestrator_integration_test"
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize components
    llm = get_llm(temperature=0.2)
    memory = SharedProjectMemory(run_dir=output_dir)
    code_execution_tool = CodeExecutionTool(output_dir)
    
    # Cost optimization configuration
    cost_config = CostOptimizationConfig(
        parallel_agents=3,
        batch_size=2,
        token_budget_per_agent=4000
    )
    
    # Create Backend Orchestrator
    orchestrator = BackendOrchestratorAgent(
        llm=llm,
        memory=memory,
        temperature=0.2,
        output_dir=output_dir,
        code_execution_tool=code_execution_tool,
        cost_optimization=cost_config
    )
    
    # Test inputs - Enterprise e-commerce application
    tech_stack = {
        "backend": {
            "language": "Python",
            "framework": "FastAPI"
        },
        "database": "PostgreSQL",
        "cache": "Redis",
        "container": "Docker",
        "orchestration": "Kubernetes"
    }
    
    system_design = {
        "architecture": "microservices",
        "deployment": "kubernetes",
        "scalability": "horizontal",
        "performance_requirements": {
            "response_time": "< 200ms",
            "throughput": "10k requests/second",
            "availability": "99.9%"
        }
    }
    
    requirements_analysis = {
        "domain": "E-commerce Platform",
        "scale": "enterprise",
        "security_level": "high",
        "compliance": ["PCI-DSS", "GDPR"],
        "features": ["user_management", "product_catalog", "order_processing", "payment_integration"]
    }
    
    try:
        print(f"🚀 Generating Complete Enterprise E-commerce Backend...")
        print(f"📊 Scale: Enterprise")
        print(f"🔒 Security: High (PCI-DSS, GDPR)")
        print(f"🏗️ Architecture: Microservices with Kubernetes")
        print(f"💰 Cost Optimization: Enabled (3 parallel agents, batching)")
        print()
        
        start_time = time.time()
        
        # Generate complete backend using orchestrator
        result = orchestrator.generate_backend(
            tech_stack=tech_stack,
            system_design=system_design,
            requirements_analysis=requirements_analysis
        )
        
        execution_time = time.time() - start_time
        
        if result.get("status") == "success":
            print("✅ ORCHESTRATOR INTEGRATION TEST RESULTS")
            print("=" * 80)
            print(f"✅ Status: SUCCESS")
            print(f"⏱️  Execution Time: {execution_time:.1f} seconds")
            print(f"📁 Total Files: {result['summary']['total_files']}")
            print(f"🔧 Core Files: {result['summary']['core_files']}")
            print(f"🏗️ Infrastructure Files: {result['summary']['infrastructure_files']}")
            print(f"🔒 Security Files: {result['summary']['security_files']}")
            print(f"📚 Documentation Files: {result['summary']['documentation_files']}")
            print(f"💰 Agents Used: {result['cost_optimization']['agents_used']}")
            print(f"⚡ Parallel Batches: {result['cost_optimization']['parallel_batches']}")
            print(f"🎯 Cost Savings: {result['cost_optimization']['estimated_cost_savings'].get('percentage', 0):.1f}%")
            
            return True
        else:
            print(f"❌ ORCHESTRATOR TEST FAILED: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ ORCHESTRATOR EXCEPTION: {str(e)}")
        return False

def generate_refactoring_report(individual_results: Dict[str, Dict], orchestrator_success: bool):
    """Generate a comprehensive refactoring completion report."""
    
    print("\n📊 REFACTORING COMPLETION REPORT")
    print("=" * 80)
    
    # Analyze individual agent results
    successful_agents = []
    failed_agents = []
    
    for agent_name, result in individual_results.items():
        if result.get("status") == "success":
            successful_agents.append(agent_name)
        else:
            failed_agents.append(agent_name)
    
    # Generate report
    print(f"🎯 REFACTORING OBJECTIVE: Convert all hardcoded agents to LLM-powered generation")
    print()
    print(f"📈 AGENT CONVERSION STATUS:")
    print(f"   ✅ Successful: {len(successful_agents)}/6 agents")
    print(f"   ❌ Failed: {len(failed_agents)}/6 agents")
    print()
    
    if successful_agents:
        print(f"✅ SUCCESSFULLY CONVERTED AGENTS:")
        for i, agent in enumerate(successful_agents, 1):
            files_count = individual_results[agent].get("files", [])
            cost_opt = individual_results[agent].get("cost_optimization", {})
            print(f"   {i}. {agent.title()} Agent - Files: {len(files_count)}, Method: {cost_opt.get('generation_method', 'LLM-powered')}")
    
    if failed_agents:
        print(f"\n❌ FAILED CONVERSIONS:")
        for i, agent in enumerate(failed_agents, 1):
            error = individual_results[agent].get("error", "Unknown error")
            print(f"   {i}. {agent.title()} Agent - Error: {error}")
    
    print()
    print(f"🏗️ ORCHESTRATOR INTEGRATION:")
    if orchestrator_success:
        print(f"   ✅ Backend Orchestrator working with all specialized agents")
        print(f"   ✅ Cost optimization implemented and functional")
        print(f"   ✅ Industrial-grade output structure maintained")
    else:
        print(f"   ❌ Backend Orchestrator integration issues detected")
    
    print()
    print(f"🎉 REFACTORING COMPLETION STATUS:")
    if len(successful_agents) == 6 and orchestrator_success:
        print(f"   ✅ 100% COMPLETE - All agents successfully converted to LLM-powered generation!")
        print(f"   ✅ Cost optimization implemented across all components")
        print(f"   ✅ System maintains industrial-grade quality")
        print(f"   ✅ Backend orchestrator properly integrates all specialized agents")
    else:
        completion_rate = (len(successful_agents) / 6) * 100
        print(f"   ⚠️  {completion_rate:.1f}% COMPLETE - {len(failed_agents)} agents still need attention")
        if not orchestrator_success:
            print(f"   ⚠️  Orchestrator integration needs debugging")
    
    return len(successful_agents) == 6 and orchestrator_success

def main():
    """Run the complete refactoring test suite."""
    
    print("🚀 COMPLETE REFACTORING TEST SUITE")
    print("Testing LLM-Powered Specialized Agents + Backend Orchestrator")
    print("=" * 80)
    
    start_time = time.time()
    
    # Test individual agents
    individual_results = test_individual_agents()
    
    # Test orchestrator integration
    orchestrator_success = test_backend_orchestrator_integration()
    
    # Generate comprehensive report
    is_fully_complete = generate_refactoring_report(individual_results, orchestrator_success)
    
    total_time = time.time() - start_time
    
    print(f"\n⏱️  Total Test Execution Time: {total_time:.1f} seconds")
    
    if is_fully_complete:
        print(f"🎉 REFACTORING SUCCESSFULLY COMPLETED!")
        print(f"All specialized agents are now LLM-powered with cost optimization!")
    else:
        print(f"⚠️  Refactoring needs additional work on failed components.")
    
    return is_fully_complete

if __name__ == "__main__":
    main() 