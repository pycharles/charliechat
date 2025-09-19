"""
PostHog Analytics Client for Charlie Chat API

This module provides PostHog integration with lazy initialization.
Only initializes when running in AWS Lambda production environment.
"""

import os
import logging
from typing import Optional, Dict, Any
from functools import wraps

# Configure logging
logger = logging.getLogger(__name__)

# Global PostHog client instance (lazy initialized)
analytics_posthog_fastapi: Optional[Any] = None


def _is_lambda_environment() -> bool:
    """
    Check if we're running in AWS Lambda environment.
    
    Returns:
        bool: True if running in Lambda, False otherwise
    """
    return bool(os.getenv("AWS_EXECUTION_ENV"))


def _initialize_posthog() -> Optional[Any]:
    """
    Initialize PostHog client if running in Lambda environment.
    
    Returns:
        PostHog client instance or None if not in Lambda or missing API key
    """
    if not _is_lambda_environment():
        logger.info("PostHog disabled: Not running in AWS Lambda environment")
        return None
    
    api_key = os.getenv("POSTHOG_API_KEY")
    if not api_key:
        logger.warning("PostHog disabled: POSTHOG_API_KEY environment variable not set")
        return None
    
    try:
        import posthog
        
        # Initialize PostHog with project-specific settings
        posthog.api_key = api_key
        posthog.host = os.getenv("POSTHOG_HOST", "https://app.posthog.com")
        
        # Configure for Lambda environment
        posthog.sync_mode = True  # Use sync mode for Lambda
        posthog.send = True  # Enable sending events
        
        logger.info("PostHog initialized successfully for FastAPI Lambda")
        return posthog
        
    except ImportError:
        logger.error("PostHog disabled: posthog package not installed")
        return None
    except Exception as e:
        logger.error(f"PostHog initialization failed: {e}")
        return None


def get_posthog_client() -> Optional[Any]:
    """
    Get PostHog client instance with lazy initialization.
    
    Returns:
        PostHog client instance or None if disabled
    """
    global analytics_posthog_fastapi
    
    if analytics_posthog_fastapi is None:
        analytics_posthog_fastapi = _initialize_posthog()
    
    return analytics_posthog_fastapi


def capture_event(event_name: str, properties: Optional[Dict[str, Any]] = None, distinct_id: Optional[str] = None) -> bool:
    """
    Safely capture an event with PostHog.
    
    Args:
        event_name: Name of the event to capture
        properties: Optional event properties dictionary
        distinct_id: Optional distinct user ID (defaults to 'anonymous')
    
    Returns:
        bool: True if event was captured successfully, False otherwise
    """
    client = get_posthog_client()
    
    if not client:
        logger.debug(f"PostHog disabled: Event '{event_name}' not captured")
        return False
    
    try:
        # Use provided distinct_id or default to 'anonymous'
        user_id = distinct_id or "anonymous"
        
        # Add Lambda context properties
        event_properties = properties or {}
        event_properties.update({
            "lambda_function": os.getenv("AWS_LAMBDA_FUNCTION_NAME", "unknown"),
            "lambda_version": os.getenv("AWS_LAMBDA_FUNCTION_VERSION", "unknown"),
            "aws_region": os.getenv("AWS_REGION", "unknown"),
        })
        
        # Capture the event
        client.capture(
            distinct_id=user_id,
            event=event_name,
            properties=event_properties
        )
        
        logger.debug(f"PostHog event captured: '{event_name}' for user '{user_id}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to capture PostHog event '{event_name}': {e}")
        return False


def identify_user(distinct_id: str, properties: Optional[Dict[str, Any]] = None) -> bool:
    """
    Identify a user with PostHog.
    
    Args:
        distinct_id: Unique identifier for the user
        properties: Optional user properties dictionary
    
    Returns:
        bool: True if user was identified successfully, False otherwise
    """
    client = get_posthog_client()
    
    if not client:
        logger.debug(f"PostHog disabled: User identification skipped for '{distinct_id}'")
        return False
    
    try:
        client.capture(
            distinct_id=distinct_id,
            event="$identify",
            properties=properties or {}
        )
        
        logger.debug(f"PostHog user identified: '{distinct_id}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to identify PostHog user '{distinct_id}': {e}")
        return False


def alias_user(alias: str, distinct_id: str) -> bool:
    """
    Create an alias for a user with PostHog.
    
    Args:
        alias: The alias to create
        distinct_id: The distinct ID to alias to
    
    Returns:
        bool: True if alias was created successfully, False otherwise
    """
    client = get_posthog_client()
    
    if not client:
        logger.debug(f"PostHog disabled: User alias skipped for '{alias}' -> '{distinct_id}'")
        return False
    
    try:
        client.capture(
            distinct_id=distinct_id,
            event="$create_alias",
            properties={"alias": alias}
        )
        
        logger.debug(f"PostHog user aliased: '{alias}' -> '{distinct_id}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to alias PostHog user '{alias}' -> '{distinct_id}': {e}")
        return False


def flush_events() -> bool:
    """
    Flush pending PostHog events.
    
    Returns:
        bool: True if events were flushed successfully, False otherwise
    """
    client = get_posthog_client()
    
    if not client:
        logger.debug("PostHog disabled: No events to flush")
        return False
    
    try:
        client.flush()
        logger.debug("PostHog events flushed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to flush PostHog events: {e}")
        return False


# Initialize the client lazily when first accessed
# This will be set by get_posthog_client() when called
