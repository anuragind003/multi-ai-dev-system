"""
Disk-Based Backup Manager for Enhanced Memory System
Provides robust persistence and recovery for server restarts
"""

import os
import json
import pickle
import gzip
import time
import threading
import hashlib
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class BackupMetadata:
    """Metadata for backup files"""
    backup_id: str
    timestamp: float
    session_id: str
    data_hash: str
    size_bytes: int
    compressed: bool
    backup_type: str  # 'full', 'incremental', 'checkpoint'
    
class DiskBackupManager:
    """
    Manages disk-based backups for the Enhanced Memory Manager
    
    Features:
    - Automatic full and incremental backups
    - Checkpoint creation before critical operations
    - Data integrity verification
    - Backup rotation and cleanup
    - Fast recovery from corruption
    """
    
    def __init__(self, backup_dir: str = "./backups", 
                 max_backups: int = 50,
                 backup_interval_seconds: int = 300,  # 5 minutes
                 enable_compression: bool = True):
        
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_backups = max_backups
        self.backup_interval = backup_interval_seconds
        self.enable_compression = enable_compression
        
        # Thread safety
        self._lock = threading.RLock()
        self._backup_thread = None
        self._should_stop = threading.Event()
        
        # Tracking
        self.last_backup_time = 0
        self.backup_count = 0
        
        # Start automatic backup thread
        self.start_backup_thread()
        
        logger.info(f"Disk Backup Manager initialized: {backup_dir}")
    
    def create_checkpoint(self, session_id: str, data: Dict[str, Any], 
                         checkpoint_type: str = "manual") -> str:
        """
        Create an immediate checkpoint backup
        
        Args:
            session_id: Session identifier
            data: Data to backup
            checkpoint_type: Type of checkpoint (manual, pre_approval, auto)
            
        Returns:
            Backup ID for the created checkpoint
        """
        with self._lock:
            timestamp = time.time()
            backup_id = f"checkpoint_{session_id}_{int(timestamp)}_{checkpoint_type}"
            
            try:
                # Serialize data
                serialized_data = self._serialize_data(data)
                
                # Create backup file
                backup_path = self.backup_dir / f"{backup_id}.backup"
                
                if self.enable_compression:
                    with gzip.open(backup_path, 'wb') as f:
                        f.write(serialized_data)
                else:
                    with open(backup_path, 'wb') as f:
                        f.write(serialized_data)
                
                # Create metadata
                data_hash = hashlib.sha256(serialized_data).hexdigest()
                metadata = BackupMetadata(
                    backup_id=backup_id,
                    timestamp=timestamp,
                    session_id=session_id,
                    data_hash=data_hash,
                    size_bytes=len(serialized_data),
                    compressed=self.enable_compression,
                    backup_type="checkpoint"
                )
                
                # Save metadata
                self._save_metadata(metadata)
                
                logger.info(f"Checkpoint created: {backup_id} ({len(serialized_data)} bytes)")
                return backup_id
                
            except Exception as e:
                logger.error(f"Failed to create checkpoint: {e}")
                raise
    
    def create_full_backup(self, session_id: str, data: Dict[str, Any]) -> str:
        """Create a full backup of all data"""
        with self._lock:
            timestamp = time.time()
            backup_id = f"full_{session_id}_{int(timestamp)}"
            
            try:
                # Serialize data
                serialized_data = self._serialize_data(data)
                
                # Create backup file
                backup_path = self.backup_dir / f"{backup_id}.backup"
                
                if self.enable_compression:
                    with gzip.open(backup_path, 'wb') as f:
                        f.write(serialized_data)
                else:
                    with open(backup_path, 'wb') as f:
                        f.write(serialized_data)
                
                # Create metadata
                data_hash = hashlib.sha256(serialized_data).hexdigest()
                metadata = BackupMetadata(
                    backup_id=backup_id,
                    timestamp=timestamp,
                    session_id=session_id,
                    data_hash=data_hash,
                    size_bytes=len(serialized_data),
                    compressed=self.enable_compression,
                    backup_type="full"
                )
                
                # Save metadata
                self._save_metadata(metadata)
                
                self.last_backup_time = timestamp
                self.backup_count += 1
                
                logger.info(f"Full backup created: {backup_id} ({len(serialized_data)} bytes)")
                return backup_id
                
            except Exception as e:
                logger.error(f"Failed to create full backup: {e}")
                raise
    
    def restore_from_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """
        Restore data from a specific backup
        
        Args:
            backup_id: ID of the backup to restore
            
        Returns:
            Restored data or None if restoration failed
        """
        with self._lock:
            try:
                backup_path = self.backup_dir / f"{backup_id}.backup"
                
                if not backup_path.exists():
                    logger.error(f"Backup file not found: {backup_path}")
                    return None
                
                # Load metadata to verify backup
                metadata = self._load_metadata(backup_id)
                if not metadata:
                    logger.warning(f"Metadata not found for backup: {backup_id}")
                
                # Load backup data
                if metadata and metadata.compressed:
                    with gzip.open(backup_path, 'rb') as f:
                        serialized_data = f.read()
                else:
                    with open(backup_path, 'rb') as f:
                        serialized_data = f.read()
                
                # Verify data integrity if metadata available
                if metadata:
                    data_hash = hashlib.sha256(serialized_data).hexdigest()
                    if data_hash != metadata.data_hash:
                        logger.error(f"Data integrity check failed for backup: {backup_id}")
                        return None
                
                # Deserialize data
                data = self._deserialize_data(serialized_data)
                
                logger.info(f"Successfully restored backup: {backup_id}")
                return data
                
            except Exception as e:
                logger.error(f"Failed to restore backup {backup_id}: {e}")
                return None
    
    def get_latest_backup(self, session_id: str = None) -> Optional[str]:
        """Get the ID of the most recent backup, optionally filtered by session"""
        try:
            backups = self.list_backups(session_id)
            if backups:
                # Sort by timestamp and return the latest
                latest = max(backups, key=lambda b: b.timestamp)
                return latest.backup_id
            return None
        except Exception as e:
            logger.error(f"Failed to get latest backup: {e}")
            return None
    
    def list_backups(self, session_id: str = None) -> List[BackupMetadata]:
        """List all available backups, optionally filtered by session"""
        backups = []
        
        try:
            for metadata_file in self.backup_dir.glob("*.metadata"):
                metadata = self._load_metadata_from_file(metadata_file)
                if metadata:
                    if session_id is None or metadata.session_id == session_id:
                        backups.append(metadata)
            
            # Sort by timestamp (newest first)
            backups.sort(key=lambda b: b.timestamp, reverse=True)
            return backups
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []
    
    def cleanup_old_backups(self):
        """Remove old backups to stay within the limit"""
        try:
            backups = self.list_backups()
            
            if len(backups) > self.max_backups:
                # Keep the newest backups, remove the oldest
                to_remove = backups[self.max_backups:]
                
                for backup in to_remove:
                    self._remove_backup(backup.backup_id)
                    
                logger.info(f"Cleaned up {len(to_remove)} old backups")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
    
    def start_backup_thread(self):
        """Start the automatic backup thread"""
        if self._backup_thread and self._backup_thread.is_alive():
            return
        
        self._should_stop.clear()
        self._backup_thread = threading.Thread(target=self._backup_worker, daemon=True)
        self._backup_thread.start()
        
        logger.info("Automatic backup thread started")
    
    def stop_backup_thread(self):
        """Stop the automatic backup thread"""
        self._should_stop.set()
        if self._backup_thread:
            self._backup_thread.join(timeout=5)
        
        logger.info("Automatic backup thread stopped")
    
    def _backup_worker(self):
        """Worker function for automatic backups"""
        while not self._should_stop.wait(self.backup_interval):
            try:
                # This would need to be integrated with the memory manager
                # For now, it's a placeholder for the automatic backup logic
                current_time = time.time()
                if current_time - self.last_backup_time > self.backup_interval:
                    logger.debug("Automatic backup interval reached")
                    # The memory manager would trigger this
                    
            except Exception as e:
                logger.error(f"Error in backup worker: {e}")
    
    def _serialize_data(self, data: Dict[str, Any]) -> bytes:
        """Serialize data for storage"""
        return pickle.dumps(data)
    
    def _deserialize_data(self, data: bytes) -> Dict[str, Any]:
        """Deserialize data from storage"""
        return pickle.loads(data)
    
    def _save_metadata(self, metadata: BackupMetadata):
        """Save backup metadata"""
        metadata_path = self.backup_dir / f"{metadata.backup_id}.metadata"
        
        with open(metadata_path, 'w') as f:
            json.dump(asdict(metadata), f, indent=2)
    
    def _load_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """Load backup metadata"""
        metadata_path = self.backup_dir / f"{backup_id}.metadata"
        return self._load_metadata_from_file(metadata_path)
    
    def _load_metadata_from_file(self, metadata_path: Path) -> Optional[BackupMetadata]:
        """Load backup metadata from file"""
        try:
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    data = json.load(f)
                return BackupMetadata(**data)
        except Exception as e:
            logger.error(f"Failed to load metadata from {metadata_path}: {e}")
        return None
    
    def _remove_backup(self, backup_id: str):
        """Remove a backup and its metadata"""
        try:
            # Remove backup file
            backup_path = self.backup_dir / f"{backup_id}.backup"
            if backup_path.exists():
                backup_path.unlink()
            
            # Remove metadata file
            metadata_path = self.backup_dir / f"{backup_id}.metadata"
            if metadata_path.exists():
                metadata_path.unlink()
                
            logger.debug(f"Removed backup: {backup_id}")
            
        except Exception as e:
            logger.error(f"Failed to remove backup {backup_id}: {e}")