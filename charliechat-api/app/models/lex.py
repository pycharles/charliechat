"""
Lex V2 data models

These models define the structure for Lex V2 events and responses
used in the Charlie Chat application.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class LexSlot(BaseModel):
    """Represents a Lex slot value"""
    value: Optional[Dict[str, Any]] = None
    values: Optional[List[Dict[str, Any]]] = None


class LexIntent(BaseModel):
    """Represents a Lex intent"""
    name: str
    state: str
    slots: Optional[Dict[str, Any]] = None  # Changed from LexSlot to Any for flexibility


class LexSessionState(BaseModel):
    """Represents Lex session state"""
    dialog_action: Optional[Dict[str, Any]] = None
    intent: Optional[LexIntent] = None
    session_attributes: Optional[Dict[str, Any]] = None


class LexEvent(BaseModel):
    """Represents a Lex V2 event"""
    session_state: Optional[LexSessionState] = None
    input_transcript: Optional[str] = None
    interpretations: Optional[List[Dict[str, Any]]] = None


class LexResponse(BaseModel):
    """Represents a Lex V2 response"""
    messages: List[Dict[str, Any]]
    session_state: Optional[Dict[str, Any]] = None  # Changed to Any for flexibility
    interpretations: Optional[List[Dict[str, Any]]] = None
