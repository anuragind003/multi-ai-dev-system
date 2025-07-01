#!/usr/bin/env python3
"""
System Optimization Runner for Multi-AI Development System

Comprehensive optimization using existing system components:
- Enhanced Memory Manager optimization
- RAG system optimization 
- Storage cleanup (old runs, cache, logs)
- Database maintenance and compression
- Performance monitoring and reporting
"""

import os
import sys
import time
import json
import sqlite3
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def get_directory_size(directory: Path) -> float:
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


def cleanup_old_runs(preserve_days: int = 7) -> Dict[str, Any]:
    """Clean up old workflow run directories."""
    logger.info(f"🗂️ Cleaning run directories older than {preserve_days} days...")
    
    stats = {"runs_cleaned": 0, "space_freed_mb": 0.0}
    output_dir = PROJECT_ROOT / "output"
    
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
                # Calculate directory size before removal
                dir_size = get_directory_size(run_dir)
                
                # Remove old run directory
                shutil.rmtree(run_dir)
                
                stats["runs_cleaned"] += 1
                stats["space_freed_mb"] += dir_size
                
                logger.info(f"Removed old run: {run_dir.name} ({dir_size:.1f}MB)")
                
        except (ValueError, OSError) as e:
            logger.warning(f"Could not process run directory {run_dir}: {e}")
    
    logger.info(f"✅ Cleaned {stats['runs_cleaned']} old runs, freed {stats['space_freed_mb']:.1f}MB")
    return stats


def cleanup_cache_files() -> Dict[str, Any]:
    """Clean up cache files and __pycache__ directories."""
    logger.info("💾 Cleaning cache files and __pycache__ directories...")
    
    stats = {"files_cleaned": 0, "space_freed_mb": 0.0}
    
    # Clean all __pycache__ directories
    for pycache_dir in PROJECT_ROOT.rglob("__pycache__"):
        if pycache_dir.is_dir():
            try:
                dir_size = get_directory_size(pycache_dir)
                shutil.rmtree(pycache_dir)
                
                stats["files_cleaned"] += 1
                stats["space_freed_mb"] += dir_size
                
                logger.debug(f"Removed __pycache__: {pycache_dir}")
                
            except (OSError, PermissionError) as e:
                logger.warning(f"Could not remove {pycache_dir}: {e}")
    
    # Clean cache directories
    cache_dirs = [
        PROJECT_ROOT / "cache",
        PROJECT_ROOT / ".cache"
    ]
    
    for cache_dir in cache_dirs:
        if cache_dir.exists():
            try:
                # Clean old files (older than 3 days)
                cutoff_time = time.time() - (3 * 24 * 3600)
                
                for file_path in cache_dir.rglob("*"):
                    if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                        try:
                            file_size = file_path.stat().st_size / (1024 * 1024)
                            file_path.unlink()
                            
                            stats["files_cleaned"] += 1
                            stats["space_freed_mb"] += file_size
                            
                        except OSError:
                            pass
                            
            except (OSError, PermissionError) as e:
                logger.warning(f"Could not clean cache directory {cache_dir}: {e}")
    
    logger.info(f"✅ Cleaned {stats['files_cleaned']} cache files, freed {stats['space_freed_mb']:.1f}MB")
    return stats


def optimize_databases() -> Dict[str, Any]:
    """Optimize SQLite database files using VACUUM."""
    logger.info("🗄️ Optimizing database files...")
    
    stats = {"databases_optimized": 0, "space_saved_mb": 0.0}
    
    # Find all SQLite database files
    db_patterns = ["*.db", "*.sqlite", "*.sqlite3"]
    
    for pattern in db_patterns:
        for db_file in PROJECT_ROOT.rglob(pattern):
            if not db_file.exists():
                continue
            
            try:
                # Get size before optimization
                size_before = db_file.stat().st_size
                
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
                logger.warning(f"Could not optimize {db_file}: {e}")
    
    logger.info(f"✅ Optimized {stats['databases_optimized']} databases, saved {stats['space_saved_mb']:.1f}MB")
    return stats


def optimize_memory_system() -> Dict[str, Any]:
    """Optimize the enhanced memory management system."""
    logger.info("Optimizing enhanced memory system...")
    
    stats = {"status": "unknown"}
    
    try:
        from enhanced_memory_manager import create_memory_manager
        
        memory_manager = create_memory_manager()
        if memory_manager:
            # Get stats before optimization
            before_stats = memory_manager.get_stats()
            
            # Run memory optimization
            memory_manager.optimize()
            
            # Get stats after optimization
            after_stats = memory_manager.get_stats()
            
            stats.update({
                "status": "success",
                "hit_ratio": after_stats.hit_ratio,
                "operations_per_sec": after_stats.operations_per_second,
                "memory_usage_mb": after_stats.memory_usage_mb,
                "total_entries": after_stats.total_entries
            })
            
            logger.info(f"✅ Memory optimization completed: {stats['hit_ratio']:.1%} hit ratio, "
                       f"{stats['operations_per_sec']:.0f} ops/sec, {stats['total_entries']} entries")
        else:
            stats = {"status": "unavailable", "message": "Enhanced memory manager not available"}
            logger.warning("Enhanced memory manager not available")
            
    except ImportError as e:
        stats = {"status": "error", "error": f"Import error: {str(e)}"}
        logger.error(f"Could not import enhanced memory manager: {e}")
    except Exception as e:
        stats = {"status": "error", "error": str(e)}
        logger.error(f"Memory optimization failed: {e}")
    
    return stats


def optimize_rag_system() -> Dict[str, Any]:
    """Optimize the RAG (Retrieval-Augmented Generation) system."""
    logger.info("📚 Optimizing RAG system...")
    
    stats = {"status": "unknown"}
    
    try:
        from rag_manager import get_rag_manager
        
        rag_manager = get_rag_manager()
        if rag_manager:
            # Get RAG system information
            rag_info = rag_manager.get_vector_store_info()
            
            # Enable embedding cache for better performance
            if hasattr(rag_manager, 'enable_embedding_cache'):
                rag_manager.enable_embedding_cache()
                logger.debug("Enabled RAG embedding cache")
            
            # Save optimized vector store
            if hasattr(rag_manager, '_save_vector_store'):
                rag_manager._save_vector_store()
                logger.debug("Saved optimized vector store")
            
            # Get RAG store directory size
            rag_store_path = PROJECT_ROOT / ".rag_store"
            index_size = get_directory_size(rag_store_path) if rag_store_path.exists() else 0.0
            
            stats.update({
                "status": "success",
                "index_size_mb": index_size,
                "documents_count": rag_info.get("document_count", 0),
                "initialized": rag_info.get("initialized", False)
            })
            
            logger.info(f"✅ RAG optimization completed: {stats['index_size_mb']:.1f}MB index, "
                       f"{stats['documents_count']} documents")
        else:
            stats = {"status": "unavailable", "message": "RAG manager not available"}
            logger.warning("RAG manager not available")
            
    except ImportError as e:
        stats = {"status": "error", "error": f"Import error: {str(e)}"}
        logger.error(f"Could not import RAG manager: {e}")
    except Exception as e:
        stats = {"status": "error", "error": str(e)}
        logger.error(f"RAG optimization failed: {e}")
    
    return stats


def get_system_stats() -> Dict[str, Any]:
    """Get comprehensive system statistics."""
    stats = {
        "timestamp": datetime.now().isoformat(),
        "project_root": str(PROJECT_ROOT)
    }
    
    # Directory sizes
    directories = {
        "output": PROJECT_ROOT / "output",
        "cache": PROJECT_ROOT / "cache",
        ".cache": PROJECT_ROOT / ".cache",
        "logs": PROJECT_ROOT / "logs",
        ".rag_store": PROJECT_ROOT / ".rag_store"
    }
    
    for name, path in directories.items():
        stats[f"{name}_size_mb"] = get_directory_size(path)
    
    # Count run directories
    output_dir = PROJECT_ROOT / "output"
    if output_dir.exists():
        run_dirs = list(output_dir.glob("run_*"))
        stats["run_directories_count"] = len(run_dirs)
    else:
        stats["run_directories_count"] = 0
    
    # Count database files
    db_count = 0
    db_total_size = 0.0
    for pattern in ["*.db", "*.sqlite", "*.sqlite3"]:
        for db_file in PROJECT_ROOT.rglob(pattern):
            if db_file.exists():
                db_count += 1
                db_total_size += db_file.stat().st_size
    
    stats["database_files_count"] = db_count
    stats["database_total_size_mb"] = db_total_size / (1024 * 1024)
    
    return stats


def run_system_optimization(preserve_days: int = 7) -> Dict[str, Any]:
    """Run comprehensive system optimization."""
    logger.info("🚀 Starting comprehensive system optimization...")
    start_time = time.time()
    
    # Get initial system stats
    initial_stats = get_system_stats()
    logger.info("📊 Initial system state captured")
    
    # Initialize results structure
    results = {
        "start_time": start_time,
        "initial_stats": initial_stats,
        "optimization_results": {}
    }
    
    # Run optimizations
    logger.info("Starting optimization sequence...")
    
    # 1. Clean up old run directories
    results["optimization_results"]["cleanup_runs"] = cleanup_old_runs(preserve_days)
    
    # 2. Clean up cache files
    results["optimization_results"]["cleanup_cache"] = cleanup_cache_files()
    
    # 3. Optimize databases
    results["optimization_results"]["optimize_databases"] = optimize_databases()
    
    # 4. Optimize memory system
    results["optimization_results"]["optimize_memory"] = optimize_memory_system()
    
    # 5. Optimize RAG system
    results["optimization_results"]["optimize_rag"] = optimize_rag_system()
    
    # Get final system stats
    final_stats = get_system_stats()
    results["final_stats"] = final_stats
    results["duration_sec"] = time.time() - start_time
    
    # Calculate total improvements
    total_space_freed = 0.0
    for optimization_result in results["optimization_results"].values():
        if isinstance(optimization_result, dict):
            total_space_freed += optimization_result.get("space_freed_mb", 0.0)
            total_space_freed += optimization_result.get("space_saved_mb", 0.0)
    
    results["total_space_freed_mb"] = total_space_freed
    
    # Calculate storage improvements
    initial_total_size = sum(v for k, v in initial_stats.items() if k.endswith("_size_mb"))
    final_total_size = sum(v for k, v in final_stats.items() if k.endswith("_size_mb"))
    storage_reduction = initial_total_size - final_total_size
    
    results["storage_reduction_mb"] = storage_reduction
    
    # Log comprehensive summary
    log_optimization_summary(results)
    
    return results


def log_optimization_summary(results: Dict[str, Any]):
    """Log comprehensive optimization summary."""
    logger.info("🎯 System Optimization Summary")
    logger.info("=" * 60)
    logger.info(f"⏱️  Total Duration: {results['duration_sec']:.1f} seconds")
    logger.info(f"💾 Total Space Freed: {results['total_space_freed_mb']:.1f}MB")
    logger.info(f"📉 Storage Reduction: {results['storage_reduction_mb']:.1f}MB")
    logger.info("")
    
    # Storage cleanup results
    cleanup_runs = results["optimization_results"]["cleanup_runs"]
    cleanup_cache = results["optimization_results"]["cleanup_cache"]
    logger.info(f"🗂️  Run directories cleaned: {cleanup_runs['runs_cleaned']}")
    logger.info(f"💾 Cache files cleaned: {cleanup_cache['files_cleaned']}")
    
    # Database optimization results
    db_optimization = results["optimization_results"]["optimize_databases"]
    logger.info(f"🗄️  Databases optimized: {db_optimization['databases_optimized']}")
    logger.info(f"📦 Database space saved: {db_optimization['space_saved_mb']:.1f}MB")
    
    # Memory system results
    memory_optimization = results["optimization_results"]["optimize_memory"]
    if memory_optimization["status"] == "success":
        logger.info(f"Memory system: {memory_optimization['hit_ratio']:.1%} hit ratio, "
                   f"{memory_optimization['total_entries']} entries")
    else:
        logger.info(f"Memory system: {memory_optimization['status']}")
    
    # RAG system results
    rag_optimization = results["optimization_results"]["optimize_rag"]
    if rag_optimization["status"] == "success":
        logger.info(f"📚 RAG system: {rag_optimization['index_size_mb']:.1f}MB index, "
                   f"{rag_optimization['documents_count']} documents")
    else:
        logger.info(f"📚 RAG system: {rag_optimization['status']}")
    
    logger.info("")
    logger.info("📊 Storage Summary:")
    logger.info(f"   Output directory: {results['final_stats']['output_size_mb']:.1f}MB")
    logger.info(f"   Cache directory: {results['final_stats']['cache_size_mb']:.1f}MB")
    logger.info(f"   RAG store: {results['final_stats']['.rag_store_size_mb']:.1f}MB")
    logger.info(f"   Database files: {results['final_stats']['database_total_size_mb']:.1f}MB")
    logger.info("=" * 60)


def main():
    """Main function to run optimization."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Multi-AI System Optimizer")
    parser.add_argument("--preserve-days", type=int, default=7, 
                       help="Number of days to preserve run directories (default: 7)")
    parser.add_argument("--stats-only", action="store_true", 
                       help="Only show system statistics without optimization")
    parser.add_argument("--save-results", help="Save optimization results to JSON file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    setup_logging()
    
    if args.stats_only:
        # Show system statistics only
        stats = get_system_stats()
        print(json.dumps(stats, indent=2))
        return
    
    # Run optimization
    results = run_system_optimization(args.preserve_days)
    
    # Save results if requested
    if args.save_results:
        try:
            with open(args.save_results, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"📝 Optimization results saved to {args.save_results}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    # Print final summary
    print(f"\n🎉 Optimization completed successfully!")
    print(f"⏱️  Duration: {results['duration_sec']:.1f} seconds")
    print(f"💾 Space freed: {results['total_space_freed_mb']:.1f}MB")
    print(f"📉 Storage reduced: {results['storage_reduction_mb']:.1f}MB")


if __name__ == "__main__":
    main() 