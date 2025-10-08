"""
Redis Configuration
"""

import os

REDIS_CONFIG = {
    'host': os.getenv('REDIS_HOST') or 'localhost',
    'port': int(os.getenv('REDIS_PORT') or 6379),
    'db': int(os.getenv('REDIS_DB') or 0),
    'decode_responses': True,  # Auto-decode bytes to strings
    'socket_timeout': 5,
    'socket_connect_timeout': 5,
    'retry_on_timeout': True,
    'health_check_interval': 30
}

# Pub/Sub channel names
CHANNELS = {
    'notifications': 'notifications',
    'session_updates': 'session_updates:{session_id}',
    'feature_completed': 'feature_completed',
    'onboarding_events': 'onboarding:events'
}
