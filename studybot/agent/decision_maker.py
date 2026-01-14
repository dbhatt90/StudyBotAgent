"""LLM decision making logic"""

import json
from typing import Dict
from models import AgentDecision, ActionType


class DecisionMaker:
    """Handles LLM-based decision making"""
    
    SYSTEM_PROMPT = """You are an intelligent assistant helping users fill study ticket forms efficiently.

Your role:
1. FIRST: Extract any explicit field values from user input
2. THEN: Search previous studies to auto-fill remaining fields
3. Handle confirmations and modifications
4. Guide users proactively through form completion
5. Handle casual conversation politely

DECISION PRIORITY:
1. SUGGEST_FIELDS - Extract ANY explicit field values
2. UPDATE_FIELD - Single clear field update
3. SEARCH_RAG - When user describes problem but no explicit fields
4. SUBMIT_FORM - User confirms submission AND form is 100% complete
5. GENERIC_RESPONSE - Casual conversation
6. CLARIFY - Unclear input

Be conversational, proactive, and helpful."""
    
    def __init__(self, llm_session):
        """
        Initialize decision maker
        
        Args:
            llm_session: LLM service session instance
        """
        self.llm_session = llm_session
    
    async def decide_action(self, 
                           user_message: str, 
                           agent_state: Dict) -> AgentDecision:
        """
        Decide next action based on user message and current state
        
        Args:
            user_message: User's input message
            agent_state: Current agent state (progress, fields, etc.)
            
        Returns:
            AgentDecision with action type and parameters
        """
        # Attach state as context
        self.llm_session.attach_bean("agent_state", agent_state)
        
        # Build prompt
        prompt = self._build_decision_prompt(user_message, agent_state)
        
        try:
            response = self.llm_session.call_llm(
                prompt=prompt,
                agent="decision_maker",
                system_prompt=self.SYSTEM_PROMPT,
                include_history=True
            )
            
            decision_json = self._extract_json(response)
            self.llm_session.clear_beans()
            
            return AgentDecision(**decision_json)
            
        except Exception as e:
            print(f"❌ LLM decision failed: {e}")
            return self._fallback_decision(user_message)
    
    def _build_decision_prompt(self, user_message: str, state: Dict) -> str:
        """Build decision prompt from message and state"""
        return f"""Current form state:
- Progress: {state.get('progress_pct', 0)}%
- Filled fields: {json.dumps(state.get('filled_fields', {}), indent=2)}
- Empty fields: {state.get('empty_fields', [])}

User message: "{user_message}"

DECISION LOGIC:

STEP 1: Check if message is GENERIC (not about study ticket)
Is it: greeting, thanks, or unrelated chat?
→ ACTION: GENERIC_RESPONSE

STEP 2: Check for EXPLICIT field values
Does the message contain field values?
→ ACTION: SUGGEST_FIELDS

STEP 3: Check if describes problem (no explicit fields)
→ ACTION: SEARCH_RAG

STEP 4: Single clear update
→ ACTION: UPDATE_FIELD

STEP 5: Submit request AND 100% complete
→ ACTION: SUBMIT_FORM

OTHERWISE:
→ ACTION: CLARIFY

Respond with JSON:
{{
  "action": "suggest_fields|update_field|search_rag|submit_form|clarify|generic_response",
  "reasoning": "explanation",
  "suggested_fields": {{"field": "value"}} if SUGGEST_FIELDS,
  "message_to_user": "conversational message",
  "requires_user_input": true/false,
  "confidence": 0.0-1.0
}}"""
    
    def _extract_json(self, response: Dict) -> Dict:
        """Extract JSON from LLM response"""
        if "candidates" in response and len(response["candidates"]) > 0:
            text = response["candidates"][0]["content"]["parts"][0]["text"]
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        raise ValueError("No valid response from LLM")
    
    def _fallback_decision(self, message: str) -> AgentDecision:
        """Fallback decision when LLM fails"""
        return AgentDecision(
            action=ActionType.CLARIFY,
            reasoning="Error processing request",
            message_to_user="I'm having trouble understanding. Could you rephrase that?",
            requires_user_input=True,
            confidence=0.3
        )
