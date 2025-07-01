#!/bin/bash

echo "🔧 Multi-AI Development System - Starting LangGraph Server"
echo ""

# Set correct environment variables
export LOG_LEVEL=INFO
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_PROJECT=multi-ai-dev-system

echo "✅ Environment variables configured:"
echo "   LOG_LEVEL=$LOG_LEVEL"
echo "   LANGCHAIN_TRACING_V2=$LANGCHAIN_TRACING_V2"
echo "   LANGCHAIN_PROJECT=$LANGCHAIN_PROJECT"
echo ""

# Check if virtual environment exists and activate it
if [ -f "venv/Scripts/activate" ]; then
    echo "✅ Activating virtual environment (Windows)..."
    source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    echo "✅ Activating virtual environment (Linux/Mac)..."
    source venv/bin/activate
else
    echo "⚠️  Virtual environment not found, using system Python"
fi

echo ""
echo "🚀 Starting LangGraph development server..."
echo "📍 Server endpoints:"
echo "   - API: http://127.0.0.1:3001"
echo "   - MCP: http://127.0.0.1:3001/mcp"
echo "   - Docs: http://127.0.0.1:3001/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
langgraph dev --port 3001 --host localhost 