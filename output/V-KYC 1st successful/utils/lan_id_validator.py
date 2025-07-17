import re
import logging

log = logging.getLogger(__name__)

# Regex for LAN ID validation.
# Example: "LAN123456", "ABC-98765", "XYZ_0001"
# This regex allows alphanumeric characters, hyphens, and underscores.
# It requires at least one letter and one digit.
# Adjust this regex based on actual LAN ID format requirements.
LAN_ID_REGEX = r"^[A-Z0-9_.-]{5,20}$" # Example: 5 to 20 characters, alphanumeric, underscore, hyphen, dot.
# A more specific example: Starts with 3 letters, followed by a hyphen, then 5-7 digits.
# LAN_ID_REGEX = r"^[A-Z]{3}-\d{5,7}$"

def is_valid_lan_id(lan_id: str) -> bool:
    """
    Validates a single LAN ID against a predefined regex pattern.

    Args:
        lan_id (str): The LAN ID string to validate.

    Returns:
        bool: True if the LAN ID is valid, False otherwise.
    """
    if not isinstance(lan_id, str):
        log.debug(f"LAN ID '{lan_id}' is not a string.")
        return False
    
    # Remove leading/trailing whitespace
    cleaned_lan_id = lan_id.strip()

    if not cleaned_lan_id:
        log.debug("LAN ID is empty after stripping whitespace.")
        return False

    match = re.fullmatch(LAN_ID_REGEX, cleaned_lan_id)
    if not match:
        log.debug(f"LAN ID '{cleaned_lan_id}' does not match regex pattern.")
    return bool(match)