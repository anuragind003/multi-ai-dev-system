import os
from PyPDF2 import PdfReader
from docx import Document

class DocumentParser:
    """
    A tool to parse and extract text content from various document formats.
    """
    def parse_document(self, file_path: str) -> str:
        """
        Parses a document (txt, md, pdf, docx) and returns its text content.
        Raises ValueError if the file type is unsupported or if parsing fails.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document not found at: {file_path}")

        file_extension = os.path.splitext(file_path)[1].lower()

        if file_extension in ['.txt', '.md']:
            return self._read_text_file(file_path)
        elif file_extension == '.pdf':
            return self._read_pdf_file(file_path)
        elif file_extension == '.docx':
            return self._read_docx_file(file_path)
        else:
            raise ValueError(f"Unsupported document format: {file_extension}. "
                             "Supported formats: .txt, .md, .pdf, .docx")

    def _read_text_file(self, file_path: str) -> str:
        """Reads content from a plain text or markdown file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise IOError(f"Error reading text/markdown file {file_path}: {e}")

    def _read_pdf_file(self, file_path: str) -> str:
        """Reads content from a PDF file."""
        text_content = []
        try:
            reader = PdfReader(file_path)
            for page in reader.pages:
                text_content.append(page.extract_text())
            return "\n".join(text_content)
        except Exception as e:
            raise IOError(f"Error reading PDF file {file_path}: {e}. "
                          "Ensure it's a valid PDF and not password protected.")

    def _read_docx_file(self, file_path: str) -> str:
        """Reads content from a DOCX (Word) file."""
        text_content = []
        try:
            document = Document(file_path)
            for paragraph in document.paragraphs:
                text_content.append(paragraph.text)
            return "\n".join(text_content)
        except Exception as e:
            raise IOError(f"Error reading DOCX file {file_path}: {e}. "
                          "Ensure it's a valid .docx file and not an older .doc format.")