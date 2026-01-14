"""Confirmation detection logic"""

import json
from typing import Dict
from models import ConfirmationDetection


class ConfirmationHandler:
    """Handles confirmation/rejection/modification detection"""
    
    def __init__(self, llm_session):
        """
        Initialize confirmation handler
        
        Args:
            llm_session: LLM service session instance
        """
        self.llm_session = llm_session
    
    async def detect_confirmation(self, 
                                  user_message: str, 
                                  pending_suggestions: Dict) -> ConfirmationDetection:
        """
        Detect if user is confirming, rejecting, or modifying suggestions
        
        Args:
            user_message: User's response
            pending_suggestions: Currently pending field suggestions
            
        Returns:
            ConfirmationDetection with classification
        """
        self.llm_session.attach_bean("confirmation_context", {
            "pending_suggestions": pending_suggestions
        })
        
        prompt = f"""I suggested these field values:
{json.dumps(pending_suggestions, indent=2)}

User responded: "{user_message}"

Classify as:
1. CONFIRMATION (yes/ok/looks good/apply/correct)
2. REJECTION (no/wrong/don't apply)
3. MODIFICATION (change X to Y)

JSON response:
{{
  "is_confirmation": true/false,
  "is_rejection": true/false,
  "is_modification_request": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "explanation",
  "extracted_modifications": {{"field": "value"}} or null
}}"""
        
        try:
            response = self.llm_session.call_llm(
                prompt=prompt,
                agent="confirmation_detector",
                system_prompt="You detect user confirmations accurately.",
                include_history=False
            )
            
            confirmation_json = self._extract_json(response)
            self.llm_session.clear_beans()
            
            return ConfirmationDetection(**confirmation_json)
            
        except Exception as e:
            print(f"⚠️ Confirmation detection failed: {e}")
            return self._fallback_detection(user_message)
    
    def _extract_json(self, response: Dict) -> Dict:
        """Extract JSON from LLM response"""
        if "candidates" in response and len(response["candidates"]) > 0:
            text = response["candidates"][0]["content"]["parts"][0]["text"]
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        raise ValueError("No valid response from LLM")
    
    def _fallback_detection(self, message: str) -> ConfirmationDetection:
        """Rule-based fallback for confirmation detection"""
        msg_lower = message.lower().strip()
        
        is_conf = any(word in msg_lower for word in 
                     ["ok", "yes", "yeah", "sure", "looks good", "apply", "correct"])
        is_rej = any(word in msg_lower for word in 
                    ["no", "nope", "wrong", "incorrect", "don't", "cancel"])
        
        return ConfirmationDetection(
            is_confirmation=is_conf,
            is_rejection=is_rej,
            is_modification_request=False,
            confidence=0.7,
            reasoning="Fallback rule-based detection"
        )