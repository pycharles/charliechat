"""
Lex V2 Service

This service handles all interactions with AWS Lex V2, including
text recognition, slot extraction, and session management.
"""

from __future__ import annotations
import boto3
from typing import Dict, Any, Optional

from ..config import Settings
from ..models.lex import LexResponse


class LexService:
    """Service for interacting with AWS Lex V2"""
    
    def __init__(self, settings: Settings) -> None:
        """Initialize the Lex service with AWS credentials"""
        session = boto3.Session(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            aws_session_token=settings.aws_session_token,
            region_name=settings.aws_region,
        )
        self.client = session.client("lexv2-runtime", region_name=settings.aws_region)
        self.bot_id = settings.lex_bot_id
        self.bot_alias_id = settings.lex_bot_alias_id
        self.locale_id = settings.lex_bot_locale_id

    def recognize_text(self, session_id: str, text: str, session_state: Optional[Dict[str, Any]] = None) -> LexResponse:
        """
        Send text to Lex V2 for recognition and slot extraction
        
        Args:
            session_id: Unique session identifier
            text: User input text
            session_state: Optional session state for context
            
        Returns:
            LexResponse containing messages, session state, and interpretations
        """
        kwargs: Dict[str, Any] = {
            "botId": self.bot_id,
            "botAliasId": self.bot_alias_id,
            "localeId": self.locale_id,
            "sessionId": session_id,
            "text": text,
        }
        
        if session_state:
            # Format session state for Lex V2 API
            intent = session_state.get("intent", {})
            slots = intent.get("slots", {})
            
            # Ensure slots are properly formatted (not None)
            formatted_slots = {}
            for slot_name, slot_value in slots.items():
                if slot_value is not None:
                    formatted_slots[slot_name] = slot_value
                else:
                    formatted_slots[slot_name] = {}
            
            formatted_session_state = {
                "sessionAttributes": session_state.get("sessionAttributes", {}),
                "dialogAction": session_state.get("dialogAction", {"type": "Delegate"}),
                "intent": {
                    "name": intent.get("name", "FallbackIntent"),
                    "state": intent.get("state", "ReadyForFulfillment"),
                    "slots": formatted_slots
                }
            }
            kwargs["sessionState"] = formatted_session_state
            
        response = self.client.recognize_text(**kwargs)
        
        # Return structured response with raw data (avoid Pydantic validation issues)
        return LexResponse(
            messages=response.get("messages", []),
            session_state=response.get("sessionState"),
            interpretations=response.get("interpretations", [])
        )

    def extract_slots(self, lex_response: LexResponse) -> tuple[Optional[str], Optional[str]]:
        """
        Extract person and question slots from Lex response
        
        Args:
            lex_response: Response from Lex recognition
            
        Returns:
            Tuple of (person_slot, question_slot) values
        """
        person_slot = None
        question_slot = None
        
        interpretations = lex_response.interpretations or []
        
        for interpretation in interpretations:
            slots = interpretation.get("intent", {}).get("slots", {})
            
            # Extract person slot
            person_data = slots.get("person")
            if person_data and isinstance(person_data, dict):
                person_value = person_data.get("value", {})
                if isinstance(person_value, dict):
                    person_slot = person_value.get("originalValue")
            
            # Extract question slot
            question_data = slots.get("question")
            if question_data and isinstance(question_data, dict):
                question_value = question_data.get("value", {})
                if isinstance(question_value, dict):
                    question_slot = question_value.get("originalValue")
        
        return person_slot, question_slot

    def has_direct_response(self, lex_response: LexResponse) -> bool:
        """
        Check if Lex provided a direct response (no AI needed)
        
        Args:
            lex_response: Response from Lex recognition
            
        Returns:
            True if Lex has direct messages, False otherwise
        """
        messages = lex_response.messages or []
        return len(messages) > 0

    def get_direct_response_text(self, lex_response: LexResponse) -> str:
        """
        Extract text from Lex direct response messages
        
        Args:
            lex_response: Response from Lex recognition
            
        Returns:
            Combined text from all messages
        """
        messages = lex_response.messages or []
        return " ".join(msg.get("content", "") for msg in messages if msg.get("contentType") == "PlainText")
