# This file is intentionally left blank.
import subprocess
import os

class CodeInterpreterTool:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir # The root directory for generated code

    def run_python_check(self, code_content: str, file_path: str = "temp_check.py") -> tuple[bool, str]:
        """
        Writes Python code to a temporary file and attempts a basic syntax check.
        Returns (success_boolean, output_string).
        """
        full_path = os.path.join(self.output_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True) # Ensure subdir exists

        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(code_content)
            
            # Use 'python -m py_compile' for basic syntax check without running
            # For a Flask app, we can try to import the app module
            process = subprocess.run(
                ["python", "-c", f"import sys; sys.path.append('{os.path.dirname(full_path)}'); import {os.path.basename(full_path).split('.')[0]}"],
                capture_output=True, text=True, timeout=10
            )

            if process.returncode == 0:
                return True, "Syntax and basic imports OK."
            else:
                return False, process.stderr
        except subprocess.TimeoutExpired:
            return False, "Code check timed out."
        except Exception as e:
            return False, f"An unexpected error occurred during Python check: {e}"
        finally:
            # Clean up temp file if it's a temporary check
            if file_path == "temp_check.py" and os.path.exists(full_path):
                os.remove(full_path)

    def run_command(self, command: list[str], cwd: str = None) -> tuple[bool, str]:
        """
        Runs a shell command (e.g., 'npm install', 'python app.py').
        Returns (success_boolean, output_string).
        """
        try:
            # If cwd is not provided, default to the output directory
            if cwd is None:
                cwd = self.output_dir

            process = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=600 # 10 minutes timeout for longer commands like install
            )
            if process.returncode == 0:
                return True, process.stdout
            else:
                return False, process.stderr
        except subprocess.TimeoutExpired:
            return False, f"Command '{' '.join(command)}' timed out."
        except FileNotFoundError:
            return False, f"Command not found: '{command[0]}'. Ensure it's in your PATH."
        except Exception as e:
            return False, f"An unexpected error occurred: {e}"