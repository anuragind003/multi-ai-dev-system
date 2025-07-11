### FILE: utils/helpers.py
import os
import re
import asyncio
from typing import AsyncGenerator
from utils.logger import logger
from utils.exceptions import FileAccessException

def sanitize_filename(filename: str) -> str:
    """
    Sanitizes a filename to prevent directory traversal and invalid characters.
    Replaces potentially problematic characters with underscores.
    """
    # Remove any directory traversal attempts
    filename = os.path.basename(filename)
    # Replace invalid characters with underscores
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces or dots
    filename = filename.strip(' .')
    # Ensure it's not empty after sanitization
    if not filename:
        return "sanitized_file"
    return filename

async def file_streamer(file_path: str, chunk_size: int = 8192) -> AsyncGenerator[bytes, None]:
    """
    Asynchronously streams a file in chunks.
    Handles file opening and closing, and potential IO errors.
    """
    try:
        # Use asyncio.to_thread for blocking file I/O to not block the event loop
        # This is crucial for performance in an async application like FastAPI
        def read_chunk():
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

        for chunk in await asyncio.to_thread(read_chunk):
            yield chunk
        logger.info(f"Successfully streamed file: {file_path}")
    except FileNotFoundError:
        logger.error(f"File not found for streaming: {file_path}")
        raise FileAccessException(detail=f"File not found: {os.path.basename(file_path)}")
    except PermissionError:
        logger.error(f"Permission denied to access file: {file_path}")
        raise FileAccessException(detail=f"Permission denied to access file: {os.path.basename(file_path)}")
    except Exception as e:
        logger.error(f"Error streaming file {file_path}: {e}", exc_info=True)
        raise FileAccessException(detail=f"An error occurred while streaming file: {os.path.basename(file_path)}")