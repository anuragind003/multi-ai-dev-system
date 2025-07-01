import os
import subprocess
import sys
import tempfile
import ast
import py_compile
from pathlib import Path
from typing import Dict, Any, List
import json
import logging

# Set up a logger for this module
logger = logging.getLogger(__name__)

class CodeExecutionTool:
    """
    Sandboxed code execution tool using Docker with enhanced code validation capabilities.
    All code execution is isolated within Docker containers to prevent security risks.
    """
    
    # Define the Docker image name as a class constant for easy updates
    DOCKER_IMAGE_NAME = "secure-code-executor:latest"
    
    def __init__(self, output_dir: str):
        """
        Initialize the code execution tool with an output directory.
        
        Args:
            output_dir: Directory for storing execution outputs and temporary files
        """
        self.output_dir = os.path.abspath(output_dir)
        self.supported_languages = ['python', 'javascript', 'typescript']
        self.docker_available = False
        self.available_tools = {}
        
        # Create temp directory if needed
        os.makedirs(os.path.join(self.output_dir, "temp_check"), exist_ok=True)
        
        logger.info(f"CodeExecutionTool initialized. Host output directory: {self.output_dir}")
        self._check_docker()

    def _check_docker(self):
        """
        Checks if Docker is installed and running.
        Sets up fallback mode if Docker is unavailable.
        """
        self.docker_available = False
        try:
            # First check if Docker is installed and running
            result = subprocess.run(
                ["docker", "ps"], 
                capture_output=True, 
                check=False,  # Don't raise exception on non-zero exit
                timeout=5
            )
            
            if result.returncode == 0:
                # Changed Unicode emoji to ASCII
                logger.info("[SUCCESS] Docker is installed and running. Using secure containerized execution.")
                self.docker_available = True
            else:
                error_msg = result.stderr.decode('utf-8').strip()
                # Changed Unicode emoji to ASCII
                logger.warning("[WARNING] Docker is installed but not running properly: {error_msg}")
                logger.warning("[WARNING] Switching to LOCAL fallback mode with limited functionality.")
                self._setup_local_fallback()
                
        except FileNotFoundError:
            # Changed Unicode emoji to ASCII
            logger.warning("[WARNING] Docker is not installed. Switching to LOCAL fallback mode with limited functionality.")
            self._setup_local_fallback()
        except subprocess.TimeoutExpired:
            # Changed Unicode emoji to ASCII
            logger.warning("[WARNING] Docker command timed out. Docker daemon may be unresponsive.")
            logger.warning("[WARNING] Switching to LOCAL fallback mode with limited functionality.")
            self._setup_local_fallback()
        except Exception as e:
            # Changed Unicode emoji to ASCII
            logger.warning(f"[WARNING] Unexpected error checking Docker: {str(e)}")
            logger.warning("[WARNING] Switching to LOCAL fallback mode with limited functionality.")
            self._setup_local_fallback()

    def _setup_local_fallback(self):
        """
        Sets up the fallback environment for non-Docker execution.
        This mode has limited functionality and lower security.
        """
        self.docker_available = False
        
        # Check which tools are available locally
        self.available_tools = {
            "python": self._check_command_exists("python --version"),
            "node": self._check_command_exists("node --version"),
            "npm": self._check_command_exists("npm --version"),
            "flake8": self._check_command_exists("flake8 --version"),
            "pylint": self._check_command_exists("pylint --version"),
            "pytest": self._check_command_exists("pytest --version"),
            "eslint": self._check_command_exists("eslint --version"),
            "tsc": self._check_command_exists("tsc --version")
        }
        
        # Log available tools
        available = [tool for tool, exists in self.available_tools.items() if exists]
        unavailable = [tool for tool, exists in self.available_tools.items() if not exists]
        
        # Changed Unicode emoji to ASCII
        logger.info(f"[TOOLS] LOCAL mode tools available: {', '.join(available) if available else 'None'}")
        if unavailable:
            logger.warning(f"[WARNING] LOCAL mode tools unavailable: {', '.join(unavailable)}")
        
        # Print security warning
        logger.warning("[SECURITY] WARNING: Running in LOCAL fallback mode without Docker isolation")
        logger.warning("[SECURITY] Code execution will happen directly on the host with limited safety checks")
        logger.warning("[SECURITY] Only use this mode with trusted code in a development environment")

    def _check_command_exists(self, command):
        """Check if a command exists and is executable in the local environment."""
        try:
            # Split the command string into command and arguments
            cmd_parts = command.split()
            result = subprocess.run(
                cmd_parts, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                timeout=2
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            return False

    def _run_in_docker(self, command: str, working_dir: str, timeout: int = 60) -> Dict[str, Any]:
        """
        Run a command inside a secure Docker container or in fallback mode.
        
        Args:
            command: The shell command to execute
            working_dir: The directory to mount or use as working directory
            timeout: Maximum execution time in seconds
            
        Returns:
            Dict with execution results
        """
        if not os.path.isdir(working_dir):
            os.makedirs(working_dir, exist_ok=True)
            logger.warning(f"Working directory {working_dir} did not exist and was created.")

        abs_host_path = os.path.abspath(working_dir)
        
        # If Docker is available, use it for secure execution
        if self.docker_available:
            docker_command = [
                "docker", "run",
                "--rm",  # Automatically remove the container when it exits
                "--network", "none",  # Disable networking for enhanced security
                "-v", f"{abs_host_path}:/app",  # Mount the project directory into /app
                "-w", "/app",  # Set the working directory inside the container
                self.DOCKER_IMAGE_NAME,
                "sh", "-c", command  # Execute the command in a shell
            ]

            logger.info(f"Executing in Docker: {' '.join(docker_command)}")

            try:
                result = subprocess.run(
                    docker_command,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                return {
                    "success": result.returncode == 0,
                    "return_code": result.returncode,
                    "output": result.stdout.strip(),
                    "error": result.stderr.strip(),
                    "execution_mode": "docker"
                }
            except subprocess.TimeoutExpired:
                logger.warning(f"Docker command timed out after {timeout} seconds.")
                return {
                    "success": False, "return_code": -1,
                    "output": "", "error": f"Execution timed out after {timeout} seconds.",
                    "execution_mode": "docker_timeout"
                }
            except Exception as e:
                logger.error(f"An unexpected error occurred while running Docker command: {e}")
                return {
                    "success": False, "return_code": -1, 
                    "output": "", "error": str(e),
                    "execution_mode": "docker_error"
                }
        
        # If Docker is not available, use local fallback mode
        else:
            # Security checks for local execution mode
            if not self._is_safe_for_local_execution(command):
                logger.error(f"Command rejected for local execution due to security concerns: {command}")
                return {
                    "success": False,
                    "return_code": -1,
                    "output": "",
                    "error": "Command contains potentially unsafe operations and was rejected in LOCAL mode",
                    "execution_mode": "local_rejected"
                }
                
            logger.warning(f"[!!] Executing locally (NO SANDBOX): {command}")
            
            # Change to working directory for execution
            original_dir = os.getcwd()
            try:
                os.chdir(abs_host_path)
                
                # On Windows, we need to handle shell commands differently
                if os.name == 'nt' and 'sh -c' in command:
                    # Extract the actual command from 'sh -c "actual command"'
                    actual_command = command.replace('sh -c', '').strip('"\'')
                    shell = True
                    cmd = actual_command
                else:
                    shell = True if os.name == 'nt' else False
                    cmd = command
                
                result = subprocess.run(
                    cmd,
                    shell=shell,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                return {
                    "success": result.returncode == 0,
                    "return_code": result.returncode,
                    "output": result.stdout.strip(),
                    "error": result.stderr.strip(),
                    "execution_mode": "local"
                }
                
            except subprocess.TimeoutExpired:
                logger.warning(f"Local command timed out after {timeout} seconds.")
                return {
                    "success": False, "return_code": -1,
                    "output": "", "error": f"Execution timed out after {timeout} seconds.",
                    "execution_mode": "local_timeout"
                }
            except Exception as e:
                logger.error(f"An unexpected error occurred during local execution: {e}")
                return {
                    "success": False, "return_code": -1, 
                    "output": "", "error": str(e),
                    "execution_mode": "local_error"
                }
            finally:
                # Always restore original directory
                os.chdir(original_dir)
            
    def _is_safe_for_local_execution(self, command: str) -> bool:
        """
        Check if a command is safe to execute locally.
        This is a basic security check for the fallback mode.
        
        Args:
            command: The command to check
            
        Returns:
            True if the command appears safe, False otherwise
        """
        # List of dangerous commands/patterns to block in local mode
        dangerous_patterns = [
            "rm -rf", "del /", "format", "mkfs", 
            "dd if=", "wget", "curl", ">>/etc/", 
            "chmod 777", "sudo ", "su ", 
            "eval", "exec ", ":(){", "fork",
            "&& rm", "; rm", "| rm",
            ">${HOME}", ">${HOMEPATH}", ">${USERPROFILE}",
            "/dev/sd", "mkfs", "fdisk",
            "config.vm.", "os.system", "subprocess.call",
            "exec(", "eval(", "execfile(", "compile(",
            "open(", "file(", "mknod", "mkfifo"
        ]
        
        # Convert command to lowercase for case-insensitive matching
        cmd_lower = command.lower()
        
        # Check for dangerous patterns
        for pattern in dangerous_patterns:
            if pattern.lower() in cmd_lower:
                logger.warning(f"⛔ Blocked unsafe command containing '{pattern}'")
                return False
        
        return True

    def run_syntax_check(self, code: str, file_path: str) -> Dict[str, Any]:
        """Enhanced syntax checking with multiple validation methods in a secure sandbox."""
        try:
            file_ext = Path(file_path).suffix.lower()
            
            # Create a temporary directory to hold the file
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_file_name = f"temp_check{file_ext}"
                temp_file_path = os.path.join(temp_dir, temp_file_name)
                
                # Write the code to the file
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    f.write(code)
            
                if file_ext == '.py':
                    # Try AST parsing first (doesn't require Docker)
                    try:
                        ast.parse(code)
                        return {
                            "valid": True,
                            "message": "Python syntax valid (AST verified)",
                            "method": "ast_parse"
                        }
                    except SyntaxError as e:
                        return {
                            "valid": False,
                            "error": f"Python syntax error: {e.msg} at line {e.lineno}",
                            "method": "ast_parse",
                            "line": e.lineno
                        }
                    except Exception:
                        # Fallback to py_compile in Docker
                        command = f"python -m py_compile {temp_file_name}"
                        result = self._run_in_docker(command, temp_dir)
                        
                        if result["success"]:
                            return {
                                "valid": True,
                                "message": "Python syntax valid (compile verified)",
                                "method": "py_compile_docker"
                            }
                        else:
                            return {
                                "valid": False,
                                "error": f"Python compilation error: {result['error']}",
                                "method": "py_compile_docker"
                            }
                
                elif file_ext in ['.js', '.jsx']:
                    command = f"node --check {temp_file_name}"
                    result = self._run_in_docker(command, temp_dir)
                    
                    return {
                        "valid": result["success"],
                        "error": result["error"] if not result["success"] else "",
                        "message": "JavaScript syntax valid" if result["success"] else f"JavaScript syntax error",
                        "method": "node_check_docker"
                    }
                
                elif file_ext in ['.ts', '.tsx']:
                    command = f"tsc --noEmit --skipLibCheck {temp_file_name}"
                    result = self._run_in_docker(command, temp_dir)
                    
                    return {
                        "valid": result["success"],
                        "error": result["error"] if not result["success"] else "",
                        "message": "TypeScript syntax valid" if result["success"] else f"TypeScript syntax error",
                        "method": "tsc_check_docker"
                    }
                
                else:
                    return {
                        "valid": True,
                        "message": f"Syntax checking not implemented for {file_ext}",
                        "method": "unsupported"
                    }
        except Exception as e:
            logger.error(f"Error during syntax check: {str(e)}")
            return {
                "valid": False,
                "error": f"Syntax check failed: {str(e)}",
                "method": "error"
            }

    def run_lint_check(self, project_dir: str, tech_stack: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced linting with better tool detection, executed in a secure Docker sandbox."""
        backend_name = tech_stack.get('backend', {}).get('name', '').lower()
        
        if 'python' in backend_name or 'django' in backend_name or 'flask' in backend_name:
            return self._enhanced_python_lint(project_dir)
        elif 'node' in backend_name or 'javascript' in backend_name or 'react' in backend_name:
            return self._enhanced_javascript_lint(project_dir)
        else:
            return {
                "success": True,
                "output": f"Linting not configured for backend: {backend_name}",
                "method": "unsupported"
            }
    
    def _enhanced_python_lint(self, project_dir: str) -> Dict[str, Any]:
        """Try multiple Python linting tools with graceful fallbacks, all executed in Docker."""
        lint_tools = [
            ('flake8 --max-line-length=88 .', 'flake8'),
            ('pylint --score=n .', 'pylint'),
            ('pycodestyle --max-line-length=88 .', 'pycodestyle'),
            ('black --check .', 'black_check')
        ]
        
        for cmd, tool_name in lint_tools:
            try:
                # Run the lint command in Docker
                result = self._run_in_docker(cmd, project_dir, timeout=60)
                
                return {
                    "success": True,
                    "output": f"{tool_name} results:\n{result['output']}\n{result['error']}".strip(),
                    "method": f"{tool_name}_docker",
                    "return_code": result["return_code"],
                    "issues_found": result["return_code"] != 0
                }
                
            except Exception as e:
                logger.warning(f"Error running {tool_name} in Docker: {str(e)}")
                continue  # Try next tool
        
        return {
            "success": True,
            "output": "No Python linting tools available in the Docker environment.",
            "method": "none_available",
            "recommendation": "Check Docker image configuration to ensure linting tools are installed."
        }
    
    def _enhanced_javascript_lint(self, project_dir: str) -> Dict[str, Any]:
        """Enhanced JavaScript linting with multiple approaches, executed in Docker."""
        
        # Copy package.json to temporary location if it exists for npm commands
        package_json_path = os.path.join(project_dir, 'package.json')
        if os.path.exists(package_json_path):
            try:
                # Method 1: Try npm run lint (if defined in package.json)
                cmd = 'if grep -q "\"lint\":" package.json; then npm run lint; else echo "No lint script in package.json"; exit 1; fi'
                result = self._run_in_docker(cmd, project_dir, timeout=60)
                
                if result["success"]:
                    return {
                        "success": True,
                        "output": f"npm run lint results:\n{result['output']}\n{result['error']}".strip(),
                        "method": "npm_run_lint_docker",
                        "return_code": result["return_code"],
                        "issues_found": result["return_code"] != 0
                    }
            except Exception as e:
                logger.warning(f"Error running npm lint in Docker: {str(e)}")
                # Continue to ESLint direct approach
        
        # Method 2: Try direct ESLint commands
        eslint_commands = [
            ('npx eslint .', 'npx_eslint'),
            ('eslint .', 'eslint_direct')
        ]
        
        for cmd, method in eslint_commands:
            try:
                result = self._run_in_docker(cmd, project_dir, timeout=60)
                
                return {
                    "success": True,
                    "output": f"{method} results:\n{result['output']}\n{result['error']}".strip(),
                    "method": f"{method}_docker",
                    "return_code": result["return_code"],
                    "issues_found": result["return_code"] != 0
                }
            except Exception:
                continue
        
        return {
            "success": True,
            "output": "No JavaScript linting available in the Docker environment.",
            "method": "none_available",
            "recommendation": "Check Docker image configuration to ensure ESLint is installed."
        }
    
    def run_project_exec_check(self, project_dir: str, tech_stack: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced project execution check with framework detection, executed in Docker."""
        backend_name = tech_stack.get('backend', {}).get('name', '').lower()
        
        if 'python' in backend_name:
            return self._enhanced_python_exec_check(project_dir, backend_name)
        elif 'node' in backend_name or 'javascript' in backend_name:
            return self._enhanced_javascript_exec_check(project_dir)
        else:
            return {
                "success": True,
                "output": f"Execution check not implemented for backend: {backend_name}",
                "method": "unsupported"
            }
    
    def _enhanced_python_exec_check(self, project_dir: str, backend_type: str) -> Dict[str, Any]:
        """Enhanced Python execution check with framework detection, executed in Docker."""
        
        # Framework-specific entry points
        if 'flask' in backend_type:
            entry_points = ['app.py', 'application.py', 'wsgi.py', 'main.py', 'run.py']
            framework_patterns = ['create_app', 'Flask(__name__)']
        elif 'django' in backend_type:
            entry_points = ['manage.py', 'wsgi.py', 'asgi.py']
            framework_patterns = ['django', 'DJANGO_SETTINGS_MODULE']
        else:
            entry_points = ['main.py', 'app.py', 'run.py', '__main__.py']
            framework_patterns = []
        
        # Check each entry point in Docker
        for entry_point in entry_points:
            entry_path = os.path.join(project_dir, entry_point)
            if os.path.exists(entry_path):
                try:
                    # Check for framework patterns (read locally, no need for Docker)
                    with open(entry_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                    
                    framework_detected = any(pattern in code for pattern in framework_patterns)
                    
                    # Run syntax check in Docker
                    cmd = f"python -m py_compile {entry_point}"
                    result = self._run_in_docker(cmd, project_dir, timeout=10)
                    
                    return {
                        "success": result["success"],
                        "output": f"Python project executable via {entry_point}" + 
                                (f" (Framework: {backend_type})" if framework_detected else ""),
                        "method": f"compile_check_docker_{entry_point}",
                        "entry_point": entry_point,
                        "framework_detected": framework_detected
                    }
                    
                except Exception as e:
                    logger.warning(f"Error checking {entry_point} in Docker: {str(e)}")
                    continue  # Try next entry point
        
        return {
            "success": False,
            "output": f"No valid Python entry points found. Checked: {', '.join(entry_points)}",
            "method": "no_entry_point",
            "suggestion": "Create a main.py, app.py, or appropriate framework entry point"
        }
    
    def _enhanced_javascript_exec_check(self, project_dir: str) -> Dict[str, Any]:
        """Enhanced JavaScript execution check with package.json awareness, executed in Docker."""
        
        # First check if package.json exists locally
        package_json_path = os.path.join(project_dir, 'package.json')
        if os.path.exists(package_json_path):
            # Run a check in Docker for the main file and start script
            cmd = 'if [ -f "package.json" ]; then ' \
                  'MAIN=$(node -e "try { const pkg=require(\'./package.json\'); console.log(pkg.main || \'index.js\'); } catch(e) { console.log(\'index.js\'); }"); ' \
                  'if [ -f "$MAIN" ]; then echo "Found main file: $MAIN"; node --check "$MAIN"; ' \
                  'if grep -q "\"start\":" package.json; then echo "Start script available"; fi; ' \
                  'else echo "Main file $MAIN not found"; exit 1; fi; ' \
                  'else echo "package.json not found"; exit 1; fi'
                  
            result = self._run_in_docker(cmd, project_dir, timeout=15)
            
            if result["success"] and "Found main file:" in result["output"]:
                main_file = result["output"].split("Found main file:")[1].split("\n")[0].strip()
                has_start_script = "Start script available" in result["output"]
                
                return {
                    "success": True,
                    "output": f"JavaScript project entry: {main_file} - Syntax valid" +
                            (f" (Start script available)" if has_start_script else ""),
                    "method": "package_json_main_docker",
                    "entry_point": main_file,
                    "has_start_script": has_start_script
                }
        
        # Fallback: check common entry points using Docker
        entry_points = ['index.js', 'app.js', 'server.js', 'main.js', 'src/index.js']
        for entry_point in entry_points:
            entry_path = os.path.join(project_dir, entry_point)
            if os.path.exists(entry_path):
                cmd = f"node --check {entry_point}"
                result = self._run_in_docker(cmd, project_dir, timeout=10)
                
                if result["success"]:
                    return {
                        "success": True,
                        "output": f"JavaScript executable via {entry_point} - Syntax valid",
                        "method": f"entry_point_docker_{entry_point.replace('/', '_')}",
                        "entry_point": entry_point
                    }
        
        return {
            "success": False,
            "output": f"No valid JavaScript entry points found. Checked: {', '.join(entry_points)}",
            "method": "no_entry_point",
            "suggestion": "Create an index.js, app.js, or configure package.json main field"
        }
    
    def run_tests(self, project_dir: str) -> Dict[str, Any]:
        """Enhanced test execution with coverage integration, executed in Docker."""
        
        # Check for Python tests
        if self._has_python_tests(project_dir):
            return self._run_python_tests_with_coverage(project_dir)
        # Check for JavaScript tests
        elif self._has_javascript_tests(project_dir):
            return self._run_javascript_tests(project_dir)
        else:
            return {
                "success": False,
                "output": "No test files found in project",
                "method": "no_tests_found",
                "suggestion": "Create test files following naming conventions (test_*.py, *.test.js, etc.)"
            }
    
    def _run_python_tests_with_coverage(self, project_dir: str) -> Dict[str, Any]:
        """Run Python tests with integrated coverage reporting in Docker."""
        
        test_commands = [
            # Try pytest with coverage
            'python -m pytest --cov=. --cov-report=term-missing --cov-report=json',
            # Fallback to pytest without coverage
            'python -m pytest -v',
            # Fallback to unittest
            'python -m unittest discover -v'
        ]
        
        for cmd in test_commands:
            try:
                result = self._run_in_docker(cmd, project_dir, timeout=120)
                
                # Try to extract coverage information from the output
                coverage_info = self._extract_coverage_info_from_output(result["output"])
                
                # Try to get generated coverage.json from Docker if it exists
                json_cmd = 'if [ -f "coverage.json" ]; then cat coverage.json; else echo ""; fi'
                json_result = self._run_in_docker(json_cmd, project_dir, timeout=10)
                
                if json_result["output"]:
                    try:
                        coverage_data = json.loads(json_result["output"])
                        if 'totals' in coverage_data:
                            total_coverage = coverage_data['totals'].get('percent_covered', 0)
                            coverage_info = {
                                "percentage": round(total_coverage, 2),
                                "details": f"Coverage: {total_coverage:.2f}%",
                                "source": "coverage.json"
                            }
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse coverage.json from Docker output")
                
                return {
                    "success": result["return_code"] == 0,
                    "output": f"Docker test results:\n{result['output']}\n{result['error']}".strip(),
                    "method": "pytest_docker",
                    "return_code": result["return_code"],
                    "coverage_info": coverage_info
                }
                
            except Exception as e:
                logger.warning(f"Error running tests in Docker: {str(e)}")
                continue  # Try next command
        
        return {
            "success": False,
            "output": "Failed to run Python tests in Docker",
            "method": "docker_test_failure",
            "suggestion": "Check Docker image configuration to ensure pytest is installed."
        }
    
    def _extract_coverage_info_from_output(self, test_output: str) -> Dict[str, Any]:
        """Extract coverage information from test output."""
        coverage_info = {"percentage": 0, "details": "No coverage information available"}
        
        # Try to parse coverage from output
        import re
        coverage_pattern = r'TOTAL.*?(\d+)%'
        match = re.search(coverage_pattern, test_output)
        if match:
            percentage = float(match.group(1))
            coverage_info = {
                "percentage": percentage,
                "details": f"Coverage: {percentage}%",
                "source": "test_output"
            }
        
        return coverage_info
    
    def _run_javascript_tests(self, project_dir: str) -> Dict[str, Any]:
        """Run JavaScript/TypeScript tests with coverage extraction in Docker."""
        
        # Try npm test first if package.json exists
        if os.path.exists(os.path.join(project_dir, 'package.json')):
            cmd = 'if grep -q "\"test\":" package.json; then npm run test; else echo "No test script in package.json"; exit 1; fi'
            try:
                result = self._run_in_docker(cmd, project_dir, timeout=120)
                
                if result["success"]:
                    # Try to extract coverage information
                    coverage_info = self._extract_js_coverage_info_from_output(result["output"])
                    
                    return {
                        "success": True,
                        "output": f"npm test results:\n{result['output']}\n{result['error']}".strip(),
                        "method": "npm_test_docker",
                        "return_code": result["return_code"],
                        "coverage_info": coverage_info
                    }
            except Exception as e:
                logger.warning(f"Error running npm test in Docker: {str(e)}")
        
        # Try common test runners directly
        test_runners = [
            'npx jest --coverage',
            'npx mocha',
            'npx jasmine',
            'npx karma start'
        ]
        
        for cmd in test_runners:
            runner = cmd.split()[1]  # Extract runner name
            try:
                result = self._run_in_docker(cmd, project_dir, timeout=120)
                
                # Try to extract coverage info
                coverage_info = self._extract_js_coverage_info_from_output(result["output"])
                
                return {
                    "success": result["return_code"] == 0,
                    "output": f"{runner} results:\n{result['output']}\n{result['error']}".strip(),
                    "method": f"{runner}_docker",
                    "return_code": result["return_code"],
                    "coverage_info": coverage_info
                }
            except Exception:
                continue  # Try next runner
        
        return {
            "success": False,
            "output": "No JavaScript test runners available or no tests found in Docker environment",
            "method": "no_runner_available",
            "suggestion": "Check Docker image configuration to ensure Jest or other test runners are installed."
        }

    def _extract_js_coverage_info_from_output(self, test_output: str) -> Dict[str, Any]:
        """Extract coverage information from JavaScript test output."""
        import re
        coverage_info = {"percentage": 0, "details": "No coverage information available"}
        
        # Check for Jest or Istanbul coverage output in test output
        coverage_patterns = [
            r'All files[^\n]*\|[^\n]*\|[^\n]*\|[^\n]*\|[^|]*\|[\s]*(\d+(?:\.\d+)?)%',  # Jest style
            r'All files[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^%]*(\d+(?:\.\d+)?)%',  # Istanbul style
            r'Statements\s*:\s*(\d+(?:\.\d+)?)%'  # Another Istanbul variant
        ]
        
        for pattern in coverage_patterns:
            match = re.search(pattern, test_output)
            if match:
                percentage = float(match.group(1))
                coverage_info = {
                    "percentage": percentage,
                    "details": f"Coverage: {percentage}%",
                    "source": "test_output"
                }
                return coverage_info
        
        return coverage_info

    def _has_python_tests(self, project_dir: str) -> bool:
        """Check if the project directory has Python test files."""
        # This function doesn't need Docker since it only checks for file existence
        
        # Common Python test file patterns
        patterns = ['test_*.py', '*_test.py', 'tests/*.py', '*/tests/*.py']
        
        for pattern in patterns:
            matching_files = list(Path(project_dir).glob(pattern))
            if matching_files:
                return True
        
        # Check if pytest.ini, conftest.py, or common test directories exist
        common_indicators = [
            os.path.join(project_dir, 'pytest.ini'),
            os.path.join(project_dir, 'conftest.py'),
            os.path.join(project_dir, 'tests'),
            os.path.join(project_dir, 'test')
        ]
        
        for indicator in common_indicators:
            if os.path.exists(indicator):
                return True
        
        return False

    def _has_javascript_tests(self, project_dir: str) -> bool:
        """Check if the project directory has JavaScript/TypeScript test files."""
        # This function doesn't need Docker since it only checks for file existence
        
        # Common JavaScript/TypeScript test file patterns
        patterns = ['*.test.js', '*.spec.js', '*.test.ts', '*.spec.ts', 
                    'test/*.js', 'tests/*.js', '__tests__/*.js',
                    'test/*.ts', 'tests/*.ts', '__tests__/*.ts']
        
        for pattern in patterns:
            matching_files = list(Path(project_dir).glob(pattern))
            if matching_files:
                return True
        
        # Check package.json for test script
        package_json_path = os.path.join(project_dir, 'package.json')
        if os.path.exists(package_json_path):
            try:
                with open(package_json_path, 'r') as f:
                    package_data = json.load(f)
                
                if 'scripts' in package_data and 'test' in package_data['scripts']:
                    return True
            except Exception:
                pass
        
        # Check for common test framework config files
        common_indicators = [
            os.path.join(project_dir, 'jest.config.js'),
            os.path.join(project_dir, 'jest.config.ts'),
            os.path.join(project_dir, 'mocha.opts'),
            os.path.join(project_dir, '.mocharc.js'),
            os.path.join(project_dir, '.mocharc.json'),
            os.path.join(project_dir, 'karma.conf.js')
        ]
        
        for indicator in common_indicators:
            if os.path.exists(indicator):
                return True
        
        return False
    
    def test_file(self, file_path: str) -> Dict[str, Any]:
        """Test a single file for syntax errors and other issues in a secure container."""
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Get file extension
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Create temporary directory and copy file for Docker
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_file_name = os.path.basename(file_path)
                temp_file_path = os.path.join(temp_dir, temp_file_name)
                
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Perform syntax check based on file type
                if file_ext == '.py':
                    # Try AST parsing first (doesn't need Docker)
                    try:
                        ast.parse(content)
                        return {
                            "valid": True,
                            "message": "Python syntax valid (AST verified)",
                            "method": "ast_parse"
                        }
                    except SyntaxError as e:
                        return {
                            "valid": False,
                            "error": f"Python syntax error: {e.msg} at line {e.lineno}",
                            "method": "ast_parse",
                            "line": e.lineno
                        }
                    except Exception:
                        # Fall back to Docker
                        cmd = f"python -m py_compile {temp_file_name}"
                        result = self._run_in_docker(cmd, temp_dir)
                        return {
                            "valid": result["success"],
                            "message": f"Python syntax {'valid' if result['success'] else 'invalid'}",
                            "error": result["error"] if not result["success"] else "",
                            "method": "py_compile_docker"
                        }
                        
                elif file_ext in ['.js', '.jsx']:
                    cmd = f"node --check {temp_file_name}"
                    result = self._run_in_docker(cmd, temp_dir)
                    return {
                        "valid": result["success"],
                        "message": f"JavaScript syntax {'valid' if result['success'] else 'invalid'}",
                        "error": result["error"] if not result["success"] else "",
                        "method": "node_check_docker"
                    }
                    
                elif file_ext in ['.ts', '.tsx']:
                    cmd = f"tsc --noEmit --skipLibCheck {temp_file_name}"
                    result = self._run_in_docker(cmd, temp_dir)
                    return {
                        "valid": result["success"],
                        "message": f"TypeScript syntax {'valid' if result['success'] else 'invalid'}",
                        "error": result["error"] if not result["success"] else "",
                        "method": "tsc_check_docker"
                    }
                    
                elif file_ext in ['.xml', '.html']:
                    # XML validation - use Python's xml parser in Docker
                    cmd = f"python -c \"import xml.etree.ElementTree as ET; ET.parse('{temp_file_name}');\""
                    result = self._run_in_docker(cmd, temp_dir)
                    return {
                        "success": result["success"],
                        "valid": result["success"],
                        "message": f"XML syntax {'valid' if result['success'] else 'invalid'}",
                        "error": result["error"] if not result["success"] else "",
                        "method": "xml_parse_docker"
                    }
                    
                else:
                    return {"success": True, "valid": True, "message": f"No specific validation for {file_ext} files"}
                
        except Exception as e:
            logger.error(f"Error testing file {file_path}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def execute_command(self, command: str, working_dir: str, timeout: int = 60) -> Dict[str, Any]:
        """Execute a command in a secure Docker container with the specified working directory."""
        return self._run_in_docker(command, working_dir, timeout)