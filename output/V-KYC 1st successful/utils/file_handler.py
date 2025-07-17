import os
import re
import csv
from typing import AsyncGenerator, List
import aiofiles
from exceptions import FileOperationException, NotFoundException, ValidationException, ServiceUnavailableException
from config import settings
from utils.logger import logger

class NFSFileHandler:
    """
    Handles interactions with the NFS file system for VKYC recordings.
    Provides methods for path construction, existence checks, and file streaming.
    """
    def __init__(self, base_path: str):
        self.base_path = base_path
        # Basic check for NFS mount point existence (can be more robust)
        if not os.path.exists(self.base_path):
            logger.warning(f"NFS base path '{self.base_path}' does not exist. File operations may fail.")
        elif not os.access(self.base_path, os.R_OK):
            logger.warning(f"NFS base path '{self.base_path}' is not readable. Check permissions.")

    def get_full_file_path(self, relative_path: str) -> str:
        """
        Constructs the full, absolute path to a file on the NFS server.
        Sanitizes the relative path to prevent directory traversal attacks.
        """
        # Normalize path to prevent '..' traversal
        normalized_path = os.path.normpath(relative_path)
        if normalized_path.startswith('..') or normalized_path.startswith('/'):
            raise ValidationException(f"Invalid file path format: {relative_path}")

        full_path = os.path.join(self.base_path, normalized_path)
        # Ensure the resulting path is still within the base_path
        if not full_path.startswith(self.base_path):
            raise ValidationException(f"Attempted directory traversal: {relative_path}")
        return full_path

    async def file_exists(self, relative_path: str) -> bool:
        """Checks if a file exists at the given relative path on NFS."""
        try:
            full_path = self.get_full_file_path(relative_path)
            return os.path.exists(full_path) and os.path.isfile(full_path)
        except ValidationException as e:
            logger.warning(f"File path validation failed for existence check: {e.detail}")
            return False
        except Exception as e:
            logger.error(f"Error checking file existence for {relative_path}: {e}")
            raise ServiceUnavailableException(f"Failed to check file existence: {e}")

    async def stream_file(self, relative_path: str, chunk_size: int = 8192) -> AsyncGenerator[bytes, None]:
        """
        Streams a file from the NFS server in chunks.
        Raises NotFoundException if the file does not exist.
        Raises FileOperationException for other file-related errors.
        """
        full_path = self.get_full_file_path(relative_path)
        logger.info(f"Attempting to stream file from: {full_path}")
        if not await self.file_exists(relative_path):
            logger.warning(f"File not found for streaming: {full_path}")
            raise NotFoundException(f"Recording file not found: {relative_path}")

        try:
            async with aiofiles.open(full_path, mode="rb") as f:
                while True:
                    chunk = await f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
            logger.info(f"Successfully streamed file: {full_path}")
        except PermissionError:
            logger.error(f"Permission denied to access file: {full_path}")
            raise FileOperationException(f"Permission denied to access file: {relative_path}")
        except OSError as e:
            logger.error(f"OS error during file streaming {full_path}: {e}")
            raise FileOperationException(f"Error streaming file: {relative_path} - {e}")
        except Exception as e:
            logger.critical(f"Unexpected error during file streaming {full_path}: {e}", exc_info=True)
            raise FileOperationException(f"An unexpected error occurred while streaming file: {relative_path}")

    async def read_csv_lan_ids(self, file_content: bytes) -> List[str]:
        """
        Reads LAN IDs from a CSV file content.
        Assumes CSV has a header and LAN IDs are in a column named 'LAN_ID'.
        Performs basic sanitization on read IDs.
        """
        try:
            # Decode bytes to string, assuming UTF-8
            content_str = file_content.decode('utf-8')
            # Use io.StringIO to treat string as a file
            import io
            csv_file = io.StringIO(content_str)
            reader = csv.DictReader(csv_file)

            if 'LAN_ID' not in reader.fieldnames:
                raise ValidationException("CSV must contain a 'LAN_ID' column.")

            lan_ids = []
            for row in reader:
                lan_id = row.get('LAN_ID')
                if lan_id:
                    sanitized_lan_id = self._sanitize_lan_id(lan_id)
                    if sanitized_lan_id:
                        lan_ids.append(sanitized_lan_id)
                    else:
                        logger.warning(f"Skipping invalid LAN ID during CSV read: '{lan_id}'")
            return lan_ids
        except UnicodeDecodeError:
            logger.error("Failed to decode CSV file content. Ensure it's UTF-8.")
            raise ValidationException("Invalid file encoding. Please upload a UTF-8 CSV file.")
        except csv.Error as e:
            logger.error(f"CSV parsing error: {e}")
            raise ValidationException(f"Invalid CSV file format: {e}")
        except Exception as e:
            logger.critical(f"Unexpected error reading CSV LAN IDs: {e}", exc_info=True)
            raise FileOperationException("An unexpected error occurred while processing the CSV file.")

    def _sanitize_lan_id(self, lan_id: str) -> str:
        """
        Sanitizes a LAN ID string.
        Removes leading/trailing whitespace and non-alphanumeric characters.
        """
        if not isinstance(lan_id, str):
            return ""
        sanitized = re.sub(r'[^a-zA-Z0-9]', '', lan_id).strip()
        return sanitized

# Initialize the NFS file handler
nfs_file_handler = NFSFileHandler(settings.NFS_BASE_PATH)

def get_nfs_file_handler() -> NFSFileHandler:
    """Dependency to provide the NFSFileHandler instance."""
    return nfs_file_handler