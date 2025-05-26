import json
import os
import shutil # New import for potentially cleaning old outputs
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from tools.code_execution_tool import CodeExecutionTool # Updated import

class CodeGenerationAgent:
    def __init__(self, llm, memory, output_dir: str, code_execution_tool: CodeExecutionTool):
        """
        Initializes the CodeGenerationAgent.

        Args:
            llm: An initialized Gemini GenerativeModel instance.
            memory: An instance of SharedProjectMemory.
            output_dir (str): The root directory where generated code will be saved.
            code_execution_tool (CodeExecutionTool): Instance of the code execution tool.
        """
        self.llm = llm
        self.memory = memory
        self.output_dir = output_dir
        self.code_execution_tool = code_execution_tool # Store the tool
        # Ensure the output directory for this specific run is created
        os.makedirs(self.output_dir, exist_ok=True)

    def _generate_file_structure(self, context_for_llm: str) -> dict:
        """
        Asks LLM to generate a proposed file structure for the project.
        """
        print("Code Generation Agent: Generating project file structure...")
        tech_stack = json.loads(context_for_llm).get('tech_stack_recommendation', {})
        backend_name = tech_stack.get('backend', {}).get('name', 'selected backend')
        architecture_overview = json.loads(context_for_llm).get('system_design', {}).get('architecture_overview', 'application')

        prompt = f"""
        You are an expert Software Engineer AI.
        Based on the following project context (BRD analysis, tech stack, and system design),
        propose a suitable file and directory structure for the entire application.

        Focus on a typical structure for a {backend_name}-based {architecture_overview}.
        Include common files like `requirements.txt` (for Python), `package.json` (for Node.js), `README.md`, config files, main app files, routes, models, tests directory, etc.
        If the backend is Python, ensure there's a `run.py` or `main.py` entry point and a `tests/` directory.

        The output should be a JSON object where keys are relative file paths (e.g., "src/main.py", "README.md", "tests/test_api.py")
        and values are placeholder content indicating the file's purpose (e.g., "# Main application entry point", "## Project Readme").
        Do NOT include actual code here, just placeholders.

        Ensure the output is ONLY a valid JSON object.

        --- Project Context ---
        {context_for_llm}
        --- END Project Context ---

        Example Output for a Flask app:
        ```json
        {{
            "README.md": "# Project Title",
            "requirements.txt": "Flask\nSQLAlchemy",
            "run.py": "# Entry point for the Flask application",
            "app/__init__.py": "# App package initialization",
            "app/config.py": "# Configuration settings",
            "app/models.py": "# Database models",
            "app/routes.py": "# API endpoints",
            "tests/test_app.py": "# Unit and integration tests for the Flask app"
        }}
        ```
        """
        
        try:
            response = self.llm.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.1
                },
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
            )
            raw_json_output = response.text.strip()
            if raw_json_output.startswith("```json"):
                raw_json_output = raw_json_output.split("```json", 1)[1]
            if raw_json_output.endswith("```"):
                raw_json_output = raw_json_output.rsplit("```", 1)[0]
            raw_json_output = raw_json_output.strip()

            return json.loads(raw_json_output)
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error in file structure generation: {e}")
            print(f"Problematic raw output: {raw_json_output}")
            return {} # Return empty structure if parsing fails
        except Exception as e:
            print(f"Error generating file structure: {e}")
            return {}

    def _generate_and_refine_code(self, file_path: str, context_for_llm: str, max_retries: int = 3) -> str:
        """
        Generates code for a single file and attempts to self-correct using the interpreter.
        """
        print(f"  Generating code for: {file_path}")
        
        tech_stack = json.loads(context_for_llm).get('tech_stack_recommendation', {})
        backend_name_raw = tech_stack.get("backend", {}).get("name", "N/A")
        backend_lang = backend_name_raw.split('/')[0].lower() # e.g., 'python' from 'Python/Flask'
        
        # Determine specific instructions for the file based on its path
        file_role_instruction = ""
        if "readme.md" in file_path.lower():
            file_role_instruction = "Write a comprehensive README.md file for the project."
        elif "requirements.txt" in file_path.lower():
            file_role_instruction = f"List all necessary Python packages for a {backend_name_raw} project based on the requirements. Output ONLY the package names, one per line."
        elif "package.json" in file_path.lower():
            file_role_instruction = f"Generate a complete package.json for a {backend_name_raw} project, including scripts for start, test, and lint if applicable. Output ONLY the JSON."
        elif "__init__.py" in file_path.lower() and backend_lang == "python":
            file_role_instruction = "Write the `__init__.py` file to initialize the Python package. If it's the main app package, define the `create_app()` function here."
        elif "config.py" in file_path.lower() and backend_lang == "python":
            file_role_instruction = "Write the `config.py` for Python, defining configuration classes (e.g., Config, DevelopmentConfig, TestingConfig)."
        elif "models.py" in file_path.lower() and backend_lang == "python":
            file_role_instruction = "Write the `models.py` file for Python using SQLAlchemy, defining database models based on the `database_schema` in the system design."
        elif "routes.py" in file_path.lower() and backend_lang == "python":
            file_role_instruction = "Write the `routes.py` file for Python using Flask Blueprints, implementing all API endpoints defined in the system design."
        elif "run.py" in file_path.lower() and backend_lang == "python":
            file_role_instruction = "Write the `run.py` entry point for the Flask application. It should import and run the app from `app/__init__.py`."
        elif "tests/" in file_path.lower():
            # For tests, the TestCaseGeneratorAgent will handle it, but CodeGenAgent might produce placeholder
            file_role_instruction = "This is a test file. Provide a basic placeholder for tests compatible with the chosen tech stack's testing framework."
        else:
            file_role_instruction = f"Write the code for this file `{file_path}` based on its implied role in a {backend_name_raw} project. Focus on implementing relevant logic from the system design."


        initial_prompt = f"""
        You are an expert Software Engineer AI.
        Your task is to write the complete code for the file `{file_path}`
        based on the provided project context (BRD analysis, tech stack, system design, and previous error feedback).

        The chosen tech stack includes:
        - Backend: {backend_name_raw}
        - Database: {tech_stack.get("database", {}).get("name", "N/A")}
        - Frontend: {tech_stack.get("frontend", {}).get("name", "N/A")}

        --- Project Context ---
        {context_for_llm}
        --- END Project Context ---

        **Specific Instruction for this file ({file_path}):**
        {file_role_instruction}

        Write ONLY the code for `{file_path}`. Do NOT include any markdown code block fences (```) or explanatory text outside the code.
        Ensure the code is directly runnable and follows good practices for the chosen tech stack.
        For database interactions, use appropriate ORM/library based on the chosen tech stack.
        For API endpoints, implement the logic as specified in the system design.
        Include necessary imports and basic setup.
        """
        
        current_prompt = initial_prompt
        generated_code = ""

        for retry in range(max_retries):
            try:
                response = self.llm.generate_content(
                    current_prompt,
                    generation_config={
                        "temperature": 0.1 # Keep low for consistent code
                    },
                    safety_settings={
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    }
                )
                generated_code = response.text.strip()
                
                # Try to clean up code blocks if they appear
                if generated_code.startswith("```"):
                    parts = generated_code.split('\n', 1) # Split after first line (```lang)
                    if len(parts) > 1:
                        generated_code = parts[1] # Take content after ```lang
                    if generated_code.endswith("```"):
                        generated_code = generated_code[:-3].strip() # Remove closing ```

                # Skip interpreter check for non-code files (README, requirements, .db files, etc.)
                if not (file_path.lower().endswith((".py", ".js", ".java", ".ts", ".go", ".c", ".cpp"))):
                    print(f"  Skipping interpreter check for non-code file: {file_path}")
                    return generated_code

                # Use interpreter for basic syntax/import check
                # Note: `full_file_path` is passed to the tool because it needs to create a temporary file
                # The file_path passed to `run_syntax_check` should help it determine the language.
                full_file_path_in_output = os.path.join(self.output_dir, file_path)
                success, output = self.code_execution_tool.run_syntax_check(generated_code, file_path=full_file_path_in_output, lang=backend_lang)
                
                if success:
                    print(f"  Code for {file_path} looks good (basic check).")
                    return generated_code
                else:
                    print(f"  Code check failed for {file_path} (Retry {retry+1}/{max_retries}):\n{output.strip()}")
                    # Refine prompt with error feedback
                    current_prompt = (
                        initial_prompt +
                        f"\n\nThe previous attempt to generate code for `{file_path}` resulted in errors:\n"
                        f"```\n{output}\n```\n"
                        "Please review the errors and generate corrected, complete code for this file. "
                        "Remember to output ONLY the code, no markdown fences or extra text. "
                        "Ensure all necessary imports are present and paths are correct relative to the project root. "
                        "Pay close attention to Python package imports if this file is part of a larger package structure."
                    )
            except Exception as e:
                print(f"  Error during code generation/refinement for {file_path}: {e}")
                # Provide a more generic error for the LLM
                current_prompt = (
                    initial_prompt +
                    f"\n\nAn unexpected error occurred during code generation/check for `{file_path}`. "
                    "Please ensure the code is syntactically correct and includes all necessary imports for a standalone runnable file. "
                    "Remember to output ONLY the code, no markdown fences or extra text."
                )

        print(f"  Failed to generate valid code for {file_path} after {max_retries} retries.")
        return generated_code # Return last generated code, even if flawed

    def run(self, brd_analysis: dict, tech_stack_recommendation: dict, system_design: dict, error_feedback: str = "") -> dict:
        """
        Generates the entire codebase for the project.
        """
        print("Code Generation Agent: Starting code generation process...")
        if error_feedback:
            print(f"Code Generation Agent: Received feedback for correction:\n{error_feedback}")

        # Consolidate all context into a single string for the LLM
        full_context = json.dumps({
            "brd_analysis": brd_analysis,
            "tech_stack_recommendation": tech_stack_recommendation,
            "system_design": system_design,
            "previous_errors_feedback": error_feedback # Add feedback to context for LLM to fix
        }, indent=2)

        # 1. Generate the initial file structure
        file_structure = self._generate_file_structure(full_context)
        if not file_structure:
            print("Code Generation Agent: Failed to generate a valid file structure. Aborting.")
            return {}

        generated_files = {}

        # 2. Iterate through the proposed file structure and generate content for each file
        for file_path, placeholder_content in file_structure.items():
            full_path_in_output_dir = os.path.join(self.output_dir, file_path)
            os.makedirs(os.path.dirname(full_path_in_output_dir), exist_ok=True) # Ensure directory exists

            # Check if this is a test file path (to be handled by TestCaseGeneratorAgent primarily)
            # CodeGen will still produce a placeholder, but TestCaseGenerator will overwrite/fill.
            is_test_file_path = "tests/" in file_path.lower() or file_path.lower().startswith("test_")

            # For static files like README, requirements.txt, or .db (placeholder content only)
            # The LLM gives us placeholder content for these.
            if any(ext in file_path.lower() for ext in ["readme.md", "requirements.txt", "package.json", ".gitignore", ".env.example"]) or \
               (file_path.lower().endswith(".db") and not is_test_file_path): # .db files are usually just placeholders
                content_to_write = placeholder_content
                with open(full_path_in_output_dir, "w", encoding="utf-8") as f:
                    f.write(content_to_write)
                generated_files[file_path] = content_to_write
                print(f"  Created static/placeholder file: {file_path}")
                continue
            
            # For actual code files, generate content with self-correction
            # Note: Test files will get a placeholder from CodeGen, but then the TestCaseGeneratorAgent will fill them.
            generated_code = self._generate_and_refine_code(file_path, full_context)
            if generated_code:
                with open(full_path_in_output_dir, "w", encoding="utf-8") as f:
                    f.write(generated_code)
                generated_files[file_path] = generated_code
                print(f"  Successfully generated and saved: {file_path}")
            else:
                print(f"  Skipping {file_path} due to persistent generation errors.")
        
        print("Code Generation Agent: Code generation process complete.")
        self.memory.set("generated_codebase_files", generated_files)
        # Store the actual root path where code was generated
        self.memory.set("generated_app_root_path", self.output_dir)
        return generated_files