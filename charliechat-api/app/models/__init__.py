"""
Data models for Charlie Chat

This module contains all Pydantic models for data validation and serialization.
"""

from .chat import ChatRequest, ChatResponse

__all__ = [
    "ChatRequest",
    "ChatResponse"
]
