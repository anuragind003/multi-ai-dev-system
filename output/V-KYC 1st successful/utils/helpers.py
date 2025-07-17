import os
from config import settings
from utils.logger import get_logger
from core.exceptions import ServiceUnavailableException

logger = get_logger(__name__)

def resolve_nfs_path(relative_file_path: str) -> str:
    """
    Resolves a relative file path to a full path on the NFS server.
    This function simulates interaction with an NFS mount.
    In a real-world scenario, this might involve:
    - Checking if the NFS mount point is accessible.
    - Validating the file_path for security (e.g., preventing directory traversal).
    - Potentially interacting with an NFS client library or system calls.

    Args:
        relative_file_path (str): The relative path to the file (e.g., "2023/LAN12345.mp4").

    Returns:
        str: The full, absolute path to the file on the NFS mount.

    Raises:
        ServiceUnavailableException: If the NFS base path is not accessible or file not found.
        ValueError: If the relative_file_path is invalid or attempts directory traversal.
    """
    if not relative_file_path or ".." in relative_file_path or relative_file_path.startswith("/"):
        logger.error(f"Invalid relative file path provided: {relative_file_path}")
        raise ValueError("Invalid file path format. Must be a relative path without directory traversal.")

    full_path = os.path.join(settings.NFS_BASE_PATH, relative_file_path)
    
    # Simulate checking NFS mount point and file existence
    # In a real system, you'd check if settings.NFS_BASE_PATH is actually mounted
    # and then if the file exists within that mount.
    
    # For demonstration, we'll just check if the base path exists (mocked)
    # and then assume the file exists for now.
    # In production, use os.path.exists(full_path) and handle permissions.
    
    if not os.path.exists(settings.NFS_BASE_PATH):
        logger.critical(f"NFS base path '{settings.NFS_BASE_PATH}' is not accessible or does not exist.")
        raise ServiceUnavailableException(detail="NFS server is currently unreachable or not mounted.")
    
    # Simulate file existence check (remove this if you want to test actual file existence)
    # if not os.path.exists(full_path):
    #     logger.warning(f"File not found on NFS: {full_path}")
    #     raise NotFoundException(detail=f"Recording file not found at {relative_file_path}.")

    logger.debug(f"Resolved '{relative_file_path}' to full path: '{full_path}'")
    return full_path

if __name__ == "__main__":
    # Create a dummy NFS base path for testing
    dummy_nfs_path = "./temp_nfs_mount"
    os.makedirs(dummy_nfs_path, exist_ok=True)
    settings.NFS_BASE_PATH = dummy_nfs_path # Temporarily override for testing

    # Create a dummy file
    dummy_file_path = os.path.join(dummy_nfs_path, "2024", "test_recording.mp4")
    os.makedirs(os.path.dirname(dummy_file_path), exist_ok=True)
    with open(dummy_file_path, "w") as f:
        f.write("This is a dummy recording file.")

    print(f"Dummy NFS base path: {settings.NFS_BASE_PATH}")
    print(f"Dummy file created at: {dummy_file_path}")

    # Test valid path
    try:
        resolved_path = resolve_nfs_path("2024/test_recording.mp4")
        print(f"Resolved path: {resolved_path}")
        assert resolved_path == dummy_file_path
    except Exception as e:
        print(f"Error resolving valid path: {e}")

    # Test invalid path (directory traversal)
    try:
        resolve_nfs_path("../../../etc/passwd")
    except ValueError as e:
        print(f"Caught expected error for invalid path: {e}")
    except Exception as e:
        print(f"Unexpected error for invalid path: {e}")

    # Test non-existent NFS base path (simulate unmounted NFS)
    original_nfs_path = settings.NFS_BASE_PATH
    settings.NFS_BASE_PATH = "/non/existent/nfs/path"
    try:
        resolve_nfs_path("some/file.mp4")
    except ServiceUnavailableException as e:
        print(f"Caught expected error for unavailable NFS: {e}")
    except Exception as e:
        print(f"Unexpected error for unavailable NFS: {e}")
    finally:
        settings.NFS_BASE_PATH = original_nfs_path # Restore original

    # Clean up dummy files
    os.remove(dummy_file_path)
    os.rmdir(os.path.dirname(dummy_file_path)) # Remove 2024 dir
    os.rmdir(dummy_nfs_path) # Remove temp_nfs_mount dir
    print("Cleaned up dummy files.")