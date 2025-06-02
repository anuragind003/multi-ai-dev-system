"""
Multi-AI Development System API Server Runner.
Launches the FastAPI server directly with proper paths.
"""

import uvicorn
import os
import sys

def main():
    """Run the API server with appropriate configuration."""
    # Ensure the app directory is in the path
    app_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, app_dir)
    
    print("🚀 Starting Multi-AI Development System API")
    print(f"📂 Working directory: {os.getcwd()}")
    
    # Run the server using app/server.py
    uvicorn.run(
        "app.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

if __name__ == "__main__":
    main()