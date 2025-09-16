"""
Chat Service

This service orchestrates the chat flow by coordinating between
Lex service, AI service, and session management.
"""

from typing import Dict, Any, Optional, Tuple
from ..config import Settings
from ..models.lex import LexResponse
from .lex_service import LexService
from .ai_service import AIService


class ChatService:
    """Service for orchestrating chat interactions"""
    
    def __init__(self, settings: Settings):
        """Initialize the chat service with dependencies"""
        self.lex_service = LexService(settings)
        self.ai_service = AIService()

    def process_chat(self, session_id: str, text: str, session_state: Optional[Dict[str, Any]] = None, voice_style: str = "normal") -> Tuple[str, Dict[str, Any]]:
        """
        Process a chat interaction end-to-end
        
        Args:
            session_id: Unique session identifier
            text: User input text
            session_state: Optional session state for context
            
        Returns:
            Tuple of (response_text, updated_session_state)
        """
        # Step 1: Call Lex to process user input and extract slots
        lex_response = self.lex_service.recognize_text(session_id, text, session_state)
        
        # Step 2: Check if Lex provided a direct response (cost savings)
        # Only use Lex direct responses for specific intents, not fallback responses
        if self.lex_service.has_direct_response(lex_response):
            # Check if this is a fallback response (indicates Lex couldn't understand)
            interpretations = lex_response.interpretations or []
            is_fallback = False
            if interpretations:
                # Get the first interpretation (highest confidence)
                top_interpretation = interpretations[0]
                top_intent_name = top_interpretation.get("intent", {}).get("name")
                is_fallback = top_intent_name == "FallbackIntent"
            
            if not is_fallback:
                direct_response = self.lex_service.get_direct_response_text(lex_response)
                if direct_response.strip():
                    # Check if this is an error response from Lex
                    error_indicators = [
                        "something went wrong while answering that",
                        "try again in a moment",
                        "error",
                        "failed",
                        "hmm, something went wrong"
                    ]
                    is_error_response = any(
                        indicator in direct_response.lower() 
                        for indicator in error_indicators
                    )
                    
                    if not is_error_response:
                        # Use Lex direct response for other intents
                        return direct_response, lex_response.session_state or {}
                    else:
                        # Lex returned error, fall back to AI
                        pass
        
        # Step 3: Extract slots for AI processing
        person_slot, question_slot = self.lex_service.extract_slots(lex_response)
        
        # Step 4: Normalize person name
        person = self.ai_service.normalize_person_name(person_slot)
        
        # Step 5: Get session attributes for context
        session_attributes = self._get_session_attributes(lex_response)
        
        # Store the current voice_style in session attributes for persistence
        if session_attributes is None:
            session_attributes = {}
        session_attributes['current_voice_style'] = voice_style
        
        # Step 6: Process with AI if we have a valid question
        if question_slot and question_slot.strip():
            # Use the extracted question from Lex
            question = question_slot.strip()
        elif text and text.strip():
            # Fallback: use the raw user input as the question
            question = text.strip()
        else:
            # No question available - clear stale memory and return fallback
            updated_session_state = self._update_session_state(lex_response, {})
            return "I did not catch a question. Please ask me about experience, skills, or leadership style.", updated_session_state
        
        # Process with AI
        ai_response, updated_attributes = self.ai_service.query_bedrock(
            person=person,
            question=question,
            session_attributes=session_attributes,
            voice_style=voice_style
        )
        
        # Update session state with AI response
        updated_session_state = self._update_session_state(lex_response, updated_attributes)
        return ai_response, updated_session_state

    def _get_session_attributes(self, lex_response: LexResponse) -> Dict[str, Any]:
        """
        Extract session attributes from Lex response
        
        Args:
            lex_response: Response from Lex recognition
            
        Returns:
            Session attributes dictionary
        """
        if not lex_response.session_state:
            return {}
        
        # Handle raw dict data from Lex
        if isinstance(lex_response.session_state, dict):
            return lex_response.session_state.get("sessionAttributes", {})
        
        # Handle Pydantic model (if it exists)
        return getattr(lex_response.session_state, "session_attributes", {}) or {}

    def _update_session_state(self, lex_response: LexResponse, updated_attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update session state with new attributes
        
        Args:
            lex_response: Original Lex response
            updated_attributes: New attributes to add
            
        Returns:
            Updated session state
        """
        if not lex_response.session_state:
            return {"sessionAttributes": updated_attributes}
        
        # Handle raw dict data from Lex
        if isinstance(lex_response.session_state, dict):
            session_state = lex_response.session_state.copy()
        else:
            # Handle Pydantic model (if it exists)
            session_state = lex_response.session_state.dict() if hasattr(lex_response.session_state, 'dict') else {}
        
        # Update session attributes
        if "sessionAttributes" not in session_state:
            session_state["sessionAttributes"] = {}
        
        session_state["sessionAttributes"].update(updated_attributes)
        
        return session_state
