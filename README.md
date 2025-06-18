# Multi-AI Agent Software Engineering Automation System

A modern, production-ready Python system that automates the entire software development lifecycle from business requirements to deployable code using a pipeline of temperature-optimized AI agents and LangGraph workflows.

---

## 🚀 Features

- **End-to-end automation:** From BRD to code, tests, docs, and deployment configs
- **Specialized AI agents:** Each agent optimized for its task with temperature binding
- **LangGraph workflow engine:** Unified, resumable, and visualizable workflows
- **Multi-format BRD support:** PDF, DOCX, TXT, MD
- **Real-time monitoring:** API call tracking, performance metrics, and error recovery
- **RAG integration:** Vector store for context-aware code generation
- **Extensible architecture:** Modular agents, tools, and workflows

---

## 🧩 Agent Pipeline & Temperature Strategy

| Agent                 | Purpose                              | Temperature |
| --------------------- | ------------------------------------ | ----------- |
| BRD Analyst           | Extracts structured requirements     | 0.3         |
| Tech Stack Advisor    | Recommends technology stack          | 0.2         |
| System Designer       | Architecture & DB schema             | 0.2         |
| Planning Agent        | Implementation strategy & timeline   | 0.4         |
| Code Generation Agent | Deterministic code output            | 0.1         |
| Test Case Generator   | Comprehensive test suites            | 0.2         |
| Code Quality Agent    | Quality analysis & linting           | 0.1         |
| Test Validation Agent | Test execution & coverage validation | 0.1         |

- **Analytical tasks:** 0.1–0.2
- **Creative tasks:** 0.3–0.4
- **Code generation:** 0.1

---

## ⚡ Quickstart

1. **Clone the repository:**

   ```bash
   git clone https://github.com/anuragind003/multi-ai-dev-system.git
   cd multi-ai-dev-system
   ```

2. **Create a virtual environment:**

   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Unix/Mac:
   source venv/bin/activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   # Or minimally:
   pip install google-generativeai python-dotenv
   ```

4. **Configure environment variables:**
   Create a `.env` file in the project root:

   ```env
   GEMINI_API_KEY=your_gemini_api_key
   GEMINI_MODEL_NAME=gemini-2.5-flash-preview-05-20
   LANGCHAIN_API_KEY=your_langsmith_api_key  # Optional
   LANGCHAIN_PROJECT=multi-ai-dev-system     # Optional
   ```

   > **Do NOT commit your `.env` file!**

5. **Run the system:**
   ```bash
   python main.py --workflow phased brds/sample.txt
   # With options:
   python main.py --workflow phased --output-dir custom_output brds/sample.txt
   ```

---

## 🏗️ Project Structure

```
multi_ai_dev_system/
├── agents/                 # Specialized AI agents
├── tools/                  # Utility tools (code execution, parsing, RAG)
├── brds/                   # Sample BRD documents
├── output/                 # Generated artifacts
├── app/                    # API server components
├── config.py               # LLM configuration and temperature settings
├── monitoring.py           # Real-time API monitoring
├── graph.py                # LangGraph workflow definition
├── main.py                 # System entry point
└── ...
```

---

## 📥 Input & 📤 Output

- **Input:** BRD in `.txt`, `.md`, `.pdf`, `.docx`, or `.doc`
- **Output:**
  - Extracted requirements
  - Technology recommendations
  - System architecture diagrams
  - Database schema
  - API endpoint definitions
  - Implementation code
  - Test cases & validation reports
  - Documentation & deployment configs

---

## 🧠 Workflow Types

| Workflow  | Best For                       | Features                                    |
| --------- | ------------------------------ | ------------------------------------------- |
| basic     | Prototyping, debugging         | Linear, fast, minimal overhead              |
| phased    | Production, real-world dev     | Phase-based, quality checks, error recovery |
| iterative | Complex, high-quality projects | Retry logic, quality threshold, validation  |
| modular   | Education, subsystem focus     | Logical grouping, clear separation          |
| resumable | Large/long projects            | Checkpointing, resume support               |

**Example:**

```bash
python main.py --brd brds/sample.txt --workflow phased --quality-threshold 7.0
```

---

## 🌐 API & Dev Server

- **Production API:**
  ```bash
  python serve.py
  # API at http://localhost:8001
  ```
- **LangGraph Dev UI:**
  ```bash
  langgraph dev
  # UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
  ```

---

## 🛠️ Troubleshooting

- **Port conflicts:** Change port in `serve.py` if 8001 is in use
- **Memory errors:** Increase RAM for large projects
- **RAG errors:** Ensure output directory exists
- **API docs:** Access `/api/workflow` endpoint
- **LangGraph errors:** Ensure all node names use `_node` suffix; check for missing function imports

---

## 🤝 Contributing

- Follow the agent temperature strategy
- Use type hints, error handling, and logging
- See `CONTRIBUTING.md` for details (or open an issue)

---

## 📚 References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Documentation](https://python.langchain.com/)
- [Gemini API](https://ai.google.dev/)

---

## License

MIT
