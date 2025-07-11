import os
import shutil
from typing import Generator, Optional
from pathlib import Path
from config import get_settings
from exceptions import NFSConnectionError, NFSFileNotFoundError, FileOperationError
from logger import logger

class NFSManager:
    """
    Manages interactions with the NFS server.
    Assumes the NFS share is mounted locally at NFS_MOUNT_PATH.
    """
    def __init__(self, nfs_mount_path: str):
        self.nfs_mount_path = Path(nfs_mount_path)
        self._check_nfs_mount()

    def _check_nfs_mount(self):
        """
        Checks if the NFS mount path exists and is accessible.
        Raises NFSConnectionError if not.
        """
        if not self.nfs_mount_path.exists():
            logger.error(f"NFS mount path does not exist: {self.nfs_mount_path}")
            raise NFSConnectionError(f"NFS mount path '{self.nfs_mount_path}' not found or accessible.")
        if not self.nfs_mount_path.is_dir():
            logger.error(f"NFS mount path is not a directory: {self.nfs_mount_path}")
            raise NFSConnectionError(f"NFS mount path '{self.nfs_mount_path}' is not a directory.")
        
        # Attempt to list contents to verify accessibility
        try:
            # List a few items to confirm it's not empty/unresponsive
            _ = next(os.scandir(self.nfs_mount_path), None)
            logger.info(f"NFS mount path '{self.nfs_mount_path}' is accessible.")
        except OSError as e:
            logger.critical(f"NFS mount path '{self.nfs_mount_path}' is inaccessible: {e}")
            raise NFSConnectionError(f"NFS mount path '{self.nfs_mount_path}' is inaccessible: {e}")

    def get_full_file_path(self, relative_path: str) -> Path:
        """Constructs the full, absolute path to a file on the NFS share."""
        # Ensure the relative path doesn't try to escape the mount directory
        full_path = self.nfs_mount_path / relative_path.lstrip('/')
        try:
            full_path.resolve(strict=True) # Resolve symlinks and check existence
            if not full_path.is_relative_to(self.nfs_mount_path):
                # This check prevents directory traversal attacks
                logger.warning(f"Attempted path traversal detected: {relative_path} resolves outside {self.nfs_mount_path}")
                raise NFSFileNotFoundError(f"Invalid file path: {relative_path}")
        except FileNotFoundError:
            raise NFSFileNotFoundError(f"File not found on NFS: {relative_path}")
        except Exception as e:
            logger.error(f"Error resolving NFS path {relative_path}: {e}")
            raise FileOperationError(f"Error accessing file path: {relative_path}")
        return full_path

    def check_file_exists(self, relative_path: str) -> bool:
        """Checks if a file exists at the given relative path on NFS."""
        try:
            full_path = self.get_full_file_path(relative_path)
            return full_path.is_file()
        except (NFSFileNotFoundError, FileOperationError):
            return False
        except Exception as e:
            logger.error(f"Error checking file existence for {relative_path}: {e}")
            raise FileOperationError(f"Could not check file existence for {relative_path}")

    def get_file_size(self, relative_path: str) -> int:
        """Returns the size of a file in bytes."""
        try:
            full_path = self.get_full_file_path(relative_path)
            return full_path.stat().st_size
        except FileNotFoundError:
            raise NFSFileNotFoundError(f"File not found on NFS: {relative_path}")
        except Exception as e:
            logger.error(f"Error getting file size for {relative_path}: {e}")
            raise FileOperationError(f"Could not get file size for {relative_path}")

    def get_file_stream(self, relative_path: str, chunk_size: int = 8192) -> Generator[bytes, None, None]:
        """
        Streams a file from the NFS server in chunks.
        Raises NFSFileNotFoundError if the file does not exist.
        Raises FileOperationError for other read errors.
        """
        full_path = self.get_full_file_path(relative_path)
        if not full_path.is_file():
            raise NFSFileNotFoundError(f"File not found on NFS: {relative_path}")

        try:
            with open(full_path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
            logger.info(f"Successfully streamed file: {relative_path}")
        except OSError as e:
            logger.error(f"Error reading file {relative_path} from NFS: {e}")
            raise FileOperationError(f"Failed to read file from NFS: {e}")
        except Exception as e:
            logger.exception(f"An unexpected error occurred while streaming {relative_path}")
            raise FileOperationError(f"An unexpected error occurred during file streaming: {e}")

    def list_files_in_directory(self, relative_dir_path: str = "") -> list[str]:
        """
        Lists files and directories within a specified relative directory on NFS.
        Returns a list of relative paths.
        """
        full_dir_path = self.get_full_file_path(relative_dir_path)
        if not full_dir_path.is_dir():
            raise NFSFileNotFoundError(f"Directory not found on NFS: {relative_dir_path}")

        try:
            files = []
            for entry in os.scandir(full_dir_path):
                # Only include files, not directories, and construct relative path
                if entry.is_file():
                    files.append(str(Path(relative_dir_path) / entry.name))
            logger.info(f"Listed {len(files)} files in directory: {relative_dir_path}")
            return files
        except OSError as e:
            logger.error(f"Error listing files in {relative_dir_path} from NFS: {e}")
            raise FileOperationError(f"Failed to list files from NFS: {e}")
        except Exception as e:
            logger.exception(f"An unexpected error occurred while listing files in {relative_dir_path}")
            raise FileOperationError(f"An unexpected error occurred during file listing: {e}")

    def create_temp_zip_file(self, file_paths_on_nfs: list[str], output_zip_path: Path) -> Path:
        """
        Creates a temporary zip file containing specified files from NFS.
        `file_paths_on_nfs` are the relative paths on the NFS share.
        `output_zip_path` is the full path where the zip should be created.
        """
        import zipfile
        
        if not output_zip_path.parent.exists():
            output_zip_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for relative_path in file_paths_on_nfs:
                    full_nfs_path = self.get_full_file_path(relative_path)
                    if not full_nfs_path.is_file():
                        logger.warning(f"File not found for zipping: {relative_path}")
                        continue # Skip missing files
                    
                    # Add file to zip with its base name
                    zipf.write(full_nfs_path, arcname=full_nfs_path.name)
            logger.info(f"Successfully created zip file: {output_zip_path} with {len(file_paths_on_nfs)} files.")
            return output_zip_path
        except (NFSFileNotFoundError, FileOperationError) as e:
            logger.error(f"Error during zip creation due to NFS file issue: {e}")
            raise BulkDownloadError(f"Failed to create zip file due to missing NFS file: {e.detail}")
        except Exception as e:
            logger.exception(f"An unexpected error occurred during zip file creation for {file_paths_on_nfs}")
            raise BulkDownloadError(f"An unexpected error occurred during zip file creation: {e}")