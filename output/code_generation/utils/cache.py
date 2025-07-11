import time
import logging
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)

class SimpleCache:
    """
    A simple in-memory cache with a time-to-live (TTL) for entries.
    Not suitable for multi-process/multi-server deployments.
    For production, consider Redis or Memcached.
    """
    def __init__(self, ttl: int = 300):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl # Time-to-live in seconds
        logger.info(f"SimpleCache initialized with TTL: {self.ttl} seconds.")

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Sets a value in the cache with an optional custom TTL.
        """
        expire_time = time.time() + (ttl if ttl is not None else self.ttl)
        self._cache[key] = {"value": value, "expire_time": expire_time}
        logger.debug(f"Cache set for key: {key}, expires in {ttl if ttl is not None else self.ttl}s.")

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieves a value from the cache. Returns None if key not found or expired.
        """
        entry = self._cache.get(key)
        if entry:
            if time.time() < entry["expire_time"]:
                logger.debug(f"Cache hit for key: {key}")
                return entry["value"]
            else:
                self.delete(key) # Expired, remove it
                logger.debug(f"Cache expired for key: {key}")
        logger.debug(f"Cache miss for key: {key}")
        return None

    def delete(self, key: str):
        """
        Deletes an entry from the cache.
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache deleted for key: {key}")

    def clear(self):
        """
        Clears all entries from the cache.
        """
        self._cache.clear()
        logger.info("Cache cleared.")

    def __len__(self):
        """Returns the number of active items in the cache."""
        return len([k for k in self._cache if time.time() < self._cache[k]["expire_time"]])

    def __contains__(self, key: str):
        """Checks if a key is in the cache and not expired."""
        return self.get(key) is not None