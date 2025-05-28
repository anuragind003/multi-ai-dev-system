import json
import os
import shutil
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from tools.code_execution_tool import CodeExecutionTool # Updated import
from langchain_core.retrievers import BaseRetriever # NEW IMPORT

class CodeGenerationAgent:
    def __init__(self, llm, memory, output_dir: str, code_execution_tool: CodeExecutionTool, rag_retriever: BaseRetriever = None):
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
        # Ensure the output directory for this specific run is created.
        # This is handled by main.py, but good to ensure here too if this agent is run standalone.
        self.rag_retriever = rag_retriever # Store the retriever
        os.makedirs(self.output_dir, exist_ok=True)
    
    def _get_relevant_context_from_rag(self, query: str) -> str:
        """Retrieves relevant documents from the RAG store based on a query."""
        if self.rag_retriever:
            try:
                # Query the retriever and get content from retrieved documents
                docs = self.rag_retriever.invoke(query)
                # Concatenate the content of the retrieved documents
                return "\n\n".join([doc.page_content for doc in docs])
            except Exception as e:
                print(f"Warning: RAG retrieval failed: {e}. Proceeding without RAG context.")
                return ""
        return ""
    

    def _generate_file_structure(self, brd_analysis: dict, tech_stack_recommendation: dict, system_design: dict) -> dict:
        """
        Asks LLM to generate a proposed file structure for the project.
        """
        print("Code Generation Agent: Generating project file structure...")
        
        # Prepare context for the prompt
        backend_name = tech_stack_recommendation.get('backend', {}).get('name', 'selected backend')
        architecture_overview = system_design.get('architecture_overview', 'application')
        
        # Use full details from memory for this initial broad step
        # This will be added to RAG too, so individual file generation can retrieve it.
        context_for_llm_string = json.dumps({
            "brd_analysis": brd_analysis,
            "tech_stack_recommendation": tech_stack_recommendation,
            "system_design": system_design
        }, indent=2)
        
        prompt = f"""
        You are an expert Software Engineer AI.
        Based on the following project context (BRD analysis, tech stack, and system design),
        propose a suitable file and directory structure for the entire application.

        Focus on a typical, clean, and organized structure for a {backend_name}-based {architecture_overview}.
        Include common and necessary files for the chosen tech stack, such as:
        - `README.md`
        - The primary dependency file (e.g., `requirements.txt` for Python, `package.json` for Node.js) MUST be placed at the ROOT of the project.
        - Main application entry point (e.g., `app.py`, `main.py`, `run.py`, `index.js`)
        - Configuration files (e.g., `config.py`)
        - Database models/schema definitions
        - API endpoint definitions/routes
        - A dedicated `tests/` directory for test files.

        The output should be a JSON object where keys are relative file paths (e.g., "src/main.py", "README.md", "tests/test_api.py")
        and values are placeholder content indicating the file's purpose (e.g., "# Main application entry point", "## Project Readme").
        Do NOT include actual code here, just placeholders.

        Ensure the output is ONLY a valid JSON object.

        --- Project Context ---
        {context_for_llm_string}
        --- END Project Context ---

        Example Output for a Flask app (ensure test files are explicitly part of the structure):
        ```json
        {{
            "README.md": "# Project Title",
            "requirements.txt": "Flask\\nSQLAlchemy\\npytest\\nflake8\\ncoverage",
            "run.py": "# Entry point for the Flask application",
            "app/__init__.py": "# App package initialization",
            "app/config.py": "# Configuration settings",
            "app/models.py": "# Database models",
            "app/routes.py": "# API endpoints",
            "tests/test_api.py": "# Unit and integration tests for the API"
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
            # Clean up markdown code block fences if LLM sometimes includes them despite response_mime_type
            if raw_json_output.startswith("```json"):
                raw_json_output = raw_json_output.split("```json", 1)[1]
            if raw_json_output.endswith("```"):
                raw_json_output = raw_json_output.rsplit("```", 1)[0]
            raw_json_output = raw_json_output.strip()

            return json.loads(raw_json_output)
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error in file structure generation: {e}")
            print(f"Problematic raw output: {raw_json_output}")
            return {} # Return empty structure if parsing fails (will lead to early exit)
        except Exception as e:
            print(f"Error generating file structure: {e}")
            return {}

    def _generate_file_structure(self, brd_analysis: dict, tech_stack_recommendation: dict, system_design: dict) -> dict: # Updated parameters
        """
        Asks LLM to generate a proposed file structure for the project.
        """
        print("Code Generation Agent: Generating project file structure...")
        
        # REMOVE this line if it's still there:
        # context_data = json.loads(context_for_llm) 

        # Directly use the tech_stack_recommendation parameter
        backend_name = tech_stack_recommendation.get('backend', {}).get('name', 'selected backend')
        architecture_overview = system_design.get('architecture_overview', 'application')
        
        # Prepare context for the prompt
        # This string is what gets passed to the LLM for its understanding.
        context_for_llm_string = json.dumps({
            "brd_analysis": brd_analysis,
            "tech_stack_recommendation": tech_stack_recommendation,
            "system_design": system_design
            # Do NOT include "previous_errors_feedback" here, it's specific to file content generation
        }, indent=2)

        prompt = f"""
        You are an expert Software Engineer AI.
        Based on the following project context (BRD analysis, tech stack, and system design),
        propose a suitable file and directory structure for the entire application.

        Focus on a typical, clean, and organized structure for a {backend_name}-based {architecture_overview}.
        Include common and necessary files for the chosen tech stack, such as:
        - `README.md`
        - The primary dependency file (e.g., `requirements.txt` for Python, `package.json` for Node.js) MUST be placed at the ROOT of the project.
        - Main application entry point (e.g., `app.py`, `main.py`, `run.py`, `index.js`)
        - Configuration files (e.g., `config.py`)
        - Database models/schema definitions
        - API endpoint definitions/routes
        - A dedicated `tests/` directory for test files.

        The output should be a JSON object where keys are relative file paths (e.g., "src/main.py", "README.md", "tests/test_api.py")
        and values are placeholder content indicating the file's purpose (e.g., "# Main application entry point", "## Project Readme").
        Do NOT include actual code here, just placeholders.

        Ensure the output is ONLY a valid JSON object.

        --- Project Context ---
        {context_for_llm_string}
        --- END Project Context ---

        Example Output for a Flask app (ensure test files are explicitly part of the structure):
        ```json
        {{
            "README.md": "# Project Title",
            "requirements.txt": "Flask\\nSQLAlchemy\\npytest\\nflake8\\ncoverage",
            "run.py": "# Entry point for the Flask application",
            "app/__init__.py": "# App package initialization",
            "app/config.py": "# Configuration settings",
            "app/models.py": "# Database models",
            "app/routes.py": "# API endpoints",
            "tests/test_api.py": "# Unit and integration tests for the API"
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
            return {} # Return empty structure if parsing fails (will lead to early exit)
        except Exception as e:
            print(f"Error generating file structure: {e}")
            return {}

    def _generate_and_refine_code(self, file_path: str, brd_analysis: dict, tech_stack_recommendation: dict, system_design: dict, error_feedback: str = "", max_retries: int = 3) -> str:
        """
        Generates code for a single file and attempts to self-correct using the interpreter.
        """
        print(f"  Generating code for: {file_path}")
        
        # --- CRITICAL FIX: Assign tech_stack_recommendation to a local 'tech_stack' variable for convenience ---
        tech_stack = tech_stack_recommendation 

        backend_name_raw = tech_stack.get("backend", {}).get("name", "N/A")
        backend_lang = backend_name_raw.split('/')[0].lower()
        
        # Determine specific instructions for the file based on its path
        file_role_instruction = f"Write the code for this file `{file_path}` based on its implied role in a {backend_name_raw} project. Focus on implementing relevant logic from the system design."
        if "readme.md" in file_path.lower():
            file_role_instruction = "Write a comprehensive README.md file for the project, including setup, how to run, and API endpoints documentation."
        elif "requirements.txt" in file_path.lower() and backend_lang == "python":
            file_role_instruction = f"List all necessary Python packages for a {backend_name_raw} project based on the requirements and system design. Include common packages for web APIs, database interaction, testing, and linting (e.g., Flask, SQLAlchemy, pytest, flake8, coverage). Output ONLY the package names, one per line. Ensure the list is comprehensive and accurate."
        elif "package.json" in file_path.lower() and (backend_lang == "node.js" or tech_stack.get("frontend",{}).get("name", "").lower() in ["react", "vue.js"]):
            file_role_instruction = f"Generate a complete package.json for a {backend_name_raw} project, including dependencies for API, database, and testing (e.g., express, pg, jest). Include scripts for start, test, and lint if applicable. Output ONLY the JSON. Ensure all necessary dependencies are listed."
        elif "__init__.py" in file_path.lower() and backend_lang == "python":
            file_role_instruction = "Write the `__init__.py` file to initialize the Python package. If it's the main app package, define the `create_app()` function here which sets up the Flask/Django app, connects to DB, and registers blueprints/routes."
        elif "config.py" in file_path.lower() and backend_lang == "python":
            file_role_instruction = "Write the `config.py` for Python, defining configuration classes (e.g., `Config`, `DevelopmentConfig`, `TestingConfig`) for database URI, secret keys, etc."
        elif "models.py" in file_path.lower() and backend_lang == "python":
            file_role_instruction = "Write the `models.py` file for Python using SQLAlchemy, defining database models (`Product` etc.) based on the `database_schema` in the system design. Include UUID for primary keys if specified."
        elif "routes.py" in file_path.lower() and backend_lang == "python":
            file_role_instruction = "Write the `routes.py` file for Python using Flask Blueprints, implementing all API endpoints defined in the system design (GET, POST, PUT, DELETE for products). Ensure proper JSON responses and basic error handling."
        elif "run.py" in file_path.lower() and backend_lang == "python":
            file_role_instruction = "Write the `run.py` entry point for the Flask application. It should import and run the app from `app/__init__.py`. Include commands to initialize the database if it's SQLite (create tables)."
        elif "tests/" in file_path.lower():
            file_role_instruction = f"This is a test file. Provide a basic placeholder structure for tests compatible with `{tech_stack.get('backend', {}).get('name', 'selected tech')}`'s testing framework (e.g., Pytest/Jest). You will fill this later."
        elif file_path.lower().endswith(".db"):
            file_role_instruction = "This is a database file (e.g., SQLite). Provide just a comment indicating its purpose, no code content needed."


        # --- RAG Integration for Context ---
        query = f"BRD requirements, system design, and existing code for file: {file_path}, to write code for a {backend_name_raw} application."
        retrieved_context = self._get_relevant_context_from_rag(query)
        
        # Combine all relevant structured information for the prompt
        full_prompt_context_data = {
            "brd_analysis": brd_analysis,
            "tech_stack_recommendation": tech_stack, # <--- Use the assigned tech_stack here
            "system_design": system_design,
            "relevant_retrieved_context_from_rag": retrieved_context if retrieved_context else "No additional relevant context retrieved from RAG.",
            "previous_errors_feedback": error_feedback if error_feedback else "No previous errors."
        }
        full_prompt_context_string = json.dumps(full_prompt_context_data, indent=2)

        initial_prompt = f"""
        You are an expert Software Engineer AI.
        Your task is to write the complete code for the file `{file_path}`
        based on the provided project context.

        The chosen tech stack includes:
        - Backend: {backend_name_raw}
        - Database: {tech_stack.get("database", {}).get("name", "N/A")}
        - Frontend: {tech_stack.get("frontend", {}).get("name", "N/A")}

        --- Project Context ---
        {full_prompt_context_string}
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
                        "temperature": 0.1
                    },
                    safety_settings={
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    }
                )
                generated_code = response.text.strip()
                
                if generated_code.startswith("```"):
                    parts = generated_code.split('\n', 1) 
                    if len(parts) > 1:
                        generated_code = parts[1] 
                    if generated_code.endswith("```"):
                        generated_code = generated_code[:-3].strip() 

                if "requirements.txt" in file_path.lower() or "package.json" in file_path.lower():
                    if not generated_code.strip():
                        print(f"  Warning: {file_path} is empty, but expected content. Forcing retry.")
                        raise ValueError(f"{file_path} generated empty content.")
                    print(f"  Dependency file {file_path} generated content.")
                    return generated_code 

                if not (file_path.lower().endswith((".py", ".js", ".java", ".ts", ".go", ".c", ".cpp"))):
                    print(f"  Skipping interpreter check for non-code file: {file_path}")
                    return generated_code

                full_file_path_in_output = os.path.join(self.output_dir, file_path)
                success, output = self.code_execution_tool.run_syntax_check(generated_code, file_path=full_file_path_in_output, lang=backend_lang)
                
                if success:
                    print(f"  Code for {file_path} looks good (basic check).")
                    return generated_code
                else:
                    print(f"  Code check failed for {file_path} (Retry {retry+1}/{max_retries}):\n{output.strip()}")
                    
                    error_detail_prompt = ""
                    if "F541" in output:
                        error_detail_prompt += "\n**CRITICAL F541 ERROR:** The f-string is malformed or missing placeholders. Ensure all variables within f-strings are correctly defined and braced (e.g., `f\"Hello, {name}\"`)."
                    if "F821" in output:
                        error_detail_prompt += "\n**CRITICAL F821 ERROR:** An 'undefined name' was found. This means a variable, function, or class was used without being imported or defined. Ensure all necessary imports are at the top of the file, and all variables/functions are declared before use."
                    if "C901" in output:
                        error_detail_prompt += "\n**C901 COMPLEXITY WARNING:** While not blocking, consider simplifying highly complex functions by breaking them into smaller, more focused units. This improves readability and maintainability."
                    
                    current_prompt = (
                        initial_prompt +
                        f"\n\nThe previous attempt to generate code for `{file_path}` resulted in errors:\n"
                        f"```\n{output}\n```\n"
                        f"Please review the errors carefully and generate corrected, complete code for this file. "
                        f"{error_detail_prompt.strip()}\n\n"
                        "Remember to output ONLY the code, no markdown fences or extra text. "
                        "Ensure all necessary imports are present and paths are correct relative to the project root. "
                        "Pay close attention to Python package imports if this file is part of a larger package structure. "
                        "If the error is 'ModuleNotFoundError', ensure the necessary modules are installed/defined or that the import path is correct."
                        "Ensure the file contains substantial, functional code relevant to its role."
                    )
            except Exception as e:
                print(f"  Error during code generation/refinement for {file_path}: {e}")
                current_prompt = (
                    initial_prompt +
                    f"\n\nAn unexpected error occurred during code generation/check for `{file_path}`: {e}. "
                    "Please ensure the code is syntactically correct and includes all necessary imports for a standalone runnable file. "
                    "Remember to output ONLY the code, no markdown fences or extra text. "
                    "Ensure the file contains substantial, functional code relevant to its role."
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

        # The full_context string for initial prompt is now just the core structured data
        # This will be added to RAG, so individual file generation can retrieve relevant parts.
        full_context_core_for_initial_prompt = json.dumps({
            "brd_analysis": brd_analysis,
            "tech_stack_recommendation": tech_stack_recommendation,
            "system_design": system_design,
            "previous_errors_feedback": error_feedback
        }, indent=2)

        # 1. Generate the initial file structure
        # This initial step still needs the full high-level context
        file_structure = self._generate_file_structure(brd_analysis, tech_stack_recommendation, system_design) # Updated call parameters
        if not file_structure:
            print("Code Generation Agent: Failed to generate a valid file structure. Aborting.")
            return {}

        generated_files = {}

        # 2. Iterate through the proposed file structure and generate content for each file
        for file_path, placeholder_content in file_structure.items():
            full_path_in_output_dir = os.path.join(self.output_dir, file_path)
            os.makedirs(os.path.dirname(full_path_in_output_dir), exist_ok=True)

            is_test_file_path = "tests/" in file_path.lower() or file_path.lower().startswith("test_")

            # For static files like README, requirements.txt, or .db (placeholder content only)
            # The LLM gives us placeholder content for these.
            if any(ext in file_path.lower() for ext in ["readme.md", "requirements.txt", "package.json", ".gitignore", ".env.example"]) or \
               (file_path.lower().endswith(".db") and not is_test_file_path):
                content_to_write = placeholder_content
                with open(full_path_in_output_dir, "w", encoding="utf-8") as f:
                    f.write(content_to_write)
                generated_files[file_path] = content_to_write
                print(f"  Created static/placeholder file: {file_path}")
                continue
            
            # For actual code files, generate content with self-correction
            # Pass individual structured contexts to the generator, RAG will pick up relevant parts
            generated_code = self._generate_and_refine_code(
                file_path,
                brd_analysis,             # Pass full structured BRD
                tech_stack_recommendation, # Pass full structured tech stack
                system_design,             # Pass full structured system design
                error_feedback             # Pass error feedback
            )
            if generated_code:
                with open(full_path_in_output_dir, "w", encoding="utf-8") as f:
                    f.write(generated_code)
                generated_files[file_path] = generated_code
                print(f"  Successfully generated and saved: {file_path}")
            else:
                print(f"  Skipping {file_path} due to persistent generation errors.")
        
        print("Code Generation Agent: Code generation process complete.")
        self.memory.set("generated_codebase_files", generated_files)
        self.memory.set("generated_app_root_path", self.output_dir) # This should point to the specific run directory
        return generated_files