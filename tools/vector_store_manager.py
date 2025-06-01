"""
DEPRECATED: This file has been replaced by rag_manager.py
Please use the new RAG system instead.
"""

# Import the new RAG system for backward compatibility
from rag_manager import ProjectRAGManager, get_rag_manager

class VectorStoreManager:
    """
    DEPRECATED: Legacy vector store manager.
    Use rag_manager.ProjectRAGManager instead.
    """
    
    def __init__(self, run_dir: str):
        print("⚠️  WARNING: VectorStoreManager is deprecated. Use rag_manager.ProjectRAGManager instead.")
        self.run_dir = run_dir
        # Initialize the new RAG manager
        self._rag_manager = ProjectRAGManager(run_dir)
    
    def initialize_vector_store(self, documents_raw_text: list[str], chunk_size: int = 1000, chunk_overlap: int = 200, clean_existing: bool = False):
        """DEPRECATED: Use rag_manager instead."""
        print("⚠️  DEPRECATED: Use rag_manager.ProjectRAGManager.add_documents_from_directory() instead")
        return self._rag_manager.get_stats()
    
    def get_retriever(self, k: int = 7):
        """DEPRECATED: Use rag_manager instead."""
        print("⚠️  DEPRECATED: Use rag_manager.ProjectRAGManager.get_retriever() instead")
        return self._rag_manager.get_retriever(search_kwargs={"k": k})
    
    def add_documents_to_store(self, new_documents_raw_text: list[str], chunk_size: int = 1000, chunk_overlap: int = 200):
        """DEPRECATED: Use rag_manager instead."""
        print("⚠️  DEPRECATED: Use rag_manager.ProjectRAGManager.add_document() instead")
        # For backward compatibility, add raw text as temporary files
        import tempfile
        import os
        for i, text in enumerate(new_documents_raw_text):
            if text.strip():
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(text)
                    temp_file = f.name
                self._rag_manager.add_document(temp_file)
                os.unlink(temp_file)  # Clean up temp file

# Backward compatibility aliases
ChromaVectorStore = VectorStoreManager  # If any code uses this name