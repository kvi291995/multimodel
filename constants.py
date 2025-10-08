"""
Constants for the onboarding system
"""

# Agent names
AGENT_SUPERVISOR = "supervisor"
AGENT_SIGNUP = "signup"
AGENT_COMPANY = "company"
AGENT_KYC = "kyc"
AGENT_BANK = "bank"
AGENT_COMPLETE = "complete"
AGENT_END = "end"

# Status values
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_ERROR = "error"

# LLM Configuration
DEFAULT_MODEL = "gemini-2.0-flash"
LLM_MAX_RETRIES = 3
LLM_TIMEOUT = 30

# Response messages
MSG_SUCCESS = "Processing completed successfully"
MSG_ERROR = "An error occurred during processing"
MSG_VALIDATION_FAILED = "Validation failed. Please check your inputs"

# Completion status emojis (optional)
EMOJI_COMPLETE = "✅"
EMOJI_INCOMPLETE = "❌"
EMOJI_PROCESSING = "🔄"
EMOJI_SUCCESS = "🎉"

