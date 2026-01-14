"""Decision and confirmation models"""

from typing import Dict, Optional
from pydantic import BaseModel, Field
from .action_types import ActionType


class AgentDecision(BaseModel):
    """LLM decision output"""
    action: ActionType
    reasoning: str
    field_name: Optional[str] = None
    field_value: Optional[str] = None
    search_query: Optional[str] = None
    suggested_fields: Optional[Dict[str, str]] = None
    message_to_user: str
    requires_user_input: bool
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class ConfirmationDetection(BaseModel):
    """Confirmation analysis output"""
    is_confirmation: bool
    is_rejection: bool
    is_modification_request: bool
    confidence: float
    reasoning: str
    extracted_modifications: Optional[Dict[str, str]] = None

