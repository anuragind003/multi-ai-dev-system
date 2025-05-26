import os

class FileManagerTool:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir

    def read_file(self, relative_path: str) -> str:
        """Reads the content of a file within the base directory."""
        full_path = os.path.join(self.base_dir, relative_path)
        if not os.path.exists(full_path):
            return f"Error: File not found at {relative_path}"
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file {relative_path}: {e}"

    def write_file(self, relative_path: str, content: str) -> str:
        """Writes content to a file within the base directory."""
        full_path = os.path.join(self.base_dir, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"File written successfully: {relative_path}"
        except Exception as e:
            return f"Error writing file {relative_path}: {e}"