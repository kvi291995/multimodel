"""
Signup AI Agent
Specialized agent for handling user signup processes with subgraph integration
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from agents.state.graph_state import GraphState, create_initial_state
from agents.subgraphs.validation_subgraph import validation_graph
from agents.subgraphs.api_subgraph import api_graph

logger = logging.getLogger(__name__)


class SignupAgent:
    """
    Specialized AI agent for handling user signup processes.
    Integrates with validation and API subgraphs for complete signup flow.
    """
    
    def __init__(self):
        """Initialize the SignupAgent"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("SignupAgent initialized")
    
    def process_signup(self, user_data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a complete signup request with user data
        
        Args:
            user_data: Dictionary containing user information (name, email, phone)
            session_id: Optional session ID for tracking
            
        Returns:
            Dict containing signup result and status
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        self.logger.info(f"Processing signup for session: {session_id}")
        
        try:
            # Step 1: Validate user data using validation subgraph
            validation_result = self._validate_user_data(user_data)
            
            if not validation_result['success']:
                return {
                    'success': False,
                    'status': 'validation_failed',
                    'errors': validation_result['errors'],
                    'session_id': session_id,
                    'message': 'Please fix the validation errors and try again.'
                }
            
            # Step 2: Generate entity ID using API subgraph
            api_result = self._generate_entity_id(user_data)
            
            if not api_result['success']:
                return {
                    'success': False,
                    'status': 'api_failed',
                    'error': api_result['error'],
                    'session_id': session_id,
                    'message': 'Failed to generate entity ID. Please try again.'
                }
            
            # Step 3: Complete signup
            signup_result = self._complete_signup(user_data, api_result['entity_id'])
            
            return {
                'success': True,
                'status': 'completed',
                'entity_id': api_result['entity_id'],
                'user_data': user_data,
                'session_id': session_id,
                'message': f'Signup completed successfully! Your entity ID is: {api_result["entity_id"]}',
                'signup_details': signup_result
            }
            
        except Exception as e:
            self.logger.error(f"Signup processing error: {str(e)}")
            return {
                'success': False,
                'status': 'error',
                'error': str(e),
                'session_id': session_id,
                'message': 'An error occurred during signup. Please try again.'
            }
    
    def process_conversational_signup(self, user_message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process conversational signup where user provides information step by step
        
        Args:
            user_message: User's input message
            session_id: Optional session ID for tracking
            
        Returns:
            Dict containing response and updated state
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        self.logger.info(f"Processing conversational signup for session: {session_id}")
        
        # Get or create session state
        session_state = self._get_session_state(session_id)
        
        # Extract information from user message
        extracted_data = self._extract_user_data(user_message)
        
        # Update session state with extracted data
        session_state.update(extracted_data)
        
        # Check if we have all required information
        if self._has_all_required_data(session_state):
            # Process complete signup
            return self.process_signup(session_state, session_id)
        else:
            # Continue conversation to collect missing data
            return self._continue_conversation(session_state, session_id)
    
    def _validate_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user data using validation subgraph"""
        self.logger.info("Validating user data using validation subgraph")
        
        validation_input = {
            'name': user_data.get('name'),
            'email': user_data.get('email'),
            'phone': user_data.get('phone'),
            'errors': []
        }
        
        try:
            result = validation_graph.invoke(validation_input)
            
            return {
                'success': result.get('validation_complete', False),
                'name_valid': result.get('name_valid', False),
                'email_valid': result.get('email_valid', False),
                'phone_valid': result.get('phone_valid', False),
                'errors': result.get('errors', [])
            }
        except Exception as e:
            self.logger.error(f"Validation subgraph error: {str(e)}")
            return {
                'success': False,
                'errors': [f'Validation error: {str(e)}']
            }
    
    def _generate_entity_id(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate entity ID using API subgraph"""
        self.logger.info("Generating entity ID using API subgraph")
        
        api_input = {
            'user_data': user_data,
            'api_url': 'http://localhost:8000',
            'retry_count': 0
        }
        
        try:
            result = api_graph.invoke(api_input)
            
            return {
                'success': result.get('success', False),
                'entity_id': result.get('entity_id'),
                'error': result.get('error_message') if not result.get('success') else None
            }
        except Exception as e:
            self.logger.error(f"API subgraph error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _complete_signup(self, user_data: Dict[str, Any], entity_id: str) -> Dict[str, Any]:
        """Complete the signup process"""
        self.logger.info(f"Completing signup for entity ID: {entity_id}")
        
        # Here you would typically:
        # 1. Save user data to database
        # 2. Send welcome email
        # 3. Set up user account
        # 4. Log signup event
        
        return {
            'signup_timestamp': datetime.now().isoformat(),
            'entity_id': entity_id,
            'user_data': user_data,
            'status': 'completed'
        }
    
    def _get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Get or create session state"""
        # In a real implementation, this would retrieve from a database
        # For now, we'll use a simple in-memory approach
        if not hasattr(self, '_session_states'):
            self._session_states = {}
        
        if session_id not in self._session_states:
            self._session_states[session_id] = create_initial_state(session_id)
        
        return self._session_states[session_id]
    
    def _extract_user_data(self, message: str) -> Dict[str, Any]:
        """Extract user data from message"""
        extracted = {}
        
        # Extract name
        name = self._extract_name(message)
        if name:
            extracted['name'] = name
        
        # Extract email
        email = self._extract_email(message)
        if email:
            extracted['email'] = email
        
        # Extract phone
        phone = self._extract_phone(message)
        if phone:
            extracted['phone'] = phone
        
        return extracted
    
    def _extract_name(self, text: str) -> Optional[str]:
        """Extract name from text"""
        words = text.strip().split()
        if len(words) >= 2:
            return ' '.join(words[:2])
        elif len(words) == 1 and len(words[0]) > 1:
            return words[0]
        return None
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email from text"""
        import re
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(pattern, text)
        return match.group() if match else None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone from text"""
        import re
        pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        match = re.search(pattern, text)
        return match.group() if match else None
    
    def _has_all_required_data(self, session_state: Dict[str, Any]) -> bool:
        """Check if session has all required data"""
        required_fields = ['name', 'email', 'phone']
        return all(session_state.get(field) for field in required_fields)
    
    def _continue_conversation(self, session_state: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Continue conversation to collect missing data"""
        missing_fields = []
        
        if not session_state.get('name'):
            missing_fields.append('name')
        if not session_state.get('email'):
            missing_fields.append('email')
        if not session_state.get('phone'):
            missing_fields.append('phone')
        
        if not missing_fields:
            # All data collected, process signup
            return self.process_signup(session_state, session_id)
        
        # Generate appropriate response based on missing fields
        if 'name' in missing_fields:
            message = "What's your full name?"
        elif 'email' in missing_fields:
            message = "What's your email address?"
        elif 'phone' in missing_fields:
            message = "What's your phone number?"
        else:
            message = "I need a bit more information to complete your signup."
        
        return {
            'success': False,
            'status': 'collecting_data',
            'message': message,
            'session_id': session_id,
            'missing_fields': missing_fields,
            'current_data': session_state
        }
    
    def get_signup_status(self, session_id: str) -> Dict[str, Any]:
        """Get current signup status for a session"""
        session_state = self._get_session_state(session_id)
        
        return {
            'session_id': session_id,
            'has_name': bool(session_state.get('name')),
            'has_email': bool(session_state.get('email')),
            'has_phone': bool(session_state.get('phone')),
            'is_complete': self._has_all_required_data(session_state),
            'current_data': session_state
        }
    
    def reset_signup(self, session_id: str) -> Dict[str, Any]:
        """Reset signup for a session"""
        if hasattr(self, '_session_states') and session_id in self._session_states:
            del self._session_states[session_id]
        
        return {
            'success': True,
            'message': 'Signup reset successfully',
            'session_id': session_id
        }
