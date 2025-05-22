import json
from google.generativeai.types import HarmBlockThreshold, HarmCategory

class SystemDesignerAgent:
    def __init__(self, llm, memory):
        """
        Initializes the SystemDesignerAgent.

        Args:
            llm: An initialized Gemini GenerativeModel instance.
            memory: An instance of SharedProjectMemory for context.
        """
        self.llm = llm
        self.memory = memory

    def run(self, brd_analysis: dict, tech_stack_recommendation: dict) -> dict:
        """
        Generates a high-level system design based on BRD analysis and tech stack.

        Args:
            brd_analysis (dict): Structured output from BRD Analyst Agent.
            tech_stack_recommendation (dict): Structured output from Tech Stack Advisor Agent.

        Returns:
            dict: A JSON object containing the system design.
        """
        print("System Designer Agent: Designing the system architecture...")

        # Extract relevant information
        summary = brd_analysis.get("summary", "N/A")
        functional_reqs = "\n".join(brd_analysis.get("functional_requirements", []))
        non_functional_reqs = "\n".join(brd_analysis.get("non_functional_requirements", []))
        user_stories = "\n".join(brd_analysis.get("user_stories", []))
        assumptions = "\n".join(brd_analysis.get("assumptions", []))

        # Extract chosen tech stack details
        backend_name = tech_stack_recommendation.get("backend", {}).get("name", "N/A")
        database_name = tech_stack_recommendation.get("database", {}).get("name", "N/A")
        frontend_name = tech_stack_recommendation.get("frontend", {}).get("name", "N/A")


        prompt = f"""
        You are an expert System Designer AI.
        Your task is to create a high-level system design based on the provided BRD analysis and chosen technology stack.
        The design should be suitable for a Minimum Viable Product (MVP), prioritizing simplicity and directness.

        **Inputs Provided:**
        - **Project Summary:** {summary}
        - **Functional Requirements:**
          {functional_reqs if functional_reqs else "N/A"}
        - **Non-Functional Requirements:**
          {non_functional_reqs if non_functional_reqs else "N/A"}
        - **User Stories:**
          {user_stories if user_stories else "N/A"}
        - **Assumptions:**
          {assumptions if assumptions else "N/A"}

        - **Chosen Technology Stack:**
            - Frontend: {frontend_name}
            - Backend: {backend_name}
            - Database: {database_name}

        **Design Elements to Include (Output MUST be ONLY a valid JSON object):**

        1.  **`architecture_overview` (string):** A brief description of the overall system architecture (e.g., "A monolithic backend API connecting to a relational database.").
        2.  **`main_modules` (array of strings):** A list of the primary functional modules or components of the system (e.g., "User Management", "Product Catalog", "Order Processing").
        3.  **`api_endpoints` (array of objects):** A list of the essential RESTful API endpoints required to fulfill the functional requirements. For each endpoint, include:
            *   `path` (string): e.g., "/products"
            *   `method` (string): e.g., "GET", "POST", "PUT", "DELETE"
            *   `description` (string): A short explanation of what the endpoint does.
            *   `request_body` (object, optional): Example fields expected in the request body for POST/PUT. Use simple types (string, integer, float).
            *   `response_example` (object, optional): A minimal example of a successful response.
        4.  **`database_schema` (string):** A conceptual database schema in SQL DDL format (e.g., `CREATE TABLE` statements) for the chosen database type. Include primary keys, relevant data types, and foreign keys if applicable. Keep it minimal for MVP.
        5.  **`design_notes` (array of strings):** Any additional brief design considerations, patterns, or specific instructions for the next steps (e.g., "Error handling should return standard HTTP status codes.", "No authentication needed for API calls.").

        **Output Format:**
        Your output MUST be a valid JSON object. Do not include any markdown fences (```json) or conversational text outside the JSON.

        ```json
        {{
            "architecture_overview": "A RESTful API backend service using {backend_name} interacting with a {database_name} database.",
            "main_modules": [
                "Product Management"
            ],
            "api_endpoints": [
                {{
                    "path": "/products",
                    "method": "POST",
                    "description": "Creates a new product.",
                    "request_body": {{"name": "string", "description": "string", "price": 0.0, "stock_quantity": 0}},
                    "response_example": {{"id": "uuid", "name": "string", "price": 0.0}}
                }},
                {{
                    "path": "/products",
                    "method": "GET",
                    "description": "Retrieves all products.",
                    "response_example": [
                        {{"id": "uuid", "name": "string", "price": 0.0}}
                    ]
                }}
            ],
            "database_schema": "CREATE TABLE products (\n    id TEXT PRIMARY KEY,\n    name TEXT NOT NULL,\n    description TEXT,\n    price REAL NOT NULL,\n    stock_quantity INTEGER NOT NULL\n);",
            "design_notes": [
                "All IDs should be unique identifiers (e.g., UUIDs).",
                "Basic error handling for 404 Not Found and 400 Bad Request."
            ]
        }}
        ```
        """

        try:
            response = self.llm.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.1 # Keep low for deterministic design choices
                },
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
            )

            raw_json_output = response.text.strip()

            # Basic post-processing to remove potential markdown fences if they appear
            if raw_json_output.startswith("```json"):
                raw_json_output = raw_json_output.split("```json", 1)[1]
            if raw_json_output.endswith("```"):
                raw_json_output = raw_json_output.rsplit("```", 1)[0]
            raw_json_output = raw_json_output.strip()

            # We can re-use the JSON parsing and error handling pattern from BRDAnalystAgent
            try:
                parsed_data = json.loads(raw_json_output)
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error in System Designer Agent: {e}")
                print(f"Problematic raw output (around position {e.pos}):")
                start = max(0, e.pos - 50)
                end = min(len(raw_json_output), e.pos + 50)
                print(f"...{raw_json_output[start:end]}...")
                print("\n--- Full problematic raw_json_output for debugging ---")
                print(raw_json_output)
                print("--- End full problematic raw_json_output ---")
                raise # Re-raise the exception after printing context

            print("System Designer Agent: Design complete.")
            return parsed_data

        except Exception as e:
            print(f"An unexpected error occurred in System Designer Agent: {e}")
            print(f"Problematic raw output (if any): {response.text if 'response' in locals() else 'No response object'}")
            raise # Re-raise the exception