"""
KYC (Know Your Customer) AI Agent
Handles KYC processes with sub-agents for different document types
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from agents.state.graph_state import GraphState, create_initial_state
from agents.subgraphs.validation_subgraph import validation_graph
from agents.subgraphs.api_subgraph import api_graph

logger = logging.getLogger(__name__)


class KYCAgent:
    """
    KYC AI agent that coordinates different KYC sub-agents.
    Supports hierarchical structure with specialized sub-agents.
    """
    
    def __init__(self):
        """Initialize the KYCAgent"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("KYCAgent initialized")
        
        # Initialize sub-agents
        self.pan_agent = KYCPanAgent()
        self.aadhar_agent = KYCAadharAgent()
        self.gst_agent = KYCGSTAgent()
    
    def process_kyc(self, kyc_data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process KYC with appropriate sub-agents
        
        Args:
            kyc_data: Dictionary containing KYC information
            session_id: Optional session ID for tracking
            
        Returns:
            Dict containing KYC processing result
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        self.logger.info(f"Processing KYC for session: {session_id}")
        
        try:
            # Step 1: Detect KYC requirements
            requirements = self._detect_kyc_requirements(kyc_data)
            
            # Step 2: Coordinate KYC sub-agents
            kyc_results = {}
            
            if requirements.get('pan_required'):
                kyc_results['pan'] = self.pan_agent.process_pan(kyc_data.get('pan_data', {}))
            
            if requirements.get('aadhar_required'):
                kyc_results['aadhar'] = self.aadhar_agent.process_aadhar(kyc_data.get('aadhar_data', {}))
            
            if requirements.get('gst_required'):
                kyc_results['gst'] = self.gst_agent.process_gst(kyc_data.get('gst_data', {}))
            
            # Step 3: Validate overall KYC completion
            validation_result = self._validate_kyc_completion(kyc_results, requirements)
            
            if validation_result['success']:
                return {
                    'success': True,
                    'status': 'completed',
                    'kyc_results': kyc_results,
                    'requirements': requirements,
                    'session_id': session_id,
                    'message': 'KYC process completed successfully',
                    'kyc_id': f"KYC_{uuid.uuid4().hex[:8].upper()}"
                }
            else:
                return {
                    'success': False,
                    'status': 'incomplete',
                    'kyc_results': kyc_results,
                    'missing_requirements': validation_result['missing'],
                    'session_id': session_id,
                    'message': 'KYC process incomplete. Please provide missing documents.'
                }
            
        except Exception as e:
            self.logger.error(f"KYC processing error: {str(e)}")
            return {
                'success': False,
                'status': 'error',
                'error': str(e),
                'session_id': session_id,
                'message': 'An error occurred during KYC processing.'
            }
    
    def _detect_kyc_requirements(self, kyc_data: Dict[str, Any]) -> Dict[str, bool]:
        """Detect what KYC documents are required"""
        requirements = {
            'pan_required': bool(kyc_data.get('pan_data')),
            'aadhar_required': bool(kyc_data.get('aadhar_data')),
            'gst_required': bool(kyc_data.get('gst_data'))
        }
        
        # Auto-detect based on business type
        business_type = kyc_data.get('business_type', '').lower()
        if 'company' in business_type or 'corp' in business_type:
            requirements['gst_required'] = True
        
        return requirements
    
    def _validate_kyc_completion(self, kyc_results: Dict[str, Any], requirements: Dict[str, bool]) -> Dict[str, Any]:
        """Validate KYC completion"""
        missing = []
        
        for req_type, required in requirements.items():
            if required and not kyc_results.get(req_type.replace('_required', ''), {}).get('success'):
                missing.append(req_type.replace('_required', ''))
        
        return {
            'success': len(missing) == 0,
            'missing': missing
        }


class KYCPanAgent:
    """KYC PAN sub-agent"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process_pan(self, pan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process PAN document"""
        self.logger.info("Processing PAN document")
        
        pan_number = pan_data.get('pan_number', '')
        
        # Validate PAN format
        if self._validate_pan_format(pan_number):
            return {
                'success': True,
                'pan_number': pan_number,
                'status': 'verified',
                'message': 'PAN document processed successfully'
            }
        else:
            return {
                'success': False,
                'error': 'Invalid PAN format',
                'message': 'Please provide a valid PAN number'
            }
    
    def _validate_pan_format(self, pan_number: str) -> bool:
        """Validate PAN number format"""
        import re
        pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
        return bool(re.match(pattern, pan_number))


class KYCAadharAgent:
    """KYC Aadhar sub-agent"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process_aadhar(self, aadhar_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Aadhar document"""
        self.logger.info("Processing Aadhar document")
        
        aadhar_number = aadhar_data.get('aadhar_number', '')
        
        # Validate Aadhar format
        if self._validate_aadhar_format(aadhar_number):
            return {
                'success': True,
                'aadhar_number': aadhar_number,
                'status': 'verified',
                'message': 'Aadhar document processed successfully'
            }
        else:
            return {
                'success': False,
                'error': 'Invalid Aadhar format',
                'message': 'Please provide a valid Aadhar number'
            }
    
    def _validate_aadhar_format(self, aadhar_number: str) -> bool:
        """Validate Aadhar number format"""
        import re
        pattern = r'^\d{12}$'
        return bool(re.match(pattern, aadhar_number))


class KYCGSTAgent:
    """KYC GST sub-agent"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process_gst(self, gst_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process GST document"""
        self.logger.info("Processing GST document")
        
        gst_number = gst_data.get('gst_number', '')
        
        # Validate GST format
        if self._validate_gst_format(gst_number):
            return {
                'success': True,
                'gst_number': gst_number,
                'status': 'verified',
                'message': 'GST document processed successfully'
            }
        else:
            return {
                'success': False,
                'error': 'Invalid GST format',
                'message': 'Please provide a valid GST number'
            }
    
    def _validate_gst_format(self, gst_number: str) -> bool:
        """Validate GST number format"""
        import re
        pattern = r'^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$'
        return bool(re.match(pattern, gst_number))
