from fastapi import FastAPI
from langserve import add_routes
from langchain_core.prompts import PromptTemplate
import os
import sys

# Import from the project
from serve_chain import create_workflow_runnable
from config import get_llm

# Initialize FastAPI app
app = FastAPI(
    title="Multi-AI Development System API",
    version="1.0",
    description="API for automated software development using specialized AI agents"
)

@app.get("/")
def read_root():
    return {"message": "Multi-AI Development System API is running"}

# Create API output directory if it doesn't exist
api_output_dir = os.path.join(os.getcwd(), "output", "api_workflow")
os.makedirs(api_output_dir, exist_ok=True)

# Create runnable workflow
workflow_runnable = create_workflow_runnable()

# Add routes using the runnable workflow
add_routes(
    app,
    workflow_runnable,
    path="/api/workflow",
)

# Get LLM for additional routes
llm = get_llm()

# Create a prompt template - MODERN APPROACH (no deprecated LLMChain)
prompt_template = PromptTemplate.from_template("You are a helpful assistant. {question}")

# Create a runnable sequence (modern approach)
assistant_chain = prompt_template | llm

# Add additional route
add_routes(
    app,
    assistant_chain,
    path="/api/llm",
)