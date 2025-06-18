"""
Multi-AI Development System API - Development Server

This script provides a development server with hot reload enabled.
Use this during development for faster iteration cycles.
For production deployment, use serve.py instead.
"""

import uvicorn
import os
import sys

def main():
    """Run the API development server with hot reload enabled."""
    print("🔧 Starting Development Server with Hot Reload")
    print("⚠️ For production deployment, use serve.py instead")
    print(f"📂 Working directory: {os.getcwd()}")
    
    # Run the server using app/server.py with reload enabled
    uvicorn.run(
        "app.server:app",
        host="0.0.0.0",
        port=8001,  # Standardized on port 8001
        reload=True
    )

if __name__ == "__main__":
    main()