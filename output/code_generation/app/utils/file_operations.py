import asyncio
import random
from datetime import datetime, timedelta, timezone
import os
from app.core.config import settings
from app.core.exceptions import ServiceUnavailableException
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Simulate NFS server behavior
# This dictionary stores mock file existence and metadata
# In a real scenario, this would be actual file system calls or NFS client library calls.
MOCK_NFS_FILES = {
    "LAN1234567890": {
        "exists": True,
        "size": 1024 * 1024 * 50,  # 50 MB
        "last_modified": datetime.now(timezone.utc) - timedelta(days=30)
    },
    "LAN0987654321": {
        "exists": True,
        "size": 1024 * 1024 * 100, # 100 MB
        "last_modified": datetime.now(timezone.utc) - timedelta(days=15)
    },
    "LAN1122334455": {
        "exists": False, # Simulate file not found
    },
    "LAN9988776655": {
        "exists": True,
        "size": 1024 * 1024 * 25, # 25 MB
        "last_modified": datetime.now(timezone.utc) - timedelta(days=5)
    },
    # Add more mock files as needed for testing
}

async def simulate_nfs_delay():
    """Simulates network latency or I/O delay for NFS operations."""
    await asyncio.sleep(random.uniform(0.05, 0.5)) # Simulate 50ms to 500ms delay

def generate_mock_file_path(lan_id: str) -> str:
    """
    Generates a mock file path based on LAN ID.
    In a real system, this would be based on actual file naming conventions.
    """
    # Example: /mnt/vkyc_recordings/2023/01/LAN1234567890.mp4
    year = datetime.now().year
    month = datetime.now().month
    return os.path.join(settings.NFS_BASE_PATH, str(year), f"{month:02d}", f"{lan_id}.mp4")

async def check_file_exists(file_path: str) -> bool:
    """
    Simulates checking if a file exists on the NFS server.
    Introduces a random chance of ServiceUnavailableException.
    """
    await simulate_nfs_delay()

    if random.random() < 0.01: # 1% chance of NFS being unavailable
        logger.error(f"Simulated NFS service unavailability for path: {file_path}")
        raise ServiceUnavailableException(service_name="NFS Server", details={"path": file_path})

    # Extract LAN ID from mock path for lookup
    lan_id = os.path.basename(file_path).split('.')[0]
    
    file_info = MOCK_NFS_FILES.get(lan_id)
    return file_info["exists"] if file_info else False

async def get_file_metadata(file_path: str) -> dict:
    """
    Simulates fetching metadata for a file on the NFS server.
    Assumes file_exists has already been called and returned True.
    """
    await simulate_nfs_delay()

    if random.random() < 0.01: # 1% chance of NFS being unavailable
        logger.error(f"Simulated NFS service unavailability during metadata fetch for path: {file_path}")
        raise ServiceUnavailableException(service_name="NFS Server", details={"path": file_path})

    lan_id = os.path.basename(file_path).split('.')[0]
    file_info = MOCK_NFS_FILES.get(lan_id)

    if file_info and file_info["exists"]:
        return {
            "size": file_info.get("size"),
            "last_modified": file_info.get("last_modified")
        }
    else:
        # This case should ideally not be reached if check_file_exists was called first
        logger.warning(f"Attempted to get metadata for non-existent or unknown file: {file_path}")
        return {} # Or raise a specific error if appropriate