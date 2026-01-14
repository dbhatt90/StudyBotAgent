"""UI message models"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel


class UIMessage(BaseModel):
    """Structured message for frontend UI"""
    type: str  # "status", "suggestion", "confirmation", "question", "success", "error"
    message: str
    progress_pct: float
    filled_fields: Dict[str, str]
    empty_fields: List[str]
    suggestions: Optional[Dict[str, str]] = None
    awaiting_confirmation: bool = False
    metadata: Optional[Dict[str, Any]] = None
    conversation_history: Optional[List[Dict[str, Any]]] = None