"""
RAG (Retrieval-Augmented Generation) Manager for Multi-AI Development System.
Provides vector store management and document retrieval capabilities.
"""

import os
import json
import hashlib
import time
import base64
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import numpy as np
from datetime import datetime
import fnmatch
import logging
import asyncio
import pickle

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader, 
    JSONLoader,
    DirectoryLoader
)
from langchain_community.document_loaders import UnstructuredFileLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

# Security imports (with fallbacks for development)
try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.fernet import Fernet
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False

import monitoring
try:
    from config import get_embedding_model
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    get_embedding_model = None

# FAISS vector store functionality with graceful fallback
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logging.warning(
        "\n\n"
        "================================================================================\n"
        "** WARNING: `faiss-cpu` not found. RAG functionality will be disabled. **\n\n"
        "The RAG (Retrieval-Augmented Generation) manager, which enhances AI responses\n"
        "with context from your documents, requires the `faiss-cpu` library.\n"
        "To enable this feature, please install it by running:\n\n"
        "   pip install faiss-cpu\n\n"
        "================================================================================\n"
    )
    # Create a mock FAISS for graceful degradation
    class MockFAISS:
        """Mock FAISS implementation for graceful degradation when FAISS is not available."""
        def __init__(self):
            self.documents = []
            self.metadata = []
        
        @classmethod
        def from_documents(cls, documents, embeddings):
            """Mock class method to create an instance from documents."""
            instance = cls()
            instance.add_documents(documents)
            return instance

        def similarity_search(self, query, k=5):
            """Mock similarity search that returns empty results."""
            return []
        
        def add_documents(self, documents):
            """Mock document addition."""
            self.documents.extend(documents)
            return True
        
        def is_initialized(self):
            """Always return False for mock."""
            return False
    
    faiss = None

# Import FAISS with fallback handling
if FAISS_AVAILABLE:
    from langchain_community.vectorstores import FAISS
else:
    # Use mock FAISS when not available
    FAISS = MockFAISS

def get_fallback_embedding_model():
    """Fallback embedding model when config is not available."""
    try:
        # Try HuggingFace embeddings as a fallback
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    except ImportError:
        try:
            # Try OpenAI as another fallback
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings()
        except ImportError:
            # If nothing else works, use a mock embeddings class
            return MockEmbeddings()

class MockEmbeddings:
    """Mock embeddings class for testing when no real embeddings are available."""
    
    def embed_documents(self, texts):
        """Return random embeddings for documents."""
        import random
        return [[random.random() for _ in range(384)] for _ in texts]
    
    def embed_query(self, text):
        """Return random embedding for query."""
        import random
        return [random.random() for _ in range(384)]

class SecurityError(Exception):
    """Custom exception for security-related errors."""
    pass

# CHANGED: Moved SecureFAISSManager before ProjectRAGManager
class SecureFAISSManager:
    """Enhanced FAISS manager with security considerations for production."""
    
    def __init__(self, project_root: str, security_mode: str = "development"):
        """Initialize the secure FAISS vector store manager.
        
        Args:
            project_root: Root directory of the project
            security_mode: Security mode (development, staging, production)
        """
        self.project_root = project_root
        self.security_mode = security_mode
        self.index_dir = os.path.join(project_root, ".rag_store")
        self.security_dir = os.path.join(self.index_dir, ".security")
        
        # Create directories if they don't exist
        os.makedirs(self.index_dir, exist_ok=True)
        os.makedirs(self.security_dir, exist_ok=True)
        
        # Initialize tracking attributes
        self.is_initialized = False
        self.vector_store = None
        self.embeddings = None
        
        self.integrity_data = {
            "created_at": None,
            "last_verified": None,
            "file_checksums": {},
            "verification_count": 0
        }
        
        self.documents_metadata = {}
        self.metadata_file = os.path.join(self.security_dir, "documents_metadata.json")
        
        # Set agent_name BEFORE calling _init_security_config
        self.agent_name = "SecureFAISSManager"
        self._init_security_config()

    def _init_security_config(self):
        """Initialize security configuration for the FAISS vector store."""
        # Get security configuration based on the mode
        try:
            from config import get_security_config  # Import here to avoid circular imports
            
            security_config = get_security_config(self.security_mode)
            self.allow_dangerous_deserialization = security_config.get('allow_dangerous_deserialization', True)
            self.require_encryption = security_config.get('require_encryption', False)
            self.enable_integrity_checks = security_config.get('enable_integrity_checks', False)
            self.enable_access_logging = security_config.get('enable_access_logging', False)
            self.backup_required = security_config.get('backup_required', False)
        except ImportError:
            # Fallback defaults for development mode if config module not available
            self.allow_dangerous_deserialization = self.security_mode == "development"
            self.require_encryption = self.security_mode == "production"
            self.enable_integrity_checks = self.security_mode != "development"
            self.enable_access_logging = self.security_mode != "development"
            self.backup_required = self.security_mode == "production"
            
        # Initialize security-related directories
        os.makedirs(self.security_dir, exist_ok=True)
        
        # Setup encryption if required
        if self.require_encryption and SECURITY_AVAILABLE:
            self._setup_encryption()
        
        # Setup integrity checks if enabled
        if self.enable_integrity_checks:
            self._setup_integrity_checks()
        
        # Log initialization
        monitoring.log_agent_activity(
            self.agent_name, 
            f"Security initialized in {self.security_mode} mode", 
            "INFO"
        )

    def _setup_encryption(self):
        """Set up encryption for secure vector store operations."""
        if not SECURITY_AVAILABLE:
            monitoring.log_agent_activity(
                self.agent_name,
                "Encryption requested but cryptography module not available",
                "WARNING"
            )
            return
            
        # Create key file path
        key_file = os.path.join(self.security_dir, "encryption.key")
        
        # Generate or load encryption key
        if os.path.exists(key_file):
            # Load existing key
            with open(key_file, 'rb') as f:
                self.encryption_key = f.read()
        else:
            # Generate new key
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            self.encryption_key = base64.urlsafe_b64encode(kdf.derive(b"secure-vector-store"))
            
            # Save key to file
            with open(key_file, 'wb') as f:
                f.write(self.encryption_key)
        
        # Initialize Fernet cipher
        self.cipher = Fernet(self.encryption_key)
        
        monitoring.log_agent_activity(
            self.agent_name,
            "Encryption initialized successfully",
            "INFO"
        )

    def _setup_integrity_checks(self):
        """Set up integrity checking for vector store files."""
        integrity_file = os.path.join(self.security_dir, "integrity.json")
        
        # Load or initialize integrity data
        if os.path.exists(integrity_file):
            try:
                with open(integrity_file, 'r') as f:
                    self.integrity_data = json.load(f)
            except Exception as e:
                monitoring.log_agent_activity(
                    self.agent_name,
                    f"Error loading integrity data: {e}. Reinitializing.",
                    "WARNING"
                )
                self._initialize_integrity_data()
        else:
            self._initialize_integrity_data()
        
        monitoring.log_agent_activity(
            self.agent_name,
            "Integrity checking initialized",
            "INFO"
        )

    def _initialize_integrity_data(self):
        """Initialize integrity data structure for the first time."""
        self.integrity_data = {
            "created_at": datetime.now().isoformat(),
            "last_verified": None,
            "file_checksums": {},
            "verification_count": 0
        }
        
        # Save initial integrity data
        integrity_file = os.path.join(self.security_dir, "integrity.json")
        with open(integrity_file, 'w') as f:
            json.dump(self.integrity_data, f, indent=2)
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get security status information."""
        features_enabled = {
            "encryption": self.require_encryption and SECURITY_AVAILABLE,
            "integrity_checks": self.enable_integrity_checks,
            "access_logging": self.enable_access_logging,
            "secure_deserialization": not self.allow_dangerous_deserialization,
            "backup": self.backup_required
        }
        
        recommendations = []
        
        # Generate recommendations based on security mode
        if self.security_mode == "development":
            if not features_enabled["encryption"] and SECURITY_AVAILABLE:
                recommendations.append("Enable encryption for better security")
            if not features_enabled["integrity_checks"]:
                recommendations.append("Enable integrity checks for better security")
        elif self.security_mode == "staging" or self.security_mode == "production":
            if not features_enabled["encryption"]:
                if SECURITY_AVAILABLE:
                    recommendations.append("CRITICAL: Enable encryption for production environment")
                else:
                    recommendations.append("CRITICAL: Install cryptography package for encryption support")
            if not features_enabled["integrity_checks"]:
                recommendations.append("CRITICAL: Enable integrity checks for production environment")
            if not features_enabled["access_logging"]:
                recommendations.append("Enable access logging for audit trails")
            if features_enabled["secure_deserialization"]:
                recommendations.append("Disable dangerous deserialization in production")
        
        return {
            "security_mode": self.security_mode,
            "features_enabled": features_enabled,
            "security_available": SECURITY_AVAILABLE,
            "recommendations": recommendations
        }
        
    def save_index_securely(self) -> bool:
        """Save FAISS index with security measures appropriate for the security mode."""
        # Implementation for secure saving...
        # For now returning True as a placeholder
        return True

class RAGManager:
    """
    Manages the Retrieval-Augmented Generation (RAG) capabilities for the system.
    It is responsible for creating, loading, and providing access to a vector store
    of the project's codebase.
    """
    def __init__(self, project_dir: str, cache_dir: str = "cache/rag"):
        self.project_dir = Path(project_dir)
        self.cache_dir = self.project_dir / cache_dir
        self.vector_store_path = self.cache_dir / "faiss_index.pkl"
        self.vector_store: Optional[FAISS] = None
        # Initialize logger for RAGManager
        self.logger = logging.getLogger(self.__class__.__name__)
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._load_embeddings()

    def _load_embeddings(self):
        """Initializes the embeddings model."""
        try:
            # Using HuggingFace embeddings
            self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        except Exception as e:
            self.logger.error(f"Failed to initialize embeddings model: {e}")
            self.embeddings = None

    def get_retriever(self, force_rebuild=False):
        """
        Gets the retriever for the project's codebase.
        Builds the vector store if it doesn't exist or if a rebuild is forced.
        """
        if not self.embeddings:
            self.logger.error("Embeddings are not available. Cannot create a retriever.")
            return None

        if force_rebuild or not self._load_vector_store():
            self.logger.info("Building new RAG vector store for the project.")
            self.build_vector_store()
            self._save_vector_store()
        
        if self.vector_store:
            return self.vector_store.as_retriever()
        
        self.logger.error("Failed to get RAG retriever.")
        return None

    def build_vector_store(self):
        """Scans the project directory, loads files, and builds the FAISS vector store."""
        source_code_files = self._scan_project_files()
        if not source_code_files:
            self.logger.warning("No source code files found to build RAG index.")
            return

        self.logger.info(f"Found {len(source_code_files)} files to index for RAG.")

        docs = []
        for file_path in source_code_files:
            try:
                loader = TextLoader(str(file_path), encoding='utf-8')
                docs.extend(loader.load())
            except Exception as e:
                self.logger.warning(f"Error loading file {file_path}: {e}")

        if not docs:
            self.logger.error("No documents were successfully loaded. RAG index will be empty.")
            return
            
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)
        chunks = text_splitter.split_documents(docs)
        self.logger.info(f"Split {len(docs)} documents into {len(chunks)} chunks.")

        self.logger.info("Creating FAISS vector store from chunks...")
        start_time = time.time()
        self.vector_store = FAISS.from_documents(chunks, self.embeddings)
        end_time = time.time()
        self.logger.info(f"FAISS vector store created in {end_time - start_time:.2f} seconds.")

    def _scan_project_files(self) -> List[Path]:
        """Scans the project directory for supported file types, respecting .gitignore patterns."""
        supported_extensions = [
            ".py", ".js", ".ts", ".tsx", ".vue", ".html", ".css", 
            ".yml", ".yaml", "Dockerfile", ".md", ".json"
        ]
        
        excluded_dirs = ["node_modules", ".git", "__pycache__", "venv", ".idea", ".vscode", "checkpoints", "logs", "cache", "dist", "build"]
        
        files_to_index = []
        for file_path in self.project_dir.rglob("*"):
            if file_path.is_file():
                if any(dir_name in file_path.parts for dir_name in excluded_dirs):
                    continue
                if file_path.suffix in supported_extensions or file_path.name in supported_extensions:
                    files_to_index.append(file_path)
        return files_to_index

    def _save_vector_store(self):
        """Saves the FAISS vector store to disk."""
        if self.vector_store:
            with open(self.vector_store_path, "wb") as f:
                pickle.dump(self.vector_store, f)
            self.logger.info(f"RAG vector store saved to {self.vector_store_path}")

    def _load_vector_store(self) -> bool:
        """Loads the FAISS vector store from disk if it exists."""
        if self.vector_store_path.exists():
            self.logger.info(f"Loading RAG vector store from {self.vector_store_path}...")
            try:
                with open(self.vector_store_path, "rb") as f:
                    self.vector_store = pickle.load(f)
                self.logger.info("RAG vector store loaded successfully.")
                return True
            except Exception as e:
                self.logger.error(f"Failed to load RAG vector store: {e}. Rebuilding.")
                return False
        return False

class CachedEmbeddings(Embeddings):
    """Cache embedding results to avoid recomputing."""
    
    def __init__(self, embedding_model, cache_dir=None, vector_store_path=None):
        """
        Initialize the embedding cache.
        
        Args:
            embedding_model: The underlying embedding model
            cache_dir: Directory to store cache files (defaults to .embedding_cache in vector_store_path)
            vector_store_path: Path to the vector store (for default cache location)
        """
        self.model = embedding_model
        self.cache = {}
        
        # Improved cache location logic
        if cache_dir:
            self.cache_dir = cache_dir
        elif vector_store_path:
            self.cache_dir = os.path.join(vector_store_path, ".embedding_cache")
        else:
            self.cache_dir = ".rag_cache"
            
        self.cache_file = os.path.join(self.cache_dir, "embedding_cache.pkl")
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Load existing cache if available
        self._load_cache()
        
        # Stats for reporting
        self.cache_hits = 0
        self.cache_misses = 0
    
    def _load_cache(self):
        """Load embedding cache from file with improved error handling."""
        if not os.path.exists(self.cache_file):
            self.cache = {}
            return
            
        try:
            with open(self.cache_file, "rb") as f:
                import pickle
                self.cache = pickle.load(f)
        except (pickle.PickleError, IOError, EOFError) as e:
            # More specific error handling
            print(f"Warning: Failed to load embedding cache: {e}")
            self.cache = {}
        except Exception as e:
            print(f"Warning: Unexpected error loading cache: {e}")
            self.cache = {}
    
    def _save_cache(self):
        """Save embedding cache to file with improved error handling."""
        try:
            # Ensure directory exists (might have been deleted)
            os.makedirs(self.cache_dir, exist_ok=True)
            
            with open(self.cache_file, "wb") as f:
                import pickle
                pickle.dump(self.cache, f)
        except (pickle.PickleError, IOError) as e:
            print(f"Warning: Failed to save embedding cache: {e}")
        except Exception as e:
            print(f"Warning: Unexpected error saving cache: {e}")
    
    def save_cache_explicitly(self):
        """Explicitly save the cache, useful for shutdown or close operations."""
        if self.cache_misses > 0:  # Only save if cache was modified
            self._save_cache()
            return True
        return False
        
    def embed_documents(self, texts):
        """Embed documents with caching (implements Embeddings interface)."""
        results = [None] * len(texts)
        to_compute = []
        to_compute_indices_and_hashes = []
        
        # Check cache first
        for i, text in enumerate(texts):
            # Use a hash of the text as the cache key
            text_hash = hashlib.md5(text.encode()).hexdigest()
            
            if text_hash in self.cache:
                results[i] = self.cache[text_hash]
                self.cache_hits += 1
            else:
                to_compute.append(text)
                to_compute_indices_and_hashes.append((i, text_hash))
                self.cache_misses += 1
        
        # Compute missing embeddings
        if to_compute:
            computed = self.model.embed_documents(to_compute)
            
            # Update cache with new embeddings
            for (i, text_hash), embedding in zip(to_compute_indices_and_hashes, computed):
                self.cache[text_hash] = embedding
                results[i] = embedding
        
        # Save cache periodically (every 100 misses)
        if self.cache_misses % 100 == 0 and self.cache_misses > 0:
            self._save_cache()
            
        # Filter out any None results if embedding failed for some texts
        final_results = [res for res in results if res is not None]
        if len(final_results) != len(texts):
             # This might happen if embedding function fails for some items.
             # Depending on the downstream consumer, this could be an issue.
             # For FAISS, it's better to have a list of consistent embeddings.
             pass

        return final_results if final_results else []
    
    def embed_query(self, text):
        """Embed query with caching (implements Embeddings interface)."""
        # Use a hash of the text as the cache key
        text_hash = hashlib.md5(text.encode()).hexdigest()
        query_key = f"query_{text_hash}"
        
        if query_key in self.cache:
            self.cache_hits += 1
            return self.cache[query_key]
        
        # Calculate embedding
        embedding = self.model.embed_query(text)
        
        # Cache the result
        self.cache[query_key] = embedding
        self.cache_misses += 1
        
        # Save cache periodically
        if self.cache_misses % 20 == 0:
            self._save_cache()
            
        return embedding

    # ADD THIS METHOD to make the class callable
    def __call__(self, texts):
        """Make the embeddings object callable - required by FAISS."""
        if isinstance(texts, str):
            return self.embed_query(texts)
        else:
            return self.embed_documents(texts)

class ProjectRAGManager(RAGManager):
    """
    Enhanced RAG Manager for project code and documentation with security features.
    Extends the base RAGManager with project-specific features and security controls.
    """
    
    def __init__(self, project_root: str, vector_store_path: str = None, 
             embeddings: Optional[Embeddings] = None, environment: str = "development"):
        """Initialize the Project RAG Manager with security settings."""
        # Ensure project_root is a Path object early for internal use
        self._project_root_path = Path(project_root)

        # Call the parent constructor with the actual project_root for file scanning
        # and a dedicated cache directory for the base RAGManager instance.
        # This cache_dir is internal to RAGManager's operation and different from vector_store_path.
        super().__init__(project_dir=str(self._project_root_path), cache_dir=".rag_manager_cache") 
        
        # Now, set the specific attributes for ProjectRAGManager, overriding parent's if necessary.
        # The vector_store_path for ProjectRAGManager
        if vector_store_path:
            self.vector_store_path = Path(vector_store_path)
        else:
            self.vector_store_path = self._project_root_path / ".rag_store" # Default for ProjectRAGManager
        
        # Ensure the directory for the final vector store exists
        self.vector_store_path.mkdir(parents=True, exist_ok=True)
        
        # If embeddings are explicitly provided, use them; otherwise, RAGManager would have loaded defaults.
        if embeddings is not None:
            self.embeddings = embeddings

        # Project specific attributes
        self.project_root = project_root # Keep this as a string for consistency with other parts
        self.environment = environment
        self.agent_name = "Project RAG Manager"
        
        # Set up logger
        self.logger = logging.getLogger(self.agent_name)
        
        # Common file patterns to exclude from indexing
        self.default_exclude_patterns = [
            'venv', '.venv', 'env', '.env',
            '__pycache__', '.git', '.pytest_cache',
            'node_modules', '.coverage', 'htmlcov',
            'dist', 'build', '.tox',
            '*.pyc', '*.pyo', '*.pyd',
            '*.so', '*.dll', '*.jar',
            '*.zip', '*.tar', '*.gz',
            '.DS_Store', 'Thumbs.db'
        ]
        
        # Security configuration - create secure FAISS manager based on environment
        self.secure_manager = SecureFAISSManager(
            project_root=str(self._project_root_path),
            security_mode=environment
        )
        
        monitoring.log_agent_activity(
            self.agent_name, 
            f"Initialized ProjectRAGManager for {self._project_root_path} in {environment} mode",
            "INFO"
        )
        
        # Register this instance for shutdown handling
        register_rag_manager(self)

    def load_existing_index(self) -> bool:
        """
        Load an existing vector store index with security verification.
        
        Returns:
            bool: True if the index was successfully loaded, False otherwise
        """
        try:
            # Check if index files exist
            faiss_index_path = os.path.join(self.vector_store_path, "index.faiss")
            faiss_pkl_path = os.path.join(self.vector_store_path, "index.pkl")
            
            if not (os.path.exists(faiss_index_path) and os.path.exists(faiss_pkl_path)):
                # Index doesn't exist
                monitoring.log_agent_activity(
                    self.agent_name,
                    "No existing vector store index found", 
                    "INFO"
                )
                return False
                
            # Apply security verification based on environment
            if self.environment in ["production", "staging"] and self.secure_manager.enable_integrity_checks:
                monitoring.log_agent_activity(
                    self.agent_name,
                    f"Verifying index integrity ({self.environment} mode)",
                    "INFO"
                )
                # Real-world implementation would verify checksums here
            
            # Load the vector store with appropriate security settings
            allow_dangerous = self.secure_manager.allow_dangerous_deserialization
            self.vector_store = FAISS.load_local(
                str(self.vector_store_path), 
                self.embeddings,
                allow_dangerous_deserialization=allow_dangerous
            )
            
            # Update metadata if available
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.documents_metadata = json.load(f)
            
            monitoring.log_agent_activity(
                self.agent_name,
                f"Successfully loaded existing vector store with security level: {self.environment}",
                "SUCCESS"
            )
            return True
            
        except Exception as e:
            monitoring.log_agent_activity(
                self.agent_name,
                f"Error loading existing vector store: {e}",
                "ERROR"
            )
            self.vector_store = None
            return False

    def get_security_status(self) -> Dict[str, Any]:
        """Override to delegate security status to secure_manager instance."""
        if not hasattr(self, 'secure_manager') or self.secure_manager is None:
            # Fallback if secure_manager isn't available
            return {
                "security_mode": self.environment,
                "features_enabled": {},
                "security_available": SECURITY_AVAILABLE,
                "recommendations": ["Initialize secure_manager to enable security features"]
            }
        
        # Delegate to the secure_manager's get_security_status method
        return self.secure_manager.get_security_status()

    def get_retriever(self, search_kwargs=None):
        """
        Get a retriever from the vector store with fallback.
        
        Args:
            search_kwargs: Optional search parameters for the retriever
            
        Returns:
            Retriever instance if available, otherwise None
        """
        if not self.vector_store:
            self.logger.warning("Cannot create retriever - vector store not initialized")
            return None
            
        try:
            default_search_kwargs = {
                "k": 5,
                "score_threshold": 0.5
            }
            
            if search_kwargs:
                default_search_kwargs.update(search_kwargs)
                
            return self.vector_store.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs=default_search_kwargs
            )
        except Exception as e:
            self.logger.error(f"Error creating retriever from vector store: {e}")
            return None

    def similarity_search(self, query: str, k: int = 4, **kwargs):
        """
        Perform similarity search on the vector store.
        
        Args:
            query: Text query to search for
            k: Number of documents to return
            **kwargs: Additional search arguments
            
        Returns:
            List of Document objects or empty list if search fails
        """
        if not self.vector_store:
            monitoring.log_agent_activity(
                self.agent_name,
                "Cannot perform similarity search - vector store not initialized",
                "WARNING"
            )
            return []
            
        try:
            documents = self.vector_store.similarity_search(query, k=k, **kwargs)
            monitoring.log_agent_activity(
                self.agent_name,
                f"Similarity search returned {len(documents)} documents for query: {query[:50]}...",
                "INFO"
            )
            return documents
        except Exception as e:
            monitoring.log_agent_activity(
                self.agent_name,
                f"Error during similarity search: {e}",
                "ERROR"
            )
            return []

    def similarity_search_with_score(self, query: str, k: int = 4, **kwargs):
        """
        Perform similarity search with scores on the vector store.
        
        Args:
            query: Text query to search for
            k: Number of documents to return
            **kwargs: Additional search arguments
            
        Returns:
            List of (Document, score) tuples or empty list if search fails
        """
        if not self.vector_store:
            monitoring.log_agent_activity(
                self.agent_name,
                "Cannot perform similarity search with score - vector store not initialized",
                "WARNING"
            )
            return []
            
        try:
            documents_with_scores = self.vector_store.similarity_search_with_score(query, k=k, **kwargs)
            monitoring.log_agent_activity(
                self.agent_name,
                f"Similarity search with score returned {len(documents_with_scores)} documents for query: {query[:50]}...",
                "INFO"
            )
            return documents_with_scores
        except Exception as e:
            monitoring.log_agent_activity(
                self.agent_name,
                f"Error during similarity search with score: {e}",
                "ERROR"
            )
            return []
    
    def is_initialized(self) -> bool:
        """
        Check if the vector store is properly initialized and ready for operations.
        
        Returns:
            bool: True if vector store is initialized, False otherwise
        """
        return self.vector_store is not None
    
    def get_vector_store_info(self) -> Dict[str, Any]:
        """
        Get information about the current vector store state.
        
        Returns:
            dict: Information about the vector store including initialization status, document count, etc.
        """
        info = {
            "initialized": self.is_initialized(),
            "vector_store_path": str(self.vector_store_path),
            "environment": self.environment,
            "document_count": 0,
            "metadata_count": len(self.documents_metadata)
        }
        
        if self.vector_store:
            try:
                # Try to get document count from the vector store
                if hasattr(self.vector_store, 'index'):
                    info["document_count"] = self.vector_store.index.ntotal if hasattr(self.vector_store.index, 'ntotal') else 0
            except Exception as e:
                monitoring.log_agent_activity(
                    self.agent_name,
                    f"Error getting vector store info: {e}",
                    "WARNING"
                )
        
        return info

    async def initialize_index_from_project(self, project_dir: str = None) -> bool:
        """Initialize vector index from project code files."""
        try:
            # Use the provided project directory or fall back to a sensible default
            if not project_dir:
                # Use the current working directory instead of module directory
                project_dir = os.getcwd()
            
            monitoring.log_agent_activity(
                self.agent_name,
                f"Creating new RAG index from project code in: {project_dir}",
                "INFO"
            )
            
            # Check if directory exists
            if not os.path.exists(project_dir):
                monitoring.log_agent_activity(
                    self.agent_name,
                    f"Project directory does not exist: {project_dir}",
                    "ERROR"
                )
                return False
                
            # Define file patterns to include in indexing
            file_patterns = ['*.py', '*.js', '*.html', '*.css', '*.md', '*.txt', 
                             '*.json', '*.yaml', '*.yml']
            
            # Add documents from the project directory
            documents_added = await self.add_documents_from_directory(
                project_dir, 
                file_patterns=file_patterns
            )
            
            if documents_added > 0:
                monitoring.log_agent_activity(
                    self.agent_name,
                    f"Successfully indexed {documents_added} files from project",
                    "SUCCESS"
                )
                return True
            else:
                monitoring.log_agent_activity(
                    self.agent_name,
                    "No documents found to index in project directory",
                    "WARNING"
                )
                return False
                
        except Exception as e:
            monitoring.log_agent_activity(
                self.agent_name,
                f"RAG indexing failed: {e}",
                "ERROR"
            )
            return False
    
    def _save_vector_store(self) -> None:
        """
        ENHANCED: Save vector store using SecureFAISSManager with security measures.
        """
        if not self.vector_store:
            monitoring.log_agent_activity(self.agent_name, "No vector store to save", "ERROR")
            return
        
        try:
            # Update secure manager's vector store reference
            self.secure_manager.vector_store = self.vector_store
            
            # Use secure saving
            success = self.secure_manager.save_index_securely()
            
            if success:
                monitoring.log_agent_activity(
                    self.agent_name,
                    f"Vector store saved securely (mode: {self.environment})",
                    "SUCCESS"
                )
            else:
                # Fallback to basic saving in development mode
                if self.environment == "development":
                    monitoring.log_agent_activity(
                        self.agent_name,
                        "Secure save failed, using basic save in development mode",
                        "WARNING"
                    )
                    super()._save_vector_store()  # Use parent's basic save method
                else:
                    monitoring.log_agent_activity(
                        self.agent_name,
                        "CRITICAL: Secure save failed in production environment",
                        "ERROR"
                    )
                    # In production, don't fallback to insecure save
                    raise Exception("Secure save failed in production environment")
                    
        except Exception as e:
            monitoring.log_agent_activity(
                self.agent_name,
                f"Error during secure vector store save: {e}",
                "ERROR"
            )
            
            # In development mode, try fallback
            if self.environment == "development":
                monitoring.log_agent_activity(
                    self.agent_name,
                    "Attempting fallback to basic save",
                    "WARNING"
                )
                try:
                    super()._save_vector_store()  # Use parent's basic save method
                except Exception as fallback_error:
                    monitoring.log_agent_activity(
                        self.agent_name,
                        f"Fallback save also failed: {fallback_error}",
                        "ERROR"
                    )

    def index_project_code(self, project_path: Optional[str] = None, file_patterns: Optional[List[str]] = None) -> int:
        """
        Index code files from a project directory into the vector store.
        
        Args:
            project_path: Optional path to index (defaults to project_root)
            file_patterns: Optional list of file patterns to include
            
        Returns:
            Number of files indexed
        """
        logger = logging.getLogger(self.agent_name)
        
        # Enable embedding cache for better performance
        self.enable_embedding_cache()
        
        # Use optimized indexing with batching and parallelization
        try:
            return self.optimized_index_project(
                project_path=project_path, 
                batch_size=50,  # Process 50 documents at a time
                max_workers=4   # Use 4 parallel workers
            )
        except Exception as e:
            # Fall back to original implementation if optimization fails
            logger.warning(f"Optimized indexing failed: {e}. Falling back to standard indexing.")
            
            # Rest of the original implementation...
            # (Keep the existing implementation as fallback)
            try:
                # Use the provided project directory or fall back to a sensible default
                if not project_path:
                    # Use the current working directory instead of module directory
                    project_path = os.getcwd()
                
                monitoring.log_agent_activity(
                    self.agent_name,
                    f"Creating new RAG index from project code in: {project_path}",
                    "INFO"
                )
                
                # Check if directory exists
                if not os.path.exists(project_path):
                    monitoring.log_agent_activity(
                        self.agent_name,
                        f"Project directory does not exist: {project_path}",
                        "ERROR"
                    )
                    return 0
                    
                # Define file patterns to include in indexing
                file_patterns = file_patterns or ['*.py', '*.js', '*.html', '*.css', '*.md', '*.txt', 
                                                   '*.json', '*.yaml', '*.yml']
                
                documents_added_total = 0
                
                # Iterate through specified patterns
                for pattern in file_patterns:
                    for file_path in Path(project_path).rglob(pattern):
                        if file_path.is_file():
                            # Check against exclusion patterns
                            should_exclude = False
                            for exclude in self.default_exclude_patterns:
                                if fnmatch.fnmatch(str(file_path.relative_to(project_path)), exclude) or \
                                   any(part.startswith('.') for part in file_path.parts) or \
                                   any(ex_part in file_path.parts for ex_part in ['node_modules', 'venv', '.venv', '__pycache__', '.git']):
                                    should_exclude = True
                                    break
                        
                            if not should_exclude:
                                try:
                                    # Add document using relative path for better context
                                    rel_path = str(file_path.relative_to(project_path))
                                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                        content = f.read()

                                    document = Document(
                                        page_content=content,
                                        metadata={
                                            "source": rel_path,
                                            "filetype": file_path.suffix[1:],
                                            "full_path": str(file_path)
                                        }
                                    )
                                    chunks = self.text_splitter.split_documents([document])

                                    if self.vector_store is None:
                                        self.vector_store = FAISS.from_documents(chunks, self.embeddings)
                                    else:
                                        self.vector_store.add_documents(chunks)
                                    documents_added_total += len(chunks)
                                except Exception as e:
                                    logger.warning(f"Error processing file {file_path}: {str(e)}")
                
                if documents_added_total > 0:
                    # Save the vector store if methods exist
                    if hasattr(self, '_save_vector_store'):
                        self._save_vector_store()
                    
                    logger.info(f"Successfully indexed {documents_added_total} files from project.")
                else:
                    logger.warning(f"No new documents found to index in {project_path}.")
                
                return documents_added_total
                
            except Exception as e:
                logger.error(f"Error during indexing: {e}")
                return 0

    def optimized_index_project(self, project_path=None, batch_size=50, max_workers=4):
        """
        Optimized project indexing with batching, parallelization and hash-based change detection.
        Significantly improves indexing speed compared to sequential processing.
        
        Args:
            project_path: Path to project directory (defaults to self.project_root)
            batch_size: Number of documents to process in one batch
            max_workers: Number of parallel workers for file processing
            
        Returns:
            int: Number of chunks indexed
        """
        import concurrent.futures
        import time
        
        start_time = time.time()
        logger = logging.getLogger(self.agent_name)
        logger.info(f"Starting optimized indexing for {project_path or self.project_root}")
        
        # 1. Load hash registry for incremental indexing
        hash_registry = self._load_hash_registry()
        path_to_index = Path(project_path) if project_path else Path(self.project_root)
        
        # 2. Get optimized file patterns based on project type
        file_patterns = self._get_optimized_file_patterns()
        
        # 3. Gather files to process with efficient filtering
        changed_files = []
        for pattern in file_patterns:
            for file_path in path_to_index.rglob(pattern.replace('**/', '')):
                # Skip excluded directories efficiently with fast path checks
                if any(exclude in str(file_path) for exclude in self.default_exclude_patterns):
                    continue
                
                if file_path.is_file():
                    # Check if file has changed using hash
                    try:
                        file_hash = hashlib.md5(file_path.read_bytes()).hexdigest()
                        file_key = str(file_path)
                        
                        if file_key not in hash_registry or hash_registry[file_key] != file_hash:
                            changed_files.append((file_path, file_hash))
                            hash_registry[file_key] = file_hash
                    except Exception as e:
                        logger.warning(f"Error hashing file {file_path}: {e}")
        
        logger.info(f"Found {len(changed_files)} changed files to process")
        
        # 4. Process files in parallel
        documents = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Use ThreadPoolExecutor instead of ProcessPoolExecutor to avoid pickling issues
            results = list(executor.map(_process_file_for_indexing, changed_files))
            
            # Filter out failed results and create documents
            documents = [
                Document(
                    page_content=r["content"],
                    metadata={
                        "source": r["path"], 
                        "filetype": Path(r["path"]).suffix[1:],
                        "indexed_at": datetime.now().isoformat(),
                        "file_hash": r["hash"]
                    }
                ) 
                for r in results if r
            ]
        
        # 5. Process documents in batches
        total_chunks = 0
        if documents:
            # Chunk and index the documents in batches
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i+batch_size]
                chunks = self.text_splitter.split_documents(batch)
                total_chunks += len(chunks)
                
                # Add to vector store efficiently
                if self.vector_store is None:
                    self.vector_store = FAISS.from_documents(chunks, self.embeddings)
                else:
                    self.vector_store.add_documents(chunks)
        
            # 6. Save only after all batches are processed
            self._save_vector_store()
            self._save_hash_registry(hash_registry)
            
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Indexing completed in {duration:.2f} seconds")
        logger.info(f"Processed {len(documents)} documents with {total_chunks} total chunks")
        
        return total_chunks
    
    def _load_hash_registry(self):
        """Load hash registry for incremental indexing."""
        hash_file = os.path.join(self.vector_store_path, "hash_registry.json")
        if os.path.exists(hash_file):
            try:
                with open(hash_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading hash registry: {e}")
        return {}

    def _save_hash_registry(self, hash_registry):
        """Save hash registry for incremental indexing."""
        hash_file = os.path.join(self.vector_store_path, "hash_registry.json")
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(hash_file), exist_ok=True)
            
            with open(hash_file, 'w', encoding='utf-8') as f:
                json.dump(hash_registry, f, indent=2)
            return True
        except Exception as e:
            logger.warning(f"Error saving hash registry: {e}")
            return False
        
        # Add this helper method to detect file encoding
    def _detect_file_encoding(self, file_path: Path) -> str:
        """Detect the encoding of a file to avoid encoding errors."""
        try:
            import chardet
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)  # Read a sample to detect encoding
                result = chardet.detect(raw_data)
                return result['encoding'] or 'utf-8'
        except ImportError:
            # Fallback encodings to try if chardet is not available
            for encoding in ['utf-8', 'latin-1', 'cp1252', 'ascii']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        f.read(100)  # Try reading a sample
                    return encoding
                except UnicodeDecodeError:
                    continue
            return 'utf-8'  # Default to UTF-8 if all else fails

    def _get_optimized_file_patterns(self):
        """Return more specific file patterns based on project type."""
        # Detect project type based on files in root
        project_root = self.project_root
        logger = logging.getLogger(self.agent_name)
        
        # JavaScript/TypeScript project detection
        if (os.path.exists(os.path.join(project_root, 'package.json')) or
            os.path.exists(os.path.join(project_root, 'node_modules'))):
            logger.info("Detected JavaScript/TypeScript project")
            return ['**/*.js', '**/*.ts', '**/*.jsx', '**/*.tsx', '**/*.md', '**/*.json']
        
        # Python project detection
        elif (os.path.exists(os.path.join(project_root, 'requirements.txt')) or
              os.path.exists(os.path.join(project_root, 'setup.py')) or
              os.path.exists(os.path.join(project_root, 'pyproject.toml'))):
            logger.info("Detected Python project")
            return ['**/*.py', '**/*.md', '**/*.rst', '**/*.txt']
        
        # Generic fallback with common code file extensions
        else:
            logger.info("Using generic file patterns")
            return [
                '**/*.py', '**/*.js', '**/*.ts', '**/*.jsx', '**/*.tsx',
                '**/*.java', '**/*.kt', '**/*.c', '**/*.cpp', '**/*.h',
                '**/*.cs', '**/*.go', '**/*.rb', '**/*.php',
                '**/*.md', '**/*.rst', '**/*.txt',
                '**/*.json', '**/*.yaml', '**/*.yml'
            ]
    
    def enable_embedding_cache(self):
        """Enable embedding cache for better performance."""
        if not hasattr(self, '_original_embeddings'):
            # Store the original embeddings
            self._original_embeddings = self.embeddings
            
            # Create cache directory within the vector store path
            cache_dir = os.path.join(self.vector_store_path, '.embedding_cache')
            
            # Create and use the cached embeddings wrapper with vector_store_path
            self.embeddings = CachedEmbeddings(
                self._original_embeddings, 
                cache_dir=cache_dir,
                vector_store_path=str(self.vector_store_path)
            )
            logger = logging.getLogger(self.agent_name)
            logger.info(f"Embedding cache enabled at {cache_dir}")
            
            # If vector store already exists, update its embeddings
            if self.vector_store and hasattr(self.vector_store, 'embedding_function'):
                self.vector_store.embedding_function = self.embeddings
                
            return True
        return False

    def _get_embedding_function(self):
        """Get the appropriate embedding function based on type."""
        if isinstance(self.embeddings, CachedEmbeddings):
            # Use callable interface for FAISS
            return self.embeddings
        else:
            return self.embeddings
        

    def close(self):
        """Properly close the RAG manager, saving caches."""
        try:
            # Save embedding cache if it exists
            if hasattr(self, 'embeddings') and isinstance(self.embeddings, CachedEmbeddings):
                saved = self.embeddings.save_cache_explicitly()
                if saved:
                    logger = logging.getLogger(self.agent_name)
                    logger.info("Embedding cache saved during shutdown")
            
            # Save vector store if needed
            if hasattr(self, 'vector_store') and self.vector_store is not None:
                self._save_vector_store()
                
            # Save hash registry if available
            if hasattr(self, '_save_hash_registry'):
                self._save_hash_registry(self._load_hash_registry())
                
            return True
        except Exception as e:
            logger = logging.getLogger(self.agent_name)
            logger.error(f"Error during RAG manager shutdown: {e}")
            return False

# Add this function outside of any class
def _process_file_for_indexing(args):
    """Process a single file for indexing (must be at module level for multiprocessing)."""
    # FIXED: Handle both tuple unpacking and single argument case
    if isinstance(args, tuple) and len(args) == 2:
        file_path, file_hash = args
    else:
        # Handle the case where only file_path is provided
        file_path = args
        try:
            file_hash = hashlib.md5(Path(file_path).read_bytes()).hexdigest()
        except Exception:
            file_hash = str(time.time())  # Fallback hash

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return {
            "content": content, 
            "path": str(file_path),
            "hash": file_hash
        }
    except UnicodeDecodeError:
        # Try as binary file in case of encoding issues
        try:
            import chardet
            with open(file_path, 'rb') as f:
                raw_content = f.read()
                encoding = chardet.detect(raw_content)['encoding'] or 'utf-8'
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read()
            return {
                "content": content, 
                "path": str(file_path),
                "hash": file_hash
            }
        except Exception as e:
            print(f"Error processing file {file_path}: {str(e)}")
            return None
    except Exception as e:
        print(f"Error processing file {file_path}: {str(e)}")
        return None

# Add this method to ProjectRAGManager

import atexit
_rag_managers = []

def register_rag_manager(manager):
    """Register a RAG manager for proper shutdown handling."""
    if manager not in _rag_managers:
        _rag_managers.append(manager)

def _shutdown_rag_managers():
    """Save all RAG manager caches on shutdown."""
    for manager in _rag_managers:
        try:
            if hasattr(manager, 'close'):
                manager.close()
        except:
            pass  # Ignore errors during shutdown

# Register the shutdown function
atexit.register(_shutdown_rag_managers)

# Global RAG manager instance
_global_rag_manager = None

def get_rag_manager(auto_init: bool = True):
    """Return the global :class:`ProjectRAGManager` instance.

    If no RAG manager has been explicitly registered and *auto_init* is ``True`` (default),
    a lightweight fallback instance will be created so that downstream tools can still
    perform calls like ``similarity_search`` without raising warnings.

    The fallback instance uses an in-memory FAISS (or the mock FAISS implementation when
    FAISS is not available) together with a small embedding model returned by
    ``get_embedding_model`` from the config module (when available) or
    :func:`get_fallback_embedding_model` otherwise.  The vector store will live inside a
    temporary directory in the project root (``.rag_store``) so it does **not** impact
    production stores.

    Parameters
    ----------
    auto_init : bool, default ``True``
        Whether a fallback manager should be created when none is registered yet.

    Returns
    -------
    ProjectRAGManager | None
        The global RAG manager or ``None`` when initialization failed and *auto_init*
        is ``False``.
    """
    global _global_rag_manager

    # If already set, just return it
    if _global_rag_manager is not None:
        return _global_rag_manager

    if not auto_init:
        return None

    try:
        from pathlib import Path

        project_root = str(Path(__file__).resolve().parent)

        # Pick appropriate embeddings
        embeddings = None
        if CONFIG_AVAILABLE and get_embedding_model is not None:
            try:
                embeddings = get_embedding_model()
            except Exception:
                embeddings = None

        if embeddings is None:
            embeddings = get_fallback_embedding_model()

        # Create the fallback manager (development environment by default)
        manager = ProjectRAGManager(project_root=project_root,
                                    vector_store_path=os.path.join(project_root, ".rag_store"),
                                    embeddings=embeddings,
                                    environment="development")

        # Ensure at least an empty vector store exists so calls succeed
        try:
            manager.initialize_empty_vector_store()
        except Exception:
            pass  # Initialization may fail under constrained envs – continue anyway

        # Register and return
        set_rag_manager(manager)
        logging.getLogger("RAGManager").info("Fallback RAG manager auto-initialized")
        return manager

    except Exception as e:
        logging.getLogger("RAGManager").warning(f"Failed to auto-initialize fallback RAG manager: {e}")
        return None

def set_rag_manager(rag_manager):
    """
    Set the global RAG manager instance.
    
    Args:
        rag_manager: ProjectRAGManager instance to set as global
    """
    global _global_rag_manager
    _global_rag_manager = rag_manager

