"""Conversation history management"""

from datetime import datetime
from typing import List, Dict, Optional


class ConversationManager:
    """Manages clean conversation history"""
    
    def __init__(self, max_history: int = 50):
        """
        Initialize conversation manager
        
        Args:
            max_history: Maximum number of messages to keep
        """
        self.history: List[Dict] = []
        self.max_history = max_history
    
    def add_message(self, role: str, content: str, action: Optional[str] = None):
        """
        Add message to conversation history
        
        Args:
            role: 'user' or 'assistant'
            content: Message text
            action: Optional action type for context
        """
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "action": action
        }
        
        self.history.append(entry)
        
        # Trim if exceeds max
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_history(self) -> List[Dict]:
        """Get full conversation history"""
        return self.history.copy()
    
    def get_recent(self, n: int = 10) -> List[Dict]:
        """Get last N messages"""
        return self.history[-n:]
    
    def clear(self):
        """Clear all history"""
        self.history = []
    
    def to_dict(self) -> List[Dict]:
        """Export history as list of dicts"""
        return self.history.copy()
    
    def from_dict(self, history: List[Dict]):
        """Import history from list of dicts"""
        self.history = history[-self.max_history:]
