@echo off
echo 🔧 Multi-AI Development System - Starting LangGraph Server
echo.

REM Set correct environment variables
set LOG_LEVEL=INFO
set LANGCHAIN_TRACING_V2=true
set LANGCHAIN_PROJECT=multi-ai-dev-system

echo ✅ Environment variables configured:
echo    LOG_LEVEL=%LOG_LEVEL%
echo    LANGCHAIN_TRACING_V2=%LANGCHAIN_TRACING_V2%
echo    LANGCHAIN_PROJECT=%LANGCHAIN_PROJECT%
echo.

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    echo ✅ Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo ⚠️  Virtual environment not found, using system Python
)

echo.
echo 🚀 Starting LangGraph development server...
echo 📍 Server endpoints:
echo    - API: http://127.0.0.1:3001
echo    - MCP: http://127.0.0.1:3001/mcp
echo    - Docs: http://127.0.0.1:3001/docs
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the server
langgraph dev --port 3001 --host localhost

pause 