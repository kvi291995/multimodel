"""
Validation Subgraph
Provides validation logic for user input data
"""

import logging
import re
from typing import Dict, Any
from langgraph.graph import StateGraph, END

from agents.state.graph_state import ValidationState

logger = logging.getLogger(__name__)


def validate_name(state: ValidationState) -> Dict[str, Any]:
    """Validate name field"""
    name = state.get('name')
    
    if not name or not isinstance(name, str):
        return {
            'name_valid': False,
            'errors': state.get('errors', []) + ['Name is required']
        }
    
    name = name.strip()
    
    if len(name) < 2:
        return {
            'name_valid': False,
            'errors': state.get('errors', []) + ['Name must be at least 2 characters']
        }
    
    if len(name) > 100:
        return {
            'name_valid': False,
            'errors': state.get('errors', []) + ['Name must be less than 100 characters']
        }
    
    return {'name_valid': True}


def validate_email(state: ValidationState) -> Dict[str, Any]:
    """Validate email field"""
    email = state.get('email')
    
    if not email or not isinstance(email, str):
        return {
            'email_valid': False,
            'errors': state.get('errors', []) + ['Email is required']
        }
    
    email = email.strip().lower()
    
    # Basic email validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return {
            'email_valid': False,
            'errors': state.get('errors', []) + ['Invalid email format']
        }
    
    return {'email_valid': True}


def validate_phone(state: ValidationState) -> Dict[str, Any]:
    """Validate phone field"""
    phone = state.get('phone')
    
    if not phone or not isinstance(phone, str):
        return {
            'phone_valid': False,
            'errors': state.get('errors', []) + ['Phone is required']
        }
    
    phone = phone.strip()
    
    # Remove common phone formatting characters
    phone_digits = re.sub(r'[^0-9]', '', phone)
    
    if len(phone_digits) < 10 or len(phone_digits) > 15:
        return {
            'phone_valid': False,
            'errors': state.get('errors', []) + ['Phone must be between 10 and 15 digits']
        }
    
    return {'phone_valid': True}


def check_validation_complete(state: ValidationState) -> Dict[str, Any]:
    """Check if all validations are complete"""
    name_valid = state.get('name_valid', False)
    email_valid = state.get('email_valid', False)
    phone_valid = state.get('phone_valid', False)
    
    validation_complete = name_valid and email_valid and phone_valid
    
    return {'validation_complete': validation_complete}


def create_validation_subgraph() -> StateGraph:
    """Create the validation subgraph"""
    workflow = StateGraph(ValidationState)
    
    # Add validation nodes
    workflow.add_node("validate_name", validate_name)
    workflow.add_node("validate_email", validate_email)
    workflow.add_node("validate_phone", validate_phone)
    workflow.add_node("check_complete", check_validation_complete)
    
    # Set entry point
    workflow.set_entry_point("validate_name")
    
    # Add edges
    workflow.add_edge("validate_name", "validate_email")
    workflow.add_edge("validate_email", "validate_phone")
    workflow.add_edge("validate_phone", "check_complete")
    workflow.add_edge("check_complete", END)
    
    return workflow.compile()


# Create the validation graph instance
validation_graph = create_validation_subgraph()

logger.info("Validation subgraph initialized")

