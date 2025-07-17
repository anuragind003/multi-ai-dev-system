import logging
import os
import aiofiles
from pathlib import Path
from typing import AsyncGenerator, Tuple, Optional

from core.exceptions import NotFoundException, BadRequestException, ServiceUnavailableException, ForbiddenException

logger = logging.getLogger(__name__)

class FileService:
    """
    Service layer for handling file operations, specifically streaming from NFS.
    """
    def __init__(self, base_path: str):
        self.base_path = Path(base_path).resolve()
        if not self.base_path.is_dir():
            logger.error(f"NFS base path does not exist or is not a directory: {self.base_path}")
            # In a real scenario, this might indicate a critical deployment issue
            # For now, we'll log and let subsequent file operations fail gracefully.
            # raise ServiceUnavailableException(f"NFS base path not found: {self.base_path}")

    async def stream_file_chunked(
        self,
        file_path: Path,
        start_byte: int = 0,
        end_byte: Optional[int] = None,
        chunk_size: int = 1024 * 1024 # 1 MB
    ) -> AsyncGenerator[bytes, None]:
        """
        Asynchronously streams a file in chunks, supporting byte range requests.
        Ensures the file path is within the configured base path for security.
        """
        absolute_file_path = file_path.resolve()

        # Security check: Ensure the requested file is within the allowed base path
        if not absolute_file_path.is_relative_to(self.base_path):
            logger.error(f"Attempted to stream file outside base path: {absolute_file_path}")
            raise ForbiddenException("Access to specified file path is forbidden.")

        if not absolute_file_path.exists():
            logger.warning(f"File not found for streaming: {absolute_file_path}")
            raise NotFoundException(f"File not found at {absolute_file_path}")
        
        if not absolute_file_path.is_file():
            logger.warning(f"Path is not a file: {absolute_file_path}")
            raise BadRequestException(f"Path {absolute_file_path} is not a file.")

        try:
            file_size = absolute_file_path.stat().st_size
            if end_byte is None or end_byte >= file_size:
                end_byte = file_size - 1

            if start_byte < 0 or start_byte > end_byte:
                logger.warning(f"Invalid byte range for streaming: start={start_byte}, end={end_byte}, size={file_size}")
                raise BadRequestException("Invalid byte range specified for file streaming.")

            logger.info(f"Streaming file {absolute_file_path} from byte {start_byte} to {end_byte}")
            async with aiofiles.open(absolute_file_path, mode="rb") as f:
                await f.seek(start_byte)
                bytes_read = 0
                total_bytes_to_read = end_byte - start_byte + 1

                while bytes_read < total_bytes_to_read:
                    read_size = min(chunk_size, total_bytes_to_read - bytes_read)
                    chunk = await f.read(read_size)
                    if not chunk:
                        break # End of file
                    yield chunk
                    bytes_read += len(chunk)
            logger.info(f"Finished streaming file {absolute_file_path}.")
        except FileNotFoundError:
            logger.error(f"File not found during streaming: {absolute_file_path}", exc_info=True)
            raise NotFoundException(f"File not found at {absolute_file_path}")
        except PermissionError:
            logger.error(f"Permission denied to access file: {absolute_file_path}", exc_info=True)
            raise ForbiddenException(f"Permission denied to access file at {absolute_file_path}")
        except IOError as e:
            logger.error(f"IOError during file streaming for {absolute_file_path}: {e}", exc_info=True)
            raise ServiceUnavailableException(f"Failed to read file from storage: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during file streaming for {absolute_file_path}: {e}", exc_info=True)
            raise ServiceUnavailableException("An unexpected error occurred during file streaming.")

    def parse_range_header(self, range_header: str, file_size: int) -> Tuple[Optional[int], Optional[int]]:
        """
        Parses a HTTP Range header (e.g., "bytes=0-1023") into start and end bytes.
        Returns (start, end) tuple.
        """
        if not range_header or not range_header.startswith("bytes="):
            return None, None
        
        range_str = range_header.split("=")[1]
        parts = range_str.split("-")
        
        try:
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
        except ValueError:
            logger.warning(f"Invalid range header format: {range_header}")
            return None, None

        # Ensure valid range
        start = max(0, start)
        end = min(file_size - 1, end)

        if start > end:
            logger.warning(f"Invalid range: start ({start}) > end ({end}) for file size {file_size}")
            return None, None

        return start, end