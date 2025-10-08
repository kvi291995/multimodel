"""
Company Details AI Agent
Handles company information collection and validation
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from agents.state.graph_state import GraphState, create_initial_state
from agents.subgraphs.validation_subgraph import validation_graph
from agents.subgraphs.api_subgraph import api_graph

logger = logging.getLogger(__name__)


class CompanyDetailsAgent:
    """
    AI agent for handling company details collection and validation.
    Supports hierarchical structure with specialized nodes.
    """
    
    def __init__(self):
        """Initialize the CompanyDetailsAgent"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("CompanyDetailsAgent initialized")
    
    def process_company_details(self, company_data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process company details with validation
        
        Args:
            company_data: Dictionary containing company information
            session_id: Optional session ID for tracking
            
        Returns:
            Dict containing processing result and status
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        self.logger.info(f"Processing company details for session: {session_id}")
        
        try:
            # Step 1: Detect company type
            company_type = self._detect_company_type(company_data)
            company_data['company_type'] = company_type
            
            # Step 2: Validate company data
            validation_result = self._validate_company_data(company_data)
            
            if not validation_result['success']:
                return {
                    'success': False,
                    'status': 'validation_failed',
                    'errors': validation_result['errors'],
                    'session_id': session_id,
                    'message': 'Please fix the validation errors and try again.'
                }
            
            # Step 3: Complete company details processing
            completion_result = self._complete_company_details(company_data)
            
            return {
                'success': True,
                'status': 'completed',
                'company_data': company_data,
                'company_type': company_type,
                'session_id': session_id,
                'message': f'Company details processed successfully for {company_type}',
                'completion_details': completion_result
            }
            
        except Exception as e:
            self.logger.error(f"Company details processing error: {str(e)}")
            return {
                'success': False,
                'status': 'error',
                'error': str(e),
                'session_id': session_id,
                'message': 'An error occurred during company details processing.'
            }
    
    def _detect_company_type(self, company_data: Dict[str, Any]) -> str:
        """Detect company type based on provided data"""
        company_name = company_data.get('company_name', '').lower()
        
        # Simple type detection logic
        if any(keyword in company_name for keyword in ['ltd', 'limited', 'corp', 'corporation']):
            return 'Corporation'
        elif any(keyword in company_name for keyword in ['llc', 'llp', 'partnership']):
            return 'LLC/Partnership'
        elif any(keyword in company_name for keyword in ['pvt', 'private']):
            return 'Private Limited'
        else:
            return 'Business Entity'
    
    def _validate_company_data(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate company data"""
        self.logger.info("Validating company data")
        
        errors = []
        
        # Validate required fields
        required_fields = ['company_name', 'registration_number', 'address']
        for field in required_fields:
            if not company_data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Validate company name length
        if company_data.get('company_name') and len(company_data['company_name']) < 3:
            errors.append("Company name must be at least 3 characters")
        
        # Validate registration number format
        reg_number = company_data.get('registration_number', '')
        if reg_number and not reg_number.replace('-', '').replace(' ', '').isalnum():
            errors.append("Invalid registration number format")
        
        return {
            'success': len(errors) == 0,
            'errors': errors
        }
    
    def _complete_company_details(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Complete company details processing"""
        self.logger.info(f"Completing company details for: {company_data.get('company_name')}")
        
        return {
            'completion_timestamp': datetime.now().isoformat(),
            'company_id': f"COMP_{uuid.uuid4().hex[:8].upper()}",
            'company_data': company_data,
            'status': 'completed'
        }
    
    def extract_company_data(self, message: str) -> Dict[str, Any]:
        """Extract company data from message"""
        extracted = {}
        
        # Extract company name
        company_name = self._extract_company_name(message)
        if company_name:
            extracted['company_name'] = company_name
        
        # Extract registration number
        reg_number = self._extract_registration_number(message)
        if reg_number:
            extracted['registration_number'] = reg_number
        
        # Extract address
        address = self._extract_address(message)
        if address:
            extracted['address'] = address
        
        return extracted
    
    def _extract_company_name(self, text: str) -> Optional[str]:
        """Extract company name from text"""
        # Simple extraction - look for patterns like "Company Name: XYZ"
        import re
        patterns = [
            r'company[:\s]+([A-Za-z\s&.,]+)',
            r'business[:\s]+([A-Za-z\s&.,]+)',
            r'organization[:\s]+([A-Za-z\s&.,]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_registration_number(self, text: str) -> Optional[str]:
        """Extract registration number from text"""
        import re
        patterns = [
            r'registration[:\s]+([A-Za-z0-9\-\s]+)',
            r'reg[:\s]+([A-Za-z0-9\-\s]+)',
            r'license[:\s]+([A-Za-z0-9\-\s]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_address(self, text: str) -> Optional[str]:
        """Extract address from text"""
        import re
        patterns = [
            r'address[:\s]+([A-Za-z0-9\s,.\-]+)',
            r'location[:\s]+([A-Za-z0-9\s,.\-]+)',
            r'headquarters[:\s]+([A-Za-z0-9\s,.\-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def get_company_status(self, session_id: str) -> Dict[str, Any]:
        """Get current company details status for a session"""
        # In a real implementation, this would retrieve from a database
        return {
            'session_id': session_id,
            'status': 'ready',
            'message': 'Company details agent ready'
        }
