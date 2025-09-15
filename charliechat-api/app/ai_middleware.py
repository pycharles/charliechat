"""
AI Middleware for Charlie Chat

This module handles the integration between Lex slot extraction and Bedrock AI responses.
It normalizes person names, builds conversational prompts, and queries Bedrock for responses.

Context Memory System:
- Uses Lex sessionAttributes to store lightweight conversation context
- Tracks both last_answer and last_question for better follow-up context
- Only stores the last exchange (not full conversation history) for cost efficiency
- Allows follow-up questions to reference previous Q&A for better responses
- Developers can extend this by adding more attributes to sessionAttributes

Personality & Tone:
- Configurable in SYSTEM_PROMPT_TEMPLATE at the top of this file
- Current: "professional but chill surfer tone" - helpful and concise
- Easy to modify: change the template text to adjust personality
- Can be overridden via SYSTEM_PROMPT_TEMPLATE environment variable

Environment Variables (.env file):
- BEDROCK_MODEL_ID: Switch Claude model (haiku/sonnet/opus)
- BEDROCK_MAX_TOKENS: Control response length (100-4000)
- SYSTEM_PROMPT_TEMPLATE: Full prompt override for personality/tone
- DEFAULT_PERSON: Default person name when Lex slot is missing (allows bot reuse)
- DEBUG_LOGGING: Enable debug logging for development (true/false)
"""

import boto3
import json
import os
from typing import Optional

# Environment-driven configuration
# These can be set in .env file or AWS Lambda environment variables
# 
# Supported Environment Variables:
# - BEDROCK_MODEL_ID: Switch Claude model (haiku, sonnet, etc.)
#   Examples: "anthropic.claude-3-haiku-20240307-v1:0" (fast, cheap)
#             "anthropic.claude-3-sonnet-20240229-v1:0" (balanced)
#             "anthropic.claude-3-opus-20240229-v1:0" (most capable)
#
# - BEDROCK_MAX_TOKENS: Control output length (100-4000)
#   Examples: "1000" (default), "2000" (longer responses), "500" (shorter)
#
# - SYSTEM_PROMPT_TEMPLATE: Full system prompt override for personality/tone
#   Must include {person}, {question}, and {context} placeholders
#   Example: "You are a helpful assistant representing {person}. Answer {question} professionally. {context}"
#
# - DEFAULT_PERSON: Default person name when Lex slot is missing/empty
#   Examples: "Charles" (default), "Sarah", "Alex" - allows bot reuse for different personas
#
# - DEBUG_LOGGING: Enable debug logging for development (true/false)
#   When true, logs full prompts and AI responses for debugging
#
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
BEDROCK_MAX_TOKENS = int(os.getenv("BEDROCK_MAX_TOKENS", "1000"))
SYSTEM_PROMPT_OVERRIDE = os.getenv("SYSTEM_PROMPT_TEMPLATE")
DEFAULT_PERSON = os.getenv("DEFAULT_PERSON", "Charles")
DEBUG_LOGGING = os.getenv("DEBUG_LOGGING", "false").lower() == "true"

# System prompt template for Bedrock
# This is where you can tweak personality, verbosity, or response style
# To modify tone: change "professional but chill surfer tone" to your preferred style
# To adjust verbosity: modify "concise" or add/remove guidance about length
# Environment variable SYSTEM_PROMPT_TEMPLATE can override this entire template
DEFAULT_SYSTEM_PROMPT_TEMPLATE = """
You are Charlie Chat, a helpful assistant representing {person}.
Answer in a professional but chill surfer tone. Stay helpful, concise, and clear.
Use short paragraphs, avoid jargon, and keep answers practical and actionable.
If unsure, encourage the user to ask about {person}'s experience, leadership style, or technical skills.

{context}

Question: {question}
"""

# Use environment override if available, otherwise use default
SYSTEM_PROMPT_TEMPLATE = SYSTEM_PROMPT_OVERRIDE if SYSTEM_PROMPT_OVERRIDE else DEFAULT_SYSTEM_PROMPT_TEMPLATE


def _trim_answer(answer: str, max_length: int = 1200) -> str:
    """
    Trim answer to prevent session attributes from becoming too large.
    
    This keeps session memory lightweight while preserving the most important parts
    of the answer for follow-up context.
    
    Args:
        answer: The answer text to trim
        max_length: Maximum length before truncation
        
    Returns:
        Trimmed answer with "..." if truncated
    """
    answer = answer.strip()
    if len(answer) <= max_length:
        return answer
    return answer[:max_length-3] + "..."


def normalize_person_name(person_value: Optional[str]) -> str:
    """
    Normalize person name values from Lex slots.
    
    Maps variations like "Charlie", "Chaz", "Charles O'Brien" to "Charles".
    Uses DEFAULT_PERSON environment variable for fallback, allowing bot reuse for different personas.
    
    Args:
        person_value: Raw person name from Lex slot, can be None
        
    Returns:
        Normalized person name, defaults to DEFAULT_PERSON if None or empty
    """
    if not person_value or not person_value.strip():
        return DEFAULT_PERSON
    
    # Convert to lowercase for comparison
    name_lower = person_value.strip().lower()
    
    # Map common variations to "Charles"
    if name_lower in ["charlie", "chaz", "charles o'brien", "charles obrien", "charles o brien"]:
        return "Charles"
    
    # If it's already "charles" or starts with "charles", return "Charles"
    if name_lower == "charles" or name_lower.startswith("charles "):
        return "Charles"
    
    # For any other name, return as-is but title-cased
    return person_value.strip().title()


def build_prompt(person: str, question: str, session_attributes: dict | None = None) -> str:
    """
    Build a conversational prompt using the system template with optional context.
    
    This function creates prompts that include previous conversation context when available,
    allowing Bedrock to provide better follow-up responses without full conversation history.
    
    Args:
        person: Normalized person name
        question: User's question
        session_attributes: Optional Lex session attributes containing context
        
    Returns:
        Formatted prompt string for Bedrock with context if available
    """
    # Build context section dynamically based on available session attributes
    # This creates a clean context block that only appears when previous conversation exists
    context_lines = []
    
    if session_attributes and isinstance(session_attributes, dict):
        last_question = session_attributes.get("last_question")
        last_answer = session_attributes.get("last_answer")
        
        # Add previous question if available (helps with follow-up context)
        if last_question and last_question.strip():
            context_lines.append(f"Previous question: {last_question}")
        
        # Add previous answer if available (helps with continuity)
        if last_answer and last_answer.strip():
            context_lines.append(f"Previous answer: {last_answer}")
    
    # Format context section (empty string if no context available)
    # This ensures the template works for both first-turn and follow-up conversations
    context = "\n".join(context_lines) if context_lines else ""
    
    # Use single template with dynamic context
    return SYSTEM_PROMPT_TEMPLATE.format(
        person=person,
        question=question,
        context=context
    )


def query_bedrock(person: str, question: str, session_attributes: dict | None = None, model_id: str | None = None) -> tuple[str, dict]:
    """
    Query Bedrock with the person and question to get an AI response with context memory.
    
    This function uses session attributes to provide conversational context and returns
    updated session attributes that can be stored back in Lex session state for follow-up turns.
    
    Args:
        person: Normalized person name
        question: User's question
        session_attributes: Optional Lex session attributes containing context (e.g., last_answer)
        model_id: Bedrock model ID to use (defaults to BEDROCK_MODEL_ID env var)
        
    Returns:
        Tuple of (AI response string, updated session attributes dict)
        The updated session attributes include the new answer for future context
    """
    try:
        # Initialize Bedrock client
        bedrock = boto3.client("bedrock-runtime")
        
        # Use environment-configured model ID if not provided
        effective_model_id = model_id or BEDROCK_MODEL_ID
        
        # Build the prompt with session context if available
        prompt = build_prompt(person, question, session_attributes)
        
        # Debug logging for development (can be swapped for structured logging)
        if DEBUG_LOGGING:
            print(f"[DEBUG] Full prompt sent to Bedrock:\n{prompt}\n")
        
        # Prepare the request body for Claude
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": BEDROCK_MAX_TOKENS,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        # Call Bedrock
        response = bedrock.invoke_model(
            modelId=effective_model_id,
            body=json.dumps(body),
            contentType="application/json"
        )
        
        # Parse the response
        response_body = json.loads(response["body"].read())
        
        # Extract the content from Claude's response
        if "content" in response_body and len(response_body["content"]) > 0:
            ai_response = response_body["content"][0]["text"]
        else:
            ai_response = "I apologize, but I couldn't generate a response. Please try asking about experience, skills, or leadership style."
        
        # Debug logging for development (can be swapped for structured logging)
        if DEBUG_LOGGING:
            truncated_response = ai_response[:300] + "..." if len(ai_response) > 300 else ai_response
            print(f"[DEBUG] AI response (truncated): {truncated_response}\n")
        
        # Create updated session attributes with both answer and question for future context
        # This is lightweight memory - only storing the last exchange, not full conversation history
        updated_attributes = session_attributes.copy() if session_attributes else {}
        
        # Trim and sanitize stored context to keep memory lightweight and safe
        # This prevents session attributes from becoming too large and removes problematic characters
        updated_attributes["last_answer"] = _trim_answer(ai_response)
        updated_attributes["last_question"] = question.strip().replace('\n', ' ').replace('\r', ' ')
        
        return ai_response, updated_attributes
            
    except Exception as e:
        # Log the error (in production, you'd want proper logging)
        print(f"Bedrock error: {e}")
        fallback_response = "I'm having trouble connecting to my AI service right now. Please try asking about experience, skills, or leadership style."
        
        # Return fallback response with empty session attributes
        return fallback_response, {}
