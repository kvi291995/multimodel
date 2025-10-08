"""
Supervised Multi-Agent Onboarding System with LLM Integration
Uses Google Gemini for intelligent routing and processing
"""

import logging
import uuid
import os
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END, MessagesState
import google.generativeai as genai

from agents.signup_agent import SignupAgent
from agents.company_details_agent import CompanyDetailsAgent
from agents.kyc_agent import KYCAgent
from agents.bank_details_agent import BankDetailsAgent
from agents.constants import *
from config.llm_prompts import *

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))


class OnboardingState(MessagesState):
    """State for the supervised onboarding system"""
    next_agent: str = ""
    
    # Completion flags
    signup_complete: bool = False
    company_complete: bool = False
    kyc_complete: bool = False
    bank_complete: bool = False
    
    # Data storage
    signup_data: dict = {}
    company_data: dict = {}
    kyc_data: dict = {}
    bank_data: dict = {}
    
    # Metadata
    task_complete: bool = False
    current_task: str = ""
    session_id: str = ""
    onboarding_id: str = ""


class SupervisedOnboardingSystemWithLLM:
    """
    Supervised Onboarding System with Google Gemini Integration
    Uses LLM for intelligent routing, data extraction, and processing
    """
    
    def __init__(self, model_name: str = DEFAULT_MODEL):
        """Initialize the supervised onboarding system with LLM"""
        self.logger = logging.getLogger(__name__)
        self.model = genai.GenerativeModel(model_name)
        
        # Initialize child agents (still used for validation and API calls)
        self.signup_agent = SignupAgent()
        self.company_agent = CompanyDetailsAgent()
        self.kyc_agent = KYCAgent()
        self.bank_agent = BankDetailsAgent()
        
        # Build the graph
        self.graph = self._build_graph()
        
        self.logger.info(f"SupervisedOnboardingSystemWithLLM initialized with {model_name}")
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(OnboardingState)
        
        # Add nodes
        workflow.add_node("supervisor", self._supervisor_agent)
        workflow.add_node("signup", self._signup_node)
        workflow.add_node("company", self._company_node)
        workflow.add_node("kyc", self._kyc_node)
        workflow.add_node("bank", self._bank_node)
        workflow.add_node("complete", self._complete_node)
        
        # Set entry point
        workflow.set_entry_point("supervisor")
        
        # Add routing from each node back to supervisor
        for node in ["supervisor", "signup", "company", "kyc", "bank", "complete"]:
            workflow.add_conditional_edges(
                node,
                self._router,
                {
                    "supervisor": "supervisor",
                    "signup": "signup",
                    "company": "company",
                    "kyc": "kyc",
                    "bank": "bank",
                    "complete": "complete",
                    END: END
                }
            )
        
        return workflow.compile()
    
    def _call_llm(self, system_prompt: str, user_message: str, max_retries: int = LLM_MAX_RETRIES) -> str:
        """Call Gemini LLM with system and user prompts, with retry logic"""
        full_prompt = f"{system_prompt}\n\n{user_message}"
        
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(full_prompt)
                return response.text.strip()
            except Exception as e:
                self.logger.warning(f"LLM call attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.logger.error(f"LLM call failed after {max_retries} attempts")
                    return ""
    
    def _supervisor_agent(self, state: OnboardingState) -> Dict[str, Any]:
        """
        Supervisor uses LLM to decide which agent to route to
        """
        self.logger.info("🎯 Supervisor: Using LLM for routing decision...")
        
        # Get completion state
        has_signup = state.get("signup_complete", False)
        has_company = state.get("company_complete", False)
        has_kyc = state.get("kyc_complete", False)
        has_bank = state.get("bank_complete", False)
        
        # Prepare context for LLM
        context = f"""
CURRENT ONBOARDING STATUS:
- Signup: {'✅ Complete' if has_signup else '❌ Incomplete'}
- Company Details: {'✅ Complete' if has_company else '❌ Incomplete'}
- KYC Verification: {'✅ Complete' if has_kyc else '❌ Incomplete'}
- Bank Details: {'✅ Complete' if has_bank else '❌ Incomplete'}

CONVERSATION HISTORY:
{self._get_conversation_summary(state)}

What is the next agent that should process this request?
Remember: Follow the sequential workflow strictly.
"""
        
        # Get LLM decision
        llm_decision = self._call_llm(SUPERVISOR_SYSTEM_PROMPT, context).lower()
        
        # Parse decision
        if AGENT_SIGNUP in llm_decision or not has_signup:
            next_agent = AGENT_SIGNUP
            supervisor_msg = "📋 Supervisor: Starting with signup process..."
        elif AGENT_COMPANY in llm_decision or (has_signup and not has_company):
            next_agent = AGENT_COMPANY
            supervisor_msg = "📋 Supervisor: Signup complete. Moving to company details..."
        elif AGENT_KYC in llm_decision or (has_company and not has_kyc):
            next_agent = AGENT_KYC
            supervisor_msg = "📋 Supervisor: Company details complete. Starting KYC verification..."
        elif AGENT_BANK in llm_decision or (has_kyc and not has_bank):
            next_agent = AGENT_BANK
            supervisor_msg = "📋 Supervisor: KYC complete. Collecting bank details..."
        elif AGENT_COMPLETE in llm_decision or (has_signup and has_company and has_kyc and has_bank):
            next_agent = AGENT_COMPLETE
            supervisor_msg = "✅ Supervisor: All steps complete! Finalizing onboarding..."
        else:
            next_agent = AGENT_END
            supervisor_msg = "✅ Supervisor: Onboarding completed successfully!"
        
        self.logger.info(f"LLM Decision: {llm_decision} → Routing to: {next_agent}")
        self.logger.info(supervisor_msg)
        
        return {
            "next_agent": next_agent,
            "current_task": supervisor_msg
        }
    
    def _get_conversation_summary(self, state: OnboardingState) -> str:
        """Get a summary of the conversation"""
        messages = state.get("messages", [])
        if not messages:
            return "No conversation yet."
        
        # Get last 3 messages
        recent_messages = messages[-3:] if len(messages) >= 3 else messages
        summary = []
        for msg in recent_messages:
            content = msg.content if hasattr(msg, 'content') else str(msg)
            summary.append(f"- {content[:100]}...")
        
        return "\n".join(summary)
    
    def _extract_data_with_llm(self, prompt_template: str, user_input: str) -> dict:
        """Extract structured data using LLM"""
        try:
            prompt = prompt_template.format(message=user_input)
            response = self._call_llm("", prompt)
            
            # Clean up response (remove markdown code blocks if present)
            cleaned = response.replace('```json', '').replace('```', '').strip()
            
            # Parse JSON
            data = json.loads(cleaned)
            return data
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response: {response}")
            return {}
        except Exception as e:
            self.logger.error(f"Data extraction failed: {str(e)}")
            return {}
    
    def _signup_node(self, state: OnboardingState) -> Dict[str, Any]:
        """Process signup using LLM for data extraction"""
        self.logger.info("👤 Signup Agent: Using LLM for data extraction...")
        
        try:
            # Get user input
            messages = state.get("messages", [])
            if messages:
                user_input = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
            else:
                user_input = ""
            
            # Extract data using LLM
            extracted_data = self._extract_data_with_llm(SIGNUP_EXTRACTION_PROMPT, user_input)
            
            self.logger.info(f"LLM Extracted: {extracted_data}")
            
            # Validate and process using existing agent
            result = self.signup_agent.process_signup(
                extracted_data,
                state.get("session_id", str(uuid.uuid4()))
            )
            
            return {
                "signup_complete": result.get('success', False),
                "signup_data": extracted_data,
                "next_agent": "supervisor",
                "current_task": "Signup processing completed with LLM extraction"
            }
            
        except Exception as e:
            self.logger.error(f"Signup error: {str(e)}")
            return {
                "signup_complete": False,
                "next_agent": "supervisor",
                "current_task": f"Signup error: {str(e)}"
            }
    
    def _company_node(self, state: OnboardingState) -> Dict[str, Any]:
        """Process company details using LLM for data extraction"""
        self.logger.info("🏢 Company Agent: Using LLM for data extraction...")
        
        try:
            messages = state.get("messages", [])
            if messages:
                user_input = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
            else:
                user_input = ""
            
            # Extract data using LLM
            extracted_data = self._extract_data_with_llm(COMPANY_EXTRACTION_PROMPT, user_input)
            
            self.logger.info(f"LLM Extracted: {extracted_data}")
            
            result = self.company_agent.process_company_details(
                extracted_data,
                state.get("session_id", str(uuid.uuid4()))
            )
            
            return {
                "company_complete": result.get('success', False),
                "company_data": extracted_data,
                "next_agent": "supervisor",
                "current_task": "Company details processed with LLM extraction"
            }
            
        except Exception as e:
            self.logger.error(f"Company details error: {str(e)}")
            return {
                "company_complete": False,
                "next_agent": "supervisor",
                "current_task": f"Company error: {str(e)}"
            }
    
    def _kyc_node(self, state: OnboardingState) -> Dict[str, Any]:
        """Process KYC using LLM for data extraction"""
        self.logger.info("📄 KYC Agent: Using LLM for data extraction...")
        
        try:
            messages = state.get("messages", [])
            if messages:
                user_input = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
            else:
                user_input = ""
            
            # Extract data using LLM
            extracted_data = self._extract_data_with_llm(KYC_EXTRACTION_PROMPT, user_input)
            
            self.logger.info(f"LLM Extracted: {extracted_data}")
            
            result = self.kyc_agent.process_kyc(
                extracted_data,
                state.get("session_id", str(uuid.uuid4()))
            )
            
            return {
                "kyc_complete": result.get('success', False),
                "kyc_data": extracted_data,
                "next_agent": "supervisor",
                "current_task": "KYC processed with LLM extraction"
            }
            
        except Exception as e:
            self.logger.error(f"KYC error: {str(e)}")
            return {
                "kyc_complete": False,
                "next_agent": "supervisor",
                "current_task": f"KYC error: {str(e)}"
            }
    
    def _bank_node(self, state: OnboardingState) -> Dict[str, Any]:
        """Process bank details using LLM for data extraction"""
        self.logger.info("🏦 Bank Agent: Using LLM for data extraction...")
        
        try:
            messages = state.get("messages", [])
            if messages:
                user_input = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
            else:
                user_input = ""
            
            # Extract data using LLM
            extracted_data = self._extract_data_with_llm(BANK_EXTRACTION_PROMPT, user_input)
            
            self.logger.info(f"LLM Extracted: {extracted_data}")
            
            result = self.bank_agent.process_bank_details(
                extracted_data,
                state.get("session_id", str(uuid.uuid4()))
            )
            
            return {
                "bank_complete": result.get('success', False),
                "bank_data": extracted_data,
                "next_agent": "supervisor",
                "current_task": "Bank details processed with LLM extraction"
            }
            
        except Exception as e:
            self.logger.error(f"Bank details error: {str(e)}")
            return {
                "bank_complete": False,
                "next_agent": "supervisor",
                "current_task": f"Bank error: {str(e)}"
            }
    
    def _complete_node(self, state: OnboardingState) -> Dict[str, Any]:
        """Complete the onboarding process"""
        self.logger.info("✅ Completion Agent: Finalizing onboarding...")
        
        onboarding_id = f"ONB_{uuid.uuid4().hex[:8].upper()}"
        
        completion_message = f"""
🎉 ONBOARDING COMPLETED SUCCESSFULLY!

Onboarding ID: {onboarding_id}
Session ID: {state.get('session_id', 'N/A')}
Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✓ Signup: Complete
✓ Company Details: Complete
✓ KYC Verification: Complete
✓ Bank Details: Complete

All steps completed! You can now access the platform.
"""
        
        return {
            "task_complete": True,
            "next_agent": "end",
            "onboarding_id": onboarding_id,
            "current_task": completion_message
        }
    
    def _router(self, state: OnboardingState) -> str:
        """Route to next agent based on state"""
        next_agent = state.get("next_agent", AGENT_SUPERVISOR)
        
        if state.get("task_complete", False):
            return END
        
        return next_agent
    
    def process_onboarding(self, user_message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Process a user message through the onboarding workflow"""
        if not session_id:
            session_id = str(uuid.uuid4())
        
        self.logger.info(f"Processing onboarding for session: {session_id}")
        
        try:
            # Create initial state
            initial_state = {
                "messages": [{"role": "user", "content": user_message}],
                "session_id": session_id,
                "next_agent": "supervisor"
            }
            
            # Run the graph with recursion limit
            config = {"recursion_limit": 50}
            result = self.graph.invoke(initial_state, config)
            
            return {
                "message": result.get("current_task", "Processing..."),
                "session_id": session_id,
                "status": STATUS_COMPLETED if result.get("task_complete") else STATUS_IN_PROGRESS,
                "onboarding_id": result.get("onboarding_id"),
                "signup_complete": result.get("signup_complete", False),
                "company_complete": result.get("company_complete", False),
                "kyc_complete": result.get("kyc_complete", False),
                "bank_complete": result.get("bank_complete", False)
            }
            
        except Exception as e:
            self.logger.error(f"Error processing onboarding: {str(e)}")
            return {
                "message": MSG_ERROR,
                "session_id": session_id,
                "status": STATUS_ERROR,
                "error": str(e)
            }
    
    def get_graph_visualization(self) -> Optional[bytes]:
        """Get PNG visualization of the graph"""
        try:
            return self.graph.get_graph().draw_mermaid_png()
        except Exception as e:
            self.logger.error(f"Visualization error: {str(e)}")
            return None

