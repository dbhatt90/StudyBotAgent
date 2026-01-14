"""Action type enumeration"""

from enum import Enum

class ActionType(str, Enum):
    """Agent action types"""
    SUGGEST_FIELDS = "suggest_fields"
    UPDATE_FIELD = "update_field"
    SEARCH_RAG = "search_rag"
    APPLY_SUGGESTIONS = "apply_suggestions"
    SUBMIT_FORM = "submit_form"
    CLARIFY = "clarify"
    GENERIC_RESPONSE = "generic_response"