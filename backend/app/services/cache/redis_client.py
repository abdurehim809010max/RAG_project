"""
backend/app/services/cache/redis_client.py

Manages the connection to the Redis in-memory datastore.
"""
import redis
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        try:
            self.client = redis.Redis(
                host=host, 
                port=port, 
                db=db, 
                decode_responses=True # Automatically decodes bytes to strings
            )
            # Ping to verify connection on startup
            self.client.ping()
            logger.info("Successfully connected to Redis cache.")
        except redis.ConnectionError:
            logger.warning("Redis is not running. Caching will be disabled.")
            self.client = None

    def get(self, key: str):
        if not self.client:
            return None
        return self.client.get(key)

    def set(self, key: str, value: str, ttl: int = 86400):
        """Sets a value with a Time-To-Live (default 24 hours)."""
        if self.client:
            self.client.setex(key, ttl, value)