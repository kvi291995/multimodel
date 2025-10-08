"""
LLM Agent Nodes
Nodes that use LLMs for intelligent processing in the graph
"""

import logging
from typing import Dict, Any, Optional, List
from agents.llm.llm_manager import LLMManager

logger = logging.getLogger(__name__)


class LLMAgentNode:
    """
    Base class for LLM-powered agent nodes
    """
    
    def __init__(
        self,
        llm_manager: LLMManager,
        agent_name: str,
        system_prompt: Optional[str] = None
    ):
        """
        Initialize LLM Agent Node
        
        Args:
            llm_manager: LLM manager instance
            agent_name: Name of this agent
            system_prompt: System prompt for this agent
        """
        self.llm_manager = llm_manager
        self.agent_name = agent_name
        self.system_prompt = system_prompt or self._get_default_system_prompt()
        self.logger = logging.getLogger(f"{__name__}.{agent_name}")
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt"""
        return "You are a helpful AI assistant."
    
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process state through LLM
        
        Args:
            state: Current graph state
            
        Returns:
            Updated state
        """
        raise NotImplementedError("Subclasses must implement __call__")


class WelcomeAgentNode(LLMAgentNode):
    """
    Welcome agent powered by LLM
    """
    
    def _get_default_system_prompt(self) -> str:
        return """You are a friendly onboarding assistant. 
Your role is to welcome users and guide them through the onboarding process.
Keep your responses warm, professional, and concise."""
    
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate personalized welcome message"""
        self.logger.info("Generating welcome message with LLM")
        
        try:
            prompt = "Generate a friendly welcome message for a new user starting the onboarding process. Ask for their name."
            
            response = self.llm_manager.generate(
                prompt=prompt,
                system_message=self.system_prompt
            )
            
            message = {
                "role": "assistant",
                "content": response
            }
            
            state['messages'] = state.get('messages', []) + [message]
            state['current_step'] = 'welcome'
            
        except Exception as e:
            self.logger.error(f"Error in welcome agent: {str(e)}")
            # Fallback message
            message = {
                "role": "assistant",
                "content": "Welcome! I'm here to help you get started. What's your name?"
            }
            state['messages'] = state.get('messages', []) + [message]
        
        return state


class ConversationalAgentNode(LLMAgentNode):
    """
    Conversational agent that can handle natural dialogue
    """
    
    def _get_default_system_prompt(self) -> str:
        return """You are an intelligent onboarding assistant that helps users complete their registration.

Your tasks:
1. Collect user information: name, email, phone
2. Be conversational and natural
3. Handle clarifications and corrections
4. Extract information from natural language
5. Validate responses politely

Keep responses concise and friendly."""
    
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process user input conversationally"""
        self.logger.info("Processing with conversational agent")
        
        try:
            # Get conversation history
            messages = state.get('messages', [])
            current_step = state.get('current_step', 'welcome')
            
            # Build context
            context_info = self._build_context(state)
            
            # Get last user message
            user_message = messages[-1].get('content', '') if messages else ''
            
            # Generate prompt based on current step
            prompt = self._build_prompt(current_step, user_message, context_info)
            
            # Get conversation context (last 5 messages)
            conversation_context = messages[-5:] if len(messages) > 5 else messages
            
            # Generate response
            response = self.llm_manager.generate(
                prompt=prompt,
                system_message=self.system_prompt,
                context=conversation_context
            )
            
            # Add to messages
            message = {
                "role": "assistant",
                "content": response
            }
            
            state['messages'] = messages + [message]
            
        except Exception as e:
            self.logger.error(f"Error in conversational agent: {str(e)}")
            message = {
                "role": "assistant",
                "content": "I'm having trouble understanding. Could you please try again?"
            }
            state['messages'] = state.get('messages', []) + [message]
        
        return state
    
    def _build_context(self, state: Dict[str, Any]) -> str:
        """Build context information about current state"""
        context_parts = []
        
        if state.get('name'):
            context_parts.append(f"Name: {state['name']}")
        if state.get('email'):
            context_parts.append(f"Email: {state['email']}")
        if state.get('phone'):
            context_parts.append(f"Phone: {state['phone']}")
        
        return " | ".join(context_parts) if context_parts else "No information collected yet"
    
    def _build_prompt(
        self,
        current_step: str,
        user_message: str,
        context_info: str
    ) -> str:
        """Build prompt based on current step"""
        
        step_prompts = {
            'welcome': "The user just started. Greet them and ask for their name.",
            'collect_name': f"User said: '{user_message}'. Extract their name. If you can't find it, politely ask again.",
            'collect_email': f"Current info: {context_info}. User said: '{user_message}'. Extract their email. If invalid, politely ask again.",
            'collect_phone': f"Current info: {context_info}. User said: '{user_message}'. Extract their phone number. If invalid, politely ask again.",
            'validation': f"Information collected: {context_info}. Inform the user you're validating their information.",
            'complete': f"User has completed onboarding. Their entity ID is {context_info}. Thank them!"
        }
        
        return step_prompts.get(current_step, user_message)


class DataExtractionAgentNode(LLMAgentNode):
    """
    Specialized agent for extracting structured data from natural language
    """
    
    def _get_default_system_prompt(self) -> str:
        return """You are a data extraction specialist. 
Your job is to extract specific information from user messages.
Return ONLY the extracted information, nothing else.
If you cannot find the information, return "NOT_FOUND"."""
    
    def extract_field(
        self,
        user_message: str,
        field_type: str
    ) -> Optional[str]:
        """
        Extract a specific field from user message
        
        Args:
            user_message: User's message
            field_type: Type of field to extract (name, email, phone)
            
        Returns:
            Extracted value or None
        """
        self.logger.info(f"Extracting {field_type} from message")
        
        try:
            prompts = {
                'name': f"Extract the person's full name from this message: '{user_message}'. Return ONLY the name or NOT_FOUND.",
                'email': f"Extract the email address from this message: '{user_message}'. Return ONLY the email or NOT_FOUND.",
                'phone': f"Extract the phone number from this message: '{user_message}'. Return ONLY the phone number or NOT_FOUND."
            }
            
            response = self.llm_manager.generate(
                prompt=prompts.get(field_type, user_message),
                system_message=self.system_prompt
            ).strip()
            
            if response and response != "NOT_FOUND":
                return response
            
        except Exception as e:
            self.logger.error(f"Error extracting {field_type}: {str(e)}")
        
        return None


class ValidationAgentNode(LLMAgentNode):
    """
    Agent that provides intelligent validation feedback
    """
    
    def _get_default_system_prompt(self) -> str:
        return """You are a validation assistant. 
When given validation errors, provide friendly, helpful feedback to users.
Be specific about what needs to be fixed and why.
Keep your response concise and actionable."""
    
    def generate_validation_feedback(
        self,
        validation_errors: List[str],
        field_name: str
    ) -> str:
        """
        Generate friendly validation feedback
        
        Args:
            validation_errors: List of validation error messages
            field_name: Name of the field with errors
            
        Returns:
            Friendly feedback message
        """
        self.logger.info(f"Generating validation feedback for {field_name}")
        
        try:
            errors_text = "\n".join([f"- {err}" for err in validation_errors])
            
            prompt = f"""The user provided invalid {field_name}. 
Validation errors:
{errors_text}

Generate a friendly, helpful message explaining what's wrong and how to fix it.
Keep it concise (2-3 sentences max)."""
            
            response = self.llm_manager.generate(
                prompt=prompt,
                system_message=self.system_prompt
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error generating validation feedback: {str(e)}")
            return f"There was an issue with your {field_name}. Please check and try again."


def create_llm_agent_nodes(llm_manager: LLMManager) -> Dict[str, LLMAgentNode]:
    """
    Create all LLM agent nodes
    
    Args:
        llm_manager: LLM manager instance
        
    Returns:
        Dictionary of agent name to agent node
    """
    return {
        'welcome': WelcomeAgentNode(llm_manager, 'welcome'),
        'conversational': ConversationalAgentNode(llm_manager, 'conversational'),
        'extractor': DataExtractionAgentNode(llm_manager, 'extractor'),
        'validator': ValidationAgentNode(llm_manager, 'validator')
    }

