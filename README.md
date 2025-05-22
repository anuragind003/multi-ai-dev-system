# Multi-AI Agentic System for Automated Software Development

This project creates a pipeline of specialized AI agents that automate software development from requirements to implementation.

## System Overview

The system processes Business Requirements Documents (BRDs) through multiple specialized agents:

1. **BRD Analyst Agent**: Analyzes and extracts structured requirements from BRD documents
2. **Tech Stack Advisor Agent**: Recommends appropriate technology stack based on requirements
3. **System Designer Agent**: Creates a detailed system design with architecture, API endpoints and database schema
4. **Code Generator Agent**: Implements the designed system as actual code (coming soon)

## Setup Instructions

1. **Clone the repository:**

   ```bash
   git clone https://github.com/anuragind003/multi-ai-dev-system.git
   cd multi-ai-dev-system
   ```

2. **Create a virtual environment (recommended):**

   ```bash
   python -m venv venv
   source venv/bin/activate # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt # (We'll create this later, for now `pip install google-generativeai python-dotenv`)
   ```

4. **Set up Gemini API Key:**
   - Obtain your Gemini API key from the Google AI Studio: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
   - Create a file named `.env` in the root directory of the project (next to `main.py`).
   - Add your API key to this file:
     ```
     GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
     ```
   - **IMPORTANT:** Do NOT commit your `.env` file to version control! It's already ignored by the default `.gitignore` if you initialized your repo with Python templates.

## Running the System (Phase 1)

`python main.py`

_(Further instructions will be added as features are built.)_
