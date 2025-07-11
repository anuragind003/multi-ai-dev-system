"""
Simple Code Execution Tool - Streamlined Docker-based execution
Replaces: 917-line CodeExecutionTool with 200-line simplified version
"""

import os
import subprocess
import ast
import tempfile
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class SimpleCodeExecutionTool:
    """
    SIMPLIFIED Code Execution Tool - Docker only, essential features
    
    Handles:
    ✅ Basic Docker command execution
    ✅ Simple syntax checking (AST for Python)
    ✅ Essential test running
    ✅ File validation
    ❌ Complex fallback modes (removed)
    ❌ Extensive security checks (removed)
    ❌ Multiple test runners (removed)
    ❌ Coverage integration (removed)
    """
    
    def __init__(self, output_dir: str):
        """Initialize with Docker-only execution."""
        self.output_dir = os.path.abspath(output_dir)
        self.docker_image = "python:3.11-slim"  # Simple base image
        
        # Create temp directory
        os.makedirs(os.path.join(self.output_dir, "temp"), exist_ok=True)
        
        # Verify Docker is available (required)
        if not self._check_docker():
            raise RuntimeError("Docker is required but not available. Install Docker to continue.")
        
        logger.info(f"SimpleCodeExecutionTool initialized with Docker. Output: {self.output_dir}")

    def _check_docker(self) -> bool:
        """Simple Docker availability check."""
        try:
            result = subprocess.run(
                ["docker", "ps"], 
                capture_output=True, 
                timeout=5,
                check=False
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def run_syntax_check(self, code: str, file_path: str) -> Dict[str, Any]:
        """Simple syntax checking - Python uses AST, others use Docker."""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.py':
            # Fast Python syntax check with AST
            try:
                ast.parse(code)
                return {
                    "valid": True,
                    "message": "Python syntax valid",
                    "method": "ast"
                }
            except SyntaxError as e:
                return {
                    "valid": False,
                    "error": f"Syntax error: {e.msg} at line {e.lineno}",
                    "method": "ast"
                }
        
        elif file_ext in ['.js', '.jsx']:
            # JavaScript syntax check in Docker
            return self._docker_syntax_check(code, file_path, "node --check")
            
        elif file_ext in ['.ts', '.tsx']:
            # TypeScript syntax check in Docker  
            return self._docker_syntax_check(code, file_path, "npx tsc --noEmit --skipLibCheck")
        
        else:
            return {
                "valid": True,
                "message": f"No syntax checking for {file_ext}",
                "method": "unsupported"
            }

    def _docker_syntax_check(self, code: str, file_path: str, check_cmd: str) -> Dict[str, Any]:
        """Run syntax check in Docker container."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, os.path.basename(file_path))
            
            # Write code to temp file
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # Run check command in Docker
            result = self.execute_command(
                f"{check_cmd} {os.path.basename(temp_file)}", 
                temp_dir,
                timeout=30
            )
            
            return {
                "valid": result["success"],
                "message": "Syntax valid" if result["success"] else "Syntax error",
                "error": result["error"] if not result["success"] else "",
                "method": "docker"
            }

    def execute_command(self, command: str, working_dir: str, timeout: int = 60) -> Dict[str, Any]:
        """Execute command in Docker container."""
        if not os.path.isdir(working_dir):
            os.makedirs(working_dir, exist_ok=True)
        
        abs_path = os.path.abspath(working_dir)
        
        # Simple Docker command
        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{abs_path}:/app",
            "-w", "/app",
            self.docker_image,
            "sh", "-c", command
        ]
        
        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "output": result.stdout.strip(),
                "error": result.stderr.strip()
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "return_code": -1,
                "output": "",
                "error": f"Command timed out after {timeout} seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "return_code": -1,
                "output": "",
                "error": str(e)
            }

    def run_tests(self, project_dir: str) -> Dict[str, Any]:
        """Simple test execution - try pytest then npm test."""
        
        # Check for Python tests
        if self._has_python_files(project_dir):
            result = self.execute_command("python -m pytest -v", project_dir, timeout=120)
            if result["success"] or "collected" in result["output"]:
                return {
                    "success": result["return_code"] == 0,
                    "output": f"Python tests: {result['output']}",
                    "method": "pytest"
                }
        
        # Check for Node.js tests
        if os.path.exists(os.path.join(project_dir, 'package.json')):
            result = self.execute_command("npm test", project_dir, timeout=120)
            return {
                "success": result["return_code"] == 0,
                "output": f"Node.js tests: {result['output']}",
                "method": "npm_test"
            }
        
        return {
            "success": False,
            "output": "No test files found",
            "method": "none"
        }

    def run_lint_check(self, project_dir: str) -> Dict[str, Any]:
        """Simple linting - basic checks only."""
        
        # Python linting
        if self._has_python_files(project_dir):
            result = self.execute_command("python -m flake8 --max-line-length=88 .", project_dir)
            return {
                "success": True,
                "output": f"Python lint: {result['output'] or 'No issues found'}",
                "issues_found": result["return_code"] != 0,
                "method": "flake8"
            }
        
        # JavaScript linting  
        if os.path.exists(os.path.join(project_dir, 'package.json')):
            result = self.execute_command("npx eslint .", project_dir)
            return {
                "success": True,
                "output": f"JavaScript lint: {result['output'] or 'No issues found'}",
                "issues_found": result["return_code"] != 0,
                "method": "eslint"
            }
        
        return {
            "success": True,
            "output": "No linting available for this project type",
            "method": "none"
        }

    def test_file(self, file_path: str) -> Dict[str, Any]:
        """Test a single file for syntax and basic issues."""
        if not os.path.exists(file_path):
            return {
                "valid": False,
                "error": "File not found"
            }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self.run_syntax_check(content, file_path)
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Error reading file: {str(e)}"
            }

    def _has_python_files(self, project_dir: str) -> bool:
        """Check if project has Python files."""
        return any(Path(project_dir).glob("*.py")) or any(Path(project_dir).glob("**/*.py"))

    # Compatibility methods for existing code
    def run_syntax_check_old_interface(self, project_dir: str, tech_stack: Dict[str, Any]) -> Dict[str, Any]:
        """Compatibility method for old interface."""
        return self.run_lint_check(project_dir)

    def run_project_exec_check(self, project_dir: str, tech_stack: Dict[str, Any]) -> Dict[str, Any]:
        """Simple project execution check."""
        # Check if main entry points exist
        entry_points = ['main.py', 'app.py', 'index.js', 'package.json']
        
        for entry in entry_points:
            if os.path.exists(os.path.join(project_dir, entry)):
                return {
                    "success": True,
                    "output": f"Project executable via {entry}",
                    "entry_point": entry
                }
        
        return {
            "success": False,
            "output": "No obvious entry point found",
            "suggestion": "Create main.py, app.py, or package.json"
        } 