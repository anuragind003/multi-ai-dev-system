# Multi-AI Development System for Automated Software Engineering

This project implements a comprehensive pipeline of temperature-optimized AI agents that automate the entire software development lifecycle from business requirements to deployable code.

## System Overview

The system processes Business Requirements Documents (BRDs) through specialized agents, each optimized with specific temperature settings:

1. **BRD Analyst Agent** (temp: 0.3): Analyzes and extracts structured requirements from BRD documents
2. **Tech Stack Advisor Agent** (temp: 0.2): Recommends optimal technology stack based on requirements
3. **System Designer Agent** (temp: 0.2): Creates detailed architecture and database schema
4. **Planning Agent** (temp: 0.4): Develops implementation strategy and timelines
5. **Code Generation Agent** (temp: 0.1): Produces deterministic, consistent code output
6. **Test Case Generator Agent** (temp: 0.2): Creates comprehensive test suites
7. **Code Quality Agent** (temp: 0.1): Performs quality analysis and linting
8. **Test Validation Agent** (temp: 0.1): Validates test execution and coverage

## Temperature Optimization Strategy

This system uses specialized agent temperatures to optimize different stages of the development workflow:

- **Analytical tasks (0.1-0.2)**: Code quality, test validation, tech recommendations
- **Creative tasks (0.3-0.4)**: BRD analysis, planning, test case generation
- **Code generation (0.1)**: Deterministic, consistent code output

## Setup Instructions

1. **Clone the repository:**

   ```bash
   git clone https://github.com/anuragind003/multi-ai-dev-system.git
   cd multi-ai-dev-system
   ```

2. **Create a virtual environment (recommended):**

   ```bash
   python -m venv venv
   source venv/bin/activate # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt # (We'll create this later, for now `pip install google-generativeai python-dotenv`)
   ```

4. **Set up API Key:**

   ```
   GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
   GEMINI_MODEL_NAME="gemini-2.5-flash-preview-05-20"
   LANGCHAIN_API_KEY="YOUR_LANGSMITH_API_KEY" # Optional
   LANGCHAIN_PROJECT="multi-ai-dev-system" # Optional
   ```

   ```
   - **IMPORTANT:** Do NOT commit your `.env` file to version control! It's already ignored by the default `.gitignore` if you initialized your repo with Python templates.
   ```

5. **Running the System:**

# Basic usage

`python main.py --workflow phased brds/sample.txt`

# With advanced options

`python main.py --workflow phased --output-dir custom_output brds/sample.txt`

6. **Visual Development Mode (LangGraph Dev)**

# Start the LangGraph development server

langgraph dev

# The UI will open at: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024

7. **Project Structure**

```
multi_ai_dev_system/
├── agents/                 # Specialized AI agents
│   ├── brd_analyst.py      # BRD analysis (temp: 0.3)
│   ├── tech_advisor.py     # Tech recommendations (temp: 0.2)
│   ├── system_designer.py  # Architecture design (temp: 0.2)
│   ├── planning_agent.py   # Implementation planning (temp: 0.4)
│   └── ...
├── tools/                  # Utility tools (code execution, parsing, RAG)
├── brds/                   # Sample BRD documents
├── output/                 # Generated artifacts
├── app/                    # API server components
├── config.py               # LLM configuration and temperature settings
├── monitoring.py           # Real-time API monitoring
├── graph.py                # LangGraph workflow definition
└── main.py                 # System entry point
```

8. **Input Formats**
   The system supports BRDs in multiple formats:

Plain text (.txt)
Markdown (.md)
PDF documents (.pdf)
Word documents (.docx, .doc)

9. **Output Artifacts**
   Each run produces:

Extracted requirements
Technology recommendations
System architecture diagrams
Database schema
API endpoint definitions
Implementation code
Test cases and validation reports

10. **Troubleshooting**
    Port conflicts: If port 8001 is in use, modify the port in serve.py
    Memory errors: For large projects, increase RAM allocation
    RAG indexing errors: Ensure the output directory exists
    API documentation issues: Access the API directly at /api/workflow

11. **Contributing**
    Contributions welcome! Please follow the established temperature strategy for agent development:

BRD analysis: 0.3
Technical planning: 0.2-0.4
Code generation: 0.1
