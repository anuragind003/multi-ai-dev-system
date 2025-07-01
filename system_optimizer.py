#!/usr/bin/env python3
"""
Comprehensive System Optimizer for Multi-AI Development System

This module provides centralized optimization across all system components:
- Memory management and cleanup
- RAG index optimization  
- Cache performance tuning
- API call optimization
- Database cleanup and maintenance
- Performance monitoring and analytics
"""

import os
import sys
import time
import json
import logging
import sqlite3
import threading
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import gc

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enhanced_memory_manager import EnhancedMemoryManager, create_memory_manager
from rag_manager import ProjectRAGManager, get_rag_manager
from monitoring import log_agent_activity
from advanced_rate_limiting.optimization_strategies import OptimizationStrategies

logger = logging.getLogger(__name__)


@dataclass
class SystemOptimizationMetrics:
    """Comprehensive system optimization metrics."""
    
    # Memory optimization
    memory_cleaned_mb: float = 0.0
    memory_hit_ratio: float = 0.0
    memory_operations_per_sec: float = 0.0
    
    # Storage optimization  
    files_cleaned: int = 0
    storage_freed_mb: float = 0.0
    old_runs_cleaned: int = 0
    
    # RAG optimization
    rag_index_size_mb: float = 0.0
    rag_documents_indexed: int = 0
    rag_queries_cached: int = 0
    
    # API optimization
    api_cache_hits: int = 0
    api_calls_batched: int = 0
    api_tokens_saved: int = 0
    
    # Database optimization
    db_size_before_mb: float = 0.0
    db_size_after_mb: float = 0.0
    db_vacuum_time_sec: float = 0.0
    
    # Overall performance
    optimization_start_time: float = 0.0
    optimization_duration_sec: float = 0.0
    system_health_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return asdict(self)


class SystemOptimizer:
    """Comprehensive system optimizer for the multi-AI development system."""
    
    def __init__(self, 
                 project_root: str = None,
                 auto_cleanup: bool = True,
                 preserve_days: int = 7,
                 enable_aggressive_optimization: bool = False):
        """
        Initialize the system optimizer.
        
        Args:
            project_root: Root directory of the project
            auto_cleanup: Enable automatic cleanup of old files
            preserve_days: Number of days to preserve data
            enable_aggressive_optimization: Enable more aggressive optimization strategies
        """
        self.project_root = Path(project_root or PROJECT_ROOT)
        self.auto_cleanup = auto_cleanup
        self.preserve_days = preserve_days
        self.enable_aggressive_optimization = enable_aggressive_optimization
        
        # Initialize metrics
        self.metrics = SystemOptimizationMetrics()
        self.metrics.optimization_start_time = time.time()
        
        # Thread pool for parallel operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Initialize optimization strategies
        self.api_optimizer = OptimizationStrategies(
            cache_size_mb=200,  # Increased cache size
            cache_entries=2000
        )
        
        logger.info(f"System Optimizer initialized for {self.project_root}")
    
    def optimize_system(self, 
                       optimize_memory: bool = True,
                       optimize_storage: bool = True, 
                       optimize_rag: bool = True,
                       optimize_api: bool = True,
                       optimize_database: bool = True) -> SystemOptimizationMetrics:
        """
        Run comprehensive system optimization.
        
        Args:
            optimize_memory: Enable memory optimization
            optimize_storage: Enable storage cleanup
            optimize_rag: Enable RAG index optimization
            optimize_api: Enable API call optimization
            optimize_database: Enable database optimization
            
        Returns:
            Optimization metrics and results
        """
        logger.info("🚀 Starting comprehensive system optimization...")
        
        optimization_tasks = []
        
        if optimize_memory:
            optimization_tasks.append(("memory", self._optimize_memory))
        if optimize_storage:
            optimization_tasks.append(("storage", self._optimize_storage))
        if optimize_rag:
            optimization_tasks.append(("rag", self._optimize_rag))
        if optimize_api:
            optimization_tasks.append(("api", self._optimize_api))
        if optimize_database:
            optimization_tasks.append(("database", self._optimize_database))
        
        # Run optimizations in parallel
        futures = {}
        for task_name, task_func in optimization_tasks:
            future = self.executor.submit(task_func)
            futures[future] = task_name
        
        # Wait for completion and collect results
        completed_tasks = []
        for future in as_completed(futures):
            task_name = futures[future]
            try:
                result = future.result()
                completed_tasks.append((task_name, result))
                logger.info(f"✅ {task_name.capitalize()} optimization completed")
            except Exception as e:
                logger.error(f"❌ {task_name.capitalize()} optimization failed: {e}")
        
        # Calculate final metrics
        self.metrics.optimization_duration_sec = time.time() - self.metrics.optimization_start_time
        self.metrics.system_health_score = self._calculate_health_score()
        
        # Log optimization summary
        self._log_optimization_summary()
        
        return self.metrics
    
    def _optimize_memory(self) -> Dict[str, Any]:
        """Optimize memory management and caching."""
        logger.info("Optimizing memory management...")
        
        try:
            # Get enhanced memory manager
            memory_manager = create_memory_manager()
            
            if memory_manager:
                # Get current stats
                stats_before = memory_manager.get_stats()
                
                # Run optimization
                memory_manager.optimize()
                
                # Force garbage collection
                gc.collect()
                
                # Get stats after optimization
                stats_after = memory_manager.get_stats()
                
                # Update metrics
                self.metrics.memory_hit_ratio = stats_after.hit_ratio
                self.metrics.memory_operations_per_sec = stats_after.operations_per_second
                self.metrics.memory_cleaned_mb = max(0, stats_before.memory_usage_mb - stats_after.memory_usage_mb)
                
                logger.info(f"Memory optimization: {self.metrics.memory_cleaned_mb:.1f}MB freed, "
                           f"{self.metrics.memory_hit_ratio:.1%} hit ratio")
                
                return {
                    "status": "success",
                    "memory_freed_mb": self.metrics.memory_cleaned_mb,
                    "hit_ratio": self.metrics.memory_hit_ratio
                }
            else:
                logger.warning("Memory manager not available for optimization")
                return {"status": "skipped", "reason": "memory_manager_unavailable"}
                
        except Exception as e:
            logger.error(f"Memory optimization failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def _optimize_storage(self) -> Dict[str, Any]:
        """Optimize storage by cleaning up old files and runs."""
        logger.info("💾 Optimizing storage and cleaning up old files...")
        
        try:
            total_freed = 0.0
            files_cleaned = 0
            runs_cleaned = 0
            
            # Clean up old run directories
            output_dir = self.project_root / "output"
            if output_dir.exists():
                cutoff_date = datetime.now() - timedelta(days=self.preserve_days)
                
                for run_dir in output_dir.glob("run_*"):
                    if run_dir.is_dir():
                        try:
                            # Parse run timestamp from directory name
                            run_timestamp_str = run_dir.name.replace("run_", "")
                            run_timestamp = datetime.strptime(run_timestamp_str, "%Y%m%d_%H%M%S")
                            
                            if run_timestamp < cutoff_date:
                                # Calculate size before deletion
                                dir_size = self._get_directory_size(run_dir)
                                
                                # Remove old run directory
                                shutil.rmtree(run_dir)
                                
                                total_freed += dir_size
                                runs_cleaned += 1
                                files_cleaned += 1
                                
                                logger.debug(f"Cleaned old run: {run_dir.name} ({dir_size:.1f}MB)")
                                
                        except (ValueError, OSError) as e:
                            logger.debug(f"Could not process run directory {run_dir}: {e}")
            
            # Clean up cache directories
            cache_dirs = [
                self.project_root / "cache",
                self.project_root / ".cache", 
                self.project_root / "__pycache__"
            ]
            
            for cache_dir in cache_dirs:
                if cache_dir.exists():
                    cache_size = self._get_directory_size(cache_dir)
                    
                    if self.enable_aggressive_optimization:
                        # Clean entire cache
                        shutil.rmtree(cache_dir)
                        total_freed += cache_size
                        files_cleaned += 1
                        logger.debug(f"Cleaned cache directory: {cache_dir.name} ({cache_size:.1f}MB)")
                    else:
                        # Clean only old cache files
                        cleaned_size = self._clean_old_files(cache_dir, days=self.preserve_days)
                        total_freed += cleaned_size
                        if cleaned_size > 0:
                            files_cleaned += 1
            
            # Clean up log files
            logs_dir = self.project_root / "logs"
            if logs_dir.exists():
                cleaned_size = self._clean_old_files(logs_dir, days=self.preserve_days * 2)  # Keep logs longer
                total_freed += cleaned_size
                if cleaned_size > 0:
                    files_cleaned += 1
            
            # Update metrics
            self.metrics.files_cleaned = files_cleaned
            self.metrics.storage_freed_mb = total_freed
            self.metrics.old_runs_cleaned = runs_cleaned
            
            logger.info(f"Storage optimization: {total_freed:.1f}MB freed, "
                       f"{files_cleaned} files/directories cleaned")
            
            return {
                "status": "success",
                "storage_freed_mb": total_freed,
                "files_cleaned": files_cleaned,
                "runs_cleaned": runs_cleaned
            }
            
        except Exception as e:
            logger.error(f"Storage optimization failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def _optimize_rag(self) -> Dict[str, Any]:
        """Optimize RAG index and vector store."""
        logger.info("📚 Optimizing RAG index and vector store...")
        
        try:
            rag_manager = get_rag_manager()
            
            if not rag_manager:
                logger.warning("RAG manager not available for optimization")
                return {"status": "skipped", "reason": "rag_manager_unavailable"}
            
            # Get RAG store info
            rag_store_path = self.project_root / ".rag_store"
            initial_size = self._get_directory_size(rag_store_path) if rag_store_path.exists() else 0
            
            # Optimize vector store if available
            if hasattr(rag_manager, 'vector_store') and rag_manager.vector_store:
                # Enable embedding cache for better performance
                if hasattr(rag_manager, 'enable_embedding_cache'):
                    rag_manager.enable_embedding_cache()
                
                # Save optimized vector store
                rag_manager._save_vector_store()
            
            # Get optimization results
            final_size = self._get_directory_size(rag_store_path) if rag_store_path.exists() else 0
            
            # Update metrics
            self.metrics.rag_index_size_mb = final_size
            
            # Get document count from metadata
            metadata_file = rag_store_path / "metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    self.metrics.rag_documents_indexed = len(metadata)
                except Exception as e:
                    logger.debug(f"Could not read RAG metadata: {e}")
            
            logger.info(f"RAG optimization: {final_size:.1f}MB index size, "
                       f"{self.metrics.rag_documents_indexed} documents indexed")
            
            return {
                "status": "success",
                "index_size_mb": final_size,
                "documents_indexed": self.metrics.rag_documents_indexed
            }
            
        except Exception as e:
            logger.error(f"RAG optimization failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def _optimize_api(self) -> Dict[str, Any]:
        """Optimize API calls and caching."""
        logger.info("🌐 Optimizing API calls and caching...")
        
        try:
            # Get cache statistics from API optimizer
            cache_stats = self.api_optimizer.cache.get_stats()
            
            # Update metrics
            self.metrics.api_cache_hits = cache_stats.get('hits', 0)
            
            # Clean up expired cache entries
            if hasattr(self.api_optimizer, 'cache'):
                # Force cache optimization
                if hasattr(self.api_optimizer.cache, 'optimize'):
                    self.api_optimizer.cache.optimize()
            
            logger.info(f"API optimization: {self.metrics.api_cache_hits} cache hits, "
                       f"{cache_stats.get('hit_rate', 0):.1f}% hit rate")
            
            return {
                "status": "success",
                "cache_hits": self.metrics.api_cache_hits,
                "hit_rate": cache_stats.get('hit_rate', 0)
            }
            
        except Exception as e:
            logger.error(f"API optimization failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def _optimize_database(self) -> Dict[str, Any]:
        """Optimize database files and cleanup."""
        logger.info("🗄️ Optimizing database files...")
        
        try:
            total_size_before = 0.0
            total_size_after = 0.0
            vacuum_time = 0.0
            
            # Find all SQLite database files
            db_patterns = ["*.db", "*.sqlite", "*.sqlite3"]
            db_files = []
            
            for pattern in db_patterns:
                db_files.extend(self.project_root.rglob(pattern))
            
            for db_file in db_files:
                if db_file.exists():
                    try:
                        # Get size before optimization
                        size_before = db_file.stat().st_size / (1024 * 1024)
                        total_size_before += size_before
                        
                        # Run VACUUM to optimize database
                        start_time = time.time()
                        with sqlite3.connect(str(db_file)) as conn:
                            conn.execute("VACUUM")
                            conn.commit()
                        vacuum_time += time.time() - start_time
                        
                        # Get size after optimization
                        size_after = db_file.stat().st_size / (1024 * 1024)
                        total_size_after += size_after
                        
                        logger.debug(f"Optimized {db_file.name}: "
                                   f"{size_before:.1f}MB → {size_after:.1f}MB")
                        
                    except Exception as e:
                        logger.debug(f"Could not optimize {db_file}: {e}")
            
            # Update metrics
            self.metrics.db_size_before_mb = total_size_before
            self.metrics.db_size_after_mb = total_size_after
            self.metrics.db_vacuum_time_sec = vacuum_time
            
            space_saved = total_size_before - total_size_after
            
            logger.info(f"Database optimization: {space_saved:.1f}MB saved, "
                       f"{vacuum_time:.1f}s vacuum time")
            
            return {
                "status": "success",
                "space_saved_mb": space_saved,
                "vacuum_time_sec": vacuum_time,
                "databases_optimized": len(db_files)
            }
            
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            return {"status": "error", "error": str(e)}
    
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
        
        return total_size / (1024 * 1024)  # Convert to MB
    
    def _clean_old_files(self, directory: Path, days: int) -> float:
        """Clean files older than specified days. Returns size freed in MB."""
        if not directory.exists():
            return 0.0
        
        cutoff_time = time.time() - (days * 24 * 3600)
        total_freed = 0.0
        
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    try:
                        if file_path.stat().st_mtime < cutoff_time:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            total_freed += file_size
                    except (OSError, PermissionError):
                        pass
        except (OSError, PermissionError):
            pass
        
        return total_freed / (1024 * 1024)  # Convert to MB
    
    def _calculate_health_score(self) -> float:
        """Calculate overall system health score (0-100)."""
        score_components = []
        
        # Memory health (25%)
        if self.metrics.memory_hit_ratio > 0:
            memory_score = min(100, self.metrics.memory_hit_ratio * 100)
            score_components.append(memory_score * 0.25)
        
        # Storage health (25%) 
        storage_score = min(100, max(0, 100 - (self.metrics.storage_freed_mb / 100)))
        score_components.append(storage_score * 0.25)
        
        # RAG health (25%)
        if self.metrics.rag_documents_indexed > 0:
            rag_score = min(100, (self.metrics.rag_documents_indexed / 500) * 100)
            score_components.append(rag_score * 0.25)
        
        # API health (25%)
        if self.metrics.api_cache_hits > 0:
            api_score = min(100, (self.metrics.api_cache_hits / 100) * 100)
            score_components.append(api_score * 0.25)
        
        return sum(score_components) if score_components else 50.0
    
    def _log_optimization_summary(self):
        """Log comprehensive optimization summary."""
        logger.info("🎯 System Optimization Summary")
        logger.info("=" * 50)
        logger.info(f"⏱️  Duration: {self.metrics.optimization_duration_sec:.1f}s")
        logger.info(f"🏥 Health Score: {self.metrics.system_health_score:.1f}/100")
        logger.info("")
        logger.info(f"Memory: {self.metrics.memory_cleaned_mb:.1f}MB freed, "
                     f"{self.metrics.memory_hit_ratio:.1%} hit ratio")
        logger.info(f"💾 Storage: {self.metrics.storage_freed_mb:.1f}MB freed, "
                   f"{self.metrics.files_cleaned} files cleaned")
        logger.info(f"📚 RAG: {self.metrics.rag_index_size_mb:.1f}MB index, "
                   f"{self.metrics.rag_documents_indexed} documents")
        logger.info(f"🌐 API: {self.metrics.api_cache_hits} cache hits")
        logger.info(f"🗄️  Database: {self.metrics.db_size_before_mb - self.metrics.db_size_after_mb:.1f}MB saved")
        logger.info("=" * 50)
        
        # Log to monitoring system
        log_agent_activity(
            "SystemOptimizer",
            f"Optimization completed: {self.metrics.system_health_score:.1f}/100 health score",
            "INFO"
        )
    
    def schedule_optimization(self, interval_hours: int = 24):
        """Schedule automatic optimization to run periodically."""
        def optimization_scheduler():
            while True:
                try:
                    time.sleep(interval_hours * 3600)  # Convert hours to seconds
                    logger.info(f"Running scheduled optimization (every {interval_hours}h)")
                    self.optimize_system()
                except Exception as e:
                    logger.error(f"Scheduled optimization failed: {e}")
        
        scheduler_thread = threading.Thread(target=optimization_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info(f"Scheduled optimization every {interval_hours} hours")
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics for monitoring."""
        stats = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "preservation_days": self.preserve_days,
            "aggressive_optimization": self.enable_aggressive_optimization
        }
        
        # Add current sizes
        output_dir = self.project_root / "output"
        if output_dir.exists():
            stats["output_size_mb"] = self._get_directory_size(output_dir)
        
        rag_store = self.project_root / ".rag_store"
        if rag_store.exists():
            stats["rag_store_size_mb"] = self._get_directory_size(rag_store)
        
        cache_dir = self.project_root / "cache"
        if cache_dir.exists():
            stats["cache_size_mb"] = self._get_directory_size(cache_dir)
        
        # Add latest optimization metrics
        stats["last_optimization"] = self.metrics.to_dict()
        
        return stats
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.executor.shutdown(wait=True)


def main():
    """Run system optimization from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Multi-AI System Optimizer")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--preserve-days", type=int, default=7, help="Days to preserve data")
    parser.add_argument("--aggressive", action="store_true", help="Enable aggressive optimization")
    parser.add_argument("--memory-only", action="store_true", help="Only optimize memory")
    parser.add_argument("--storage-only", action="store_true", help="Only optimize storage") 
    parser.add_argument("--rag-only", action="store_true", help="Only optimize RAG")
    parser.add_argument("--api-only", action="store_true", help="Only optimize API")
    parser.add_argument("--database-only", action="store_true", help="Only optimize database")
    parser.add_argument("--schedule", type=int, help="Schedule optimization every N hours")
    parser.add_argument("--stats", action="store_true", help="Show system statistics only")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    with SystemOptimizer(
        project_root=args.project_root,
        preserve_days=args.preserve_days,
        enable_aggressive_optimization=args.aggressive
    ) as optimizer:
        
        if args.stats:
            # Show system statistics
            stats = optimizer.get_system_stats()
            print(json.dumps(stats, indent=2))
            return
        
        # Determine what to optimize
        optimize_memory = not any([args.storage_only, args.rag_only, args.api_only, args.database_only])
        optimize_storage = not any([args.memory_only, args.rag_only, args.api_only, args.database_only])
        optimize_rag = not any([args.memory_only, args.storage_only, args.api_only, args.database_only])
        optimize_api = not any([args.memory_only, args.storage_only, args.rag_only, args.database_only])
        optimize_database = not any([args.memory_only, args.storage_only, args.rag_only, args.api_only])
        
        if args.memory_only:
            optimize_memory = True
            optimize_storage = optimize_rag = optimize_api = optimize_database = False
        elif args.storage_only:
            optimize_storage = True
            optimize_memory = optimize_rag = optimize_api = optimize_database = False
        elif args.rag_only:
            optimize_rag = True
            optimize_memory = optimize_storage = optimize_api = optimize_database = False
        elif args.api_only:
            optimize_api = True
            optimize_memory = optimize_storage = optimize_rag = optimize_database = False
        elif args.database_only:
            optimize_database = True
            optimize_memory = optimize_storage = optimize_rag = optimize_api = False
        
        # Run optimization
        metrics = optimizer.optimize_system(
            optimize_memory=optimize_memory,
            optimize_storage=optimize_storage,
            optimize_rag=optimize_rag,
            optimize_api=optimize_api,
            optimize_database=optimize_database
        )
        
        # Schedule if requested
        if args.schedule:
            optimizer.schedule_optimization(args.schedule)
            print(f"Optimization scheduled every {args.schedule} hours. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                print("\nScheduled optimization stopped.")
        
        # Output results
        print(f"\nOptimization completed in {metrics.optimization_duration_sec:.1f}s")
        print(f"System health score: {metrics.system_health_score:.1f}/100")


if __name__ == "__main__":
    main() 