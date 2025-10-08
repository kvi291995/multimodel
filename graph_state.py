"""
State definitions for agent graphs
Provides state classes and utilities for LangGraph-based agents
"""

from typing import Dict, Any, List, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field, validator
from datetime import datetime


class GraphState(TypedDict):
    """
    Base state for agent graphs
    Used by subgraphs for validation and API processing
    """
    # Core state
    session_id: str
    messages: List[Dict[str, Any]]
    current_step: str
    next_step: str
    
    # Data fields
    user_data: Dict[str, Any]
    company_data: Dict[str, Any]
    kyc_data: Dict[str, Any]
    bank_data: Dict[str, Any]
    
    # Status fields
    is_complete: bool
    has_errors: bool
    errors: List[str]
    
    # Metadata
    metadata: Dict[str, Any]


class ValidationState(TypedDict):
    """
    State for validation subgraph
    """
    # Input data
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    
    # Validation results
    name_valid: bool
    email_valid: bool
    phone_valid: bool
    validation_complete: bool
    
    # Errors
    errors: List[str]


class APIState(TypedDict):
    """
    State for API subgraph
    """
    # API configuration
    api_url: str
    endpoint: str
    method: str
    
    # Data
    user_data: Dict[str, Any]
    request_payload: Dict[str, Any]
    
    # Response
    response_data: Dict[str, Any]
    entity_id: Optional[str]
    
    # Status
    success: bool
    retry_count: int
    error_message: Optional[str]


def create_initial_state(session_id: str) -> Dict[str, Any]:
    """
    Create an initial state for a new session
    
    Args:
        session_id: Unique session identifier
        
    Returns:
        Dictionary containing initial state
    """
    return {
        'session_id': session_id,
        'messages': [],
        'current_step': 'init',
        'next_step': 'signup',
        'user_data': {},
        'company_data': {},
        'kyc_data': {},
        'bank_data': {},
        'is_complete': False,
        'has_errors': False,
        'errors': [],
        'metadata': {
            'created_at': None,
            'updated_at': None
        }
    }


def validate_state(state: Dict[str, Any]) -> bool:
    """
    Validate that a state dict has required fields
    
    Args:
        state: State dictionary to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ['session_id', 'current_step']
    return all(field in state for field in required_fields)


def merge_state(base_state: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge updates into base state
    
    Args:
        base_state: Base state dictionary
        updates: Updates to apply
        
    Returns:
        Merged state dictionary
    """
    merged = base_state.copy()
    merged.update(updates)
    return merged


# ==========================================
# Pydantic Models for State Persistence
# ==========================================

class OnboardingStateModel(BaseModel):
    """
    Pydantic model for onboarding state with versioning
    Ensures type safety and enables schema evolution
    """
    state_version: str = Field(default="1.0", description="State schema version")
    session_id: str = Field(..., description="Unique session identifier")
    entity_id: Optional[str] = Field(None, description="Entity ID from external API")
    current_step: str = Field(default="welcome", description="Current onboarding step")
    status: str = Field(default="active", description="Session status")
    
    # User data
    user_data: Dict[str, Any] = Field(default_factory=dict, description="User signup data")
    company_data: Dict[str, Any] = Field(default_factory=dict, description="Company details")
    kyc_data: Dict[str, Any] = Field(default_factory=dict, description="KYC verification data")
    bank_data: Dict[str, Any] = Field(default_factory=dict, description="Bank account data")
    
    # Messages history
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="Conversation messages")
    
    # Metadata
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "state_version": "1.0",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "entity_id": "ENT123456",
                "current_step": "kyc",
                "status": "active",
                "user_data": {"email": "user@example.com", "phone": "+1234567890"},
                "company_data": {},
                "kyc_data": {},
                "bank_data": {},
                "messages": [],
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z"
            }
        }


class EntityFeaturesModel(BaseModel):
    """
    Pydantic model for entity feature tracking with versioning
    """
    state_version: str = Field(default="1.0", description="State schema version")
    session_id: str = Field(..., description="Session identifier")
    entity_id: Optional[str] = Field(None, description="Entity ID")
    user_email: Optional[str] = Field(None, description="User email")
    user_phone: Optional[str] = Field(None, description="User phone")
    organization_name: Optional[str] = Field(None, description="Organization name")
    
    # Feature completion tracking
    signup_completed: bool = Field(default=False)
    kyc_completed: bool = Field(default=False)
    business_details_completed: bool = Field(default=False)
    bank_details_completed: bool = Field(default=False)
    onboarding_completed: bool = Field(default=False)
    
    # Feature data
    kyc_data: Optional[Dict[str, Any]] = Field(None, description="KYC data")
    business_data: Optional[Dict[str, Any]] = Field(None, description="Business data")
    bank_data: Optional[Dict[str, Any]] = Field(None, description="Bank data")
    
    # Timestamps
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "state_version": "1.0",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "entity_id": "ENT123456",
                "user_email": "user@example.com",
                "signup_completed": True,
                "kyc_completed": False,
                "onboarding_completed": False
            }
        }


def migrate_state(state_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate state from older versions to current version
    
    Args:
        state_data: Raw state dictionary from database
        
    Returns:
        Migrated state dictionary
    """
    # Get current version (default to "1.0" if not present - legacy data)
    version = state_data.get('state_version', '1.0')
    
    # Apply migrations based on version
    if version == '1.0':
        # Current version - no migration needed
        if 'state_version' not in state_data:
            state_data['state_version'] = '1.0'
        return state_data
    
    # Future migration logic would go here
    # elif version == '1.1':
    #     # Migrate from 1.1 to 2.0
    #     state_data = migrate_1_1_to_2_0(state_data)
    
    return state_data


def validate_and_migrate_state(state_data: Dict[str, Any]) -> OnboardingStateModel:
    """
    Validate and migrate state data, returning a Pydantic model
    
    Args:
        state_data: Raw state dictionary
        
    Returns:
        Validated OnboardingStateModel
    """
    # Migrate if needed
    migrated_data = migrate_state(state_data)
    
    # Validate with Pydantic
    try:
        return OnboardingStateModel(**migrated_data)
    except Exception as e:
        # If validation fails, log and return with defaults
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"State validation failed: {e}, using defaults")
        
        # Return a valid state with minimal required fields
        return OnboardingStateModel(
            session_id=migrated_data.get('session_id', 'unknown'),
            current_step=migrated_data.get('current_step', 'welcome'),
            status=migrated_data.get('status', 'active')
        )

