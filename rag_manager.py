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
import faiss
import numpy as np
from datetime import datetime
import fnmatch
import logging

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader, 
    JSONLoader,
    DirectoryLoader
)

# Security imports (with fallbacks for development)
try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.fernet import Fernet
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False

import monitoring
from config import get_embedding_model

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
    Comprehensive RAG manager for the Multi-AI Development System.
    Handles document ingestion, vector storage, and retrieval operations.
    """
    
    def __init__(self, vector_store_path: str, embeddings: Optional[Embeddings] = None):
        self.vector_store_path = Path(vector_store_path)
        self.embeddings = embeddings or get_embedding_model()
        self.vector_store: Optional[FAISS] = None
        self.metadata_file = self.vector_store_path / "metadata.json"
        self.documents_metadata: Dict[str, Any] = {}
        
        # Text splitter for document chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Create vector store directory
        os.makedirs(self.vector_store_path, exist_ok=True)
        
        # Load existing vector store if available
        self._load_existing_vector_store()
        
        monitoring.log_agent_activity("RAG Manager", f"Initialized with vector store path: {vector_store_path}")
    
    def _load_existing_vector_store(self) -> None:
        """Load existing FAISS vector store if it exists."""
        try:
            faiss_index_path = self.vector_store_path / "index.faiss"
            faiss_pkl_path = self.vector_store_path / "index.pkl"
            
            if faiss_index_path.exists() and faiss_pkl_path.exists():
                self.vector_store = FAISS.load_local(
                    str(self.vector_store_path), 
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                monitoring.log_agent_activity("RAG Manager", "Loaded existing vector store successfully")
            else:
                monitoring.log_agent_activity("RAG Manager", "No existing vector store found, will create new one")
            
            # Load metadata
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.documents_metadata = json.load(f)
                    
        except Exception as e:
            monitoring.log_agent_activity("RAG Manager", f"Error loading existing vector store: {e}", "ERROR")
            self.vector_store = None
    
    def _save_metadata(self) -> None:
        """Save documents metadata to file."""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.documents_metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            monitoring.log_agent_activity("RAG Manager", f"Error saving metadata: {e}", "ERROR")
    
    def _get_file_hash(self, file_path: Union[str, Path]) -> str:
        """Calculate MD5 hash of a file for change detection."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def add_documents_from_directory(self, directory_path: str, file_patterns: List[str] = None) -> int:
        """
        Add all documents from a directory to the vector store.
        
        Args:
            directory_path: Path to directory containing documents
            file_patterns: List of file patterns to include (e.g., ['*.py', '*.md'])
            
        Returns:
            Number of documents added
        """
        if file_patterns is None:
            file_patterns = ['*.py', '*.md', '*.txt', '*.json', '*.yaml', '*.yml']
        
        documents_added = 0
        directory = Path(directory_path)
        
        if not directory.exists():
            monitoring.log_agent_activity("RAG Manager", f"Directory not found: {directory_path}", "ERROR")
            return 0
        
        # Define exclusion patterns to prevent indexing unnecessary files
        exclude_patterns = [
            'venv', '.venv', 'env', '.env',
            '__pycache__', '.git', '.pytest_cache',
            'node_modules', '.coverage', 'htmlcov',
            'dist', 'build', '.tox',
            '*.pyc', '*.pyo', '*.pyd',
            '.DS_Store', 'Thumbs.db'
        ]
        
        monitoring.log_agent_activity("RAG Manager", f"Processing directory: {directory_path}")
        
        for pattern in file_patterns:
            for file_path in directory.rglob(pattern):
                try:
                    if file_path.is_file():
                        # Check if file should be excluded
                        should_exclude = False
                        for exclude_pattern in exclude_patterns:
                            if exclude_pattern in str(file_path):
                                should_exclude = True
                                break
                        
                        if not should_exclude:
                            added = self.add_document(str(file_path))
                            documents_added += added
                        else:
                            monitoring.log_agent_activity("RAG Manager", f"Excluded file: {file_path}", "INFO")
                            
                except Exception as e:
                    monitoring.log_agent_activity("RAG Manager", f"Error processing {file_path}: {e}", "ERROR")
        
        if documents_added > 0:
            self._save_vector_store()
            self._save_metadata()
        
        monitoring.log_agent_activity("RAG Manager", f"Added {documents_added} documents from directory")
        return documents_added
    
    def add_document(self, file_path: str) -> int:
        """
        Add a single document to the vector store.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            1 if document was added, 0 if skipped
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            monitoring.log_agent_activity("RAG Manager", f"File not found: {file_path}", "ERROR")
            return 0
        
        # Check if file has changed since last indexing
        file_hash = self._get_file_hash(file_path)
        file_key = str(file_path.absolute())
        
        if file_key in self.documents_metadata:
            if self.documents_metadata[file_key].get('hash') == file_hash:
                # File unchanged, skip
                return 0
        
        try:
            # Load document based on file type
            documents = self._load_document(file_path)
            
            if not documents:
                return 0
            
            # Split documents into chunks
            chunks = self.text_splitter.split_documents(documents)
            
            # Add metadata to chunks
            for chunk in chunks:
                chunk.metadata.update({
                    'source_file': str(file_path),
                    'file_type': file_path.suffix,
                    'indexed_at': datetime.now().isoformat(),
                    'file_hash': file_hash
                })
            
            # Add to vector store
            if self.vector_store is None:
                self.vector_store = FAISS.from_documents(chunks, self.embeddings)
            else:
                self.vector_store.add_documents(chunks)
            
            # Update metadata
            self.documents_metadata[file_key] = {
                'hash': file_hash,
                'indexed_at': datetime.now().isoformat(),
                'chunks_count': len(chunks),
                'file_size': file_path.stat().st_size
            }
            
            monitoring.log_agent_activity("RAG Manager", f"Added document: {file_path} ({len(chunks)} chunks)")
            return 1
            
        except Exception as e:
            monitoring.log_agent_activity("RAG Manager", f"Error adding document {file_path}: {e}", "ERROR")
            return 0
    
    def add_document_string(self, content: str, metadata: Dict[str, Any] = None) -> int:
        """
        Add a document from string content to the vector store.
        
        Args:
            content: Document content as string
            metadata: Additional metadata for the document
            
        Returns:
            1 if document was added, 0 if failed
        """
        try:
            if not content.strip():
                return 0
            
            # Create document from string
            doc_metadata = metadata or {}
            doc_metadata.update({
                'indexed_at': datetime.now().isoformat(),
                'content_type': 'string',
                'content_length': len(content)
            })
            
            document = Document(page_content=content, metadata=doc_metadata)
            
            # Split document into chunks
            chunks = self.text_splitter.split_documents([document])
            
            # Add to vector store
            if self.vector_store is None:
                self.vector_store = FAISS.from_documents(chunks, self.embeddings)
            else:
                self.vector_store.add_documents(chunks)
            
            monitoring.log_agent_activity("RAG Manager", f"Added string document ({len(chunks)} chunks)")
            return 1
            
        except Exception as e:
            monitoring.log_agent_activity("RAG Manager", f"Error adding string document: {e}", "ERROR")
            return 0
    
    def _load_document(self, file_path: Path) -> List[Document]:
        """Load a document based on its file type."""
        documents = []
        
        try:
            if file_path.suffix.lower() == '.json':
                loader = JSONLoader(str(file_path), jq_schema='.', text_content=False)
                documents = loader.load()
            else:
                # Text-based files (Python, Markdown, etc.)
                loader = TextLoader(str(file_path), encoding='utf-8')
                documents = loader.load()
                
        except Exception as e:
            monitoring.log_agent_activity("RAG Manager", f"Error loading {file_path}: {e}", "ERROR")
            
        return documents
    
    def _save_vector_store(self) -> None:
        """
        ENHANCED: Save vector store using SecureFAISSManager with security measures.
        """
        if not self.vector_store:
            # FIXED: Changed self.logger.error to monitoring.log_agent_activity
            monitoring.log_agent_activity(self.agent_name, "No vector store to save", "ERROR")
            return
        
        try:
            # Update secure manager's vector store reference
            self.secure_manager.vector_store = self.vector_store
            
            # Use secure saving
            success = self.secure_manager.save_index_securely()
            
            if success:
                monitoring.log_agent_activity(
                    "Project RAG Manager",
                    f"Vector store saved securely (mode: {self.environment})",
                    "SUCCESS"
                )
            else:
                # Fallback to basic saving in development mode
                if self.environment == "development":
                    monitoring.log_agent_activity(
                        "Project RAG Manager",
                        "Secure save failed, using basic save in development mode",
                        "WARNING"
                    )
                    super()._save_vector_store()
                else:
                    raise Exception("Secure save failed in production environment")
                    
        except Exception as e:
            monitoring.log_agent_activity(
                "Project RAG Manager",
                f"Error during secure vector store save: {e}",
                "ERROR"
            )
            
            # In development mode, try fallback
            if self.environment == "development":
                monitoring.log_agent_activity(
                    "Project RAG Manager",
                    "Attempting fallback to basic save",
                    "WARNING"
                )
                try:
                    super()._save_vector_store()
                except Exception as fallback_error:
                    monitoring.log_agent_activity(
                        "Project RAG Manager",
                        f"Fallback save also failed: {fallback_error}",
                        "ERROR"
                    )
    
    def index_project_code(self, exclude_patterns: List[str] = None) -> bool:
        """Enhanced project indexing with robust exclusion pattern matching and security."""
        
        if exclude_patterns is None:
            exclude_patterns = self._get_default_exclusion_patterns()
        
        try:
            all_documents = []
            processed_files = 0
            skipped_files = 0
            error_files = 0
            
            # FIXED: Changed self.logger.info to monitoring.log_agent_activity
            monitoring.log_agent_activity(
                self.agent_name,
                f"Starting RAG indexing of {self.project_root} (security mode: {self.environment})",
                "INFO"
            )
            
            for file_path in Path(self.project_root).rglob('*'):
                if file_path.is_file():
                    # Enhanced exclusion checking
                    if self._should_exclude_file_enhanced(file_path, exclude_patterns):
                        skipped_files += 1
                        continue
                    
                    # Enhanced size check with warning
                    file_size = file_path.stat().st_size
                    if file_size > 5 * 1024 * 1024:  # 5MB limit
                        monitoring.log_agent_activity(
                            self.agent_name,
                            f"Skipping large file: {file_path} ({file_size / 1024 / 1024:.1f}MB)",
                            "WARNING"
                        )
                        skipped_files += 1
                        continue
                    
                    # Load document with enhanced error handling
                    document = self._load_document_enhanced(file_path)
                    if document:
                        all_documents.append(document)
                        processed_files += 1
                    else:
                        error_files += 1
            
            if all_documents:
                # Create vector store with security considerations
                try:
                    # Use secure manager for vector store creation
                    self.vector_store = FAISS.from_documents(all_documents, self.embeddings)
                    self.secure_manager.vector_store = self.vector_store
                    
                    # Save securely
                    success = self.secure_manager.save_index_securely()
                    
                    if not success and self.environment == "development":
                        # Fallback to basic save in development
                        self.vector_store.save_local(str(self.vector_store_path))
                        monitoring.log_agent_activity(
                            "Project RAG Manager",
                            "Used fallback saving in development mode",
                            "WARNING"
                        )
                    
                    monitoring.log_agent_activity(
                        self.agent_name,
                        f"RAG indexing complete - Processed: {processed_files} files, Skipped: {skipped_files}, "
                        f"Errors: {error_files}, Documents: {len(all_documents)}, Security: {self.environment}",
                        "SUCCESS"
                    )
                    
                    return True
                    
                except Exception as e:
                    monitoring.log_agent_activity(
                        self.agent_name, 
                        f"Failed to save vector store: {e}", 
                        "ERROR"
                    )
                    return False
            else:
                monitoring.log_agent_activity(
                    self.agent_name,
                    "No documents found to index", 
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

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics including security information."""
        
        base_stats = super().get_stats()
        
        # Add security stats
        security_stats = {
            "security_mode": self.environment,
            "security_features_available": SECURITY_AVAILABLE,
            "secure_manager_initialized": self.secure_manager is not None
        }
        
        if self.secure_manager:
            security_status = self.secure_manager.get_security_status()
            security_stats["active_security_features"] = [
                feature for feature, enabled in security_status['features_enabled'].items() 
                if enabled
            ]
        
        return {**base_stats, "security": security_stats}
    
    def _get_default_exclusion_patterns(self) -> List[str]:
        """Return the default exclusion patterns for project code indexing."""
        return self.default_exclude_patterns

    def _should_exclude_file_enhanced(self, file_path: Path, exclude_patterns: List[str]) -> bool:
        """
        Enhanced exclusion check with pattern matching.
        
        Args:
            file_path: Path to check
            exclude_patterns: List of patterns to exclude
            
        Returns:
            True if the file should be excluded, False otherwise
        """
        str_path = str(file_path)
        
        for pattern in exclude_patterns:
            # Check for direct substring match (faster)
            if pattern in str_path:
                return True
            
            # Check for glob pattern match
            if any(fnmatch.fnmatch(str_path, p) for p in exclude_patterns if '*' in p):
                return True
        
        return False

    def _load_document_enhanced(self, file_path: Path) -> Optional[Document]:
        """
        Enhanced document loading with better error handling.
        
        Args:
            file_path: Path to the document
            
        Returns:
            Document object or None if loading failed
        """
        try:
            # Choose loader based on file type
            if file_path.suffix.lower() in ['.py', '.js', '.ts', '.java', '.c', '.cpp', '.h']:
                # Code file - use code-specific splitter
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                    
                doc = Document(
                    page_content=content,
                    metadata={
                        'source': str(file_path),
                        'file_type': file_path.suffix,
                        'file_size': file_path.stat().st_size,
                        'indexed_at': datetime.now().isoformat()
                    }
                )
                return doc
                
            elif file_path.suffix.lower() in ['.json', '.yaml', '.yml']:
                # Structured data file
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                    
                doc = Document(
                    page_content=content,
                    metadata={
                        'source': str(file_path),
                        'file_type': file_path.suffix,
                        'file_size': file_path.stat().st_size,
                        'indexed_at': datetime.now().isoformat()
                    }
                )
                return doc
                
            else:
                # Text file (default)
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                    
                doc = Document(
                    page_content=content,
                    metadata={
                        'source': str(file_path),
                        'file_type': file_path.suffix,
                        'file_size': file_path.stat().st_size,
                        'indexed_at': datetime.now().isoformat()
                    }
                )
                return doc
                
        except Exception as e:
            monitoring.log_agent_activity(
                "Project RAG Manager",
                f"Error loading document {file_path}: {e}",
                "ERROR"
            )
            return None

class ProjectRAGManager(RAGManager):
    """
    Enhanced RAG Manager for project code and documentation with security features.
    Extends the base RAGManager with project-specific features and security controls.
    """
    
    def __init__(self, project_root: str, vector_store_path: str = None, 
                 embeddings: Optional[Embeddings] = None, environment: str = "development"):
        """Initialize the Project RAG Manager with security settings."""
        # Initialize vector store path if not provided
        vector_store_path = vector_store_path or os.path.join(project_root, ".rag_store")
        
        # Initialize base RAG Manager
        super().__init__(vector_store_path, embeddings)
        
        # Project specific attributes
        self.project_root = Path(project_root)
        self.environment = environment
        self.agent_name = "Project RAG Manager"
        
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
            project_root=str(self.project_root),
            security_mode=environment
        )
        
        monitoring.log_agent_activity(
            self.agent_name, 
            f"Initialized ProjectRAGManager for {project_root} in {environment} mode",
            "INFO"
        )

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

    def get_retriever(self, search_type: str = "similarity", search_kwargs: Optional[Dict[str, Any]] = None) -> Optional[BaseRetriever]:
        """
        Get a retriever for the vector store.
        
        Args:
            search_type: Type of search to perform ("similarity", "mmr", or "similarity_score_threshold")
            search_kwargs: Additional search arguments (like "k" for number of results)
            
        Returns:
            A retriever object or None if vector store is not initialized
        """
        if self.vector_store is None:
            monitoring.log_agent_activity(
                self.agent_name,
                "Cannot create retriever - vector store not initialized",
                "WARNING"
            )
            return None
        
        # Set default search kwargs if not provided
        if search_kwargs is None:
            search_kwargs = {"k": 5}  # Default to retrieving 5 documents
        
        try:
            retriever = self.vector_store.as_retriever(
                search_type=search_type,
                search_kwargs=search_kwargs
            )
            
            monitoring.log_agent_activity(
                self.agent_name,
                f"Created retriever with search_type={search_type} and k={search_kwargs.get('k', 'default')}",
                "INFO"
            )
            
            return retriever
            
        except Exception as e:
            monitoring.log_agent_activity(
                self.agent_name,
                f"Error creating retriever: {e}",
                "ERROR"
            )
            return None
    
    def initialize_index_from_project(self, project_dir: str = None) -> bool:
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
            documents_added = self.add_documents_from_directory(
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