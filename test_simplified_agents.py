#!/usr/bin/env python3
"""
Test script to verify simplified agents are working correctly.
This test runs a simple workflow using the simplified agent architecture.
"""

import os
import sys
import asyncio
import json
import tempfile
import shutil
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import simplified agents
from agents.code_generation.simple_backend_agent import SimpleBackendAgent
from agents.code_generation.simple_frontend_agent import SimpleFrontendAgent
from agents.code_generation.simple_database_agent import SimpleDatabaseAgent
from agents.code_generation.simple_ops_agent import SimpleOpsAgent

# Import required components
from models.data_contracts import WorkItem
from tools.code_execution_tool import CodeExecutionTool

def create_mock_llm():
    """Create a mock LLM for testing"""
    class MockLLM:
        def __init__(self):
            self.call_count = 0
            
        def invoke(self, prompt):
            self.call_count += 1
            # Return a simple mock response in the expected multi-file format
            if "backend" in str(prompt).lower() or "api" in str(prompt).lower():
                return type('MockResponse', (), {
                    'content': """### FILE: main.py
```python
# Simple API server
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/products', methods=['GET'])
def get_products():
    return {'products': []}

@app.route('/api/products', methods=['POST'])
def create_product():
    return {'message': 'Product created'}

if __name__ == '__main__':
    app.run(debug=True)
```

### FILE: requirements.txt
```
flask==2.3.3
flask-cors==4.0.0
gunicorn==21.2.0
```"""
                })()
            elif "frontend" in str(prompt).lower() or "react" in str(prompt).lower():
                return type('MockResponse', (), {
                    'content': """### FILE: src/App.jsx
```jsx
import React from 'react';

function App() {
  return (
    <div>
      <h1>Product Manager</h1>
      <p>Simple product management interface</p>
    </div>
  );
}

export default App;
```

### FILE: package.json
```json
{
  "name": "product-manager",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build"
  }
}
```

### FILE: src/App.css
```css
.App {
  text-align: center;
  padding: 20px;
}

h1 {
  color: #333;
}
```"""
                })()
            elif "database" in str(prompt).lower():
                return type('MockResponse', (), {
                    'content': """### FILE: schema/001_initial_schema.sql
```sql
-- Products Database Schema
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_name ON products(name);
```

### FILE: seeds/001_sample_data.sql
```sql
-- Sample product data
INSERT INTO products (name, description, price) VALUES 
    ('Sample Product 1', 'First sample product', 9.99),
    ('Sample Product 2', 'Second sample product', 19.99);
```

### FILE: config/database.py
```python
import os
import sqlite3
from contextlib import contextmanager

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///products.db')

@contextmanager
def get_db_connection():
    conn = sqlite3.connect('products.db')
    try:
        yield conn
    finally:
        conn.close()
```"""
                })()
            else:  # ops/devops
                return type('MockResponse', (), {
                    'content': """### FILE: Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "main.py"]
```

### FILE: docker-compose.yml
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=development
```

### FILE: .github/workflows/ci.yml
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: python -m pytest tests/
```

### FILE: tests/test_main.py
```python
import unittest
from main import app

class TestAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
    
    def test_get_products(self):
        response = self.app.get('/api/products')
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
```

### FILE: README.md
```markdown
# Product Manager API

Simple product management system with REST API.

## Setup

```bash
pip install -r requirements.txt
python main.py
```

## API Endpoints

- GET /api/products - List all products
- POST /api/products - Create new product
```"""
                })()
                
    return MockLLM()

def test_simplified_agents():
    """Test all simplified agents with a simple product management system"""
    print("🧪 Testing Simplified Agent Architecture")
    print("=" * 50)
    
    # Create temporary test directory
    test_dir = tempfile.mkdtemp(prefix="simplified_agents_test_")
    print(f"📁 Test directory: {test_dir}")
    
    try:
        # Initialize mock components
        mock_llm = create_mock_llm()
        code_execution_tool = CodeExecutionTool(output_dir=test_dir)
        
        # Define test state (simplified version of actual state)
        test_state = {
            "brd_content": "Simple product management API with CRUD operations",
            "requirements_analysis": {
                "project_name": "Product Manager",
                "requirements": [
                    {"id": "REQ-001", "description": "Create API endpoints for products"},
                    {"id": "REQ-002", "description": "Store products in database"},
                    {"id": "REQ-003", "description": "Frontend to manage products"}
                ]
            },
            "tech_stack_recommendation": {
                "backend": {"name": "Python Flask"},
                "frontend": {"name": "React"},
                "database": {"name": "SQLite"}
            },
            "system_design": {
                "architecture_pattern": "REST API",
                "api_endpoints": [
                    {"path": "/api/products", "method": "GET"},
                    {"path": "/api/products", "method": "POST"},
                    {"path": "/api/products/<id>", "method": "PUT"},
                    {"path": "/api/products/<id>", "method": "DELETE"}
                ]
            }
        }
        
        # Test agents and work items
        test_cases = [
            {
                "agent_class": SimpleBackendAgent,
                "work_item": WorkItem(
                    id="BACKEND-001",
                    description="Create REST API for product management",
                    agent_role="backend_developer",
                    acceptance_criteria=["API endpoints created", "Database integration"],
                    estimated_time="2h",
                    dependencies=[]
                ),
                "expected_files": ["main.py", "requirements.txt"]
            },
            {
                "agent_class": SimpleFrontendAgent,
                "work_item": WorkItem(
                    id="FRONTEND-001", 
                    description="Create React frontend for product management",
                    agent_role="frontend_developer",
                    acceptance_criteria=["React components created", "API integration"],
                    estimated_time="3h",
                    dependencies=["BACKEND-001"]
                ),
                "expected_files": ["src/App.jsx", "package.json"]
            },
            {
                "agent_class": SimpleDatabaseAgent,
                "work_item": WorkItem(
                    id="DATABASE-001",
                    description="Design database schema for products",
                    agent_role="database_specialist", 
                    acceptance_criteria=["Schema created", "Migration scripts"],
                    estimated_time="1h",
                    dependencies=[]
                ),
                "expected_files": ["schema.sql"]
            },
            {
                "agent_class": SimpleOpsAgent,
                "work_item": WorkItem(
                    id="OPS-001",
                    description="Setup deployment and documentation",
                    agent_role="devops_specialist",
                    acceptance_criteria=["Docker setup", "Documentation"],
                    estimated_time="1h", 
                    dependencies=["BACKEND-001", "FRONTEND-001"]
                ),
                "expected_files": ["Dockerfile", "README.md"]
            }
        ]
        
        results = {}
        
        # Test each simplified agent
        for i, test_case in enumerate(test_cases, 1):
            agent_class = test_case["agent_class"]
            work_item = test_case["work_item"]
            expected_files = test_case["expected_files"]
            
            print(f"\n{i}. Testing {agent_class.__name__}")
            print(f"   Work Item: {work_item.id} - {work_item.description}")
            
            try:
                # Create agent instance
                agent = agent_class(
                    llm=mock_llm,
                    memory=None,  # Simplified for testing
                    temperature=0.1,
                    output_dir=test_dir,
                    code_execution_tool=code_execution_tool
                )
                
                # Run the agent
                result = agent.run(work_item=work_item, state=test_state)
                
                # Validate result - handle both CodeGenerationOutput objects and dict formats
                generated_files = []
                if hasattr(result, 'generated_files'):
                    # CodeGenerationOutput object
                    generated_files = result.generated_files
                    files_dict = {f.file_path: f.content for f in generated_files}
                elif isinstance(result, dict) and "generated_files" in result:
                    # Legacy dict format
                    generated_files = result["generated_files"]
                    files_dict = generated_files if isinstance(generated_files, dict) else {}
                else:
                    files_dict = {}
                
                if files_dict:
                    print(f"   ✅ Agent executed successfully")
                    print(f"   📄 Generated {len(files_dict)} files: {list(files_dict.keys())}")
                    
                    # Check if expected files were generated
                    missing_files = [f for f in expected_files if not any(f in path for path in files_dict.keys())]
                    if missing_files:
                        print(f"   ⚠️  Missing expected files: {missing_files}")
                    else:
                        print(f"   ✅ All expected files generated")
                    
                    results[work_item.id] = {
                        "status": "success",
                        "files_generated": len(files_dict),
                        "agent": agent_class.__name__
                    }
                else:
                    print(f"   ❌ Invalid result format from {agent_class.__name__}")
                    results[work_item.id] = {
                        "status": "error", 
                        "error": "Invalid result format",
                        "agent": agent_class.__name__
                    }
                    
            except Exception as e:
                print(f"   ❌ Error testing {agent_class.__name__}: {str(e)}")
                results[work_item.id] = {
                    "status": "error",
                    "error": str(e),
                    "agent": agent_class.__name__
                }
        
        # Print summary
        print(f"\n📊 Test Results Summary")
        print("=" * 30)
        
        successful_tests = [r for r in results.values() if r["status"] == "success"]
        failed_tests = [r for r in results.values() if r["status"] == "error"]
        
        print(f"✅ Successful: {len(successful_tests)}/{len(results)}")
        print(f"❌ Failed: {len(failed_tests)}/{len(results)}")
        
        if successful_tests:
            total_files = sum(r["files_generated"] for r in successful_tests)
            print(f"📄 Total files generated: {total_files}")
        
        # Print detailed results
        for work_id, result in results.items():
            status_icon = "✅" if result["status"] == "success" else "❌"
            print(f"{status_icon} {work_id}: {result['agent']} - {result['status']}")
            if result["status"] == "error":
                print(f"    Error: {result['error']}")
        
        print(f"\n🎯 Architecture Migration Test: {'PASSED' if len(failed_tests) == 0 else 'FAILED'}")
        print(f"   - Simplified agents are {'working correctly' if len(failed_tests) == 0 else 'experiencing issues'}")
        print(f"   - Migration from 13 complex agents to 4 simple agents: {'✅ SUCCESSFUL' if len(failed_tests) == 0 else '❌ ISSUES DETECTED'}")
        
        return len(failed_tests) == 0
        
    finally:
        # Cleanup
        try:
            shutil.rmtree(test_dir)
            print(f"\n🧹 Cleaned up test directory: {test_dir}")
        except Exception as e:
            print(f"⚠️  Failed to cleanup test directory: {e}")

if __name__ == "__main__":
    print("🚀 Starting Simplified Agent Architecture Test")
    success = test_simplified_agents()
    
    if success:
        print("\n🎉 All tests passed! Simplified architecture is working correctly.")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed. Please check the output above.")
        sys.exit(1) 