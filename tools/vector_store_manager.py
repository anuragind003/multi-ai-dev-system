import os
import shutil
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader, PyPDFLoader, Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter, Language
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from config import get_gemini_embedding_model
from langchain_core.documents import Document
import time
import google.api_core.exceptions


class VectorStoreManager:
    def __init__(self, run_dir: str):
        self.run_dir = run_dir
        self.chroma_db_path = os.path.join(self.run_dir, "chroma_db")
        os.makedirs(self.chroma_db_path, exist_ok=True)
        self.embedding_function = get_gemini_embedding_model()
        self.vectorstore = None

    def _load_existing_vector_store(self):
        """Attempts to load an existing ChromaDB from disk."""
        if os.path.exists(self.chroma_db_path) and os.listdir(self.chroma_db_path):
            print(f"Vector Store Manager: Loading existing vector store from {self.chroma_db_path}...")
            try:
                self.vectorstore = Chroma(
                    persist_directory=self.chroma_db_path,
                    embedding_function=self.embedding_function
                )
            except Exception as e:
                print(f"Error loading existing ChromaDB: {e}. Reinitializing.")
                self.vectorstore = None
                return False
        else:
            self.vectorstore = None
        return self.vectorstore is not None

    def initialize_vector_store(self, documents_raw_text: list[str], chunk_size: int = 1000, chunk_overlap: int = 200, clean_existing: bool = False):
        """
        Initializes or updates the vector store from raw text documents.
        Each string in documents_raw_text is treated as a single document for splitting.
        """
        print(f"Vector Store Manager: Initializing/Updating vector store in {self.chroma_db_path}...")
        
        if clean_existing and os.path.exists(self.chroma_db_path):
            print(f"Vector Store Manager: Cleaning existing ChromaDB at {self.chroma_db_path}...")
            shutil.rmtree(self.chroma_db_path)
            os.makedirs(self.chroma_db_path, exist_ok=True)
            self.vectorstore = None

        if self.vectorstore is None:
            self._load_existing_vector_store()
        
        docs_to_add = [Document(page_content=text) for text in documents_raw_text if text.strip()]

        if not docs_to_add:
            print("Vector Store Manager: No documents provided to initialize/add.")
            return

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
        chunks = text_splitter.split_documents(docs_to_add)
        
        max_retries = 5
        base_delay = 2 # seconds
        for attempt in range(max_retries):
            try:
                if self.vectorstore:
                    self.vectorstore.add_documents(chunks)
                else:
                    self.vectorstore = Chroma.from_documents(
                        chunks,
                        self.embedding_function,
                        persist_directory=self.chroma_db_path
                    )
                # Removed: self.vectorstore.persist() # <--- REMOVED THIS LINE
                print(f"Vector Store Manager: Added {len(chunks)} chunks to vector store. Total chunks: {self.vectorstore._collection.count()}")
                return # Success
            except google.api_core.exceptions.ResourceExhausted as e:
                delay = base_delay * (2 ** attempt)
                print(f"Vector Store Manager: Embedding quota exhausted (429). Retrying in {delay} seconds (Attempt {attempt+1}/{max_retries}). Error: {e}")
                time.sleep(delay)
            except Exception as e:
                print(f"Vector Store Manager: Error during embedding or vector store operation: {e}")
                raise
        
        print("Vector Store Manager: Failed to initialize/add documents after multiple retries due to quota exhaustion.")
        raise google.api_core.exceptions.ResourceExhausted("Failed to embed documents after retries.")


    def get_retriever(self, k: int = 7):
        """Returns a retriever for querying the vector store."""
        if self.vectorstore is None:
            if not self._load_existing_vector_store():
                self.initialize_vector_store([], clean_existing=False)
                if self.vectorstore is None:
                    raise ValueError("Vector store not initialized or not found on disk after attempting initialization.")
        return self.vectorstore.as_retriever(search_kwargs={"k": k})
    
    def add_documents_to_store(self, new_documents_raw_text: list[str], chunk_size: int = 1000, chunk_overlap: int = 200):
        """Adds new documents (raw text) to the existing vector store."""
        if not new_documents_raw_text:
            return

        if self.vectorstore is None:
            if not self._load_existing_vector_store():
                print("Vector store not initialized. Cannot add documents.")
                return
        
        docs_to_add = [Document(page_content=text) for text in new_documents_raw_text if text.strip()]
        if not docs_to_add:
            print("Vector Store Manager: No new documents to add (empty list or all empty strings).")
            return

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
        chunks = text_splitter.split_documents(docs_to_add)

        max_retries = 5
        base_delay = 2 # seconds
        for attempt in range(max_retries):
            try:
                self.vectorstore.add_documents(chunks)
                # Removed: self.vectorstore.persist() # <--- REMOVED THIS LINE
                print(f"Vector Store Manager: Added {len(chunks)} new chunks to vector store. Total chunks: {self.vectorstore._collection.count()}")
                return # Success
            except google.api_core.exceptions.ResourceExhausted as e:
                delay = base_delay * (2 ** attempt)
                print(f"Vector Store Manager: Embedding quota exhausted (429). Retrying in {delay} seconds (Attempt {attempt+1}/{max_retries}). Error: {e}")
                time.sleep(delay)
            except Exception as e:
                print(f"Vector Store Manager: Error during embedding or vector store operation: {e}")
                raise

        print("Vector Store Manager: Failed to add documents after multiple retries due to quota exhaustion.")
        raise google.api_core.exceptions.ResourceExhausted("Failed to embed new documents after retries.")