"""
Redis Pub/Sub Service
Real-time messaging for onboarding events
"""

import redis
import json
import logging
import threading
from typing import Callable, Dict, Any
from config.redis_config import REDIS_CONFIG, CHANNELS

logger = logging.getLogger(__name__)

class RedisPubSub:
    """Redis Pub/Sub service for real-time events"""
    
    def __init__(self):
        """Initialize Pub/Sub client"""
        try:
            self.redis_client = redis.Redis(**REDIS_CONFIG)
            self.pubsub = self.redis_client.pubsub(ignore_subscribe_messages=True)
            self.listener_thread = None
            self.is_listening = False
            logger.info("✅ Redis Pub/Sub initialized")
        except Exception as e:
            logger.error(f"❌ Redis Pub/Sub initialization failed: {e}")
            self.redis_client = None
            self.pubsub = None
    
    # ==========================================
    # Publisher Methods
    # ==========================================
    
    def publish(self, channel: str, message: Any) -> int:
        """
        Publish message to channel
        
        Args:
            channel: Channel name
            message: Message (dict will be JSON encoded)
            
        Returns:
            Number of subscribers that received the message
        """
        try:
            if isinstance(message, dict):
                message = json.dumps(message)
            
            count = self.redis_client.publish(channel, message)
            logger.info(f"📤 Published to '{channel}': {count} subscribers")
            return count
        except Exception as e:
            logger.error(f"Publish error: {e}")
            return 0
    
    def publish_session_update(self, session_id: str, event: str, data: Dict[str, Any]):
        """Publish session-specific update"""
        channel = CHANNELS['session_updates'].format(session_id=session_id)
        message = {
            'event': event,
            'session_id': session_id,
            'data': data,
            'timestamp': self._get_timestamp()
        }
        return self.publish(channel, message)
    
    def publish_feature_completed(self, session_id: str, feature: str, data: Dict[str, Any] = None):
        """Publish feature completion event"""
        message = {
            'event': 'feature_completed',
            'session_id': session_id,
            'feature': feature,
            'data': data or {},
            'timestamp': self._get_timestamp()
        }
        return self.publish(CHANNELS['feature_completed'], message)
    
    def publish_onboarding_event(self, session_id: str, event_type: str, data: Dict[str, Any]):
        """Publish general onboarding event"""
        message = {
            'event': event_type,
            'session_id': session_id,
            'data': data,
            'timestamp': self._get_timestamp()
        }
        return self.publish(CHANNELS['onboarding_events'], message)
    
    # ==========================================
    # Subscriber Methods
    # ==========================================
    
    def subscribe(self, *channels: str, callback: Callable = None):
        """
        Subscribe to one or more channels
        
        Args:
            channels: Channel names to subscribe to
            callback: Function to call when message received
        """
        try:
            self.pubsub.subscribe(*channels)
            logger.info(f"📥 Subscribed to channels: {channels}")
            
            if callback:
                self._start_listener(callback)
        except Exception as e:
            logger.error(f"Subscribe error: {e}")
    
    def subscribe_to_session(self, session_id: str, callback: Callable):
        """Subscribe to session-specific updates"""
        channel = CHANNELS['session_updates'].format(session_id=session_id)
        self.subscribe(channel, callback=callback)
    
    def unsubscribe(self, *channels: str):
        """Unsubscribe from channels"""
        try:
            self.pubsub.unsubscribe(*channels)
            logger.info(f"📤 Unsubscribed from: {channels}")
        except Exception as e:
            logger.error(f"Unsubscribe error: {e}")
    
    def _start_listener(self, callback: Callable):
        """Start background listener thread"""
        if self.is_listening:
            return
        
        self.is_listening = True
        self.listener_thread = threading.Thread(
            target=self._listen,
            args=(callback,),
            daemon=True
        )
        self.listener_thread.start()
        logger.info("🎧 Listener thread started")
    
    def _listen(self, callback: Callable):
        """Listen for messages (runs in background thread)"""
        try:
            for message in self.pubsub.listen():
                if message['type'] == 'message':
                    try:
                        # Try to parse as JSON
                        data = json.loads(message['data'])
                    except:
                        data = message['data']
                    
                    # Call user's callback
                    callback(message['channel'], data)
        except Exception as e:
            logger.error(f"Listener error: {e}")
            self.is_listening = False
    
    def stop_listening(self):
        """Stop listener thread"""
        self.is_listening = False
        if self.listener_thread:
            self.listener_thread.join(timeout=1)
        logger.info("🛑 Listener stopped")
    
    # ==========================================
    # Helper Methods
    # ==========================================
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    def close(self):
        """Close Pub/Sub connection"""
        self.stop_listening()
        if self.pubsub:
            self.pubsub.close()
        if self.redis_client:
            self.redis_client.close()
        logger.info("✅ Redis Pub/Sub closed")


# Singleton instance
redis_pubsub = RedisPubSub()
