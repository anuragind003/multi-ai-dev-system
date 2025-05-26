import subprocess
import os
import shutil # For safely cleaning directories

class CodeExecutionTool:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir # The root directory for generated project(s)

    def _run_cmd(self, command: list[str], cwd: str, timeout: int = 300) -> tuple[bool, str]:
        """Helper to run shell commands."""
        try:
            process = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False # Do not raise CalledProcessError, capture output and return code
            )
            success = process.returncode == 0
            output = process.stdout + process.stderr # Combine stdout and stderr
            return success, output
        except subprocess.TimeoutExpired:
            return False, f"Command '{' '.join(command)}' timed out after {timeout} seconds."
        except FileNotFoundError:
            return False, f"Command not found: '{command[0]}'. Ensure it's in your PATH."
        except Exception as e:
            return False, f"An unexpected error occurred: {e}"

    def run_syntax_check(self, code_content: str, file_path: str, lang: str = "python") -> tuple[bool, str]:
        """
        Performs a basic syntax check on code content for a given language.
        `file_path` here should be the *intended* full path where the file will be saved.
        """
        temp_dir = os.path.join(self.output_dir, "temp_check")
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_full_path = os.path.join(temp_dir, os.path.basename(file_path))

        try:
            with open(temp_file_full_path, "w", encoding="utf-8") as f:
                f.write(code_content)

            if lang.lower() == "python":
                # Use compile to check for syntax errors without executing
                # Note: This is very basic. For module resolution, we'd need more context.
                # A better check might be: `python -m py_compile {temp_file_full_path}`
                # Or for Flask/Django: try to import the main app object
                success, output = self._run_cmd(["python", "-m", "py_compile", temp_file_full_path], cwd=temp_dir, timeout=10)
                if not success: # If py_compile fails, it means a syntax error
                    return False, output
                
                # Try a slightly more robust check: attempt a bare import from the context of the temp_dir
                # This helps catch simple import errors, but won't resolve complex package structures.
                module_name = os.path.basename(temp_file_full_path).split('.')[0]
                success, output = self._run_cmd(
                    ["python", "-c", f"import sys; sys.path.append('.'); import {module_name}"],
                    cwd=temp_dir, timeout=10
                )
                if not success and "ModuleNotFoundError" not in output: # Only fail if it's not a module not found (which is expected for nested files)
                    return False, output # Fail on other import-related issues
                return True, "Syntax and basic imports OK."

            elif lang.lower() == "javascript":
                # For JS, a simple syntax check often involves trying to parse with Node.js
                return self._run_cmd(["node", "--check", temp_file_full_path], cwd=temp_dir, timeout=10)
            # Add other language checks as needed (e.g., Java, Go)

            return False, f"Unsupported language for syntax check: {lang}"
        finally:
            # Clean up the temporary directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def install_dependencies(self, project_path: str, tech_stack: dict) -> tuple[bool, str]:
        """
        Installs dependencies for the generated project.
        `tech_stack` will be used to determine the package manager (pip, npm, etc.).
        """
        print(f"  Attempting to install dependencies in {project_path}...")
        backend_name = tech_stack.get("backend", {}).get("name", "").lower()
        frontend_name = tech_stack.get("frontend", {}).get("name", "").lower()

        if "python" in backend_name or "flask" in backend_name or "django" in backend_name:
            if os.path.exists(os.path.join(project_path, "requirements.txt")):
                return self._run_cmd(["pip", "install", "-r", "requirements.txt"], cwd=project_path, timeout=300)
            else:
                return False, "requirements.txt not found for Python project."
        elif "node.js" in backend_name or "express" in backend_name or "react" in frontend_name or "vue.js" in frontend_name:
            if os.path.exists(os.path.join(project_path, "package.json")):
                return self._run_cmd(["npm", "install"], cwd=project_path, timeout=300)
            else:
                return False, "package.json not found for Node.js/JS project."
        # Add more cases for Java, Go, etc.
        return True, "No known dependencies to install for this tech stack." # Assume success if no specific dependency file found

    def run_lint_check(self, project_path: str, tech_stack: dict) -> tuple[bool, str]:
        """
        Runs language-specific linters on the generated project.
        """
        print(f"  Running lint checks in {project_path}...")
        backend_name = tech_stack.get("backend", {}).get("name", "").lower()
        
        if "python" in backend_name or "flask" in backend_name or "django" in backend_name:
            # Flake8 is good for quick, strict checks
            success, output = self._run_cmd(["flake8", "."], cwd=project_path, timeout=60)
            if not success:
                # If flake8 finds issues, it returns non-zero. This isn't a *failure* of the tool, but a finding.
                # So we return True for tool execution success, but output contains the linting errors.
                return True, output # This output needs to be parsed by the agent
            return True, "No linting issues found by Flake8."
        elif "node.js" in backend_name or "express" in backend_name or "react" in tech_stack.get("frontend",{}).get("name","").lower():
            # ESLint requires configuration; assume .eslintrc or similar exists
            if os.path.exists(os.path.join(project_path, ".eslintrc.js")) or \
               os.path.exists(os.path.join(project_path, "package.json")): # package.json might have lint script
                success, output = self._run_cmd(["npm", "run", "lint"], cwd=project_path, timeout=60)
                return True, output
            else:
                return True, "No ESLint config found, skipping JS lint."
        
        return True, "No specific linting tool configured for this tech stack."

    def run_tests(self, project_path: str, tech_stack: dict) -> tuple[bool, str]:
        """
        Runs the test suite for the generated project.
        """
        print(f"  Running tests in {project_path}...")
        backend_name = tech_stack.get("backend", {}).get("name", "").lower()
        frontend_name = tech_stack.get("frontend", {}).get("name", "").lower()

        if "python" in backend_name or "flask" in backend_name or "django" in backend_name:
            # Assume pytest is installed via requirements.txt
            if os.path.exists(os.path.join(project_path, "tests")): # Common pytest convention
                 # Use pytest with coverage
                return self._run_cmd(["pytest", "--cov=.", "--cov-report=json"], cwd=project_path, timeout=120)
            else:
                return False, "No 'tests' directory found or pytest not installed."
        elif "node.js" in backend_name or "express" in backend_name or "react" in frontend_name:
            if os.path.exists(os.path.join(project_path, "package.json")):
                # Assume a 'test' script in package.json (e.g., 'jest')
                return self._run_cmd(["npm", "test"], cwd=project_path, timeout=120)
            else:
                return False, "No package.json found for Node.js/JS project."
        
        return False, "No test runner configured for this tech stack."