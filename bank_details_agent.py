"""
Bank Details AI Agent
Handles bank account information collection and validation
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from agents.state.graph_state import GraphState, create_initial_state
from agents.subgraphs.validation_subgraph import validation_graph
from agents.subgraphs.api_subgraph import api_graph

logger = logging.getLogger(__name__)


class BankDetailsAgent:
    """
    AI agent for handling bank details collection and validation.
    Supports hierarchical structure with specialized nodes.
    """
    
    def __init__(self):
        """Initialize the BankDetailsAgent"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("BankDetailsAgent initialized")
    
    def process_bank_details(self, bank_data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process bank details with validation
        
        Args:
            bank_data: Dictionary containing bank information
            session_id: Optional session ID for tracking
            
        Returns:
            Dict containing processing result and status
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        self.logger.info(f"Processing bank details for session: {session_id}")
        
        try:
            # Step 1: Validate bank data
            validation_result = self._validate_bank_data(bank_data)
            
            if not validation_result['success']:
                return {
                    'success': False,
                    'status': 'validation_failed',
                    'errors': validation_result['errors'],
                    'session_id': session_id,
                    'message': 'Please fix the validation errors and try again.'
                }
            
            # Step 2: Complete bank details processing
            completion_result = self._complete_bank_details(bank_data)
            
            return {
                'success': True,
                'status': 'completed',
                'bank_data': bank_data,
                'session_id': session_id,
                'message': 'Bank details processed successfully',
                'completion_details': completion_result
            }
            
        except Exception as e:
            self.logger.error(f"Bank details processing error: {str(e)}")
            return {
                'success': False,
                'status': 'error',
                'error': str(e),
                'session_id': session_id,
                'message': 'An error occurred during bank details processing.'
            }
    
    def _validate_bank_data(self, bank_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate bank data"""
        self.logger.info("Validating bank data")
        
        errors = []
        
        # Validate required fields
        required_fields = ['account_holder_name', 'account_number', 'ifsc_code', 'bank_name']
        for field in required_fields:
            if not bank_data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Validate account number
        account_number = bank_data.get('account_number', '')
        if account_number and not account_number.isdigit():
            errors.append("Account number must contain only digits")
        
        # Validate IFSC code format
        ifsc_code = bank_data.get('ifsc_code', '')
        if ifsc_code and not self._validate_ifsc_format(ifsc_code):
            errors.append("Invalid IFSC code format")
        
        # Validate account holder name
        account_holder = bank_data.get('account_holder_name', '')
        if account_holder and len(account_holder.strip()) < 2:
            errors.append("Account holder name must be at least 2 characters")
        
        return {
            'success': len(errors) == 0,
            'errors': errors
        }
    
    def _validate_ifsc_format(self, ifsc_code: str) -> bool:
        """Validate IFSC code format"""
        import re
        pattern = r'^[A-Z]{4}0[A-Z0-9]{6}$'
        return bool(re.match(pattern, ifsc_code))
    
    def _complete_bank_details(self, bank_data: Dict[str, Any]) -> Dict[str, Any]:
        """Complete bank details processing"""
        self.logger.info(f"Completing bank details for: {bank_data.get('account_holder_name')}")
        
        return {
            'completion_timestamp': datetime.now().isoformat(),
            'bank_id': f"BANK_{uuid.uuid4().hex[:8].upper()}",
            'bank_data': bank_data,
            'status': 'completed'
        }
    
    def extract_bank_data(self, message: str) -> Dict[str, Any]:
        """Extract bank data from message"""
        extracted = {}
        
        # Extract account holder name
        account_holder = self._extract_account_holder(message)
        if account_holder:
            extracted['account_holder_name'] = account_holder
        
        # Extract account number
        account_number = self._extract_account_number(message)
        if account_number:
            extracted['account_number'] = account_number
        
        # Extract IFSC code
        ifsc_code = self._extract_ifsc_code(message)
        if ifsc_code:
            extracted['ifsc_code'] = ifsc_code
        
        # Extract bank name
        bank_name = self._extract_bank_name(message)
        if bank_name:
            extracted['bank_name'] = bank_name
        
        return extracted
    
    def _extract_account_holder(self, text: str) -> Optional[str]:
        """Extract account holder name from text"""
        import re
        patterns = [
            r'account[:\s]+holder[:\s]+([A-Za-z\s]+)',
            r'name[:\s]+([A-Za-z\s]+)',
            r'holder[:\s]+([A-Za-z\s]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_account_number(self, text: str) -> Optional[str]:
        """Extract account number from text"""
        import re
        patterns = [
            r'account[:\s]+number[:\s]+(\d+)',
            r'acc[:\s]+no[:\s]+(\d+)',
            r'account[:\s]+(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_ifsc_code(self, text: str) -> Optional[str]:
        """Extract IFSC code from text"""
        import re
        patterns = [
            r'ifsc[:\s]+([A-Z0-9]+)',
            r'code[:\s]+([A-Z0-9]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip().upper()
        
        return None
    
    def _extract_bank_name(self, text: str) -> Optional[str]:
        """Extract bank name from text"""
        import re
        patterns = [
            r'bank[:\s]+([A-Za-z\s]+)',
            r'institution[:\s]+([A-Za-z\s]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def get_bank_status(self, session_id: str) -> Dict[str, Any]:
        """Get current bank details status for a session"""
        return {
            'session_id': session_id,
            'status': 'ready',
            'message': 'Bank details agent ready'
        }
