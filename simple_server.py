"""
Simple FastAPI Server using Unified Workflow
Replaces the complex old server with a clean, minimal approach.
"""

import asyncio
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

from app.endpoints.workflow_endpoints import router as workflow_router
from app.middleware import setup_cors

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Multi-AI Unified Development System",
    description="Clean server using unified async workflow",
    version="2.0.0"
)

# Setup CORS
setup_cors(app)

# Include workflow endpoints
app.include_router(workflow_router, prefix="/api")

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

@app.get("/")
async def root():
    return {
        "message": "Multi-AI Unified Development System", 
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "workflow": "/api/workflow",
            "static": "/static",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "unified-workflow"}

@app.get("/demo")
async def demo_page():
    """Simple demo page for testing"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Multi-AI Dev System</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            h1 { color: #333; }
            .status { background: #e8f5e8; padding: 20px; border-radius: 8px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Multi-AI Development System</h1>
            <div class="status">
                <h3>✅ Server Status: Running</h3>
                <p><strong>Version:</strong> 2.0.0 (Unified Workflow)</p>
                <p><strong>Features:</strong></p>
                <ul>
                    <li>Simplified 4-agent architecture</li>
                    <li>Pure async workflow</li>
                    <li>WebSocket support</li>
                    <li>Human approval system</li>
                </ul>
                <p><strong>API Endpoints:</strong></p>
                <ul>
                    <li><a href="/docs">/docs</a> - API Documentation</li>
                    <li><a href="/api/workflow/status">/api/workflow/status</a> - Workflow Status</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """)

if __name__ == "__main__":
    print("🚀 Starting Multi-AI Unified Development System...")
    print("📋 Server: FastAPI")
    print("🔄 Workflow: Unified Async")
    print("🏗️  Architecture: 4 Simplified Agents")
    print("🌐 Frontend: Vue.js")
    
    uvicorn.run(
        "simple_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 