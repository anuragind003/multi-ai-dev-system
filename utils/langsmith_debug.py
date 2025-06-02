import os
from langsmith import Client
from datetime import datetime, timedelta

def check_langsmith_integration():
    """Verify LangSmith integration is working properly"""
    api_key = os.getenv("LANGSMITH_API_KEY")
    project = os.getenv("LANGCHAIN_PROJECT", "Multi-AI-Dev-System")
    
    if not api_key:
        print("❌ LangSmith API key not found in environment")
        return False
    
    try:
        client = Client()
        projects = client.list_projects()
        project_names = [p.name for p in projects]
        
        if project in project_names:
            print(f"✅ LangSmith integration verified - Project '{project}' exists")
            return True
        else:
            print(f"⚠️ Project '{project}' not found. Available projects: {project_names}")
            return False
    except Exception as e:
        print(f"❌ LangSmith connection error: {str(e)}")
        return False

if __name__ == "__main__":
    check_langsmith_integration()