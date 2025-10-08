"""
API Subgraph
Handles external API calls with retry logic
"""

import logging
import time
from typing import Dict, Any
from langgraph.graph import StateGraph, END

from agents.state.graph_state import APIState

logger = logging.getLogger(__name__)


def prepare_api_request(state: APIState) -> Dict[str, Any]:
    """Prepare API request payload"""
    user_data = state.get('user_data', {})
    
    request_payload = {
        'name': user_data.get('name'),
        'email': user_data.get('email'),
        'phone': user_data.get('phone'),
        'timestamp': time.time()
    }
    
    return {
        'request_payload': request_payload,
        'endpoint': '/api/entity/create',
        'method': 'POST'
    }


def call_external_api(state: APIState) -> Dict[str, Any]:
    """
    Call external API to create entity
    Makes actual HTTP request to signup API
    """
    try:
        import requests
        
        # Get retry count
        retry_count = state.get('retry_count', 0)
        
        # Make actual API call
        api_url = state.get('api_url', 'http://localhost:8000')
        endpoint = state.get('endpoint', '/api/entity/create')
        payload = state.get('request_payload', {})
        
        logger.info(f"Calling API: {api_url}{endpoint}")
        
        response = requests.post(
            f"{api_url}{endpoint}",
            json=payload,
            timeout=30
        )
        
        response.raise_for_status()  # Raise exception for HTTP errors
        response_data = response.json()
        
        # Extract entity ID from response
        entity_id = response_data.get('entity_id')
        
        if not entity_id:
            raise ValueError("No entity_id in API response")
        
        logger.info(f"API call successful - Entity ID: {entity_id}")
        
        return {
            'success': True,
            'entity_id': entity_id,
            'response_data': response_data,
            'error_message': None
        }
        
    except requests.exceptions.Timeout:
        logger.error("API request timeout")
        return {
            'success': False,
            'entity_id': None,
            'response_data': {},
            'error_message': 'API request timeout - please try again'
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        return {
            'success': False,
            'entity_id': None,
            'response_data': {},
            'error_message': f'API connection error: {str(e)}'
        }
    except Exception as e:
        logger.error(f"API call failed: {str(e)}")
        return {
            'success': False,
            'entity_id': None,
            'response_data': {},
            'error_message': str(e)
        }


def handle_api_retry(state: APIState) -> Dict[str, Any]:
    """Handle API retry logic"""
    success = state.get('success', False)
    retry_count = state.get('retry_count', 0)
    max_retries = 3
    
    if success:
        return {'retry_count': retry_count}
    
    if retry_count < max_retries:
        logger.info(f"Retrying API call (attempt {retry_count + 1}/{max_retries})")
        time.sleep(2 ** retry_count)  # Exponential backoff
        return {'retry_count': retry_count + 1}
    
    logger.error(f"API call failed after {max_retries} retries")
    return {'retry_count': retry_count}


def router(state: APIState) -> str:
    """Route based on success status"""
    success = state.get('success', False)
    retry_count = state.get('retry_count', 0)
    max_retries = 3
    
    if success:
        return END
    elif retry_count < max_retries:
        return "call_api"
    else:
        return END


def create_api_subgraph() -> StateGraph:
    """Create the API subgraph"""
    workflow = StateGraph(APIState)
    
    # Add nodes
    workflow.add_node("prepare_request", prepare_api_request)
    workflow.add_node("call_api", call_external_api)
    workflow.add_node("handle_retry", handle_api_retry)
    
    # Set entry point
    workflow.set_entry_point("prepare_request")
    
    # Add edges
    workflow.add_edge("prepare_request", "call_api")
    workflow.add_edge("call_api", "handle_retry")
    
    # Add conditional routing from handle_retry
    workflow.add_conditional_edges(
        "handle_retry",
        router,
        {
            "call_api": "call_api",
            END: END
        }
    )
    
    return workflow.compile()


# Create the API graph instance
api_graph = create_api_subgraph()

logger.info("API subgraph initialized")

