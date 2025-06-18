"""
Checkpoint Manager for resumable workflows.
Enables saving and loading workflow state at critical points.
"""

import json
import os
import sqlite3
import time
from typing import Dict, Any, Optional, List
import uuid
import logging
from pathlib import Path


class CheckpointManager:
    """
    Manages checkpoints for workflow state persistence.
    Enables workflows to be paused and resumed from various points.
    """
    
    def __init__(self, output_dir: str):
        """
        Initialize the checkpoint manager with an output directory.
        
        Args:
            output_dir: Directory where checkpoint database will be stored
        """
        self.output_dir = output_dir
        self.checkpoint_db = os.path.join(output_dir, "checkpoints.db")
        self.logger = logging.getLogger(__name__)
        self._init_db()
        
    def _init_db(self) -> None:
        """Initialize the checkpoint database with required tables"""
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            
            with sqlite3.connect(self.checkpoint_db) as conn:
                cursor = conn.cursor()
                
                # Create checkpoints table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
                """)
                
                # Create checkpoint_tags table for easier lookup
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS checkpoint_tags (
                    checkpoint_id TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    PRIMARY KEY (checkpoint_id, tag),
                    FOREIGN KEY (checkpoint_id) REFERENCES checkpoints(id) ON DELETE CASCADE
                )
                """)
                
                # Create index for faster lookups
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflow_id ON checkpoints(workflow_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_phase ON checkpoints(phase)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags ON checkpoint_tags(tag)")
                
                conn.commit()
                self.logger.debug(f"Checkpoint database initialized at {self.checkpoint_db}")
        except Exception as e:
            self.logger.error(f"Error initializing checkpoint database: {e}")
            raise
    
    def save_checkpoint(self, 
                       workflow_id: str, 
                       phase: str, 
                       state: Dict[str, Any], 
                       metadata: Optional[Dict[str, Any]] = None,
                       tags: Optional[List[str]] = None) -> str:
        """
        Save workflow state as a checkpoint.
        
        Args:
            workflow_id: Identifier for the workflow
            phase: Current phase name
            state: The workflow state to save
            metadata: Optional metadata about the checkpoint
            tags: Optional tags for categorizing checkpoints
            
        Returns:
            checkpoint_id: Unique ID of the saved checkpoint
        """
        checkpoint_id = str(uuid.uuid4())
        
        try:
            # Make a deep copy of state to avoid reference issues
            state_copy = json.loads(json.dumps(state))
            
            # Create a checkpoint record
            with sqlite3.connect(self.checkpoint_db) as conn:
                conn.execute(
                    """
                    INSERT INTO checkpoints (id, workflow_id, phase, state, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (
                        checkpoint_id,
                        workflow_id,
                        phase,
                        json.dumps(state_copy),
                        json.dumps(metadata or {})
                    )
                )
                
                # Add tags if provided
                if tags:
                    for tag in tags:
                        conn.execute(
                            """
                            INSERT INTO checkpoint_tags (checkpoint_id, tag)
                            VALUES (?, ?)
                            """,
                            (checkpoint_id, tag)
                        )
                
                conn.commit()
                self.logger.info(f"Checkpoint {checkpoint_id} saved for workflow {workflow_id} at phase {phase}")
                
            return checkpoint_id
        except Exception as e:
            self.logger.error(f"Error saving checkpoint: {e}")
            return None
    
    def load_checkpoint(self, 
                       checkpoint_id: str = None, 
                       workflow_id: str = None, 
                       phase: str = None,
                       tag: str = None) -> Optional[Dict[str, Any]]:
        """
        Load workflow state from a checkpoint.
        
        Args:
            checkpoint_id: Specific checkpoint ID to load
            workflow_id: Filter by workflow ID
            phase: Filter by phase name
            tag: Filter by tag
            
        Returns:
            The workflow state dictionary or None if not found
        """
        try:
            query = """
                SELECT c.state
                FROM checkpoints c
                """
                
            params = []
            where_clauses = []
            
            # Add checkpoint_tags join if tag is provided
            if tag:
                query += """
                    JOIN checkpoint_tags ct ON c.id = ct.checkpoint_id
                    """
                where_clauses.append("ct.tag = ?")
                params.append(tag)
            
            # Add other filters
            if checkpoint_id:
                where_clauses.append("c.id = ?")
                params.append(checkpoint_id)
            
            if workflow_id:
                where_clauses.append("c.workflow_id = ?")
                params.append(workflow_id)
                
            if phase:
                where_clauses.append("c.phase = ?")
                params.append(phase)
                
            # Add WHERE clause if we have conditions
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
                
            # Add ordering and limit
            query += " ORDER BY c.created_at DESC LIMIT 1"
            
            with sqlite3.connect(self.checkpoint_db) as conn:
                cursor = conn.execute(query, params)
                result = cursor.fetchone()
                
            if result:
                self.logger.info(f"Checkpoint loaded successfully")
                return json.loads(result[0])
            else:
                self.logger.warning(f"No checkpoint found matching criteria")
                return None
        except Exception as e:
            self.logger.error(f"Error loading checkpoint: {e}")
            return None
    
    def list_checkpoints(self, 
                        workflow_id: str = None,
                        phase: str = None,
                        tag: str = None,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """
        List available checkpoints.
        
        Args:
            workflow_id: Filter by workflow ID
            phase: Filter by phase name
            tag: Filter by tag
            limit: Maximum number of checkpoints to return
            
        Returns:
            List of checkpoint metadata dictionaries
        """
        try:
            query = """
                SELECT DISTINCT c.id, c.workflow_id, c.phase, c.created_at, c.metadata
                FROM checkpoints c
                """
                
            params = []
            where_clauses = []
            
            # Add checkpoint_tags join if tag is provided
            if tag:
                query += """
                    JOIN checkpoint_tags ct ON c.id = ct.checkpoint_id
                    """
                where_clauses.append("ct.tag = ?")
                params.append(tag)
            
            # Add other filters
            if workflow_id:
                where_clauses.append("c.workflow_id = ?")
                params.append(workflow_id)
                
            if phase:
                where_clauses.append("c.phase = ?")
                params.append(phase)
                
            # Add WHERE clause if we have conditions
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
                
            # Add ordering and limit
            query += f" ORDER BY c.created_at DESC LIMIT {limit}"
            
            with sqlite3.connect(self.checkpoint_db) as conn:
                cursor = conn.execute(query, params)
                results = cursor.fetchall()
                
            # Format results
            checkpoints = []
            for row in results:
                checkpoint_id, workflow_id, phase, created_at, metadata_json = row
                
                # Get tags for this checkpoint
                with sqlite3.connect(self.checkpoint_db) as conn:
                    tags_cursor = conn.execute(
                        "SELECT tag FROM checkpoint_tags WHERE checkpoint_id = ?", 
                        (checkpoint_id,)
                    )
                    tags = [tag[0] for tag in tags_cursor.fetchall()]
                
                checkpoints.append({
                    "id": checkpoint_id,
                    "workflow_id": workflow_id,
                    "phase": phase,
                    "created_at": created_at,
                    "tags": tags,
                    "metadata": json.loads(metadata_json) if metadata_json else {}
                })
                
            return checkpoints
        except Exception as e:
            self.logger.error(f"Error listing checkpoints: {e}")
            return []