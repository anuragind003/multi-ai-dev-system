import logging
import os
import zipfile
from typing import Generator

logger = logging.getLogger(__name__)

def read_file_in_chunks(file_path: str, chunk_size: int = 8192) -> Generator[bytes, None, None]:
    """
    Reads a file in chunks for efficient streaming.
    Yields bytes chunks.
    """
    try:
        with open(file_path, mode="rb") as file_like:
            while chunk := file_like.read(chunk_size):
                yield chunk
        logger.debug(f"Finished streaming file: {file_path}")
    except FileNotFoundError:
        logger.error(f"File not found for streaming: {file_path}")
        raise
    except IOError as e:
        logger.error(f"Error reading file in chunks: {file_path} - {e}", exc_info=True)
        raise

def get_file_size(file_path: str) -> int:
    """
    Returns the size of a file in bytes.
    Raises FileNotFoundError if the file does not exist.
    """
    try:
        size = os.path.getsize(file_path)
        logger.debug(f"File size of '{file_path}': {size} bytes")
        return size
    except FileNotFoundError:
        logger.error(f"File not found when trying to get size: {file_path}")
        raise
    except OSError as e:
        logger.error(f"OS error getting file size for '{file_path}': {e}", exc_info=True)
        raise

def safe_delete_file(file_path: str):
    """
    Safely deletes a file, logging any errors.
    Intended for use in background tasks.
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Successfully deleted temporary file: {file_path}")
        else:
            logger.warning(f"Attempted to delete non-existent file: {file_path}")
    except OSError as e:
        logger.error(f"Error deleting temporary file '{file_path}': {e}", exc_info=True)

def create_zip_archive(file_paths: list[str], output_zip_path: str) -> str:
    """
    Helper function to create a ZIP archive from a list of file paths.
    This is a generic utility, the service layer handles the specific logic.
    """
    try:
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    logger.warning(f"File not found, skipping: {file_path}")
                    continue
                # Add file to ZIP, using its base name as the archive name
                zf.write(file_path, arcname=os.path.basename(file_path))
                logger.debug(f"Added '{file_path}' to ZIP.")
        logger.info(f"ZIP archive created at: {output_zip_path}")
        return output_zip_path
    except Exception as e:
        logger.error(f"Failed to create ZIP archive at {output_zip_path}: {e}", exc_info=True)
        raise