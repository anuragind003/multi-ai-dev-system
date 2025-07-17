import logging
import csv
from io import StringIO
from typing import List
import re

from app.core.exceptions import InvalidInputException
from config import settings

logger = logging.getLogger(__name__)

def parse_lan_ids_from_csv(file_content: StringIO) -> List[str]:
    """
    Parses a CSV or TXT file content (as StringIO) to extract LAN IDs.
    Assumes LAN IDs are in the first column or are the only content per line.
    Performs basic sanitization and validation.
    """
    lan_ids = []
    reader = csv.reader(file_content)
    line_num = 0
    for row in reader:
        line_num += 1
        if not row:
            continue # Skip empty rows

        raw_lan_id = row[0].strip() # Take the first column
        
        # Skip empty strings after stripping
        if not raw_lan_id:
            logger.debug(f"Skipping empty LAN ID on line {line_num}.")
            continue

        # Basic sanitization: remove non-alphanumeric characters except underscore/hyphen
        # and convert to uppercase for consistency
        sanitized_lan_id = re.sub(r'[^a-zA-Z0-9_-]', '', raw_lan_id).upper()

        # Basic validation: check length and if it's not just whitespace
        if not (5 <= len(sanitized_lan_id) <= 50): # Example length range
            logger.warning(f"Invalid LAN ID length on line {line_num}: '{raw_lan_id}' (sanitized: '{sanitized_lan_id}')")
            # Optionally, raise an error or collect invalid IDs
            continue
        
        lan_ids.append(sanitized_lan_id)
    
    if not lan_ids:
        raise InvalidInputException("No valid LAN IDs found in the uploaded file.")

    logger.info(f"Successfully parsed {len(lan_ids)} LAN IDs from file.")
    return lan_ids

def generate_nfs_path(lan_id: str) -> str:
    """
    Generates a hypothetical NFS file path for a given LAN ID.
    This is a placeholder function. In a real system, this logic
    would be more sophisticated, potentially involving:
    - A lookup service for actual file locations.
    - A defined directory structure (e.g., /year/month/day/lan_id.mp4).
    - Checking for file existence on NFS (which might be done asynchronously).
    """
    # Example: /mnt/vkyc_recordings/LANID_YYYYMMDD_HHMMSS.mp4
    # For simplicity, we'll just use the LAN ID and a dummy extension.
    # The actual file name might be more complex, e.g., including date/time of recording.
    # For bulk upload, we assume the file *will be* or *is already* at this path.
    file_name = f"{lan_id}.mp4"
    # You might want to categorize by date or other attributes
    # For example: current_date = datetime.now().strftime("%Y/%m/%d")
    # return os.path.join(settings.NFS_BASE_PATH, current_date, file_name)
    
    # Simple path for demonstration
    return f"{settings.NFS_BASE_PATH}/{file_name}"