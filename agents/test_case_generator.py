import json
import os
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from langchain_core.retrievers import BaseRetriever # NEW IMPORT

class TestCaseGeneratorAgent:
    def __init__(self, llm, memory, output_dir: str, rag_retriever: BaseRetriever = None): # NEW PARAM
        self.llm = llm
        self.memory = memory
        self.output_dir = output_dir
        self.rag_retriever = rag_retriever # Store retriever

    def _get_relevant_context_from_rag(self, query: str) -> str:
        """Retrieves relevant documents from the RAG store based on a query."""
        if self.rag_retriever:
            try:
                docs = self.rag_retriever.invoke(query)
                # Concatenate the content of the retrieved documents
                return "\n\n".join([doc.page_content for doc in docs])
            except Exception as e:
                print(f"Warning: RAG retrieval failed: {e}. Proceeding without RAG context.")
                return ""
        return ""

    def run(self, brd_analysis: dict, system_design: dict, generated_code_files: dict, tech_stack: dict) -> dict:
        print("Test Case Generator Agent: Generating test cases...")

        backend_name = tech_stack.get("backend", {}).get("name", "").lower()
        test_framework = "pytest" if "python" in backend_name else "jest" if "node.js" in backend_name else "unspecified"
        test_file_extension = ".py" if "python" in backend_name else ".js"

        generated_app_root = self.output_dir # Assuming generated code is directly in output_dir/project_run_XYZ

        # We need the code to generate relevant tests.
        # Instead of dumping all code snippets into prompt, rely on RAG.
        # We'll still give the LLM a general idea of what files exist to guide its RAG queries.
        code_file_list = [f for f in generated_code_files.keys() if f.lower().endswith((".py", ".js", ".java"))]

        # Prepare core context for the prompt
        core_context_string = json.dumps({
            "brd_analysis": brd_analysis,
            "system_design": system_design,
            "tech_stack": tech_stack,
            "generated_code_files_list": code_file_list # List of generated code files for agent's awareness
        }, indent=2)

        prompt = f"""
        You are an expert Test Engineer AI.
        Your task is to generate automated test cases for the application.

        **Project Core Context:**
        {core_context_string}

        **Instructions:**
        1.  **Test Types:** Focus on generating unit tests for core logic/functions and integration tests for API endpoints.
        2.  **Test Framework:** Use `{test_framework}`.
        3.  **Coverage:** Aim for good coverage, covering happy paths, edge cases, and error conditions (e.g., invalid input, resource not found) for the *implemented functionality*.
        4.  **Data Persistence:** Ensure tests cover CRUD operations interacting with the database.
        5.  **Use RAG for Code Details:** To get details about specific files (e.g., models.py, routes.py), formulate queries (e.g., "Retrieve the code content for app/models.py", "Show API endpoints from system design") and use the RAG retriever to get relevant code snippets or design details. Incorporate the retrieved snippets into your test generation. The RAG will provide specific context from the BRD, system design, and generated code.
        6.  **Output Format:** Provide a JSON object where keys are the relative file paths (e.g., `tests/test_products{test_file_extension}`, `app/tests/unit/test_utils{test_file_extension}`)
            and values are the complete code content for that test file.
        7.  **DO NOT** include markdown fences (```) or explanatory text outside the JSON. The values are pure code.

        Example JSON output for a Flask app with Pytest:
        ```json
        {{
            "tests/test_products{test_file_extension}": \"\"\"
import pytest
from app import create_app # Assuming this is your app factory
# Example of how you might use RAG to get model details:
# relevant_model_context = get_relevant_context_from_rag("database schema and Product model definition")
# Based on retrieved_model_context, construct your test data or mock objects.

@pytest.fixture
def client():
    app = create_app({{
        'TESTING': True,
        'DATABASE': 'sqlite:///test.db'
    }})
    with app.test_client() as client:
        with app.app_context():
            # setup db, e.g., db.create_all() or initialize_test_db() based on context
        yield client

def test_create_product(client):
    response = client.post('/products', json={{"name": "Laptop", "price": 1200.0, "stock_quantity": 5}})
    assert response.status_code == 201
    assert 'id' in response.json and response.json['name'] == 'Laptop'

def test_get_all_products(client):
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