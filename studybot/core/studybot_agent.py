"""Main StudyBot agent orchestrator"""

import asyncio
from typing import Dict, Optional, Any, Callable
from datetime import datetime

from models import UIMessage
from storage import CheckpointManager
from services import FieldManager, RAGService
from agent import (
    DecisionMaker,
    ConfirmationHandler,
    ConversationManager,
    ActionExecutor
)
from .config import Config
from llm_service_session import LLMServiceSession


class StudyBotAgent:
    """
    Main StudyBot agent that orchestrates all components
    
    This is the high-level interface that ties together:
    - Field management
    - RAG search
    - LLM decision making
    - Confirmation handling
    - Conversation tracking
    - Action execution
    - WebSocket communication
    """
    
    def __init__(self,
                 session_id: str,
                 api_key: str,
                 rag_client: Optional[Any] = None,
                 checkpoint_dir: str = None,
                 websocket_callback: Optional[Callable] = None):
        """
        Initialize StudyBot agent
        
        Args:
            session_id: Unique session identifier
            api_key: LLM API key
            rag_client: RAG client (optional, uses mock if None)
            checkpoint_dir: Directory for checkpoints
            websocket_callback: Function to send UI messages
        """
        self.session_id = session_id
        self.websocket_callback = websocket_callback
        
        # Initialize storage
        self.checkpoint_mgr = CheckpointManager(
            checkpoint_dir or Config.CHECKPOINT_DIR
        )
        
        # Initialize services
        self.field_manager = FieldManager()
        self.rag_service = RAGService(rag_client)
        
        # Initialize session state
        self.session = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "progress_pct": 0.0,
            "pending_suggestions": None,
            "awaiting_confirmation": False,
            "rag_search_performed": False,
            "initial_extraction_done": False,
            "last_action": None
        }
        
        # Try to restore from checkpoint
        checkpoint = self.checkpoint_mgr.load(session_id)
        
        if checkpoint:
            print(f"🔄 Restoring session: {session_id}")
            self._restore_from_checkpoint(checkpoint, api_key)
        else:
            print(f"✨ Creating new session: {session_id}")
            self._initialize_new_session(api_key)
    
    def _initialize_new_session(self, api_key: str):
        """Initialize a fresh session"""
        # Initialize LLM session
        self.llm_session = LLMServiceSession(
            api_key=api_key,
            session_id=self.session_id
        )
        
        # Initialize conversation manager
        self.conversation = ConversationManager(max_history=Config.MAX_HISTORY)
        
        # Initialize agent components
        self.decision_maker = DecisionMaker(self.llm_session)
        self.confirmation_handler = ConfirmationHandler(self.llm_session)
        self.action_executor = ActionExecutor(
            self.field_manager,
            self.rag_service,
            self.websocket_callback
        )
        
        # Send greeting
        greeting = Config.GREETING
        self.conversation.add_message("assistant", greeting, action="greeting")
        self.llm_session.add_message("assistant", greeting, metadata={"action": "greeting"})
        
        self._send_to_ui({
            "type": "greeting",
            "message": greeting,
            "progress_pct": 0.0,
            "filled_fields": {},
            "empty_fields": self.field_manager.get_empty_fields(),
            "awaiting_confirmation": False
        })
    
    def _restore_from_checkpoint(self, checkpoint: Dict, api_key: str):
        """Restore session from checkpoint"""
        # Restore session state
        self.session = checkpoint["agent_state"]
        
        # Restore field manager
        self.field_manager.from_dict(self.session.get("fields", {}))
        
        # Restore conversation
        self.conversation = ConversationManager(max_history=Config.MAX_HISTORY)
        if "conversation_history" in self.session:
            self.conversation.from_dict(self.session["conversation_history"])
        
        # Restore LLM session
        self.llm_session = LLMServiceSession.from_checkpoint_dict(
            checkpoint["llm_state"],
            api_key
        )
        
        # Reinitialize agent components
        self.decision_maker = DecisionMaker(self.llm_session)
        self.confirmation_handler = ConfirmationHandler(self.llm_session)
        self.action_executor = ActionExecutor(
            self.field_manager,
            self.rag_service,
            self.websocket_callback
        )
        
        # Update progress
        self.session["progress_pct"] = self.field_manager.calculate_progress()
        
        print(f"✅ Session restored: {self.session['progress_pct']}% complete")
        
        # Send restoration status to UI
        self._send_to_ui({
            "type": "status",
            "message": f"📋 Session restored ({self.session['progress_pct']}% complete)",
            "progress_pct": self.session['progress_pct'],
            "filled_fields": self.field_manager.get_filled_fields(),
            "empty_fields": self.field_manager.get_empty_fields(),
            "awaiting_confirmation": self.session['awaiting_confirmation'],
            "conversation_history": self.conversation.get_history()
        })
    
    async def handle_message(self, message: str) -> Dict[str, Any]:
        """
        Main message handler - entry point for user input
        
        Args:
            message: User's message text
            
        Returns:
            Response dictionary
        """
        print(f"\n{'='*60}")
        print(f"👤 USER: {message}")
        print(f"{'='*60}")
        
        # Track in conversation history
        self.conversation.add_message("user", message)
        
        # Handle confirmation flow if awaiting
        if self.session["awaiting_confirmation"]:
            response = await self._handle_confirmation_flow(message)
        else:
            response = await self._handle_regular_flow(message)
        
        # Track agent response
        self.conversation.add_message(
            "assistant",
            response.get("message", ""),
            action=self.session.get("last_action")
        )
        
        # Save checkpoint
        self._save_checkpoint()
        
        return response
    
    async def _handle_regular_flow(self, message: str) -> Dict[str, Any]:
        """Handle regular message (not confirmation)"""
        # Get decision from LLM
        agent_state = self._get_agent_state()
        decision = await self.decision_maker.decide_action(message, agent_state)
        
        self.session["last_action"] = decision.action.value
        print(f"🤖 ACTION: {decision.action.value}")
        print(f"💭 REASONING: {decision.reasoning}")
        
        # Execute action
        response = await self.action_executor.execute(decision, self.session)
        
        # Update state based on action
        if decision.action.value == "suggest_fields" and decision.suggested_fields:
            self.session["pending_suggestions"] = decision.suggested_fields
            self.session["awaiting_confirmation"] = True
            
            # Mark initial extraction done
            if not self.session["initial_extraction_done"]:
                self.session["initial_extraction_done"] = True
        
        return response
    
    async def _handle_confirmation_flow(self, message: str) -> Dict[str, Any]:
        """Handle confirmation/rejection/modification"""
        confirmation = await self.confirmation_handler.detect_confirmation(
            message,
            self.session["pending_suggestions"]
        )
        
        # CONFIRMATION
        if confirmation.is_confirmation and confirmation.confidence > 0.6:
            # Apply suggested fields
            self.field_manager.update_fields(self.session["pending_suggestions"])
            self.session["awaiting_confirmation"] = False
            self.session["pending_suggestions"] = None
            self.session["progress_pct"] = self.field_manager.calculate_progress()
            
            response_msg = "✅ **Applied!**\n\n"
            for field, value in self.field_manager.get_filled_fields().items():
                response_msg += f"• **{field}:** {value}\n"
            response_msg += f"\n📊 **Progress:** {self.session['progress_pct']}%"
            
            # Send confirmation
            self._send_to_ui({
                "type": "confirmation",
                "message": response_msg,
                "progress_pct": self.session["progress_pct"],
                "filled_fields": self.field_manager.get_filled_fields(),
                "empty_fields": self.field_manager.get_empty_fields()
            })
            
            # Auto-trigger RAG if first time and not complete
            if (not self.session["rag_search_performed"] and 
                not self.field_manager.is_complete()):
                await self._auto_trigger_rag()
            
            return {
                "type": "apply_suggestions",
                "message": response_msg,
                "progress_pct": self.session["progress_pct"]
            }
        
        # MODIFICATION
        elif confirmation.is_modification_request and confirmation.extracted_modifications:
            self.field_manager.update_fields(confirmation.extracted_modifications)
            self.session["awaiting_confirmation"] = False
            self.session["pending_suggestions"] = None
            self.session["progress_pct"] = self.field_manager.calculate_progress()
            
            response_msg = "✅ **Updated!**\n\n"
            for field, value in self.field_manager.get_filled_fields().items():
                response_msg += f"• **{field}:** {value}\n"
            
            self._send_to_ui({
                "type": "modification",
                "message": response_msg,
                "progress_pct": self.session["progress_pct"],
                "filled_fields": self.field_manager.get_filled_fields(),
                "empty_fields": self.field_manager.get_empty_fields()
            })
            
            return {
                "type": "modification",
                "message": response_msg,
                "progress_pct": self.session["progress_pct"]
            }
        
        # REJECTION
        elif confirmation.is_rejection:
            self.session["awaiting_confirmation"] = False
            self.session["pending_suggestions"] = None
            
            reject_msg = "No problem! What would you like to do instead?"
            self._send_to_ui({
                "type": "rejection",
                "message": reject_msg
            })
            
            return {"type": "rejection", "message": reject_msg}
        
        # UNCLEAR
        else:
            unclear_msg = "I'm not sure. Say **'yes'** to apply, **'no'** to cancel, or tell me what to change."
            self._send_to_ui({
                "type": "clarification",
                "message": unclear_msg,
                "awaiting_confirmation": True
            })
            
            return {"type": "unclear_confirmation", "message": unclear_msg}
    
    async def _auto_trigger_rag(self):
        """Auto-trigger RAG search after initial field extraction"""
        print("\n⭐ AUTO-TRIGGERING RAG SEARCH")
        await asyncio.sleep(0.5)
        
        # Build query from Problem field
        search_query = self.field_manager.get_field("Problem") or "study request"
        results = await self.rag_service.search(search_query)
        
        if results.get("num_results", 0) > 0 and results.get("found_fields"):
            # Filter out already-filled fields
            new_suggestions = {
                k: v for k, v in results["found_fields"].items()
                if not self.field_manager.get_field(k)
            }
            
            if new_suggestions:
                self.session["pending_suggestions"] = new_suggestions
                self.session["awaiting_confirmation"] = True
                self.session["rag_search_performed"] = True
                
                rag_msg = f"📚 **Found {results['num_results']} similar studies!**\n\n"
                for field, value in new_suggestions.items():
                    rag_msg += f"• **{field}:** {value}\n"
                
                if "similar_studies" in results:
                    rag_msg += "\n📖 **References:**\n"
                    for study in results["similar_studies"][:2]:
                        rag_msg += f"• {study}\n"
                
                rag_msg += "\n✨ Say **'yes'** to apply these."
                
                self._send_to_ui({
                    "type": "suggestion",
                    "message": rag_msg,
                    "suggestions": new_suggestions,
                    "awaiting_confirmation": True
                })
    
    def _send_to_ui(self, message_data: Dict[str, Any]):
        """Send message to UI via WebSocket"""
        if not self.websocket_callback:
            return
        
        try:
            ui_msg = UIMessage(
                type=message_data.get("type", "message"),
                message=message_data.get("message", ""),
                progress_pct=message_data.get("progress_pct", self.session["progress_pct"]),
                filled_fields=message_data.get("filled_fields", self.field_manager.get_filled_fields()),
                empty_fields=message_data.get("empty_fields", self.field_manager.get_empty_fields()),
                suggestions=message_data.get("suggestions"),
                awaiting_confirmation=message_data.get("awaiting_confirmation", False),
                metadata=message_data.get("metadata"),
                conversation_history=message_data.get("conversation_history")
            )
            
            self.websocket_callback(self.session_id, ui_msg.dict())
        except Exception as e:
            print(f"⚠️ WebSocket send failed: {e}")
    
    def _save_checkpoint(self):
        """Save current state to checkpoint"""
        self.session["fields"] = self.field_manager.to_dict()
        self.session["conversation_history"] = self.conversation.to_dict()
        
        checkpoint = {
            "checkpoint_metadata": {
                "saved_at": datetime.now().isoformat(),
                "session_id": self.session_id,
                "version": "2.0"
            },
            "session_id": self.session_id,
            "agent_state": self.session,
            "llm_state": self.llm_session.to_checkpoint_dict(),
            "schema": Config.FORM_SCHEMA
        }
        
        self.checkpoint_mgr.save(self.session_id, checkpoint)
    
    def _get_agent_state(self) -> Dict:
        """Get current agent state for decision making"""
        return {
            "progress_pct": self.field_manager.calculate_progress(),
            "filled_fields": self.field_manager.get_filled_fields(),
            "empty_fields": self.field_manager.get_empty_fields(),
            "awaiting_confirmation": self.session["awaiting_confirmation"],
            "pending_suggestions": self.session["pending_suggestions"],
            "rag_search_performed": self.session["rag_search_performed"],
            "initial_extraction_done": self.session["initial_extraction_done"]
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current session status"""
        return {
            "session_id": self.session_id,
            "progress_pct": self.field_manager.calculate_progress(),
            "filled_fields": self.field_manager.get_filled_fields(),
            "empty_fields": self.field_manager.get_empty_fields(),
            "awaiting_confirmation": self.session["awaiting_confirmation"],
            "conversation_turns": len(self.conversation.get_history()),
            "last_action": self.session.get("last_action"),
            "rag_search_performed": self.session.get("rag_search_performed", False),
            "initial_extraction_done": self.session.get("initial_extraction_done", False)
        }