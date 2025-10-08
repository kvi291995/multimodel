"""
LLM Configuration
Flexible configuration system for integrating various LLM providers
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
import os
import json


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    CUSTOM = "custom"


@dataclass
class LLMConfig:
    """
    Configuration for LLM provider
    
    Supports multiple providers with flexible configuration
    """
    provider: LLMProvider
    model_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None  # For custom endpoints or local models
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    
    # Provider-specific parameters
    extra_params: Dict[str, Any] = field(default_factory=dict)
    
    # Retry configuration
    max_retries: int = 3
    timeout: int = 30
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'LLMConfig':
        """Create LLMConfig from dictionary"""
        provider_str = config_dict.get('provider', 'openai')
        provider = LLMProvider(provider_str)
        
        return cls(
            provider=provider,
            model_name=config_dict.get('model_name', 'gpt-3.5-turbo'),
            api_key=config_dict.get('api_key') or os.getenv(f"{provider_str.upper()}_API_KEY"),
            base_url=config_dict.get('base_url'),
            temperature=config_dict.get('temperature', 0.7),
            max_tokens=config_dict.get('max_tokens', 1000),
            top_p=config_dict.get('top_p', 1.0),
            frequency_penalty=config_dict.get('frequency_penalty', 0.0),
            presence_penalty=config_dict.get('presence_penalty', 0.0),
            extra_params=config_dict.get('extra_params', {}),
            max_retries=config_dict.get('max_retries', 3),
            timeout=config_dict.get('timeout', 30)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'provider': self.provider.value,
            'model_name': self.model_name,
            'base_url': self.base_url,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'top_p': self.top_p,
            'frequency_penalty': self.frequency_penalty,
            'presence_penalty': self.presence_penalty,
            'extra_params': self.extra_params,
            'max_retries': self.max_retries,
            'timeout': self.timeout
        }
    
    @classmethod
    def from_json_file(cls, file_path: str) -> 'LLMConfig':
        """Load configuration from JSON file"""
        with open(file_path, 'r') as f:
            config_dict = json.load(f)
        return cls.from_dict(config_dict)
    
    def to_json_file(self, file_path: str) -> None:
        """Save configuration to JSON file"""
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


@dataclass
class MultiAgentLLMConfig:
    """
    Configuration for multiple LLM agents
    Allows different agents to use different models
    """
    default_config: LLMConfig
    agent_configs: Dict[str, LLMConfig] = field(default_factory=dict)
    
    def get_config_for_agent(self, agent_name: str) -> LLMConfig:
        """Get configuration for a specific agent"""
        return self.agent_configs.get(agent_name, self.default_config)
    
    def add_agent_config(self, agent_name: str, config: LLMConfig) -> None:
        """Add configuration for a specific agent"""
        self.agent_configs[agent_name] = config
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'MultiAgentLLMConfig':
        """Create from dictionary"""
        default_config = LLMConfig.from_dict(config_dict.get('default', {}))
        
        agent_configs = {}
        for agent_name, agent_config_dict in config_dict.get('agents', {}).items():
            agent_configs[agent_name] = LLMConfig.from_dict(agent_config_dict)
        
        return cls(
            default_config=default_config,
            agent_configs=agent_configs
        )
    
    @classmethod
    def from_json_file(cls, file_path: str) -> 'MultiAgentLLMConfig':
        """Load multi-agent configuration from JSON file"""
        with open(file_path, 'r') as f:
            config_dict = json.load(f)
        return cls.from_dict(config_dict)


# Predefined configurations for common setups

def get_openai_config(model: str = "gpt-3.5-turbo") -> LLMConfig:
    """Get OpenAI configuration"""
    return LLMConfig(
        provider=LLMProvider.OPENAI,
        model_name=model,
        api_key=os.getenv('OPENAI_API_KEY')
    )


def get_anthropic_config(model: str = "claude-3-sonnet-20240229") -> LLMConfig:
    """Get Anthropic configuration"""
    return LLMConfig(
        provider=LLMProvider.ANTHROPIC,
        model_name=model,
        api_key=os.getenv('ANTHROPIC_API_KEY')
    )


def get_google_config(model: str = "gemini-2.0-flash") -> LLMConfig:
    """Get Google Gemini configuration"""
    return LLMConfig(
        provider=LLMProvider.GOOGLE,
        model_name=model,
        api_key=os.getenv('GOOGLE_API_KEY')
    )


def get_ollama_config(model: str = "llama2", base_url: str = "http://localhost:11434") -> LLMConfig:
    """Get Ollama (local) configuration"""
    return LLMConfig(
        provider=LLMProvider.OLLAMA,
        model_name=model,
        base_url=base_url,
        api_key=None  # Ollama doesn't need API key
    )


def get_custom_config(
    model: str,
    base_url: str,
    api_key: Optional[str] = None,
    **kwargs
) -> LLMConfig:
    """Get custom configuration for any OpenAI-compatible API"""
    return LLMConfig(
        provider=LLMProvider.CUSTOM,
        model_name=model,
        base_url=base_url,
        api_key=api_key,
        extra_params=kwargs
    )

