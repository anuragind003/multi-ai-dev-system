#!/usr/bin/env python3
"""
Multi-AI Development System Optimization Runner

This script provides a unified interface to run all optimization strategies:
1. Memory cleanup and optimization
2. Storage cleanup and compression
3. RAG index optimization
4. API cache optimization
5. Database maintenance
6. Performance monitoring
"""

import os
import sys
import time
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('optimization.log')
        ]
    )


def cleanup_old_runs(project_root: Path, preserve_days: int = 7, dry_run: bool = False) -> Dict[str, Any]:
    """Clean up old workflow run directories."""
    import shutil
    from datetime import timedelta
    
    logger.info(f"🗂️ Cleaning run directories older than {preserve_days} days...")
    
    stats = {"runs_cleaned": 0, "space_freed_mb": 0.0, "errors": []}
    output_dir = project_root / "output"
    
    if not output_dir.exists():
        return stats
    
    cutoff_date = datetime.now() - timedelta(days=preserve_days)
    
    for run_dir in output_dir.glob("run_*"):
        if not run_dir.is_dir():
            continue
        
        try:
            # Parse timestamp from directory name
            timestamp_str = run_dir.name.replace("run_", "")
            run_timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            
            if run_timestamp < cutoff_date:
                # Calculate directory size
                dir_size = sum(f.stat().st_size for f in run_dir.rglob('*') if f.is_file())
                dir_size_mb = dir_size / (1024 * 1024)
                
                if dry_run:
                    logger.info(f"Would remove: {run_dir.name} ({dir_size_mb:.1f}MB)")
                else:
                    shutil.rmtree(run_dir)
                    logger.debug(f"Removed: {run_dir.name} ({dir_size_mb:.1f}MB)")
                
                stats["runs_cleaned"] += 1
                stats["space_freed_mb"] += dir_size_mb
                
        except (ValueError, OSError) as e:
            error_msg = f"Could not process {run_dir}: {e}"
            logger.warning(error_msg)
            stats["errors"].append(error_msg)
    
    logger.info(f"✅ Cleaned {stats['runs_cleaned']} old runs, freed {stats['space_freed_mb']:.1f}MB")
    return stats


def cleanup_cache_files(project_root: Path, preserve_days: int = 3, dry_run: bool = False) -> Dict[str, Any]:
    """Clean up cache files and directories."""
    import shutil
    
    logger.info(f"💾 Cleaning cache files older than {preserve_days} days...")
    
    stats = {"files_cleaned": 0, "space_freed_mb": 0.0, "errors": []}
    cutoff_time = time.time() - (preserve_days * 24 * 3600)
    
    cache_dirs = [
        project_root / "cache",
        project_root / ".cache",
        project_root / "__pycache__"
    ]
    
    # Add all __pycache__ directories
    cache_dirs.extend(project_root.rglob("__pycache__"))
    
    for cache_dir in cache_dirs:
        if not cache_dir.exists():
            continue
        
        try:
            if cache_dir.name == "__pycache__":
                # Remove entire __pycache__ directories
                dir_size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
                dir_size_mb = dir_size / (1024 * 1024)
                
                if dry_run:
                    logger.info(f"Would remove: {cache_dir} ({dir_size_mb:.1f}MB)")
                else:
                    shutil.rmtree(cache_dir)
                    logger.debug(f"Removed: {cache_dir}")
                
                stats["files_cleaned"] += 1
                stats["space_freed_mb"] += dir_size_mb
            else:
                # Clean old files from cache directories
                for file_path in cache_dir.rglob("*"):
                    if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                        try:
                            file_size = file_path.stat().st_size
                            file_size_mb = file_size / (1024 * 1024)
                            
                            if dry_run:
                                logger.debug(f"Would remove: {file_path} ({file_size_mb:.1f}MB)")
                            else:
                                file_path.unlink()
                                logger.debug(f"Removed: {file_path}")
                            
                            stats["files_cleaned"] += 1
                            stats["space_freed_mb"] += file_size_mb
                            
                        except OSError as e:
                            error_msg = f"Could not remove {file_path}: {e}"
                            logger.debug(error_msg)
                            stats["errors"].append(error_msg)
                            
        except (OSError, PermissionError) as e:
            error_msg = f"Could not process cache directory {cache_dir}: {e}"
            logger.warning(error_msg)
            stats["errors"].append(error_msg)
    
    logger.info(f"✅ Cleaned {stats['files_cleaned']} cache files, freed {stats['space_freed_mb']:.1f}MB")
    return stats


def optimize_databases(project_root: Path, dry_run: bool = False) -> Dict[str, Any]:
    """Optimize SQLite database files."""
    import sqlite3
    
    logger.info("🗄️ Optimizing database files...")
    
    stats = {"databases_optimized": 0, "space_saved_mb": 0.0, "errors": []}
    
    # Find all SQLite database files
    db_patterns = ["*.db", "*.sqlite", "*.sqlite3"]
    db_files = []
    
    for pattern in db_patterns:
        db_files.extend(project_root.rglob(pattern))
    
    for db_file in db_files:
        if not db_file.exists():
            continue
        
        try:
            # Get size before optimization
            size_before = db_file.stat().st_size
            
            if dry_run:
                logger.info(f"Would optimize: {db_file} ({size_before / (1024*1024):.1f}MB)")
                stats["databases_optimized"] += 1
            else:
                # Run VACUUM to optimize database
                with sqlite3.connect(str(db_file)) as conn:
                    conn.execute("VACUUM")
                    conn.commit()
                
                # Get size after optimization
                size_after = db_file.stat().st_size
                space_saved = (size_before - size_after) / (1024 * 1024)
                
                stats["databases_optimized"] += 1
                stats["space_saved_mb"] += space_saved
                
                logger.debug(f"Optimized: {db_file.name} (saved {space_saved:.1f}MB)")
                
        except Exception as e:
            error_msg = f"Could not optimize {db_file}: {e}"
            logger.warning(error_msg)
            stats["errors"].append(error_msg)
    
    logger.info(f"✅ Optimized {stats['databases_optimized']} databases, saved {stats['space_saved_mb']:.1f}MB")
    return stats


def optimize_memory_system(project_root: Path) -> Dict[str, Any]:
    """Optimize enhanced memory system."""
    logger.info("Optimizing memory system...")
    
    stats = {"status": "unknown", "hit_ratio": 0.0, "ops_per_sec": 0.0}
    
    try:
        # Import and use enhanced memory manager
        from enhanced_memory_manager import create_memory_manager
        
        memory_manager = create_memory_manager()
        if memory_manager:
            # Get current stats
            memory_stats = memory_manager.get_stats()
            
            # Run optimization
            memory_manager.optimize()
            
            # Get updated stats
            updated_stats = memory_manager.get_stats()
            
            stats.update({
                "status": "success",
                "hit_ratio": updated_stats.hit_ratio,
                "ops_per_sec": updated_stats.operations_per_second,
                "memory_usage_mb": updated_stats.memory_usage_mb
            })
            
            logger.info(f"✅ Memory optimization: {stats['hit_ratio']:.1%} hit ratio, "
                       f"{stats['ops_per_sec']:.0f} ops/sec")
        else:
            stats["status"] = "skipped"
            logger.warning("Enhanced memory manager not available")
            
    except ImportError as e:
        stats["status"] = "error"
        stats["error"] = str(e)
        logger.error(f"Could not import memory manager: {e}")
    except Exception as e:
        stats["status"] = "error"
        stats["error"] = str(e)
        logger.error(f"Memory optimization failed: {e}")
    
    return stats


def optimize_rag_system(project_root: Path) -> Dict[str, Any]:
    """Optimize RAG system and vector store."""
    logger.info("📚 Optimizing RAG system...")
    
    stats = {"status": "unknown", "index_size_mb": 0.0, "documents": 0}
    
    try:
        # Import and use RAG manager
        from rag_manager import get_rag_manager
        
        rag_manager = get_rag_manager()
        if rag_manager:
            # Enable embedding cache for better performance
            if hasattr(rag_manager, 'enable_embedding_cache'):
                rag_manager.enable_embedding_cache()
            
            # Save optimized vector store
            if hasattr(rag_manager, '_save_vector_store'):
                rag_manager._save_vector_store()
            
            # Get RAG info
            rag_info = rag_manager.get_vector_store_info()
            rag_store_path = project_root / ".rag_store"
            
            if rag_store_path.exists():
                index_size = sum(f.stat().st_size for f in rag_store_path.rglob('*') if f.is_file())
                stats["index_size_mb"] = index_size / (1024 * 1024)
            
            stats.update({
                "status": "success",
                "documents": rag_info.get("document_count", 0),
                "initialized": rag_info.get("initialized", False)
            })
            
            logger.info(f"✅ RAG optimization: {stats['index_size_mb']:.1f}MB index, "
                       f"{stats['documents']} documents")
        else:
            stats["status"] = "skipped"
            logger.warning("RAG manager not available")
            
    except ImportError as e:
        stats["status"] = "error"
        stats["error"] = str(e)
        logger.error(f"Could not import RAG manager: {e}")
    except Exception as e:
        stats["status"] = "error"
        stats["error"] = str(e)
        logger.error(f"RAG optimization failed: {e}")
    
    return stats


def get_system_stats(project_root: Path) -> Dict[str, Any]:
    """Get current system statistics."""
    stats = {
        "timestamp": datetime.now().isoformat(),
        "project_root": str(project_root)
    }
    
    # Directory sizes
    directories = {
        "output": project_root / "output",
        "cache": project_root / "cache", 
        ".cache": project_root / ".cache",
        "logs": project_root / "logs",
        ".rag_store": project_root / ".rag_store"
    }
    
    for name, path in directories.items():
        if path.exists():
            try:
                size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
                stats[f"{name}_size_mb"] = size / (1024 * 1024)
            except (OSError, PermissionError):
                stats[f"{name}_size_mb"] = 0.0
        else:
            stats[f"{name}_size_mb"] = 0.0
    
    # Count run directories
    output_dir = project_root / "output"
    if output_dir.exists():
        run_dirs = list(output_dir.glob("run_*"))
        stats["run_directories"] = len(run_dirs)
    else:
        stats["run_directories"] = 0
    
    # Count database files
    db_count = 0
    db_size = 0.0
    for pattern in ["*.db", "*.sqlite", "*.sqlite3"]:
        for db_file in project_root.rglob(pattern):
            if db_file.exists():
                db_count += 1
                db_size += db_file.stat().st_size
    
    stats["database_count"] = db_count
    stats["database_size_mb"] = db_size / (1024 * 1024)
    
    return stats


def run_comprehensive_optimization(project_root: Path, 
                                 preserve_days: int = 7,
                                 dry_run: bool = False,
                                 enable_memory: bool = True,
                                 enable_storage: bool = True,
                                 enable_rag: bool = True,
                                 enable_database: bool = True) -> Dict[str, Any]:
    """Run comprehensive system optimization."""
    logger.info("🚀 Starting comprehensive system optimization...")
    start_time = time.time()
    
    # Get initial stats
    initial_stats = get_system_stats(project_root)
    
    optimization_results = {
        "start_time": start_time,
        "initial_stats": initial_stats,
        "results": {}
    }
    
    # Run optimizations
    if enable_storage:
        optimization_results["results"]["cleanup_runs"] = cleanup_old_runs(
            project_root, preserve_days, dry_run
        )
        
        optimization_results["results"]["cleanup_cache"] = cleanup_cache_files(
            project_root, max(1, preserve_days // 2), dry_run
        )
    
    if enable_database:
        optimization_results["results"]["optimize_databases"] = optimize_databases(
            project_root, dry_run
        )
    
    if enable_memory:
        optimization_results["results"]["optimize_memory"] = optimize_memory_system(
            project_root
        )
    
    if enable_rag:
        optimization_results["results"]["optimize_rag"] = optimize_rag_system(
            project_root
        )
    
    # Get final stats
    final_stats = get_system_stats(project_root)
    optimization_results["final_stats"] = final_stats
    optimization_results["duration_sec"] = time.time() - start_time
    
    # Calculate total improvements
    total_space_freed = 0.0
    for result in optimization_results["results"].values():
        if isinstance(result, dict):
            total_space_freed += result.get("space_freed_mb", 0.0)
            total_space_freed += result.get("space_saved_mb", 0.0)
    
    optimization_results["total_space_freed_mb"] = total_space_freed
    
    # Log summary
    logger.info("🎯 Optimization Summary")
    logger.info("=" * 50)
    logger.info(f"⏱️  Duration: {optimization_results['duration_sec']:.1f}s")
    logger.info(f"💾 Total space freed: {total_space_freed:.1f}MB")
    
    if enable_storage:
        runs_result = optimization_results["results"]["cleanup_runs"]
        cache_result = optimization_results["results"]["cleanup_cache"]
        logger.info(f"🗂️  Run directories cleaned: {runs_result['runs_cleaned']}")
        logger.info(f"💾 Cache files cleaned: {cache_result['files_cleaned']}")
    
    if enable_database:
        db_result = optimization_results["results"]["optimize_databases"]
        logger.info(f"🗄️  Databases optimized: {db_result['databases_optimized']}")
    
    if enable_memory:
        memory_result = optimization_results["results"]["optimize_memory"]
        if memory_result["status"] == "success":
            logger.info(f"Memory hit ratio: {memory_result['hit_ratio']:.1%}")
    
    if enable_rag:
        rag_result = optimization_results["results"]["optimize_rag"]
        if rag_result["status"] == "success":
            logger.info(f"📚 RAG index: {rag_result['index_size_mb']:.1f}MB, {rag_result['documents']} docs")
    
    logger.info("=" * 50)
    
    return optimization_results


def main():
    """Main optimization runner."""
    parser = argparse.ArgumentParser(description="Multi-AI System Optimizer")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--preserve-days", type=int, default=7, help="Days to preserve data")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be optimized without doing it")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--stats-only", action="store_true", help="Show system statistics only")
    parser.add_argument("--output", help="Save results to JSON file")
    
    # Optimization toggles
    parser.add_argument("--no-memory", action="store_true", help="Skip memory optimization")
    parser.add_argument("--no-storage", action="store_true", help="Skip storage cleanup")
    parser.add_argument("--no-rag", action="store_true", help="Skip RAG optimization")
    parser.add_argument("--no-database", action="store_true", help="Skip database optimization")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    project_root = Path(args.project_root).resolve()
    
    if args.stats_only:
        # Show system statistics only
        stats = get_system_stats(project_root)
        print(json.dumps(stats, indent=2))
        return
    
    # Run optimization
    results = run_comprehensive_optimization(
        project_root=project_root,
        preserve_days=args.preserve_days,
        dry_run=args.dry_run,
        enable_memory=not args.no_memory,
        enable_storage=not args.no_storage,
        enable_rag=not args.no_rag,
        enable_database=not args.no_database
    )
    
    # Save results if requested
    if args.output:
        try:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Optimization results saved to {args.output}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    # Print summary
    if not args.verbose:
        print(f"\nOptimization completed in {results['duration_sec']:.1f}s")
        print(f"Total space freed: {results['total_space_freed_mb']:.1f}MB")
        
        if args.dry_run:
            print("(DRY RUN - no changes were made)")


if __name__ == "__main__":
    main() 