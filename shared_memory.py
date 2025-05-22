import json
import os
from config import PROJECT_CONTEXT_FILE, PROJECT_OUTPUT_DIR

class SharedProjectMemory:
    def __init__(self):
        self.context = {}
        self._load_context() # Try to load existing context on init

    def _load_context(self):
        """Loads the project context from a JSON file if it exists."""
        if os.path.exists(PROJECT_CONTEXT_FILE):
            try:
                with open(PROJECT_CONTEXT_FILE, 'r') as f:
                    self.context = json.load(f)
                print(f"Loaded existing project context from {PROJECT_CONTEXT_FILE}")
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from {PROJECT_CONTEXT_FILE}. Starting with empty context.")
                self.context = {}
        else:
            print(f"No existing project context found at {PROJECT_CONTEXT_FILE}. Starting with empty context.")

    def save_context(self):
        """Saves the current project context to a JSON file."""
        os.makedirs(PROJECT_OUTPUT_DIR, exist_ok=True) # Ensure directory exists
        with open(PROJECT_CONTEXT_FILE, 'w') as f:
            json.dump(self.context, f, indent=4)
        print(f"Project context saved to {PROJECT_CONTEXT_FILE}")

    def get(self, key, default=None):
        """Retrieves a value from the context."""
        return self.context.get(key, default)

    def set(self, key, value):
        """Sets a value in the context."""
        self.context[key] = value
        # Optional: save context after every set for robustness, or only at step boundaries
        self.save_context() # For Phase 1, saving often is fine.

    def __str__(self):
        return json.dumps(self.context, indent=4)

    def __repr__(self):
        return f"SharedProjectMemory(context={self.context})"