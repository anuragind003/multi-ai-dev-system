# Multi-AI Agent Software Engineering Automation System

A modern, production-ready Python system that automates the entire software development lifecycle from business requirements to deployable code using a pipeline of temperature-optimized AI agents and LangGraph workflows.

---

## 🚀 Features

- **End-to-end automation:** From BRD to code, tests, docs, and deployment configs
- **Specialized AI agents:** Each agent optimized for its task with temperature binding
- **LangGraph workflow engine:** Unified, resumable, and visualizable workflows
- **Enhanced A2A communication:** Intelligent cross-validation and error recovery between agents
- **Multi-format BRD support:** PDF, DOCX, TXT, MD
- **Real-time monitoring:** API call tracking, performance metrics, and error recovery
- **RAG integration:** Vector store for context-aware code generation
- **Extensible architecture:** Modular agents, tools, and workflows
- **Modern Web UI:** Vue.js frontend with real-time monitoring and approval workflows
- **Unified Workflow:** Single, clean async pipeline eliminating sync/async confusion

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

### Prerequisites

- **Python 3.9+** (3.11+ recommended)
- **Node.js 18+** (for frontend)
- **Git**

### 1. Clone and Setup

```bash
git clone https://github.com/anuragind003/multi-ai-dev-system.git
cd multi-ai-dev-system
```

### 2. Backend Setup

#### Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate on Windows:
venv\Scripts\activate

# Activate on Unix/Mac:
source venv/bin/activate
```

#### Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Or install minimally:
pip install google-generativeai python-dotenv fastapi uvicorn langchain langgraph
```

#### Configure Environment Variables

Create a `.env` file in the project root:

```env
# Required: Gemini API Key
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL_NAME=gemini-2.5-flash-preview-05-20

# Optional: LangSmith for tracing
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=multi-ai-dev-system
LANGCHAIN_TRACING_V2=true

# Optional: Rate limiting
LLM_RATE_LIMIT_DELAY=4.0
LLM_MAX_CALLS_PER_MINUTE=15

# Optional: Debug settings
DEBUG_JSON_PARSING=true
```

> **⚠️ Important:** Do NOT commit your `.env` file! Add it to `.gitignore`.

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Return to project root
cd ..
```

---

## 🏃‍♂️ Running the System

### Option 1: Full Stack (Recommended)

#### Start Backend API Server

```bash
# From project root
python -m app.server_refactored
```

The API server will start at `http://localhost:8001`

#### Start Frontend Development Server

```bash
# In a new terminal, from project root
cd frontend
npm run dev
```

The frontend will start at `http://localhost:5173`

#### Access the System

- **Frontend UI:** http://localhost:5173
- **API Documentation:** http://localhost:8001/docs
- **API Health Check:** http://localhost:8001/health
- **Examples:** http://localhost:8001/static/examples.html

### Option 2: Command Line Interface

```bash
# Run with unified workflow (recommended)
python main.py --workflow unified brds/sample.txt

# Run with specific output directory
python main.py --workflow unified --output-dir custom_output brds/sample.txt

# Run with enhanced A2A communication
python main.py --workflow unified --enhanced-a2a brds/sample.txt
```

### Option 3: Development Mode

#### Backend Development

```bash
# Run with auto-reload
uvicorn app.server_refactored:app --reload --host 0.0.0.0 --port 8001

# Run with debug logging
DEBUG=true python -m app.server_refactored
```

#### Frontend Development

```bash
cd frontend
npm run dev
```

---

## 🌐 API Endpoints

### Core Workflow Endpoints

- `POST /api/workflow` - Start new workflow
- `POST /api/workflow-with-monitoring` - Start workflow with real-time monitoring
- `GET /api/agent-sessions` - Get active sessions
- `GET /api/agent-sessions/{session_id}/history` - Get session history
- `GET /api/session-files/{session_id}` - Get generated files

### WebSocket Endpoints

- `WS /ws/agent-monitor` - Real-time agent monitoring
- `WS /ws/workflow-status` - Workflow status updates

### Health & Monitoring

- `GET /health` - Health check
- `GET /api/health` - API health with version info
- `GET /api/temperature-strategy` - Get temperature strategy
- `GET /api/agent-sessions` - Active sessions

---

## 🧠 Workflow Types

| Workflow  | Best For                       | Features                                    |
| --------- | ------------------------------ | ------------------------------------------- |
| unified   | **Production (Recommended)**   | Single async pipeline, clean architecture   |
| basic     | Prototyping, debugging         | Linear, fast, minimal overhead              |
| phased    | Production, real-world dev     | Phase-based, quality checks, error recovery |
| iterative | Complex, high-quality projects | Retry logic, quality threshold, validation  |
| modular   | Education, subsystem focus     | Logical grouping, clear separation          |
| resumable | Large/long projects            | Checkpointing, resume support               |

**Example:**

```bash
# Unified workflow (recommended)
python main.py --workflow unified brds/sample.txt

# With quality threshold
python main.py --workflow unified --quality-threshold 7.0 brds/sample.txt
```

---

## 🔗 Enhanced Agent-to-Agent Communication

The system includes **LangGraph-native enhanced A2A communication** for improved agent coordination:

### Quick Start: Enhanced A2A

```bash
# Basic enhanced A2A with conservative settings
python main.py --workflow unified --enhanced-a2a brds/requirements.pdf

# Aggressive A2A configuration for development
python main.py --workflow unified --enhanced-a2a --a2a-config aggressive brds/requirements.pdf

# Enable specific A2A features
python main.py --workflow unified --enhanced-a2a \
  --enable-cross-validation --enable-error-recovery --a2a-analytics brds/requirements.pdf
```

### A2A Configuration Options

- `conservative`: Production-safe, minimal features
- `default`: Balanced feature set for general use
- `aggressive`: Full feature set for development/testing

---

## 📥 Input & 📤 Output

### Input Formats
- **BRD Documents:** `.txt`, `.md`, `.pdf`, `.docx`, `.doc`
- **API Requests:** JSON payloads via REST API
- **Web Interface:** File upload via Vue.js frontend

### Output Artifacts
- **Requirements Analysis:** Structured requirements extraction
- **Technology Recommendations:** Stack suggestions with reasoning
- **System Architecture:** Design diagrams and specifications
- **Database Schema:** SQL schemas and migration files
- **API Definitions:** OpenAPI specs and endpoint documentation
- **Implementation Code:** Complete application codebase
- **Test Cases:** Unit, integration, and e2e tests
- **Documentation:** README, API docs, deployment guides
- **Deployment Configs:** Docker, CI/CD, infrastructure as code

---

## 🛠️ Development & Debugging

### Backend Development

```bash
# Run with detailed logging
DEBUG=true python -m app.server_refactored

# Run specific workflow test
python -m pytest tests/test_unified_workflow.py -v

# Check API endpoints
curl http://localhost:8001/health
```

### Frontend Development

```bash
cd frontend

# Development with hot reload
npm run dev

# Build for production
npm run build

# Type checking
npm run type-check

# Linting
npm run lint
```

### Debugging Tools

- **LangGraph Dev UI:** `langgraph dev` (if installed)
- **API Documentation:** http://localhost:8001/docs
- **WebSocket Monitor:** Connect to `ws://localhost:8001/ws/agent-monitor`
- **Session Files:** Check `output/` directory for generated artifacts

---

## 🏗️ Project Structure

```
multi-ai-dev-system/
├── app/                    # FastAPI application
│   ├── core/              # Core setup and configuration
│   ├── endpoints/         # API route handlers
│   ├── services/          # Business logic services
│   ├── static/            # Static files (HTML, examples)
│   ├── server_refactored.py  # Main API server
│   └── websocket_manager.py  # WebSocket handling
├── frontend/              # Vue.js frontend application
│   ├── src/               # Source code
│   │   ├── components/    # Vue components
│   │   ├── views/         # Page views
│   │   ├── stores/        # Pinia state management
│   │   └── router/        # Vue Router configuration
│   ├── package.json       # Node.js dependencies
│   └── vite.config.ts     # Vite configuration
├── agents/                # Specialized AI agents
├── tools/                 # Utility tools (code execution, parsing, RAG)
├── workflows/             # Workflow definitions
├── unified_workflow.py    # Unified workflow implementation
├── main.py                # CLI entry point
├── requirements.txt       # Python dependencies
└── brds/                  # Sample BRD documents
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | Required |
| `GEMINI_MODEL_NAME` | Gemini model to use | `gemini-2.5-flash-preview-05-20` |
| `LANGCHAIN_API_KEY` | LangSmith API key | Optional |
| `LANGCHAIN_PROJECT` | LangSmith project name | `multi-ai-dev-system` |
| `LLM_RATE_LIMIT_DELAY` | Rate limiting delay (seconds) | `4.0` |
| `LLM_MAX_CALLS_PER_MINUTE` | Max API calls per minute | `15` |
| `DEBUG_JSON_PARSING` | Enable JSON parsing debug | `true` |

### Temperature Strategy

The system uses temperature-optimized agents for different tasks:

```python
# Analytical tasks (0.1-0.2)
BRD_ANALYST_TEMPERATURE = 0.3
TECH_STACK_ADVISOR_TEMPERATURE = 0.2
SYSTEM_DESIGNER_TEMPERATURE = 0.2

# Creative tasks (0.3-0.4)
PLANNING_AGENT_TEMPERATURE = 0.4

# Code generation (0.1)
CODE_GENERATION_TEMPERATURE = 0.1
TEST_GENERATION_TEMPERATURE = 0.2
```

---

## 🚨 Troubleshooting

### Common Issues

#### Port Conflicts
```bash
# Change backend port
python -m app.server_refactored --port 8002

# Change frontend port
cd frontend && npm run dev -- --port 3000
```

#### Memory Errors
- Increase system RAM for large projects
- Use smaller BRD documents for testing
- Enable caching: `set_llm_cache(SQLiteCache())`

#### API Key Issues
```bash
# Verify API key is set
echo $GEMINI_API_KEY

# Test API connection
curl -H "Authorization: Bearer $GEMINI_API_KEY" \
  https://generativelanguage.googleapis.com/v1beta/models
```

#### Frontend Connection Issues
- Ensure backend is running on port 8001
- Check proxy configuration in `frontend/vite.config.ts`
- Verify WebSocket connection at `ws://localhost:8001/ws/agent-monitor`

#### Workflow Errors
```bash
# Run with debug logging
DEBUG=true python main.py --workflow unified brds/sample.txt

# Check generated files
ls -la output/

# View session history
curl http://localhost:8001/api/agent-sessions
```

### Performance Optimization

- **Enable caching:** LLM responses are cached by default
- **Rate limiting:** Configure `LLM_RATE_LIMIT_DELAY` for your API limits
- **Parallel processing:** Use `--parallel` flag for independent work items
- **Memory management:** Monitor memory usage for large projects

---

## 🤝 Contributing

### Development Setup

1. **Fork the repository**
2. **Create feature branch:** `git checkout -b feature/amazing-feature`
3. **Follow coding standards:**
   - Use type hints
   - Add error handling
   - Follow temperature strategy
   - Add tests for new features
4. **Commit changes:** `git commit -m 'Add amazing feature'`
5. **Push to branch:** `git push origin feature/amazing-feature`
6. **Open Pull Request**

### Code Standards

- **Python:** Follow PEP 8, use type hints, add docstrings
- **Vue.js:** Follow Vue 3 Composition API patterns
- **Testing:** Add unit tests for new agents and tools
- **Documentation:** Update README for new features

---

## 📚 References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Documentation](https://python.langchain.com/)
- [Gemini API](https://ai.google.dev/)
- [Vue.js Documentation](https://vuejs.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🆘 Support

- **Issues:** [GitHub Issues](https://github.com/anuragind003/multi-ai-dev-system/issues)
- **Discussions:** [GitHub Discussions](https://github.com/anuragind003/multi-ai-dev-system/discussions)
- **Documentation:** Check `/docs` directory for detailed guides

---

*Built with ❤️ using LangGraph, FastAPI, and Vue.js*
