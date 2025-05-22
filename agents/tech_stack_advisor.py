import json
from google.generativeai.types import HarmBlockThreshold, HarmCategory
# from config import get_gemini_model # Not directly used in the agent's run method, but good to keep if needed later

class TechStackAdvisorAgent:
    def __init__(self, llm, memory):
        """
        Initializes the TechStackAdvisorAgent.

        Args:
            llm: An initialized Gemini GenerativeModel instance.
            memory: An instance of SharedProjectMemory for context.
        """
        self.llm = llm
        self.memory = memory

    def run(self, brd_analysis: dict) -> dict:
        """
        Analyzes the BRD analysis and recommends a suitable technology stack.

        Args:
            brd_analysis (dict): The structured output from the BRD Analyst Agent.

        Returns:
            dict: A JSON object containing the recommended tech stack and justifications.
        """
        print("Tech Stack Advisor Agent: Analyzing requirements to recommend tech stack...")

        # Extract relevant information from the BRD analysis
        functional_reqs = "\n".join(brd_analysis.get("functional_requirements", []))
        non_functional_reqs = "\n".join(brd_analysis.get("non_functional_requirements", []))
        summary = brd_analysis.get("summary", "No summary provided.")
        assumptions = "\n".join(brd_analysis.get("assumptions", []))


        prompt = f"""
        You are an expert Software Architect and Technology Advisor AI.
        Your task is to recommend a suitable technology stack (frontend, backend, database) for a software project
        based on the provided BRD analysis.

        Consider the following derived from the BRD:
        - **Project Summary:** {summary}
        - **Functional Requirements:**
          {functional_reqs if functional_reqs else "N/A"}
        - **Non-Functional Requirements:**
          {non_functional_reqs if non_functional_reqs else "N/A"}
        - **Assumptions:**
          {assumptions if assumptions else "N/A"}

        **Specific Instructions for your Recommendation:**
        1.  **Prioritize Simplicity:** For this initial MVP, the chosen technology stack should prioritize ease of development, quick deployment, and minimal complexity.
        2.  **Backend:** Recommend a specific language/framework (e.g., Python/Flask, Node.js/Express, Java/Spring Boot, Go/Gin).
        3.  **Database:** Recommend a specific database type (e.g., PostgreSQL, MongoDB, SQLite). For simplicity and speed for MVP, consider lightweight options first if appropriate.
        4.  **Frontend:** If the project implies a web interface, recommend a simple frontend framework (e.g., React, Vue.js, basic HTML/JS). If it's purely an API, explicitly state "None" for frontend.
        5.  **Justification:** Provide a concise reason for each choice, explicitly linking it to the requirements (especially non-functional ones like "simplicity" or "data persistence").
        6.  **Overall Rationale:** A brief explanation of why the entire stack is a good fit.

        **Output Format:**
        Your output MUST be a valid JSON object. Do not include any markdown fences (```json) or conversational text.

        ```json
        {{
            "frontend": {{
                "name": "React",
                "justification": "Chosen for its component-based architecture and widespread community support, suitable for interactive web interfaces."
            }},
            "backend": {{
                "name": "Python/Flask",
                "justification": "Flask is lightweight and flexible, ideal for rapid API development as required by the BRD's simplicity NFR. Python's ease of use accelerates development."
            }},
            "database": {{
                "name": "SQLite",
                "justification": "SQLite is a file-based database, perfect for local development and simple deployments, aligning with the MVP's simplicity and single-server deployment assumption. Ensures data persistence."
            }},
            "overall_rationale": "This stack balances rapid development with the functional requirements of a CRUD API. Python/Flask provides a lightweight backend, SQLite handles data persistence with zero configuration, and a basic frontend (if needed) can consume the API easily."
        }}
        ```
        """

        try:
            response = self.llm.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json", # Crucial for telling Gemini to output JSON directly
                    "temperature": 0.1 # Keep low for deterministic choices in tech stack
                },
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
            )

            # Access the JSON content directly from response.text
            raw_json_output = response.text.strip() # Strip any leading/trailing whitespace

            # Basic post-processing to remove potential markdown fences if they appear
            if raw_json_output.startswith("```json"):
                raw_json_output = raw_json_output.split("```json", 1)[1]
            if raw_json_output.endswith("```"):
                raw_json_output = raw_json_output.rsplit("```", 1)[0]
            raw_json_output = raw_json_output.strip()

            # Attempt to parse the JSON
            parsed_data = json.loads(raw_json_output)

            print("Tech Stack Advisor Agent: Recommendation complete.")
            return parsed_data

        except json.JSONDecodeError as e:
            print(f"JSON Decode Error in Tech Stack Advisor Agent: {e}")
            print(f"Problematic raw output (around position {e.pos}):")
            start = max(0, e.pos - 50)
            end = min(len(raw_json_output), e.pos + 50)
            print(f"...{raw_json_output[start:end]}...")
            print("\n--- Full problematic raw_json_output for debugging ---")
            print(raw_json_output)
            print("--- End full problematic raw_json_output ---")
            raise # Re-raise the exception after printing context

        except Exception as e:
            print(f"An unexpected error occurred in Tech Stack Advisor Agent: {e}")
            print(f"Problematic raw output (if any): {response.text if 'response' in locals() else 'No response object'}")
            raise # Re-raise the exception