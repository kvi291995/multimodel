"""
State Manager for PostgreSQL persistence with Redis caching
Async-native implementation using asyncpg for optimal performance
Handles saving, loading, and updating onboarding states
Includes optional Redis caching and Pub/Sub notifications
"""

import asyncpg
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# Try to import Redis (optional)
try:
    from cache.redis_client import redis_client
    from cache.redis_pubsub import redis_pubsub
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.info("Redis not available - using PostgreSQL only")

class StateManager:
    """
    Async-native state persistence manager using asyncpg
    Provides high-performance database operations with Redis caching
    """
    
    _pool: Optional[asyncpg.Pool] = None
    _cache_enabled: bool = False
    _pubsub_enabled: bool = False
    
    @classmethod
    async def initialize(cls, db_config: Dict[str, str] = None, enable_cache: bool = True) -> None:
        """
        Initialize async PostgreSQL connection pool (call once at startup)
        
        Args:
            db_config: Database configuration dict with keys:
                      database, user, password, host, port
            enable_cache: Enable Redis caching and Pub/Sub (default: True)
        """
        if cls._pool is not None:
            logger.warning("StateManager already initialized")
            return
        
        # Use provided config or environment variables
        if db_config is None:
            db_config = {
                'database': os.getenv('POSTGRES_DB'),
                'user': os.getenv('POSTGRES_USER'),
                'password': os.getenv('POSTGRES_PASSWORD'),
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': int(os.getenv('POSTGRES_PORT', 5432))
            }
        
        # Get pool configuration from environment
        min_size = int(os.getenv('DB_POOL_MIN_SIZE', 10))
        max_size = int(os.getenv('DB_POOL_MAX_SIZE', 20))
        timeout = int(os.getenv('DB_POOL_TIMEOUT', 30))
        
        try:
            # Create asyncpg connection pool
            cls._pool = await asyncpg.create_pool(
                database=db_config['database'],
                user=db_config['user'],
                password=db_config['password'],
                host=db_config['host'],
                port=db_config['port'],
                min_size=min_size,
                max_size=max_size,
                command_timeout=timeout
            )
            logger.info(f"✅ Asyncpg connection pool created (min={min_size}, max={max_size})")
        except Exception as e:
            logger.error(f"❌ Failed to create asyncpg connection pool: {e}")
            raise
        
        # Redis support (optional)
        cls._cache_enabled = enable_cache and REDIS_AVAILABLE
        cls._pubsub_enabled = enable_cache and REDIS_AVAILABLE
        
        if cls._cache_enabled:
            try:
                if redis_client.is_connected():
                    logger.info("✅ Redis caching enabled")
                else:
                    cls._cache_enabled = False
                    cls._pubsub_enabled = False
                    logger.info("⚠️ Redis not connected - caching disabled")
            except:
                cls._cache_enabled = False
                cls._pubsub_enabled = False
                logger.info("⚠️ Redis not available - caching disabled")
    
    @classmethod
    async def close(cls) -> None:
        """Close the connection pool (call at shutdown)"""
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
            logger.info("PostgreSQL connection pool closed")
    
    @classmethod
    def _ensure_initialized(cls):
        """Ensure pool is initialized before operations"""
        if cls._pool is None:
            raise RuntimeError(
                "StateManager not initialized. Call 'await StateManager.initialize()' first."
            )
    
    @classmethod
    async def save_state(cls, session_id: str, state: Dict[str, Any]) -> bool:
        """
        Save state to PostgreSQL database (async, write-through cache)
        
        Args:
            session_id: Session identifier
            state: State data to save
            
        Returns:
            bool: Success status
        """
        cls._ensure_initialized()
        
        try:
            # Add state version if not present
            if 'state_version' not in state:
                state['state_version'] = '1.0'
            
            # Add/update timestamps
            if 'created_at' not in state:
                state['created_at'] = datetime.now().isoformat()
            state['updated_at'] = datetime.now().isoformat()
            
            # Write-through cache pattern: Save to DB first (source of truth)
            async with cls._pool.acquire() as conn:
                async with conn.transaction():
                    # Insert or update session (UPSERT)
                    await conn.execute('''
                        INSERT INTO chat_sessions (id, entity_id, session_type, updated_at)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (id) DO UPDATE SET
                            entity_id = EXCLUDED.entity_id,
                            session_type = EXCLUDED.session_type,
                            updated_at = EXCLUDED.updated_at
                    ''', session_id, state.get('entity_id'), 'onboarding', datetime.now())
                    
                    # Insert or update state (UPSERT)
                    state_json = json.dumps(state)
                    await conn.execute('''
                        INSERT INTO onboarding_state 
                        (id, session_id, state_data, current_step, status, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (id) DO UPDATE SET
                            state_data = EXCLUDED.state_data,
                            current_step = EXCLUDED.current_step,
                            status = EXCLUDED.status,
                            updated_at = EXCLUDED.updated_at
                    ''', session_id, session_id, state_json, state.get('current_step'), 
                          state.get('status', 'active'), datetime.now())
            
            logger.info(f"State saved for session {session_id}")
            
            # Update cache after successful DB write (if enabled)
            if cls._cache_enabled:
                try:
                    redis_client.cache_session(session_id, state, expiry=3600)
                    logger.debug(f"State cached in Redis")
                except Exception as redis_error:
                    logger.warning(f"Redis cache failed: {redis_error}")
            
            # Pub/Sub notification (if enabled)
            if cls._pubsub_enabled:
                try:
                    redis_pubsub.publish_session_update(
                        session_id=session_id,
                        event='state_saved',
                        data={'current_step': state.get('current_step')}
                    )
                except Exception as pubsub_error:
                    logger.warning(f"Pub/Sub failed: {pubsub_error}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving state: {str(e)}")
            return False
    
    @classmethod
    async def load_state(cls, session_id: str) -> Dict[str, Any]:
        """
        Load state from cache (fast) or PostgreSQL (fallback) - async
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict[str, Any]: State data with version migration applied
        """
        cls._ensure_initialized()
        
        # Try Redis cache first (if enabled)
        if cls._cache_enabled:
            try:
                cached_state = redis_client.get_cached_session(session_id)
                if cached_state:
                    logger.debug(f"✅ Cache hit for session: {session_id}")
                    # Apply migration to cached data too
                    from agents.state.graph_state import migrate_state
                    return migrate_state(cached_state)
                logger.debug(f"❌ Cache miss for session: {session_id}")
            except Exception as cache_error:
                logger.warning(f"Cache read failed: {cache_error}")
        
        # Fallback to PostgreSQL
        try:
            async with cls._pool.acquire() as conn:
                result = await conn.fetchrow('''
                    SELECT state_data FROM onboarding_state 
                    WHERE session_id = $1
                ''', session_id)
            
            if result:
                state_data = json.loads(result['state_data'])
                logger.info(f"State loaded for session {session_id}")
                
                # Apply state migration
                from agents.state.graph_state import migrate_state
                state_data = migrate_state(state_data)
                
                # Cache it for next time (if enabled)
                if cls._cache_enabled:
                    try:
                        redis_client.cache_session(session_id, state_data, expiry=3600)
                    except Exception as cache_error:
                        logger.warning(f"Failed to cache state: {cache_error}")
                
                return state_data
            else:
                # Return default state if not found
                default_state = {
                    'state_version': '1.0',
                    'session_id': session_id,
                    'current_step': 'welcome',
                    'status': 'active',
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                logger.info(f"Default state created for session {session_id}")
                return default_state
                
        except Exception as e:
            logger.error(f"Error loading state: {str(e)}")
            return {
                'state_version': '1.0',
                'session_id': session_id,
                'current_step': 'welcome',
                'status': 'active',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
    
    @classmethod
    async def update_state(cls, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update specific fields in state - async
        
        Args:
            session_id: Session identifier
            updates: Fields to update
            
        Returns:
            bool: Success status
        """
        try:
            # Load current state
            current_state = await cls.load_state(session_id)
            
            # Apply updates
            current_state.update(updates)
            current_state['updated_at'] = datetime.now().isoformat()
            
            # Save updated state
            return await cls.save_state(session_id, current_state)
            
        except Exception as e:
            logger.error(f"Error updating state: {str(e)}")
            return False
    
    @classmethod
    async def delete_state(cls, session_id: str) -> bool:
        """
        Delete state from PostgreSQL database - async
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: Success status
        """
        cls._ensure_initialized()
        
        try:
            async with cls._pool.acquire() as conn:
                async with conn.transaction():
                    # Delete from onboarding_state first (due to foreign key)
                    await conn.execute('DELETE FROM onboarding_state WHERE session_id = $1', session_id)
                    # Delete from chat_sessions (CASCADE will handle related records)
                    await conn.execute('DELETE FROM chat_sessions WHERE id = $1', session_id)
            
            logger.info(f"State deleted for session {session_id}")
            
            # Clear cache if enabled
            if cls._cache_enabled:
                try:
                    redis_client.delete(f"session:{session_id}")
                except Exception as cache_error:
                    logger.warning(f"Failed to clear cache: {cache_error}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting state: {str(e)}")
            return False
    
    @classmethod
    async def get_all_sessions(cls) -> list:
        """
        Get all active sessions from PostgreSQL - async
        
        Returns:
            list: List of session data
        """
        cls._ensure_initialized()
        
        try:
            async with cls._pool.acquire() as conn:
                results = await conn.fetch('''
                    SELECT s.id, s.entity_id, s.created_at, s.updated_at, 
                           os.current_step, os.status
                    FROM chat_sessions s
                    LEFT JOIN onboarding_state os ON s.id = os.session_id
                    ORDER BY s.updated_at DESC
                ''')
            
            sessions = []
            for row in results:
                sessions.append({
                    'session_id': row['id'],
                    'entity_id': row['entity_id'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
                    'current_step': row['current_step'],
                    'status': row['status']
                })
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error getting sessions: {str(e)}")
            return []
    
    @classmethod
    async def log_api_call(cls, session_id: str, endpoint: str, request_data: Dict[str, Any], 
                          response_data: Dict[str, Any], status_code: int) -> bool:
        """
        Log API call to PostgreSQL database - async
        
        Args:
            session_id: Session identifier
            endpoint: API endpoint
            request_data: Request data
            response_data: Response data
            status_code: HTTP status code
            
        Returns:
            bool: Success status
        """
        cls._ensure_initialized()
        
        try:
            import uuid
            log_id = str(uuid.uuid4())
            
            async with cls._pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO api_logs (id, session_id, api_endpoint, request_data, 
                                        response_data, status_code, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                ''', log_id, session_id, endpoint, json.dumps(request_data),
                      json.dumps(response_data), status_code, datetime.now())
            
            logger.info(f"API call logged for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging API call: {str(e)}")
            return False
    
    @classmethod
    async def save_entity_feature(cls, session_id: str, entity_id: str = None,
                                  user_email: str = None, user_phone: str = None,
                                  organization_name: str = None,
                                  feature: str = None, feature_data: Dict[str, Any] = None) -> bool:
        """
        Save entity ID, user information, and track feature completion - async
        
        Args:
            session_id: Session identifier
            entity_id: Entity ID from external API (saved on signup)
            user_email: User's email address
            user_phone: User's phone number
            organization_name: Organization/company name
            feature: Feature name ('signup', 'kyc', 'business_details', 'bank_details')
            feature_data: Additional feature-specific data to store
            
        Returns:
            bool: Success status
        """
        cls._ensure_initialized()
        
        try:
            import uuid
            
            async with cls._pool.acquire() as conn:
                async with conn.transaction():
                    # Check if record exists
                    existing = await conn.fetchrow(
                        'SELECT id FROM entity_features WHERE session_id = $1', session_id
                    )
                    
                    if not existing:
                        # Create new record
                        record_id = str(uuid.uuid4())
                        await conn.execute('''
                            INSERT INTO entity_features (id, session_id, entity_id, user_email, 
                                                        user_phone, organization_name, created_at, updated_at)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ''', record_id, session_id, entity_id, user_email, user_phone, 
                              organization_name, datetime.now(), datetime.now())
                    else:
                        # Update fields if provided - build dynamic query
                        updates = []
                        params = []
                        param_idx = 1
                        
                        if entity_id:
                            updates.append(f"entity_id = ${param_idx}")
                            params.append(entity_id)
                            param_idx += 1
                        if user_email:
                            updates.append(f"user_email = ${param_idx}")
                            params.append(user_email)
                            param_idx += 1
                        if user_phone:
                            updates.append(f"user_phone = ${param_idx}")
                            params.append(user_phone)
                            param_idx += 1
                        if organization_name:
                            updates.append(f"organization_name = ${param_idx}")
                            params.append(organization_name)
                            param_idx += 1
                        
                        if updates:
                            updates.append(f"updated_at = ${param_idx}")
                            params.append(datetime.now())
                            param_idx += 1
                            params.append(session_id)
                            
                            await conn.execute(f'''
                                UPDATE entity_features 
                                SET {', '.join(updates)}
                                WHERE session_id = ${param_idx}
                            ''', *params)
                    
                    # Update specific feature if provided
                    if feature:
                        feature_map = {
                            'signup': ('signup_completed', 'signup_completed_at', None),
                            'kyc': ('kyc_completed', 'kyc_completed_at', 'kyc_data'),
                            'business_details': ('business_details_completed', 'business_details_completed_at', 'business_data'),
                            'bank_details': ('bank_details_completed', 'bank_details_completed_at', 'bank_data')
                        }
                        
                        if feature in feature_map:
                            completed_col, timestamp_col, data_col = feature_map[feature]
                            
                            if data_col and feature_data:
                                await conn.execute(f'''
                                    UPDATE entity_features 
                                    SET {completed_col} = TRUE, 
                                        {timestamp_col} = $1,
                                        {data_col} = $2,
                                        updated_at = $3
                                    WHERE session_id = $4
                                ''', datetime.now(), json.dumps(feature_data), datetime.now(), session_id)
                            else:
                                await conn.execute(f'''
                                    UPDATE entity_features 
                                    SET {completed_col} = TRUE, 
                                        {timestamp_col} = $1,
                                        updated_at = $2
                                    WHERE session_id = $3
                                ''', datetime.now(), datetime.now(), session_id)
                    
                    # Check if all features are completed
                    result = await conn.fetchrow('''
                        SELECT signup_completed, kyc_completed, 
                               business_details_completed, bank_details_completed
                        FROM entity_features WHERE session_id = $1
                    ''', session_id)
                    
                    if result and all([result['signup_completed'], result['kyc_completed'],
                                      result['business_details_completed'], result['bank_details_completed']]):
                        # All features completed - mark onboarding as complete
                        await conn.execute('''
                            UPDATE entity_features 
                            SET onboarding_completed = TRUE,
                                onboarding_completed_at = $1,
                                updated_at = $2
                            WHERE session_id = $3
                        ''', datetime.now(), datetime.now(), session_id)
            
            logger.info(f"Entity feature saved for session {session_id}: {feature}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving entity feature: {str(e)}")
            return False
    
    @classmethod
    async def get_entity_features(cls, session_id: str) -> Dict[str, Any]:
        """
        Get entity feature completion status - async
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict with entity_id and completion status
        """
        cls._ensure_initialized()
        
        try:
            async with cls._pool.acquire() as conn:
                result = await conn.fetchrow('''
                    SELECT entity_id, user_email, user_phone, organization_name,
                           signup_completed, signup_completed_at,
                           kyc_completed, kyc_completed_at, kyc_data,
                           business_details_completed, business_details_completed_at, business_data,
                           bank_details_completed, bank_details_completed_at, bank_data,
                           onboarding_completed, onboarding_completed_at
                    FROM entity_features WHERE session_id = $1
                ''', session_id)
            
            if result:
                return {
                    'entity_id': result['entity_id'],
                    'user_email': result['user_email'],
                    'user_phone': result['user_phone'],
                    'organization_name': result['organization_name'],
                    'signup': {
                        'completed': result['signup_completed'],
                        'completed_at': result['signup_completed_at'].isoformat() if result['signup_completed_at'] else None
                    },
                    'kyc': {
                        'completed': result['kyc_completed'],
                        'completed_at': result['kyc_completed_at'].isoformat() if result['kyc_completed_at'] else None,
                        'data': json.loads(result['kyc_data']) if result['kyc_data'] else None
                    },
                    'business_details': {
                        'completed': result['business_details_completed'],
                        'completed_at': result['business_details_completed_at'].isoformat() if result['business_details_completed_at'] else None,
                        'data': json.loads(result['business_data']) if result['business_data'] else None
                    },
                    'bank_details': {
                        'completed': result['bank_details_completed'],
                        'completed_at': result['bank_details_completed_at'].isoformat() if result['bank_details_completed_at'] else None,
                        'data': json.loads(result['bank_data']) if result['bank_data'] else None
                    },
                    'onboarding_completed': result['onboarding_completed'],
                    'onboarding_completed_at': result['onboarding_completed_at'].isoformat() if result['onboarding_completed_at'] else None
                }
            else:
                return {
                    'entity_id': None,
                    'user_email': None,
                    'user_phone': None,
                    'organization_name': None,
                    'signup': {'completed': False, 'completed_at': None},
                    'kyc': {'completed': False, 'completed_at': None, 'data': None},
                    'business_details': {'completed': False, 'completed_at': None, 'data': None},
                    'bank_details': {'completed': False, 'completed_at': None, 'data': None},
                    'onboarding_completed': False,
                    'onboarding_completed_at': None
                }
                
        except Exception as e:
            logger.error(f"Error getting entity features: {str(e)}")
            return {}

