import os
import subprocess
import sys
import tempfile
import ast
import py_compile
from pathlib import Path
from typing import Dict, Any, List
import json

class CodeExecutionTool:
    """Enhanced code execution tool addressing the analysis feedback."""
    
    def __init__(self, output_dir: str):
        """
        Initialize the code execution tool with an output directory.
        
        Args:
            output_dir: Directory for storing execution outputs and temporary files
        """
        self.output_dir = output_dir
        self.supported_languages = ['python', 'javascript', 'typescript']
        
        # Create temp directory if needed
        os.makedirs(os.path.join(self.output_dir, "temp_check"), exist_ok=True)
    
    def run_syntax_check(self, code: str, file_path: str) -> Dict[str, Any]:
        """Enhanced syntax checking with multiple validation methods."""
        try:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.py':
                return self._enhanced_python_syntax_check(code, file_path)
            elif file_ext in ['.js', '.jsx']:
                return self._enhanced_javascript_syntax_check(code, file_path)
            elif file_ext in ['.ts', '.tsx']:
                return self._enhanced_typescript_syntax_check(code, file_path)
            else:
                return {
                    "valid": True,
                    "message": f"Syntax checking not implemented for {file_ext}",
                    "method": "unsupported"
                }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Syntax check failed: {str(e)}",
                "method": "error"
            }
    
    def _enhanced_python_syntax_check(self, code: str, file_path: str) -> Dict[str, Any]:
        """Multi-method Python syntax validation."""
        
        # Method 1: AST parsing (most reliable)
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
        
        # Method 2: py_compile fallback (if AST fails for other reasons)
        except Exception:
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                    temp_file.write(code)
                    temp_file_path = temp_file.name
                
                try:
                    py_compile.compile(temp_file_path, doraise=True)
                    return {
                        "valid": True,
                        "message": "Python syntax valid (compile verified)",
                        "method": "py_compile"
                    }
                except py_compile.PyCompileError as e:
                    return {
                        "valid": False,
                        "error": f"Python compilation error: {str(e)}",
                        "method": "py_compile"
                    }
                finally:
                    os.unlink(temp_file_path)
            except Exception as e:
                return {
                    "valid": False,
                    "error": f"All syntax checks failed: {str(e)}",
                    "method": "all_failed"
                }
    
    def _enhanced_javascript_syntax_check(self, code: str, file_path: str) -> Dict[str, Any]:
        """Enhanced JavaScript syntax checking."""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name
            
            try:
                # Try node --check for syntax validation
                result = subprocess.run(
                    ['node', '--check', temp_file_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    return {
                        "valid": True,
                        "message": "JavaScript syntax valid",
                        "method": "node_check"
                    }
                else:
                    return {
                        "valid": False,
                        "error": f"JavaScript syntax error: {result.stderr.strip()}",
                        "method": "node_check"
                    }
            finally:
                os.unlink(temp_file_path)
                
        except FileNotFoundError:
            return {
                "valid": True,  # Can't verify, assume valid
                "message": "Node.js not available, syntax check skipped",
                "method": "node_unavailable"
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"JavaScript syntax check failed: {str(e)}",
                "method": "error"
            }
    
    def _enhanced_typescript_syntax_check(self, code: str, file_path: str) -> Dict[str, Any]:
        """Enhanced TypeScript syntax checking."""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name
            
            try:
                # Try tsc --noEmit for syntax validation
                result = subprocess.run(
                    ['tsc', '--noEmit', temp_file_path],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                if result.returncode == 0:
                    return {
                        "valid": True,
                        "message": "TypeScript syntax valid",
                        "method": "tsc_check"
                    }
                else:
                    return {
                        "valid": False,
                        "error": f"TypeScript syntax error: {result.stderr.strip()}",
                        "method": "tsc_check"
                    }
            finally:
                os.unlink(temp_file_path)
                
        except FileNotFoundError:
            return {
                "valid": True,  # Can't verify, assume valid
                "message": "TypeScript compiler not available, syntax check skipped",
                "method": "tsc_unavailable"
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"TypeScript syntax check failed: {str(e)}",
                "method": "error"
            }
    
    def run_lint_check(self, project_dir: str, tech_stack: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced linting with better tool detection."""
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
        """Try multiple Python linting tools with graceful fallbacks."""
        lint_tools = [
            (['flake8', '--max-line-length=88', '.'], 'flake8'),
            (['pylint', '--score=n', '.'], 'pylint'),
            (['pycodestyle', '--max-line-length=88', '.'], 'pycodestyle'),
            (['black', '--check', '.'], 'black_check')
        ]
        
        for cmd, tool_name in lint_tools:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                return {
                    "success": True,
                    "output": f"{tool_name} results:\n{result.stdout}\n{result.stderr}".strip(),
                    "method": tool_name,
                    "return_code": result.returncode,
                    "issues_found": result.returncode != 0
                }
                
            except FileNotFoundError:
                continue  # Try next tool
            except subprocess.TimeoutExpired:
                continue  # Try next tool
            except Exception:
                continue  # Try next tool
        
        return {
            "success": True,
            "output": "No Python linting tools available. Install flake8, pylint, or pycodestyle for better code quality analysis.",
            "method": "none_available",
            "recommendation": "pip install flake8 pylint pycodestyle black"
        }
    
    def _enhanced_javascript_lint(self, project_dir: str) -> Dict[str, Any]:
        """Enhanced JavaScript linting with multiple approaches."""
        
        # Method 1: Check for package.json lint script
        package_json_path = os.path.join(project_dir, 'package.json')
        if os.path.exists(package_json_path):
            try:
                with open(package_json_path, 'r') as f:
                    package_data = json.load(f)
                
                if 'scripts' in package_data and 'lint' in package_data['scripts']:
                    result = subprocess.run(
                        ['npm', 'run', 'lint'],
                        cwd=project_dir,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    
                    return {
                        "success": True,
                        "output": f"npm run lint results:\n{result.stdout}\n{result.stderr}".strip(),
                        "method": "npm_run_lint",
                        "return_code": result.returncode,
                        "issues_found": result.returncode != 0
                    }
            except Exception:
                pass  # Fall through to direct ESLint
        
        # Method 2: Try direct ESLint
        eslint_commands = [
            (['npx', 'eslint', '.'], 'npx_eslint'),
            (['eslint', '.'], 'eslint_direct')
        ]
        
        for cmd, method in eslint_commands:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                return {
                    "success": True,
                    "output": f"{method} results:\n{result.stdout}\n{result.stderr}".strip(),
                    "method": method,
                    "return_code": result.returncode,
                    "issues_found": result.returncode != 0
                }
            except FileNotFoundError:
                continue
            except Exception:
                continue
        
        return {
            "success": True,
            "output": "No JavaScript linting available. Consider adding ESLint configuration.",
            "method": "none_available",
            "recommendation": "npm install --save-dev eslint @eslint/js"
        }
    
    def run_project_exec_check(self, project_dir: str, tech_stack: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced project execution check with better framework detection."""
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
        """Enhanced Python execution check with framework-specific patterns."""
        
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
        
        for entry_point in entry_points:
            entry_path = os.path.join(project_dir, entry_point)
            if os.path.exists(entry_path):
                try:
                    # Check syntax first
                    with open(entry_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                    
                    syntax_result = self._enhanced_python_syntax_check(code, entry_path)
                    if not syntax_result['valid']:
                        return {
                            "success": False,
                            "output": f"Syntax error in {entry_point}: {syntax_result['error']}",
                            "method": "syntax_check",
                            "entry_point": entry_point
                        }
                    
                    # Check for framework patterns
                    framework_detected = any(pattern in code for pattern in framework_patterns)
                    
                    # Try import check
                    result = subprocess.run(
                        [sys.executable, '-m', 'py_compile', entry_path],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    return {
                        "success": result.returncode == 0,
                        "output": f"Python project executable via {entry_point}" + 
                                (f" (Framework: {backend_type})" if framework_detected else ""),
                        "method": f"compile_check_{entry_point}",
                        "entry_point": entry_point,
                        "framework_detected": framework_detected
                    }
                    
                except Exception as e:
                    continue  # Try next entry point
        
        return {
            "success": False,
            "output": f"No valid Python entry points found. Checked: {', '.join(entry_points)}",
            "method": "no_entry_point",
            "suggestion": "Create a main.py, app.py, or appropriate framework entry point"
        }
    
    def _enhanced_javascript_exec_check(self, project_dir: str) -> Dict[str, Any]:
        """Enhanced JavaScript execution check with package.json awareness."""
        
        # Check package.json for main entry and scripts
        package_json_path = os.path.join(project_dir, 'package.json')
        if os.path.exists(package_json_path):
            try:
                with open(package_json_path, 'r') as f:
                    package_data = json.load(f)
                
                main_file = package_data.get('main', 'index.js')
                main_path = os.path.join(project_dir, main_file)
                
                if os.path.exists(main_path):
                    syntax_result = self._enhanced_javascript_syntax_check(
                        open(main_path, 'r').read(), main_path
                    )
                    
                    # Check for start script
                    has_start_script = 'scripts' in package_data and 'start' in package_data['scripts']
                    
                    return {
                        "success": syntax_result['valid'],
                        "output": f"JavaScript project entry: {main_file} - {syntax_result['message']}" +
                                (f" (Start script available)" if has_start_script else ""),
                        "method": "package_json_main",
                        "entry_point": main_file,
                        "has_start_script": has_start_script
                    }
            except Exception as e:
                pass
        
        # Fallback: check common entry points
        entry_points = ['index.js', 'app.js', 'server.js', 'main.js', 'src/index.js']
        for entry_point in entry_points:
            entry_path = os.path.join(project_dir, entry_point)
            if os.path.exists(entry_path):
                try:
                    with open(entry_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                    
                    syntax_result = self._enhanced_javascript_syntax_check(code, entry_path)
                    return {
                        "success": syntax_result['valid'],
                        "output": f"JavaScript executable via {entry_point} - {syntax_result['message']}",
                        "method": f"entry_point_{entry_point.replace('/', '_')}",
                        "entry_point": entry_point
                    }
                except Exception:
                    continue
        
        return {
            "success": False,
            "output": f"No valid JavaScript entry points found. Checked: {', '.join(entry_points)}",
            "method": "no_entry_point",
            "suggestion": "Create an index.js, app.js, or configure package.json main field"
        }

    def run_tests(self, project_dir: str) -> Dict[str, Any]:
        """Enhanced test execution with better coverage integration."""
        
        if self._has_python_tests(project_dir):
            return self._run_python_tests_with_coverage(project_dir)
        elif self._has_javascript_tests(project_dir):
            return self._run_javascript_tests(project_dir)  # FIXED: Call to correct function
        else:
            return {
                "success": False,
                "output": "No test files found in project",
                "method": "no_tests_found",
                "suggestion": "Create test files following naming conventions (test_*.py, *.test.js, etc.)"
            }
    
    def _run_python_tests_with_coverage(self, project_dir: str) -> Dict[str, Any]:
        """Run Python tests with integrated coverage reporting."""
        
        test_commands = [
            # Try pytest with coverage first
            (['python', '-m', 'pytest', '--cov=.', '--cov-report=term-missing', '--cov-report=json'], 'pytest_coverage'),
            # Fallback to pytest without coverage
            (['python', '-m', 'pytest', '-v'], 'pytest'),
            # Fallback to unittest
            (['python', '-m', 'unittest', 'discover', '-v'], 'unittest')
        ]
        
        for cmd, method in test_commands:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                # Try to extract coverage information
                coverage_info = self._extract_coverage_info(project_dir, result.stdout)
                
                return {
                    "success": result.returncode == 0,
                    "output": f"{method} results:\n{result.stdout}\n{result.stderr}".strip(),
                    "method": method,
                    "return_code": result.returncode,
                    "coverage_info": coverage_info
                }
                
            except FileNotFoundError:
                continue
            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "output": f"Test execution timed out after 120 seconds using {method}",
                    "method": f"{method}_timeout"
                }
            except Exception as e:
                continue
        
        return {
            "success": False,
            "output": "No Python test runners available",
            "method": "no_runner_available",
            "suggestion": "Install pytest: pip install pytest pytest-cov"
        }
    
    def _extract_coverage_info(self, project_dir: str, test_output: str) -> Dict[str, Any]:
        """Extract coverage information from test output or coverage files."""
        coverage_info = {"percentage": 0, "details": "No coverage information available"}
        
        # Try to read coverage.json if it exists
        coverage_json_path = os.path.join(project_dir, 'coverage.json')
        if os.path.exists(coverage_json_path):
            try:
                with open(coverage_json_path, 'r') as f:
                    coverage_data = json.load(f)
                
                if 'totals' in coverage_data:
                    total_coverage = coverage_data['totals'].get('percent_covered', 0)
                    coverage_info = {
                        "percentage": round(total_coverage, 2),
                        "details": f"Coverage: {total_coverage:.2f}%",
                        "source": "coverage.json"
                    }
            except Exception:
                pass
        
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
        """Run JavaScript/TypeScript tests with coverage extraction when possible."""
        
        # Method 1: Try package.json npm test script (most common)
        package_json_path = os.path.join(project_dir, 'package.json')
        if os.path.exists(package_json_path):
            try:
                with open(package_json_path, 'r') as f:
                    package_data = json.load(f)
                
                if 'scripts' in package_data and 'test' in package_data['scripts']:
                    # Execute npm test
                    result = subprocess.run(
                        ['npm', 'run', 'test'],
                        cwd=project_dir,
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    
                    # Try to extract coverage information
                    coverage_info = self._extract_js_coverage_info(project_dir, result.stdout)
                    
                    return {
                        "success": result.returncode == 0,
                        "output": f"npm test results:\n{result.stdout}\n{result.stderr}".strip(),
                        "method": "npm_test",
                        "return_code": result.returncode,
                        "coverage_info": coverage_info
                    }
            except Exception as e:
                pass  # Fall through to direct test runners
        
        # Method 2: Try common test runners directly
        test_runners = [
            (['npx', 'jest', '--coverage'], 'jest'),
            (['npx', 'mocha'], 'mocha'),
            (['npx', 'jasmine'], 'jasmine'),
            (['npx', 'karma', 'start'], 'karma')
        ]
        
        for cmd, runner in test_runners:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                # Try to extract coverage info
                coverage_info = self._extract_js_coverage_info(project_dir, result.stdout)
                
                return {
                    "success": result.returncode == 0,
                    "output": f"{runner} results:\n{result.stdout}\n{result.stderr}".strip(),
                    "method": runner,
                    "return_code": result.returncode,
                    "coverage_info": coverage_info
                }
            except FileNotFoundError:
                continue  # Try next runner
            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "output": f"Test execution timed out after 120 seconds using {runner}",
                    "method": f"{runner}_timeout"
                }
            except Exception as e:
                continue  # Try next runner
        
        return {
            "success": False,
            "output": "No JavaScript test runners available or no tests found",
            "method": "no_runner_available",
            "suggestion": "Add a test script to package.json or install Jest: npm install --save-dev jest"
        }

    def _extract_js_coverage_info(self, project_dir: str, test_output: str) -> Dict[str, Any]:
        """Extract coverage information from JavaScript test output or coverage files."""
        import re
        coverage_info = {"percentage": 0, "details": "No coverage information available"}
        
        # Check for Jest or Istanbul coverage output in test output
        coverage_patterns = [
            r'All files[^\n]*\|[^\n]*\|[^\n]*\|[^\n]*\|[^\d]*(\d+(?:\.\d+)?)%',  # Jest style
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
        
        # Try to read coverage report files
        coverage_files = [
            os.path.join(project_dir, 'coverage', 'coverage-summary.json'),
            os.path.join(project_dir, 'coverage', 'coverage-final.json'),
            os.path.join(project_dir, 'coverage.json')
        ]
        
        for coverage_file in coverage_files:
            if os.path.exists(coverage_file):
                try:
                    with open(coverage_file, 'r') as f:
                        coverage_data = json.load(f)
                    
                    # Extract percentage from various formats
                    percentage = None
                    if 'total' in coverage_data:
                        if 'statements' in coverage_data['total']:
                            percentage = coverage_data['total']['statements'].get('pct', 0)
                        elif 'lines' in coverage_data['total']:
                            percentage = coverage_data['total']['lines'].get('pct', 0)
                    
                    if percentage is not None:
                        coverage_info = {
                            "percentage": float(percentage),
                            "details": f"Coverage: {percentage}%",
                            "source": os.path.basename(coverage_file)
                        }
                        return coverage_info
                except Exception:
                    continue
        
        return coverage_info

    def _has_python_tests(self, project_dir: str) -> bool:
        """Check if the project directory has Python test files."""
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
        # Common JavaScript/TypeScript test file patterns
        patterns = ['*.test.js', '*.spec.js', '*.test.ts', '*.spec.ts', 
                    'test/*.js', 'tests/*.js', '__tests__/*.js',
                    'test/*.ts', 'tests/*.ts', '__tests__/*.ts']
        
        for pattern in patterns:
            # Use Path.glob for proper pattern matching
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
        """Test a single file for syntax errors and other issues."""
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Get file extension
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Perform syntax check based on file type
            if file_ext == '.py':
                return self._enhanced_python_syntax_check(content, file_path)
            elif file_ext in ['.js', '.jsx']:
                return self._enhanced_javascript_syntax_check(content, file_path)
            elif file_ext in ['.ts', '.tsx']:
                return self._enhanced_typescript_syntax_check(content, file_path)
            elif file_ext in ['.xml', '.html']:
                # Basic XML validation
                try:
                    import xml.etree.ElementTree as ET
                    ET.fromstring(content)
                    return {"success": True, "valid": True, "message": "XML syntax valid"}
                except Exception as e:
                    return {"success": False, "valid": False, "error": str(e)}
            else:
                return {"success": True, "valid": True, "message": f"No specific validation for {file_ext} files"}
        except Exception as e:
            return {"success": False, "error": str(e)}