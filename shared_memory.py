import json
import os
import sqlite3
import datetime # For default timestamp if run_dir isn't provided (fallback)

class SharedProjectMemory:
    def __init__(self, run_dir: str = None):
        """
        Initializes the SharedProjectMemory with an SQLite database for the specific run.

        Args:
            run_dir (str): The directory where the SQLite database file for this run
                           will be created. If None, a default timestamped directory
                           will be used (should ideally be provided by Orchestrator).
        """
        if run_dir is None:
            # Fallback: if run_dir is not provided, create a temp one.
            # In actual workflow, main.py should always provide this.
            temp_run_dir = os.path.join("output", f"temp_run_mem_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}")
            os.makedirs(temp_run_dir, exist_ok=True)
            self.db_path = os.path.join(temp_run_dir, "run_memory.db")
            print(f"Warning: SharedProjectMemory initialized without run_dir. Using temporary: {self.db_path}")
        else:
            os.makedirs(run_dir, exist_ok=True) # Ensure the run directory exists
            self.db_path = os.path.join(run_dir, "run_memory.db")
        
        self.conn = None
        self._connect_db()
        self._init_db()

    def _connect_db(self):
        """Establishes a connection to the SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row # Allows accessing columns by name
            print(f"Connected to memory database: {self.db_path}")
        except sqlite3.Error as e:
            print(f"Error connecting to database {self.db_path}: {e}")
            self.conn = None # Ensure connection is None if failed
            raise # Re-raise to halt if DB connection fails

    def _init_db(self):
        """Initializes the database schema (creates table if not exists)."""
        if not self.conn:
            raise RuntimeError("Database connection not established.")
        
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS context (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        self.conn.commit()
        print("Memory database schema initialized.")

    def save_context(self):
        """
        This method is now a no-op as context is saved immediately on 'set'.
        Kept for interface compatibility if other parts of the code call it.
        """
        pass # Context is saved implicitly by set()

    def get(self, key, default=None):
        """Retrieves a value from the context."""
        if not self.conn:
            print(f"Warning: No database connection. Cannot retrieve key '{key}'.")
            return default
            
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM context WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row['value'])
            except json.JSONDecodeError:
                # If value is not JSON, return as plain string
                return row['value']
        return default

    def set(self, key, value):
        """Sets a value in the context. Saves immediately to DB."""
        if not self.conn:
            print(f"Warning: No database connection. Cannot set key '{key}'.")
            return

        # Convert value to JSON string for storage if it's a complex type
        if isinstance(value, (dict, list)):
            value_to_store = json.dumps(value)
        else:
            value_to_store = str(value) # Store as string for primitives

        cursor = self.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO context (key, value) VALUES (?, ?)", (key, value_to_store))
        self.conn.commit()
        # print(f"Memory updated: '{key}' saved.") # Can be verbose, uncomment for debugging

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            print(f"Memory database connection closed for {self.db_path}.")
            self.conn = None

    def __del__(self):
        """Ensure connection is closed when object is garbage collected."""
        self.close()

    def __str__(self):
        """Prints all content from the database for debugging."""
        if not self.conn:
            return "SharedProjectMemory: No active database connection."
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value FROM context")
        all_items = {}
        for row in cursor.fetchall():
            try:
                all_items[row['key']] = json.loads(row['value'])
            except json.JSONDecodeError:
                all_items[row['key']] = row['value'] # Store as string if not JSON
        return json.dumps(all_items, indent=4)

    def __repr__(self):
        return f"SharedProjectMemory(db_path='{self.db_path}', connected={self.conn is not None})"