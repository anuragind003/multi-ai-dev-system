#!/usr/bin/env python3
"""
Simple MCP Setup Script
Installs required dependencies and tests basic MCP integration.
"""

import subprocess
import sys
import importlib
from pathlib import Path

def check_and_install_package(package_name, import_name=None):
    """Check if a package is installed and install it if not."""
    if import_name is None:
        import_name = package_name
    
    try:
        importlib.import_module(import_name)
        print(f"✅ {package_name} is already installed")
        return True
    except ImportError:
        print(f"❌ {package_name} not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            print(f"✅ {package_name} installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package_name}: {e}")
            return False

def install_core_dependencies():
    """Install core dependencies for MCP integration."""
    print("🔧 Installing Core Dependencies")
    print("-" * 40)
    
    core_packages = [
        ("pydantic", "pydantic"),
        ("langchain-core", "langchain_core"),
        ("langgraph", "langgraph"),
        ("langgraph-checkpoint", "langgraph.checkpoint"),
        ("mcp", "mcp"),
        ("pydantic-ai", "pydantic_ai")
    ]
    
    success_count = 0
    for package, import_name in core_packages:
        if check_and_install_package(package, import_name):
            success_count += 1
    
    print(f"\n✅ {success_count}/{len(core_packages)} packages installed successfully")
    return success_count == len(core_packages)

def test_basic_imports():
    """Test basic imports after installation."""
    print("\n🧪 Testing Basic Imports")
    print("-" * 40)
    
    test_imports = [
        ("pydantic", "from pydantic import BaseModel"),
        ("langchain_core", "from langchain_core.messages import HumanMessage"),
        ("langgraph", "from langgraph.graph import StateGraph"),
        ("mcp", "import mcp")
    ]
    
    success_count = 0
    for name, import_statement in test_imports:
        try:
            exec(import_statement)
            print(f"✅ {name}: Import successful")
            success_count += 1
        except ImportError as e:
            print(f"❌ {name}: Import failed - {e}")
        except Exception as e:
            print(f"⚠️  {name}: Import warning - {e}")
    
    return success_count == len(test_imports)

def create_simple_mcp_test():
    """Create a simple MCP test that doesn't require external servers."""
    print("\n📝 Creating Simple MCP Test")
    print("-" * 40)
    
    test_code = '''#!/usr/bin/env python3
"""
Simple MCP Test - No External Dependencies Required
"""
import asyncio
import json
from pathlib import Path

try:
    from pydantic import BaseModel, Field
    from langchain_core.messages import HumanMessage, AIMessage
    from langgraph.graph import StateGraph, START, END
    
    print("All imports successful!")
    
    class SimpleMCPState(BaseModel):
        """Simple state for testing."""
        messages: list = Field(default_factory=list)
        operations: dict = Field(default_factory=dict)
    
    def create_simple_workflow():
        """Create a simple workflow for testing."""
        workflow = StateGraph(SimpleMCPState)
        
        def process_message(state):
            if state.messages:
                last_msg = state.messages[-1]
                response = f"Processed: {last_msg.content if hasattr(last_msg, 'content') else str(last_msg)}"
                state.messages.append({"role": "assistant", "content": response})
            return state
        
        workflow.add_node("process", process_message)
        workflow.add_edge(START, "process")
        workflow.add_edge("process", END)
        
        return workflow
    
    async def test_workflow():
        """Test the simple workflow."""
        workflow = create_simple_workflow()
        app = workflow.compile()
        
        initial_state = SimpleMCPState(
            messages=[{"role": "user", "content": "Hello MCP!"}]
        )
        
        result = await app.ainvoke(initial_state)
        print("Workflow test successful!")
        print(f"Result: {result}")
        return True
    
    # Run the test
    asyncio.run(test_workflow())
    print("\\nSimple MCP test completed successfully!")
    
except ImportError as e:
    print(f"Import error: {e}")    print("Please run the setup script first to install dependencies.")
except Exception as e:
    print(f"Test error: {e}")
'''
    
    test_file = Path("simple_mcp_test.py")
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_code)
    
    print(f"Created simple test file: {test_file}")
    return test_file

def main():
    """Main setup function."""
    print("🚀 MCP Setup and Test Script")
    print("=" * 50)
    
    # Install dependencies
    if not install_core_dependencies():
        print("❌ Failed to install all dependencies. Some tests may fail.")
    
    # Test imports
    if test_basic_imports():
        print("✅ All imports working correctly!")
    else:
        print("⚠️  Some imports failed. Creating fallback test...")
    
    # Create simple test
    test_file = create_simple_mcp_test()
    
    print(f"\n📋 Next Steps:")
    print(f"1. Run: python {test_file}")
    print("2. If successful, try: python test_mcp_integration.py")
    print("3. For full MCP server support, install npm packages:")
    print("   npm install -g @modelcontextprotocol/server-filesystem")
    print("   npm install -g @modelcontextprotocol/server-git")

if __name__ == "__main__":
    main()
