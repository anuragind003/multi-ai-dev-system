#!/usr/bin/env python3
"""
Memory Cleanup System for Multi-AI Development System

This module provides intelligent memory cleanup and management:
- Automatic cleanup of old run directories
- Memory cache optimization
- Database maintenance and compression
- Smart retention policies
- Performance monitoring
"""

import os
import sys
import time
import json
import sqlite3
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import threading

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


@dataclass
class CleanupStats:
    """Statistics for cleanup operations."""
    files_removed: int = 0
    directories_removed: int = 0
    space_freed_mb: float = 0.0
    databases_optimized: int = 0
    cache_entries_cleaned: int = 0
    cleanup_duration_sec: float = 0.0
    
    def add_file(self, size_bytes: int):
        """Add a cleaned file to stats."""
        self.files_removed += 1
        self.space_freed_mb += size_bytes / (1024 * 1024)
    
    def add_directory(self, size_bytes: int):
        """Add a cleaned directory to stats."""
        self.directories_removed += 1
        self.space_freed_mb += size_bytes / (1024 * 1024)


@dataclass
class RetentionPolicy:
    """Defines retention policies for different data types."""
    run_directories_days: int = 7
    log_files_days: int = 14
    cache_files_days: int = 3
    temp_files_days: int = 1
    memory_db_days: int = 7
    checkpoint_db_days: int = 3
    
    def should_cleanup(self, file_path: Path, data_type: str) -> bool:
        """Check if a file should be cleaned up based on policy."""
        if not file_path.exists():
            return False
        
        file_age_days = (time.time() - file_path.stat().st_mtime) / (24 * 3600)
        
        policy_map = {
            'run_directory': self.run_directories_days,
            'log_file': self.log_files_days,
            'cache_file': self.cache_files_days,
            'temp_file': self.temp_files_days,
            'memory_db': self.memory_db_days,
            'checkpoint_db': self.checkpoint_db_days
        }
        
        max_age = policy_map.get(data_type, self.temp_files_days)
        return file_age_days > max_age


class MemoryCleanupSystem:
    """Intelligent memory cleanup system for the multi-AI development system."""
    
    def __init__(self, 
                 project_root: str = None,
                 retention_policy: RetentionPolicy = None,
                 enable_compression: bool = True,
                 dry_run: bool = False):
        """
        Initialize the memory cleanup system.
        
        Args:
            project_root: Root directory of the project
            retention_policy: Custom retention policy
            enable_compression: Enable database compression
            dry_run: Only report what would be cleaned, don't actually clean
        """
        self.project_root = Path(project_root or PROJECT_ROOT)
        self.retention_policy = retention_policy or RetentionPolicy()
        self.enable_compression = enable_compression
        self.dry_run = dry_run
        
        # Thread pool for parallel operations
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        # Statistics tracking
        self.stats = CleanupStats()
        
        logger.info(f"Memory Cleanup System initialized for {self.project_root}")
        if self.dry_run:
            logger.info("🔍 DRY RUN MODE: No files will be actually deleted")
    
    def cleanup_all(self) -> CleanupStats:
        """Run comprehensive cleanup of all memory-related components."""
        logger.info("🧹 Starting comprehensive memory cleanup...")
        start_time = time.time()
        
        cleanup_tasks = [
            ("run_directories", self._cleanup_run_directories),
            ("memory_databases", self._cleanup_memory_databases),
            ("cache_files", self._cleanup_cache_files),
            ("log_files", self._cleanup_log_files),
            ("temp_files", self._cleanup_temp_files)
        ]
        
        # Run cleanup tasks
        for task_name, task_func in cleanup_tasks:
            try:
                logger.info(f"🔄 Running {task_name} cleanup...")
                task_func()
                logger.info(f"✅ {task_name} cleanup completed")
            except Exception as e:
                logger.error(f"❌ {task_name} cleanup failed: {e}")
        
        # Optimize remaining databases
        if self.enable_compression:
            self._optimize_databases()
        
        self.stats.cleanup_duration_sec = time.time() - start_time
        
        # Log cleanup summary
        self._log_cleanup_summary()
        
        return self.stats
    
    def _cleanup_run_directories(self):
        """Clean up old workflow run directories."""
        output_dir = self.project_root / "output"
        if not output_dir.exists():
            return
        
        logger.info(f"🗂️  Cleaning run directories older than {self.retention_policy.run_directories_days} days...")
        
        for run_dir in output_dir.glob("run_*"):
            if not run_dir.is_dir():
                continue
            
            try:
                # Parse timestamp from directory name
                timestamp_str = run_dir.name.replace("run_", "")
                run_timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                
                if self.retention_policy.should_cleanup(run_dir, 'run_directory'):
                    # Calculate directory size before removal
                    dir_size = self._get_directory_size(run_dir)
                    
                    if self.dry_run:
                        logger.info(f"Would remove: {run_dir.name} ({dir_size:.1f}MB)")
                        self.stats.add_directory(int(dir_size * 1024 * 1024))
                    else:
                        shutil.rmtree(run_dir)
                        self.stats.add_directory(int(dir_size * 1024 * 1024))
                        logger.debug(f"Removed run directory: {run_dir.name} ({dir_size:.1f}MB)")
                        
            except (ValueError, OSError) as e:
                logger.debug(f"Could not process run directory {run_dir}: {e}")
    
    def _cleanup_memory_databases(self):
        """Clean up old memory database files."""
        logger.info("🗄️ Cleaning old memory database files...")
        
        # Find memory.db and checkpoints.db files
        db_patterns = ["memory.db", "checkpoints.db"]
        
        for pattern in db_patterns:
            for db_file in self.project_root.rglob(pattern):
                try:
                    data_type = 'checkpoint_db' if 'checkpoint' in pattern else 'memory_db'
                    
                    if self.retention_policy.should_cleanup(db_file, data_type):
                        file_size = db_file.stat().st_size
                        
                        if self.dry_run:
                            logger.info(f"Would remove: {db_file} ({file_size / (1024*1024):.1f}MB)")
                            self.stats.add_file(file_size)
                        else:
                            db_file.unlink()
                            self.stats.add_file(file_size)
                            logger.debug(f"Removed database: {db_file}")
                            
                except (OSError, PermissionError) as e:
                    logger.debug(f"Could not process database {db_file}: {e}")
    
    def _cleanup_cache_files(self):
        """Clean up cache files and directories."""
        logger.info("💾 Cleaning cache files...")
        
        cache_dirs = [
            self.project_root / "cache",
            self.project_root / ".cache",
            self.project_root / "__pycache__",
            self.project_root / ".rag_store" / ".embedding_cache"
        ]
        
        for cache_dir in cache_dirs:
            if not cache_dir.exists():
                continue
            
            try:
                if cache_dir.name == "__pycache__":
                    # Remove entire __pycache__ directories
                    for pycache in self.project_root.rglob("__pycache__"):
                        dir_size = self._get_directory_size(pycache)
                        
                        if self.dry_run:
                            logger.info(f"Would remove: {pycache} ({dir_size:.1f}MB)")
                            self.stats.add_directory(int(dir_size * 1024 * 1024))
                        else:
                            shutil.rmtree(pycache)
                            self.stats.add_directory(int(dir_size * 1024 * 1024))
                else:
                    # Clean old files from cache directories
                    self._cleanup_directory_by_age(cache_dir, 'cache_file')
                    
            except (OSError, PermissionError) as e:
                logger.debug(f"Could not process cache directory {cache_dir}: {e}")
    
    def _cleanup_log_files(self):
        """Clean up old log files."""
        logger.info("📋 Cleaning old log files...")
        
        log_dirs = [
            self.project_root / "logs",
            self.project_root / "multi_ai_dev_system" / "logs"
        ]
        
        for log_dir in log_dirs:
            if log_dir.exists():
                self._cleanup_directory_by_age(log_dir, 'log_file')
    
    def _cleanup_temp_files(self):
        """Clean up temporary files."""
        logger.info("🗑️  Cleaning temporary files...")
        
        # Common temporary file patterns
        temp_patterns = [
            "*.tmp", "*.temp", "*.bak", "*.backup",
            "*.swp", "*.swo", "*~", ".DS_Store", "Thumbs.db"
        ]
        
        for pattern in temp_patterns:
            for temp_file in self.project_root.rglob(pattern):
                try:
                    if self.retention_policy.should_cleanup(temp_file, 'temp_file'):
                        file_size = temp_file.stat().st_size
                        
                        if self.dry_run:
                            logger.info(f"Would remove: {temp_file} ({file_size / 1024:.1f}KB)")
                            self.stats.add_file(file_size)
                        else:
                            temp_file.unlink()
                            self.stats.add_file(file_size)
                            logger.debug(f"Removed temp file: {temp_file}")
                            
                except (OSError, PermissionError) as e:
                    logger.debug(f"Could not process temp file {temp_file}: {e}")
    
    def _cleanup_directory_by_age(self, directory: Path, data_type: str):
        """Clean files in a directory based on age policy."""
        if not directory.exists() or not directory.is_dir():
            return
        
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                try:
                    if self.retention_policy.should_cleanup(file_path, data_type):
                        file_size = file_path.stat().st_size
                        
                        if self.dry_run:
                            logger.debug(f"Would remove: {file_path} ({file_size / 1024:.1f}KB)")
                            self.stats.add_file(file_size)
                        else:
                            file_path.unlink()
                            self.stats.add_file(file_size)
                            logger.debug(f"Removed old file: {file_path}")
                            
                except (OSError, PermissionError) as e:
                    logger.debug(f"Could not process file {file_path}: {e}")
    
    def _optimize_databases(self):
        """Optimize remaining database files."""
        logger.info("⚡ Optimizing remaining database files...")
        
        # Find all SQLite database files
        db_patterns = ["*.db", "*.sqlite", "*.sqlite3"]
        
        for pattern in db_patterns:
            for db_file in self.project_root.rglob(pattern):
                if db_file.exists():
                    try:
                        if self.dry_run:
                            logger.info(f"Would optimize: {db_file}")
                            self.stats.databases_optimized += 1
                        else:
                            # Run VACUUM to optimize database
                            with sqlite3.connect(str(db_file)) as conn:
                                conn.execute("VACUUM")
                                conn.commit()
                            
                            self.stats.databases_optimized += 1
                            logger.debug(f"Optimized database: {db_file}")
                            
                    except Exception as e:
                        logger.debug(f"Could not optimize database {db_file}: {e}")
    
    def _get_directory_size(self, directory: Path) -> float:
        """Get directory size in MB."""
        if not directory.exists() or not directory.is_dir():
            return 0.0
        
        total_size = 0
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except (OSError, PermissionError):
            pass
        
        return total_size / (1024 * 1024)
    
    def _log_cleanup_summary(self):
        """Log comprehensive cleanup summary."""
        logger.info("🎯 Memory Cleanup Summary")
        logger.info("=" * 40)
        logger.info(f"⏱️  Duration: {self.stats.cleanup_duration_sec:.1f}s")
        logger.info(f"🗂️  Files removed: {self.stats.files_removed}")
        logger.info(f"📁 Directories removed: {self.stats.directories_removed}")
        logger.info(f"💾 Space freed: {self.stats.space_freed_mb:.1f}MB")
        logger.info(f"🗄️  Databases optimized: {self.stats.databases_optimized}")
        
        if self.dry_run:
            logger.info("⚠️  DRY RUN: No files were actually deleted")
        
        logger.info("=" * 40)
    
    def get_size_analysis(self) -> Dict[str, Any]:
        """Get detailed size analysis of the project."""
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "total_size_mb": 0.0,
            "breakdown": {}
        }
        
        # Analyze major directories
        major_dirs = [
            ("output", self.project_root / "output"),
            ("logs", self.project_root / "logs"), 
            ("cache", self.project_root / "cache"),
            (".cache", self.project_root / ".cache"),
            (".rag_store", self.project_root / ".rag_store"),
            ("__pycache__", None)  # Special handling for all __pycache__ dirs
        ]
        
        for name, path in major_dirs:
            if name == "__pycache__":
                # Sum all __pycache__ directories
                size = sum(self._get_directory_size(p) for p in self.project_root.rglob("__pycache__"))
            elif path and path.exists():
                size = self._get_directory_size(path)
            else:
                size = 0.0
            
            analysis["breakdown"][name] = {
                "size_mb": size,
                "exists": path.exists() if path else len(list(self.project_root.rglob("__pycache__"))) > 0
            }
            analysis["total_size_mb"] += size
        
        # Analyze database files
        db_count = 0
        db_size = 0.0
        for pattern in ["*.db", "*.sqlite", "*.sqlite3"]:
            for db_file in self.project_root.rglob(pattern):
                if db_file.exists():
                    db_count += 1
                    db_size += db_file.stat().st_size / (1024 * 1024)
        
        analysis["databases"] = {
            "count": db_count,
            "total_size_mb": db_size
        }
        
        # Analyze run directories
        output_dir = self.project_root / "output"
        run_dirs = []
        if output_dir.exists():
            for run_dir in output_dir.glob("run_*"):
                if run_dir.is_dir():
                    try:
                        timestamp_str = run_dir.name.replace("run_", "")
                        run_timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                        size = self._get_directory_size(run_dir)
                        age_days = (datetime.now() - run_timestamp).days
                        
                        run_dirs.append({
                            "name": run_dir.name,
                            "size_mb": size,
                            "age_days": age_days,
                            "should_cleanup": age_days > self.retention_policy.run_directories_days
                        })
                    except ValueError:
                        pass
        
        analysis["run_directories"] = sorted(run_dirs, key=lambda x: x["age_days"], reverse=True)
        
        return analysis
    
    def schedule_cleanup(self, interval_hours: int = 24):
        """Schedule automatic cleanup to run periodically."""
        def cleanup_scheduler():
            while True:
                try:
                    time.sleep(interval_hours * 3600)
                    logger.info(f"Running scheduled cleanup (every {interval_hours}h)")
                    self.cleanup_all()
                except Exception as e:
                    logger.error(f"Scheduled cleanup failed: {e}")
        
        scheduler_thread = threading.Thread(target=cleanup_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info(f"Scheduled cleanup every {interval_hours} hours")


def main():
    """Run memory cleanup from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Memory Cleanup System")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be cleaned without actually cleaning")
    parser.add_argument("--runs-days", type=int, default=7, help="Days to keep run directories")
    parser.add_argument("--logs-days", type=int, default=14, help="Days to keep log files")
    parser.add_argument("--cache-days", type=int, default=3, help="Days to keep cache files")
    parser.add_argument("--no-compression", action="store_true", help="Disable database compression")
    parser.add_argument("--analysis", action="store_true", help="Show size analysis only")
    parser.add_argument("--schedule", type=int, help="Schedule cleanup every N hours")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create retention policy
    retention_policy = RetentionPolicy(
        run_directories_days=args.runs_days,
        log_files_days=args.logs_days,
        cache_files_days=args.cache_days
    )
    
    cleanup_system = MemoryCleanupSystem(
        project_root=args.project_root,
        retention_policy=retention_policy,
        enable_compression=not args.no_compression,
        dry_run=args.dry_run
    )
    
    if args.analysis:
        # Show size analysis
        analysis = cleanup_system.get_size_analysis()
        print(json.dumps(analysis, indent=2))
        return
    
    # Run cleanup
    stats = cleanup_system.cleanup_all()
    
    if args.schedule:
        cleanup_system.schedule_cleanup(args.schedule)
        print(f"Cleanup scheduled every {args.schedule} hours. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\nScheduled cleanup stopped.")
    
    print(f"\nCleanup completed: {stats.space_freed_mb:.1f}MB freed in {stats.cleanup_duration_sec:.1f}s")


if __name__ == "__main__":
    main() 