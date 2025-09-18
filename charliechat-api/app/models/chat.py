"""
Chat-related data models

These models define the structure for chat requests and responses
in the Charlie Chat application.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ChatRequest(BaseModel):
    """Request model for chat interactions"""
    session_id: str
    text: str
    session_state: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Response model for chat interactions"""
    messages: List[Dict[str, Any]]
    session_state: Optional[Dict[str, Any]] = None
