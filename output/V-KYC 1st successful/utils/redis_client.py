import asyncio
import aioredis
from aioredis import Redis
from config import get_settings
from utils.logger import logger
from typing import Optional, Any

class RedisClient:
    """
    Manages the Redis connection and provides asynchronous methods for caching and session management.
    """
    _instance: Optional[Redis] = None

    @classmethod
    async def connect(cls):
        """Establishes a connection to Redis."""
        if cls._instance is None:
            settings = get_settings()
            try:
                cls._instance = await aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    health_check_interval=10 # Check connection health every 10 seconds
                )
                await cls._instance.ping() # Test the connection
                logger.info("Successfully connected to Redis.")
            except aioredis.RedisError as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise ConnectionError(f"Could not connect to Redis: {e}")

    @classmethod
    async def disconnect(cls):
        """Closes the Redis connection."""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None
            logger.info("Disconnected from Redis.")

    @classmethod
    def get_client(cls) -> Redis:
        """Returns the Redis client instance."""
        if cls._instance is None:
            raise RuntimeError("Redis client not initialized. Call connect() first.")
        return cls._instance

    @classmethod
    async def get(cls, key: str) -> Optional[str]:
        """Retrieves a value from Redis."""
        try:
            return await cls.get_client().get(key)
        except aioredis.RedisError as e:
            logger.error(f"Redis GET operation failed for key '{key}': {e}")
            return None

    @classmethod
    async def set(cls, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Sets a key-value pair in Redis with optional expiry."""
        try:
            return await cls.get_client().set(key, value, ex=ex)
        except aioredis.RedisError as e:
            logger.error(f"Redis SET operation failed for key '{key}': {e}")
            return False

    @classmethod
    async def delete(cls, key: str) -> int:
        """Deletes a key from Redis."""
        try:
            return await cls.get_client().delete(key)
        except aioredis.RedisError as e:
            logger.error(f"Redis DELETE operation failed for key '{key}': {e}")
            return 0

    @classmethod
    async def exists(cls, key: str) -> int:
        """Checks if a key exists in Redis."""
        try:
            return await cls.get_client().exists(key)
        except aioredis.RedisError as e:
            logger.error(f"Redis EXISTS operation failed for key '{key}': {e}")
            return 0

# Dependency for FastAPI to get Redis client
async def get_redis_client() -> Redis:
    """FastAPI dependency to provide the Redis client."""
    return RedisClient.get_client()