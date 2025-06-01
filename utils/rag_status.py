import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rag_manager import ProjectRAGManager

def check_rag_status():
    """Check current RAG system status and cleanup if needed."""
    print("🔍 RAG System Status Check")
    print("=" * 40)
    
    # Check if .rag_store exists and what's in it
    rag_store_path = project_root / ".rag_store"
    
    if rag_store_path.exists():
        print(f"📁 RAG store exists: {rag_store_path}")
        
        # Check metadata
        metadata_file = rag_store_path / "metadata.json"
        if metadata_file.exists():
            import json
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            print(f"📊 Total indexed files: {len(metadata)}")
            
            # Check for problematic files
            venv_files = [path for path in metadata.keys() if 'venv' in path or 'site-packages' in path]
            if venv_files:
                print(f"⚠️  Found {len(venv_files)} venv/site-packages files in RAG store")
                print("🧹 Cleanup recommended!")
                
                # Ask user if they want to clean up
                response = input("Would you like to clean up the RAG store? (y/n): ")
                if response.lower() == 'y':
                    cleanup_rag_store()
            else:
                print("✅ No problematic files found")
                
            # Show sample of indexed files
            project_files = [path for path in metadata.keys() if 'venv' not in path and 'site-packages' not in path]
            print(f"📄 Sample project files ({len(project_files)} total):")
            for file_path in list(project_files)[:5]:
                print(f"   - {file_path}")
                
        else:
            print("📝 No metadata file found")
    else:
        print("📭 No RAG store found - will be created on first run")

def cleanup_rag_store():
    """Clean up the RAG store by removing it entirely."""
    rag_store_path = project_root / ".rag_store"
    
    if rag_store_path.exists():
        import shutil
        shutil.rmtree(rag_store_path)
        print("🧹 RAG store cleaned up successfully")
        print("💡 A new clean RAG store will be created on next run")
    else:
        print("📭 No RAG store to clean up")

if __name__ == "__main__":
    check_rag_status()