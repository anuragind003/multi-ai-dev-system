import os
from dotenv import load_dotenv
import google.generativeai as genai
import pathlib
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

# Load environment variables from .env file
load_dotenv()

# --- Gemini API Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in a .env file.")

# Configure the Gemini API client
genai.configure(api_key=GEMINI_API_KEY)

# Define the Gemini model to use
# 'gemini-pro' is good for text generation, 'gemini-pro-vision' for multimodal
# For code generation, 'gemini-pro' or newer models are usually preferred.
GEMINI_MODEL_NAME = "gemini-2.5-flash-preview-05-20"
# GEMINI_MODEL_NAME = "gemini-1.5-pro" # If you have access and want more advanced capabilities

def get_gemini_model():
    """Initializes and returns the configured Gemini GenerativeModel."""
    return genai.GenerativeModel(GEMINI_MODEL_NAME)



# Define the Gemini embedding model
GEMINI_EMBEDDING_MODEL = "models/embedding-001" # Or 'text-embedding-004' depending on access

def get_gemini_embedding_model():
    """Initializes and returns the configured Gemini Embedding Model."""
    # Using LangChain's GoogleGenerativeAIEmbeddings for compatibility with LangChain's vectorstore integrations
    return GoogleGenerativeAIEmbeddings(model=GEMINI_EMBEDDING_MODEL, google_api_key=GEMINI_API_KEY)

# --- Other Configurations (can add more later) ---
BASE_DIR = pathlib.Path(__file__).parent
INPUT_DIR = os.path.join(BASE_DIR, "brds")
PROJECT_BRDS_DIR = INPUT_DIR  # Add this line - alias for INPUT_DIR for backward compatibility
PROJECT_OUTPUT_DIR = os.path.join(BASE_DIR, "output")


# Ensure output directory exists
try:
    if not os.path.exists(PROJECT_OUTPUT_DIR):
        os.makedirs(PROJECT_OUTPUT_DIR)
except Exception as e:
    print(f"Warning: Could not create output directory: {e}")
    # Continue execution even if directory creation fails
    pass