"""
Chat Service

This service orchestrates the chat flow by handling intent recognition
and coordinating with AI service for response generation.
"""

from typing import Dict, Any, Optional, Tuple
import traceback
import re
from ..config import Settings
from .ai_service import AIService
from ..utils.debug_logger import debug_logger
from .prompt_engineering import prompt_engineer


class ChatService:
    """Service for orchestrating chat interactions"""
    
    def __init__(self, settings: Settings):
        """Initialize the chat service with dependencies"""
        self.ai_service = AIService()
        self.settings = settings

    async def process_chat(self, request_id: str, session_id: str, text: str, session_state: Optional[Dict[str, Any]] = None, voice_style: str = "normal", request: Optional[Any] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Process a chat interaction end-to-end with direct intent recognition
        
        Args:
            request_id: Unique request identifier for tracing
            session_id: Unique session identifier
            text: User input text
            session_state: Optional session state for context
            voice_style: Voice style for response tone
            request: Optional FastAPI request object for timing
            
        Returns:
            Tuple of (response_text, updated_session_state)
        """
        debug_logger.log_chat(
            request_id,
            f"Processing chat for session {session_id}: '{text[:50]}{'...' if len(text) > 50 else ''}'",
            request
        )
        # Stack trace logging removed to reduce log noise
        
        # Step 1: Extract person and question using simple pattern matching
        person, question = self._extract_intent_slots(text)
        
        # Step 2: Normalize person name
        person = self.ai_service.normalize_person_name(person)
        
        # Step 3: Get session attributes for context
        session_attributes = session_state or {}
        session_attributes['current_voice_style'] = voice_style
        
        # Step 4: Process with AI if we have a valid question
        if question and question.strip():
            # Use the extracted question
            question_text = question.strip()
        elif text and text.strip():
            # Fallback: use the raw user input as the question
            question_text = text.strip()
        else:
            # No question available - return fallback
            debug_logger.log_chat(
                request_id,
                "No valid question found, returning fallback response",
                request
            )
            return "I did not catch a question. Please ask me about experience, skills, or leadership style.", session_attributes
        
        debug_logger.log_chat(
            request_id,
            f"Extracted person: '{person}', question: '{question_text}'",
            request
        )
        
        # Step 5: Process with AI using prompt engineering
        debug_logger.log_chat(
            request_id,
            "Calling AI service for response generation",
            request
        )
        
        # Debug logging for session attributes
        debug_logger.log_chat(
            request_id,
            f"Session attributes being passed to AI: {session_attributes}",
            request
        )
        if session_attributes and "conversation_history" in session_attributes:
            debug_logger.log_chat(
                request_id,
                f"Conversation history length: {len(session_attributes['conversation_history'])}",
                request
            )
        
        # Get KB query parameters using prompt engineering
        kb_query_params = prompt_engineer.get_kb_query_params(question_text)
        number_of_results = kb_query_params['numberOfResults']
        
        # Retrieve KB context with dynamic parameters
        kb_context = self.ai_service._retrieve_kb_context(question_text, number_of_results)
        
        # Select and potentially summarize KB context
        if kb_context and kb_context != "No additional KB context available.":
            # Parse KB passages for selection
            passages = kb_context.split('\n\n')
            selected_passages, _ = prompt_engineer.select_kb_context(question_text, passages)
            if selected_passages:
                kb_context = prompt_engineer.summarize_kb_context(selected_passages)
        
        # Calculate response length using prompt engineering
        response_length = prompt_engineer.calculate_response_length(question_text, self.ai_service.max_tokens)
        
        ai_response, updated_attributes = self.ai_service.query_bedrock(
            person=person,
            question=question_text,
            session_attributes=session_attributes,
            voice_style=voice_style,
            request_id=request_id,
            request=request,
            kb_context=kb_context,
            response_length=response_length
        )
        debug_logger.log_chat(
            request_id,
            "AI service completed successfully",
            request
        )
        
        # Step 6: Update session state with AI response
        updated_session_state = {**session_attributes, **updated_attributes}
        debug_logger.log_chat(
            request_id,
            f"Chat processing completed for session {session_id}",
            request
        )
        return ai_response, updated_session_state

    def _extract_intent_slots(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract person and question slots using simple pattern matching
        
        Args:
            text: User input text
            
        Returns:
            Tuple of (person_slot, question_slot)
        """
        if not text or not text.strip():
            return None, None
        
        text_lower = text.lower().strip()
        person = None
        question = None
        
        # Common person name patterns
        person_patterns = [
            r'\b(?:about|tell me about|what about)\s+(charles|charlie|chaz|charles o\'?brien|charles obrien)\b',
            r'\b(charles|charlie|chaz|charles o\'?brien|charles obrien)\'?s\s+(?:experience|skills|background|work|career)\b',
            r'^(charles|charlie|chaz|charles o\'?brien|charles obrien)\b',
        ]
        
        # Extract person name
        for pattern in person_patterns:
            match = re.search(pattern, text_lower)
            if match:
                person = match.group(1)
                break
        
        # If no specific person mentioned, use default
        if not person:
            person = self.settings.default_person if hasattr(self.settings, 'default_person') else 'Charles'
        
        # Extract question - remove person references to get clean question
        question = text.strip()
        
        # Remove person name references from question
        person_cleanup_patterns = [
            r'\b(?:about|tell me about)\s+(?:charles|charlie|chaz|charles o\'?brien|charles obrien)\b',
            r'\b(?:charles|charlie|chaz|charles o\'?brien|charles obrien)\'?s\s+',
            r'^(?:charles|charlie|chaz|charles o\'?brien|charles obrien)\b\s*',
        ]
        
        for pattern in person_cleanup_patterns:
            question = re.sub(pattern, '', question, flags=re.IGNORECASE)
        
        question = question.strip()
        
        return person, question if question else None
