"""
llm_service_session.py

Centralized LLM service for managing:
- Conversation history across multiple turns
- Prompt construction and API calls
- Text embeddings for RAG
- Context preservation via beans (ephemeral metadata)

Usage:
    llm = LLMServiceSession(api_key="...", session_id="session_123")
    
    # Send prompt with context
    llm.attach_bean("form_state", {"fields": {...}, "progress": 50})
    response = llm.call_llm(prompt="Decide next action", system_prompt="...")
    
    # Get embedding
    embedding = llm.get_text_embedding("molecular weight analysis")
    
    # Export for checkpoint
    checkpoint_data = llm.to_checkpoint_dict()
    
    # Restore from checkpoint
    llm = LLMServiceSession.from_checkpoint_dict(checkpoint_data, api_key)
"""

import uuid
import time
import requests
import json
from typing import Dict, Any, Optional, List

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from typing import Dict, Any, Optional
import json


class LLMServiceSession:
    """
    Centralized LLM service with conversation history and prompt handling.
    
    Key Responsibilities:
    1. Maintain conversation history (for multi-turn context)
    2. Send prompts to LLM APIs (Gemini, Claude, etc.)
    3. Manage ephemeral context via "beans"
    4. Generate text embeddings for RAG
    5. Support checkpoint/restore for session persistence
    """

    def __init__(self, api_key: str, session_id: Optional[str] = None):
        """
        Initialize LLM service session.
        
        Args:
            api_key: API key for LLM provider
            session_id: Unique session identifier (generated if not provided)
        """
        self.api_key = api_key
        self.session_id = session_id or str(uuid.uuid4())
        self.history = []  # List of message dictionaries
        self.metadata = {
            "created_at": time.time(),
            "last_updated": time.time(),
            "turn_count": 0
        }
    
    # ===================================================================
    # HISTORY MANAGEMENT
    # ===================================================================
    
    def add_message(self, sender: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Add a message to conversation history.
        
        Args:
            sender: "user", "assistant", "embedding", etc.
            content: Message text
            metadata: Optional metadata (model info, action type, etc.)
        """
        message = {
            "sender": sender,
            "content": content,
            "metadata": metadata or {},
            "timestamp": time.time()
        }
        self.history.append(message)
        self.metadata["last_updated"] = time.time()
        self.metadata["turn_count"] += 1
    
    def get_latest_user_message(self) -> Optional[str]:
        """Get most recent user message."""
        for msg in reversed(self.history):
            if msg["sender"] == "user":
                return msg["content"]
        return None
    
    # ===================================================================
    # BEANS (EPHEMERAL CONTEXT)
    # ===================================================================
    
    def attach_bean(self, name: str, data: Dict[str, Any]) -> None:
        """
        Attach ephemeral metadata ("bean") for the current request.
        
        Beans are NOT persisted in checkpoints - they're request-specific context
        like current form state, RAG results, or validation rules.
        
        Args:
            name: Bean identifier (e.g., "form_state", "rag_context")
            data: Dictionary of contextual data
        """
        self.metadata.setdefault("beans", {})[name] = data
    
    def clear_beans(self):
        """Clear all beans after request completes."""
        if "beans" in self.metadata:
            del self.metadata["beans"]
    
    # ===================================================================
    # LLM API CALLS
    # ===================================================================
    def _format_history_for_gemini_as_messages(self):
        messages = []

        for entry in self.history:
            # Determine role
            role = entry.get("role") or entry.get("metadata", {}).get("agent", "user")
            text = entry.get("content", "")

            # Append beans context if present
            if "beans" in self.metadata and role == "user":
                text += f"\n\nCurrent Context:\n{json.dumps(self.metadata['beans'], indent=2)}"

            if role.lower() == "user":
                messages.append(HumanMessage(content=text))
            else:  # treat everything else as assistant
                messages.append(HumanMessage(content=text))

        return messages


    def _format_history_for_gemini(self) -> List[Dict]:
        """
        Convert internal history format to Gemini API format.
        
        Gemini expects:
        {
          "contents": [
            {"role": "user", "parts": [{"text": "..."}]},
            {"role": "model", "parts": [{"text": "..."}]}
          ]
        }
        """
        contents = []
        for msg in self.history:
            # Map sender to Gemini role
            role = "user" if msg["sender"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        return contents



    def call_llm(self, 
                prompt: str,
                agent: str = "gemini",
                system_prompt: Optional[str] = None,
                include_history: bool = True) -> Dict[str, Any]:
        """
        Send prompt to LLM with full conversation history using Google Chat Generative AI client.
        
        Returns a dictionary similar to the raw API response, and updates message history.
        """
        # Add current prompt to history
        self.add_message("user", prompt)
        
        # Prepare messages for client
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        
        if include_history:
            # Convert your internal history to HumanMessage format
            history_messages = self._format_history_for_gemini_as_messages()
            messages.extend(history_messages)
        else:
            messages.append(HumanMessage(content=prompt))
        
        # Append beans context if available
        if "beans" in self.metadata:
            beans_context = f"\n\nCurrent Context:\n{json.dumps(self.metadata['beans'], indent=2)}"
            if messages and isinstance(messages[-1], HumanMessage):
                messages[-1].content += beans_context
            else:
                messages.append(HumanMessage(content=beans_context))
        
        # Initialize client
        llm_client = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=self.api_key,
            temperature=0.7,
            top_k=40,
            top_p=0.95,
            max_output_tokens=2048
        )
        
        print(f"🔄 Calling LLM (agent: {agent})...")
        print(f"📝 Prompt: {prompt[:80]}...")
        
        try:
            response = llm_client(messages)
            response_text = response.content if hasattr(response, "content") else str(response)
            
            # Add to history
            self.add_message("assistant", response_text, metadata={
                "agent": agent,
                "model": "gemini-2.5-flash"
            })
            
            print(f"✅ LLM responded ({len(response_text)} chars)")
            
            # Build a response dictionary similar to original API format
            result = {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": response_text}]
                        }
                    }
                ]
            }
            
            return result

        except Exception as e:
            print(f"❌ LLM API call failed: {e}")
            raise
   
    # def call_llm(self, 
    #              prompt: str,
    #              agent: str = "gemini",
    #              system_prompt: Optional[str] = None,
    #              include_history: bool = True) -> Dict[str, Any]:
    #     """
    #     Send prompt to LLM with full conversation history.
        
    #     Args:
    #         prompt: The current prompt/question
    #         agent: Agent identifier (for logging)
    #         system_prompt: System instructions (optional)
    #         include_history: Whether to include previous conversation
        
    #     Returns:
    #         Full API response dictionary
            
    #     Example:
    #         response = llm.call_llm(
    #             prompt="Decide next action based on user input",
    #             system_prompt="You are a form-filling assistant",
    #             agent="decision_maker"
    #         )
    #     """
    #     # Add current prompt to history
    #     self.add_message("user", prompt)
        
    #     # Build API payload
    #     contents = self._format_history_for_gemini() if include_history else [
    #         {"role": "user", "parts": [{"text": prompt}]}
    #     ]
        
    #     payload = {
    #         "contents": contents,
    #         "generationConfig": {
    #             "temperature": 0.7,
    #             "topK": 40,
    #             "topP": 0.95,
    #             "maxOutputTokens": 2048
    #         }
    #     }
        
    #     # Add system instructions
    #     if system_prompt:
    #         payload["systemInstruction"] = {
    #             "parts": [{"text": system_prompt}]
    #         }
        
    #     # Append beans to last user message if present
    #     if "beans" in self.metadata:
    #         beans_context = f"\n\nCurrent Context:\n{json.dumps(self.metadata['beans'], indent=2)}"
    #         payload["contents"][-1]["parts"][0]["text"] += beans_context
        
    #     # Make API call
    #     # url = f"{self.GEMINI_CHAT_URL}?key={self.api_key}"
    #     url = self.GEMINI_CHAT_URL
    #     headers = {
    #             "x-goog-api-key": self.api_key,
    #             "Content-Type": "application/json"
    #         }
        
    #     print(f"🔄 Calling LLM (agent: {agent})...")
    #     print(self.api_key)
    #     print(f"📝 Prompt: {prompt[:80]}...")
        
    #     try:
           
    #         response = requests.post(url, json=payload, headers=headers, timeout=60)
    #         response.raise_for_status()
    #         result = response.json()
            
    #         # Extract response text
    #         if "candidates" in result and len(result["candidates"]) > 0:
    #             response_text = result["candidates"][0]["content"]["parts"][0]["text"]
    #         else:
    #             response_text = "(no response)"
            
    #         # Add to history
    #         self.add_message("assistant", response_text, metadata={
    #             "agent": agent,
    #             "model": "gemini-2.5-flash"
    #         })
            
    #         print(f"✅ LLM responded ({len(response_text)} chars)")
            
    #         return result
        
    #     except requests.exceptions.RequestException as e:
    #         print(f"❌ LLM API call failed: {e}")
    #         # Add error to history
    #         error_msg = f"API Error: {str(e)}"
    #         # self.add_message("assistant", error_msg, metadata={"error": True})
    #         raise
    
    # ===================================================================
    # EMBEDDINGS
    # ===================================================================
    
    def get_text_embedding(self, text: str) -> Dict[str, Any]:
        """
        Generate text embedding for semantic search.
        
        Args:
            text: Text to embed
            
        Returns:
            Dictionary with embedding vector and metadata
            
        Example:
            result = llm.get_text_embedding("molecular weight distribution")
            embedding_vector = result["embedding"]["values"]
        """
        payload = {
            "model": "models/embedding-001",
            "content": {
                "parts": [{"text": text}]
            }
        }
        
        url = f"{self.GEMINI_EMBED_URL}?key={self.api_key}"
        
        try:
            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            # Log embedding request
            embedding_dim = len(result.get("embedding", {}).get("values", []))
            self.add_message("embedding", f"Embedded: {text[:50]}...", metadata={
                "embedding_dim": embedding_dim
            })
            
            return result
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Embedding generation failed: {e}")
            raise
    
    # ===================================================================
    # CHECKPOINT SUPPORT
    # ===================================================================
    
    def to_checkpoint_dict(self) -> Dict:
        """
        Export state for checkpoint persistence.
        
        Returns:
            Dictionary containing session_id, history, and metadata
            (excludes ephemeral beans)
        """
        return {
            "session_id": self.session_id,
            "history": self.history,
            "metadata": {
                k: v for k, v in self.metadata.items() 
                if k != "beans"  # Don't persist ephemeral beans
            }
        }
    
    @classmethod
    def from_checkpoint_dict(cls, checkpoint: Dict, api_key: str):
        """
        Restore LLM session from checkpoint.
        
        Args:
            checkpoint: Dictionary from to_checkpoint_dict()
            api_key: API key for this session
            
        Returns:
            Restored LLMServiceSession instance
        """
        instance = cls(api_key=api_key, session_id=checkpoint["session_id"])
        instance.history = checkpoint["history"]
        instance.metadata = checkpoint["metadata"]
        return instance
    
    # ===================================================================
    # UTILITIES
    # ===================================================================
    
    def get_conversation_summary(self, last_n: int = 5) -> str:
        """Get formatted summary of recent conversation."""
        recent = self.history[-last_n:] if len(self.history) > last_n else self.history
        return "\n".join([
            f"[{msg['sender'].upper()}] {msg['content'][:100]}..."
            for msg in recent
        ])
    
    def __repr__(self):
        return f"<LLMServiceSession id={self.session_id}, turns={self.metadata['turn_count']}>"