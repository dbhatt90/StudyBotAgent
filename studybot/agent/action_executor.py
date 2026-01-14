"""Action execution logic"""

from typing import Dict, Any, Callable, Optional
from datetime import datetime
from models import AgentDecision, ActionType


class ActionExecutor:
    """Executes agent actions and generates responses"""
    
    def __init__(self, 
                 field_manager,
                 rag_service,
                 websocket_callback: Optional[Callable] = None):
        """
        Initialize action executor
        
        Args:
            field_manager: FieldManager instance
            rag_service: RAGService instance
            websocket_callback: Function to send UI messages
        """
        self.field_manager = field_manager
        self.rag_service = rag_service
        self.websocket_callback = websocket_callback
    
    async def execute(self, decision: AgentDecision, session_state: Dict) -> Dict[str, Any]:
        """
        Execute an action based on decision
        
        Args:
            decision: AgentDecision with action type
            session_state: Current session state
            
        Returns:
            Response dictionary
        """
        action_map = {
            ActionType.SUGGEST_FIELDS: self._execute_suggest_fields,
            ActionType.UPDATE_FIELD: self._execute_update_field,
            ActionType.SEARCH_RAG: self._execute_search_rag,
            ActionType.SUBMIT_FORM: self._execute_submit_form,
            ActionType.CLARIFY: self._execute_clarify,
            ActionType.GENERIC_RESPONSE: self._execute_generic_response
        }
        
        handler = action_map.get(decision.action, self._execute_fallback)
        return await handler(decision, session_state)
    
    async def _execute_suggest_fields(self, decision: AgentDecision, state: Dict) -> Dict:
        """Execute SUGGEST_FIELDS action"""
        if not decision.suggested_fields:
            return {
                "type": "error",
                "message": "No fields extracted. Could you provide them one at a time?"
            }
        
        message = "📝 **I found these values:**\n\n"
        for field, value in decision.suggested_fields.items():
            message += f"• **{field}:** {value}\n"
        message += "\n✨ Say **'yes'** to apply, or tell me what to change."
        
        self._send_to_ui({
            "type": "suggestion",
            "message": message,
            "suggestions": decision.suggested_fields,
            "awaiting_confirmation": True
        }, state)
        
        return {
            "type": "suggestion_pending",
            "message": message,
            "suggestions": decision.suggested_fields
        }
    
    async def _execute_update_field(self, decision: AgentDecision, state: Dict) -> Dict:
        """Execute UPDATE_FIELD action"""
        if not decision.field_name or not decision.field_value:
            return {"type": "error", "message": "Couldn't extract field and value"}
        
        self.field_manager.update_fields({decision.field_name: decision.field_value})
        progress = self.field_manager.calculate_progress()
        
        message = f"✅ **Updated {decision.field_name}:** {decision.field_value}\n"
        message += f"\n📊 **Progress:** {progress}%"
        
        if not self.field_manager.is_complete():
            empty = self.field_manager.get_empty_fields()
            message += f"\n\n📝 **Still need:** {', '.join(empty[:3])}"
        
        self._send_to_ui({"type": "field_updated", "message": message}, state)
        
        return {"type": "field_updated", "message": message}
    
    async def _execute_search_rag(self, decision: AgentDecision, state: Dict) -> Dict:
        """Execute SEARCH_RAG action"""
        results = await self.rag_service.search(decision.search_query)
        
        if results.get("num_results", 0) > 0 and results.get("found_fields"):
            message = f"📚 **Found {results['num_results']} similar studies!**\n\n"
            for field, value in results["found_fields"].items():
                message += f"• **{field}:** {value}\n"
            
            if "similar_studies" in results:
                message += "\n📖 **References:**\n"
                for study in results["similar_studies"][:2]:
                    message += f"• {study}\n"
            
            message += "\n✨ Say **'yes'** to apply these values."
            
            self._send_to_ui({
                "type": "suggestion",
                "message": message,
                "suggestions": results["found_fields"],
                "awaiting_confirmation": True
            }, state)
            
            return {
                "type": "suggestion_pending",
                "message": message,
                "suggestions": results["found_fields"]
            }
        
        return {
            "type": "no_results",
            "message": "❌ No similar studies found. Please provide field values."
        }
    
    async def _execute_submit_form(self, decision: AgentDecision, state: Dict) -> Dict:
        """Execute SUBMIT_FORM action"""
        if not self.field_manager.is_complete():
            return {
                "type": "incomplete",
                "message": f"⚠️ Form incomplete. Missing: {', '.join(self.field_manager.get_empty_fields())}"
            }
        
        ticket_id = f"STUDY-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        ticket_data = self.field_manager.get_filled_fields()
        
        message = f"🎉 **Study ticket created!**\n\n📋 **Ticket ID:** `{ticket_id}`\n\n"
        for field, value in ticket_data.items():
            message += f"• **{field}:** {value}\n"
        
        self._send_to_ui({
            "type": "submitted",
            "message": message,
            "metadata": {"ticket_id": ticket_id}
        }, state)
        
        return {
            "type": "submitted",
            "message": message,
            "ticket_id": ticket_id,
            "ticket_data": ticket_data
        }
    
    async def _execute_clarify(self, decision: AgentDecision, state: Dict) -> Dict:
        """Execute CLARIFY action"""
        self._send_to_ui({
            "type": "clarify",
            "message": decision.message_to_user
        }, state)
        
        return {"type": "clarify", "message": decision.message_to_user}
    
    async def _execute_generic_response(self, decision: AgentDecision, state: Dict) -> Dict:
        """Execute GENERIC_RESPONSE action"""
        message = decision.message_to_user or "I'm here to help you create study tickets!"
        
        self._send_to_ui({
            "type": "generic_response",
            "message": message
        }, state)
        
        return {"type": "generic_response", "message": message}
    
    async def _execute_fallback(self, decision: AgentDecision, state: Dict) -> Dict:
        """Fallback for unknown actions"""
        return {"type": "error", "message": f"Unknown action: {decision.action}"}
    
    def _send_to_ui(self, message_data: Dict, state: Dict):
        """Send message to UI via WebSocket"""
        if not self.websocket_callback:
            return
        
        ui_message = {
            **message_data,
            "progress_pct": self.field_manager.calculate_progress(),
            "filled_fields": self.field_manager.get_filled_fields(),
            "empty_fields": self.field_manager.get_empty_fields()
        }
        
        self.websocket_callback(state.get("session_id"), ui_message)