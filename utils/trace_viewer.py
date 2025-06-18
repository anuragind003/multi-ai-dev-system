import os
import sys
from pathlib import Path

import requests
import webbrowser
from datetime import datetime, timedelta

def open_langsmith_dashboard():
    """Open LangSmith dashboard for the project in a browser."""
    project_name = os.getenv("LANGCHAIN_PROJECT", "Multi-AI-Dev-System")
    url = f"https://smith.langchain.com/projects/{project_name}/runs"
    webbrowser.open(url)
    print(f"Opening LangSmith dashboard: {url}")

def get_recent_runs(limit=10):
    """Get recent runs from the LangSmith API."""
    api_key = os.getenv("LANGSMITH_API_KEY")
    project_name = os.getenv("LANGCHAIN_PROJECT", "Multi-AI-Dev-System")
    
    if not api_key:
        print("Missing LANGSMITH_API_KEY environment variable")
        return None
    
    url = f"https://api.smith.langchain.com/runs"
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {"project": project_name, "limit": limit}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error accessing LangSmith API: {e}")
        return None

if __name__ == "__main__":
    print("📊 LangSmith Trace Viewer")
    print("=" * 50)
    
    # Display recent runs
    runs = get_recent_runs(5)
    if runs:
        print(f"\nRecent runs:")
        for run in runs:
            run_id = run.get("id")
            name = run.get("name", "Unnamed")
            status = run.get("status", "unknown")
            created_at = run.get("created_at", "")
            
            print(f"- {name} ({status}): {created_at[:19]}")
            print(f"  View: https://smith.langchain.com/runs/{run_id}")
    
    # Open dashboard
    choice = input("\nOpen dashboard in browser? (y/n): ")
    if choice.lower() == "y":
        open_langsmith_dashboard()