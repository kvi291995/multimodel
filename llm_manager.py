"""
LLM Manager
Unified interface for working with multiple LLM providers
"""

import logging
from typing import Dict, Any, Optional, List
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from config.llm_config import LLMConfig, LLMProvider

logger = logging.getLogger(__name__)


class LLMManager:
    """
    Unified manager for multiple LLM providers
    
    Supports:
    - OpenAI (GPT-3.5, GPT-4, etc.)
    - Anthropic (Claude)
    - Google (Gemini)
    - Ollama (Local models)
    - Custom OpenAI-compatible endpoints
    """
    
    def __init__(self, config: LLMConfig):
        """
        Initialize LLM Manager
        
        Args:
            config: LLMConfig instance
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.llm = self._initialize_llm()
    
    def _initialize_llm(self) -> BaseChatModel:
        """Initialize the LLM based on provider"""
        try:
            if self.config.provider == LLMProvider.OPENAI:
                return self._init_openai()
            elif self.config.provider == LLMProvider.ANTHROPIC:
                return self._init_anthropic()
            elif self.config.provider == LLMProvider.GOOGLE:
                return self._init_google()
            elif self.config.provider == LLMProvider.OLLAMA:
                return self._init_ollama()
            elif self.config.provider == LLMProvider.CUSTOM:
                return self._init_custom()
            else:
                raise ValueError(f"Unsupported provider: {self.config.provider}")
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM: {str(e)}")
            raise

    def _init_google(self) -> BaseChatModel:
        """Initialize Google Gemini LLM"""
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        return ChatGoogleGenerativeAI(
            model=self.config.model_name,
            google_api_key=self.config.api_key,
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_tokens,
            top_p=self.config.top_p,
            max_retries=self.config.max_retries,
            timeout=self.config.timeout,
            **self.config.extra_params
        )
    
    def _init_ollama(self) -> BaseChatModel:
        """Initialize Ollama (local) LLM"""
        from langchain_ollama import ChatOllama
        
        return ChatOllama(
            model=self.config.model_name,
            base_url=self.config.base_url or "http://localhost:11434",
            temperature=self.config.temperature,
            num_predict=self.config.max_tokens,
            top_p=self.config.top_p,
            **self.config.extra_params
        )

    def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        context: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate response from LLM
        
        Args:
            prompt: User prompt
            system_message: Optional system message
            context: Optional conversation context
            
        Returns:
            str: Generated response
        """
        try:
            messages = []
            
            # Add system message
            if system_message:
                messages.append(SystemMessage(content=system_message))
            
            # Add context messages
            if context:
                for msg in context:
                    if msg['role'] == 'user':
                        messages.append(HumanMessage(content=msg['content']))
                    elif msg['role'] == 'assistant':
                        messages.append(AIMessage(content=msg['content']))
            
            # Add current prompt
            messages.append(HumanMessage(content=prompt))
            
            # Generate response
            response = self.llm.invoke(messages)
            
            return response.content
            
        except Exception as e:
            self.logger.error(f"Error generating response: {str(e)}")
            raise
    
    async def agenerate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        context: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Async generate response from LLM
        
        Args:
            prompt: User prompt
            system_message: Optional system message
            context: Optional conversation context
            
        Returns:
            str: Generated response
        """
        try:
            messages = []
            
            if system_message:
                messages.append(SystemMessage(content=system_message))
            
            if context:
                for msg in context:
                    if msg['role'] == 'user':
                        messages.append(HumanMessage(content=msg['content']))
                    elif msg['role'] == 'assistant':
                        messages.append(AIMessage(content=msg['content']))
            
            messages.append(HumanMessage(content=prompt))
            
            response = await self.llm.ainvoke(messages)
            
            return response.content
            
        except Exception as e:
            self.logger.error(f"Error generating async response: {str(e)}")
            raise
    
    def stream(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        context: Optional[List[Dict[str, str]]] = None
    ):
        """
        Stream response from LLM
        
        Args:
            prompt: User prompt
            system_message: Optional system message
            context: Optional conversation context
            
        Yields:
            str: Chunks of generated response
        """
        try:
            messages = []
            
            if system_message:
                messages.append(SystemMessage(content=system_message))
            
            if context:
                for msg in context:
                    if msg['role'] == 'user':
                        messages.append(HumanMessage(content=msg['content']))
                    elif msg['role'] == 'assistant':
                        messages.append(AIMessage(content=msg['content']))
            
            messages.append(HumanMessage(content=prompt))
            
            for chunk in self.llm.stream(messages):
                yield chunk.content
                
        except Exception as e:
            self.logger.error(f"Error streaming response: {str(e)}")
            raise


class MultiAgentLLMManager:
    """
    Manager for multiple LLM instances for different agents
    """
    
    def __init__(self, default_config: LLMConfig):
        """
        Initialize with a default configuration
        
        Args:
            default_config: Default LLMConfig
        """
        self.default_manager = LLMManager(default_config)
        self.agent_managers: Dict[str, LLMManager] = {}
        self.logger = logging.getLogger(__name__)
    
    def add_agent_manager(self, agent_name: str, config: LLMConfig) -> None:
        """
        Add a specialized LLM manager for a specific agent
        
        Args:
            agent_name: Name of the agent
            config: LLMConfig for this agent
        """
        self.agent_managers[agent_name] = LLMManager(config)
        self.logger.info(f"Added LLM manager for agent: {agent_name}")
    
    def get_manager(self, agent_name: Optional[str] = None) -> LLMManager:
        """
        Get LLM manager for a specific agent
        
        Args:
            agent_name: Name of the agent (None for default)
            
        Returns:
            LLMManager instance
        """
        if agent_name and agent_name in self.agent_managers:
            return self.agent_managers[agent_name]
        return self.default_manager
    
    def generate(
        self,
        prompt: str,
        agent_name: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate response using appropriate LLM manager
        
        Args:
            prompt: User prompt
            agent_name: Name of the agent to use
            **kwargs: Additional arguments for generate
            
        Returns:
            str: Generated response
        """
        manager = self.get_manager(agent_name)
        return manager.generate(prompt, **kwargs)

