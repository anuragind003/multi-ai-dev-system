import json
import os
from google.generativeai.types import HarmBlockThreshold, HarmCategory

class TestCaseGeneratorAgent:
    def __init__(self, llm, memory, output_dir: str):
        self.llm = llm
        self.memory = memory
        self.output_dir = output_dir

    def run(self, brd_analysis: dict, system_design: dict, generated_code_files: dict, tech_stack: dict) -> dict:
        print("Test Case Generator Agent: Generating test cases...")

        backend_name = tech_stack.get("backend", {}).get("name", "").lower()
        test_framework = "pytest" if "python" in backend_name else "jest" if "node.js" in backend_name else "unspecified"
        test_file_extension = ".py" if "python" in backend_name else ".js"

        # Get the assumed project root within the output directory (e.g., output/app_project)
        # This is a critical assumption. If CodeGenAgent outputs directly to output_dir, use output_dir.
        generated_app_root = os.path.join(self.output_dir, "app_project")
        # For simplicity, if CodeGen creates directly in PROJECT_OUTPUT_DIR:
        generated_app_root = self.output_dir


        # We need the code to generate relevant tests.
        # Iterate over generated_code_files to get an overview, but don't dump all code into prompt.
        code_overview = {}
        for path, content in generated_code_files.items():
            if path.endswith((".py", ".js", ".java")): # Only show code files
                # Take first 10 lines or 500 chars as a snippet
                snippet = "\n".join(content.splitlines()[:10])
                if len(content) > 500:
                    snippet += "\n..."
                code_overview[path] = snippet


        prompt = f"""
        You are an expert Test Engineer AI.
        Your task is to generate automated test cases for the application based on the BRD analysis, system design,
        and an overview of the generated code.

        **Project Context:**
        - **BRD Analysis:** {json.dumps(brd_analysis, indent=2)}
        - **System Design:** {json.dumps(system_design, indent=2)}
        - **Chosen Tech Stack:** {json.dumps(tech_stack, indent=2)}
        - **Generated Code Overview (snippets for context):**
          {json.dumps(code_overview, indent=2)}

        **Instructions:**
        1.  **Test Types:** Focus on generating unit tests for core logic/functions and integration tests for API endpoints.
        2.  **Test Framework:** Use `{test_framework}`.
        3.  **Coverage:** Aim for good coverage, covering happy paths, edge cases, and error conditions (e.g., invalid input, resource not found).
        4.  **Data Persistence:** Ensure tests cover CRUD operations interacting with the database.
        5.  **Output Format:** Provide a JSON object where keys are the relative file paths (e.g., `tests/test_products{test_file_extension}`, `app/tests/unit/test_utils{test_file_extension}`)
            and values are the complete code content for that test file.
        6.  **DO NOT** include markdown fences (```) or explanatory text outside the JSON. The values are pure code.

        Example JSON output for a Flask app with Pytest:
        ```json
        {{
            "tests/test_products{test_file_extension}": \"\"\"
import pytest
from app import create_app
from app.models import Product # Assuming you have a Product model and Flask-SQLAlchemy

@pytest.fixture
def client():
    app = create_app({{
        'TESTING': True,
        'DATABASE': 'sqlite:///test.db'
    }})
    with app.test_client() as client:
        with app.app_context():
            # setup db
            # Product.query.delete()
        yield client

def test_create_product(client):
    response = client.post('/products', json={{"name": "Laptop", "price": 1200.0, "stock_quantity": 5}})
    assert response.status_code == 201
    assert response.json['name'] == 'Laptop'

def test_get_all_products(client):
    # Add products first if necessary
    response = client.get('/products')
    assert response.status_code == 200
    assert isinstance(response.json, list)
\"\"\"
        }}
        ```
        """

        try:
            response = self.llm.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.2 # Slightly higher temperature for test creativity
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

            generated_test_files = json.loads(raw_json_output)
            
            # Save generated test files to disk within the generated application's structure
            # Ensure the test files are placed correctly relative to the generated app root
            saved_files = {}
            for file_path, content in generated_test_files.items():
                full_path = os.path.join(generated_app_root, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                saved_files[file_path] = content
                print(f"  Saved test file: {file_path}")

            print("Test Case Generator Agent: Test case generation complete.")
            return saved_files

        except json.JSONDecodeError as e:
            print(f"JSON Decode Error in Test Case Generator Agent: {e}")
            print(f"Problematic raw output: {raw_json_output}")
            raise
        except Exception as e:
            print(f"Error in Test Case Generator Agent: {e}")
            raise