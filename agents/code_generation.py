import json
import os
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from tools.code_interpreter import CodeInterpreterTool

class CodeGenerationAgent:
    def __init__(self, llm, memory, output_dir: str):
        """
        Initializes the CodeGenerationAgent.

        Args:
            llm: An initialized Gemini GenerativeModel instance.
            memory: An instance of SharedProjectMemory.
            output_dir (str): The root directory where generated code will be saved.
        """
        self.llm = llm
        self.memory = memory
        self.output_dir = output_dir
        self.interpreter = CodeInterpreterTool(output_dir=output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

    def _generate_file_structure(self, context_for_llm: str) -> dict:
        """
        Asks LLM to generate a proposed file structure for the project.
        """
        print("Code Generation Agent: Generating project file structure...")
        prompt = f"""
        You are an expert Software Engineer AI.
        Based on the following project context (BRD analysis, tech stack, and system design),
        propose a suitable file and directory structure for the entire application.

        Focus on a typical structure for a {json.loads(context_for_llm).get('tech_stack_recommendation', {}).get('backend', {}).get('name', 'selected backend')}-based {json.loads(context_for_llm).get('system_design', {}).get('architecture_overview', 'application')}.
        Include common files like `requirements.txt` (for Python), `package.json` (for Node.js), `README.md`, config files, main app files, routes, models, etc.

        The output should be a JSON object where keys are file paths (e.g., "src/main.py", "README.md")
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
            "app.py": "# Main Flask application",
            "config.py": "# Configuration settings",
            "models.py": "# Database models",
            "routes.py": "# API endpoints"
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
        initial_prompt = f"""
        You are an expert Software Engineer AI.
        Your task is to write the complete code for the file `{file_path}`
        based on the provided project context (BRD analysis, tech stack, system design).

        The chosen tech stack includes:
        - Backend: {json.loads(context_for_llm).get('tech_stack_recommendation', {}).get('backend', {}).get('name', 'N/A')}
        - Database: {json.loads(context_for_llm).get('tech_stack_recommendation', {}).get('database', {}).get('name', 'N/A')}
        - Frontend: {json.loads(context_for_llm).get('tech_stack_recommendation', {}).get('frontend', {}).get('name', 'N/A')}

        --- Project Context ---
        {context_for_llm}
        --- END Project Context ---

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

                # Use interpreter for basic syntax/import check
                success, output = self.interpreter.run_python_check(generated_code, file_path=file_path) # Use the actual file_path
                
                if success:
                    print(f"  Code for {file_path} looks good (basic check).")
                    return generated_code
                else:
                    print(f"  Code check failed for {file_path} (Retry {retry+1}/{max_retries}): {output.strip()}")
                    # Refine prompt with error feedback
                    current_prompt = (
                        initial_prompt +
                        f"\n\nThe previous attempt to generate code for `{file_path}` resulted in errors:\n"
                        f"```\n{output}\n```\n"
                        "Please review the errors and generate corrected, complete code for this file. "
                        "Remember to output ONLY the code, no markdown fences or extra text."
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

    def run(self, brd_analysis: dict, tech_stack_recommendation: dict, system_design: dict) -> dict:
        """
        Generates the entire codebase for the project.
        """
        print("Code Generation Agent: Starting code generation process...")

        # Consolidate all context into a single string for the LLM
        # This string will be converted to JSON by the LLM in the first step
        # and then back to JSON for internal use by the CodeGenAgent
        full_context = json.dumps({
            "brd_analysis": brd_analysis,
            "tech_stack_recommendation": tech_stack_recommendation,
            "system_design": system_design
        }, indent=2)

        # 1. Generate the initial file structure
        file_structure = self._generate_file_structure(full_context)
        if not file_structure:
            print("Code Generation Agent: Failed to generate a valid file structure. Aborting.")
            return {}

        generated_files = {}

        # 2. Iterate through the proposed file structure and generate content for each file
        for file_path, placeholder_content in file_structure.items():
            full_file_path = os.path.join(self.output_dir, file_path)
            os.makedirs(os.path.dirname(full_file_path), exist_ok=True) # Ensure directory exists

            # If it's a basic file like README or requirements.txt, just write the placeholder content
            if file_path in ["README.md", "requirements.txt", "package.json", ".gitignore", "Dockerfile"]:
                content_to_write = placeholder_content
                with open(full_file_path, "w", encoding="utf-8") as f:
                    f.write(content_to_write)
                generated_files[file_path] = content_to_write # Store for memory
                print(f"  Created static file: {file_path}")
                continue
            
            # For actual code files, generate content with self-correction
            generated_code = self._generate_and_refine_code(file_path, full_context)
            if generated_code:
                with open(full_file_path, "w", encoding="utf-8") as f:
                    f.write(generated_code)
                generated_files[file_path] = generated_code # Store for memory
                print(f"  Successfully generated and saved: {file_path}")
            else:
                print(f"  Skipping {file_path} due to persistent generation errors.")
        
        print("Code Generation Agent: Code generation process complete.")
        self.memory.set("generated_codebase_files", generated_files) # Store a record of what was generated
        return generated_files