"""
Redis Client Service
Handles Redis connections and basic operations with auto-reconnection
"""

import redis
import json
import logging
import time
from typing import Any, Optional
from config.redis_config import REDIS_CONFIG

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis client wrapper with connection pooling and auto-reconnect"""
    
    _instance = None
    _client = None
    _last_health_check = 0
    _health_check_interval = 30  # seconds
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self, retries: int = 3, delay: int = 2):
        """Initialize Redis connection with retries"""
        for attempt in range(retries):
            try:
                self._client = redis.Redis(
                    connection_pool=redis.ConnectionPool(**REDIS_CONFIG)
                )
                # Test connection
                self._client.ping()
                self._last_health_check = time.time()
                logger.info("✅ Redis connected successfully")
                return
            except redis.ConnectionError as e:
                logger.warning(f"⚠️ Redis connection attempt {attempt+1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(delay)
        logger.error("❌ Redis connection failed after all retries")
        self._client = None
    
    @property
    def client(self):
        """Get Redis client with periodic health checks and auto-reconnect"""
        current_time = time.time()
        
        # If client is None, try to initialize
        if self._client is None:
            self._initialize()
            return self._client
        
        # Periodic health check (every 30 seconds) to detect dead connections
        if current_time - self._last_health_check > self._health_check_interval:
            try:
                self._client.ping()
                self._last_health_check = current_time
                logger.debug("✅ Redis health check passed")
            except (redis.ConnectionError, redis.TimeoutError, AttributeError):
                logger.warning("⚠️ Redis connection lost during health check, reconnecting...")
                self._client = None
                self._initialize()
        
        return self._client
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        try:
            if self.client:
                self.client.ping()
                return True
            return False
        except:
            return False
    
    def _execute_with_retry(self, operation):
        """Execute operation with automatic retry on connection failure"""
        try:
            return operation()
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"⚠️ Redis operation failed: {e}, attempting reconnect and retry...")
            # Force reconnection
            self._client = None
            _ = self.client  # Trigger reconnect via property
            
            # Retry once after reconnection
            if self._client:
                try:
                    return operation()
                except Exception as retry_error:
                    logger.error(f"❌ Redis retry failed: {retry_error}")
                    return None
            return None
        except Exception as e:
            logger.error(f"❌ Redis error: {e}")
            return None
    
    # ==========================================
    # Basic Operations (with auto-retry)
    # ==========================================
    
    def set(self, key: str, value: Any, expiry: int = None) -> bool:
        """
        Set key-value pair with auto-reconnect
        
        Args:
            key: Redis key
            value: Value (will be JSON encoded if dict/list)
            expiry: Expiration time in seconds
        """
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        def _operation():
            if expiry:
                return self.client.setex(key, expiry, value)
            else:
                return self.client.set(key, value)
        
        result = self._execute_with_retry(_operation)
        return result is not None
    
    def get(self, key: str, as_json: bool = False) -> Optional[Any]:
        """
        Get value by key with auto-reconnect
        
        Args:
            key: Redis key
            as_json: Parse as JSON if True
        """
        def _operation():
            value = self.client.get(key)
            if value is None:
                return None
            if as_json:
                return json.loads(value)
            return value
        
        return self._execute_with_retry(_operation)
    
    def delete(self, *keys: str) -> int:
        """Delete one or more keys with auto-reconnect"""
        def _operation():
            return self.client.delete(*keys)
        
        result = self._execute_with_retry(_operation)
        return result if result is not None else 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists with auto-reconnect"""
        def _operation():
            return self.client.exists(key) > 0
        
        result = self._execute_with_retry(_operation)
        return result if result is not None else False
    
    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key with auto-reconnect"""
        def _operation():
            return self.client.expire(key, seconds)
        
        result = self._execute_with_retry(_operation)
        return result if result is not None else False
    
    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter with auto-reconnect"""
        def _operation():
            return self.client.incr(key, amount)
        
        return self._execute_with_retry(_operation)
    
    # ==========================================
    # Cache Helpers
    # ==========================================
    
    def cache_session(self, session_id: str, data: dict, expiry: int = 3600):
        """Cache session data (default 1 hour)"""
        return self.set(f"session:{session_id}", data, expiry)
    
    def get_cached_session(self, session_id: str) -> Optional[dict]:
        """Get cached session data"""
        return self.get(f"session:{session_id}", as_json=True)
    
    def cache_entity(self, entity_id: str, data: dict, expiry: int = 1800):
        """Cache entity data (default 30 minutes)"""
        return self.set(f"entity:{entity_id}", data, expiry)
    
    def get_cached_entity(self, entity_id: str) -> Optional[dict]:
        """Get cached entity data"""
        return self.get(f"entity:{entity_id}", as_json=True)
    
    def clear_session(self, session_id: str) -> bool:
        """
        Clear a specific session from cache (safe, single key deletion)
        
        Args:
            session_id: Session ID to clear
        
        Returns:
            bool: True if successful
        """
        return self.delete(f"session:{session_id}") > 0
    
    def clear_sessions_by_pattern(self, pattern: str = "session:*", max_keys: int = 1000) -> int:
        """
        Clear sessions matching a pattern using scan_iter (NON-BLOCKING)
        
        WARNING: This iterates through keys matching the pattern. For large datasets,
        consider using TTL-based expiration instead of manual clearing.
        
        Args:
            pattern: Redis key pattern (default: "session:*")
            max_keys: Maximum number of keys to delete (safety limit)
        
        Returns:
            int: Number of keys deleted
        """
        def _operation():
            deleted_count = 0
            # scan_iter is non-blocking and yields keys in batches
            for key in self.client.scan_iter(match=pattern, count=100):
                if deleted_count >= max_keys:
                    logger.warning(f"Reached max_keys limit ({max_keys}), stopping deletion")
                    break
                self.client.delete(key)
                deleted_count += 1
            return deleted_count
        
        result = self._execute_with_retry(_operation)
        return result if result is not None else 0
    
    def invalidate_cache(self, *patterns: str):
        """
        DEPRECATED: Use clear_session() or clear_sessions_by_pattern() instead.
        This method is kept for backward compatibility but should not be used in production.
        
        Invalidate cache by patterns using safe scan_iter
        """
        logger.warning("invalidate_cache() is deprecated. Use clear_session() or clear_sessions_by_pattern()")
        
        total_deleted = 0
        for pattern in patterns:
            deleted = self.clear_sessions_by_pattern(pattern)
            total_deleted += deleted
        
        return total_deleted > 0


# Singleton instance
redis_client = RedisClient()