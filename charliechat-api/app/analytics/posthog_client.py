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


def _is_test_environment() -> bool:
    """
    Check if we're running in a test environment.
    
    Returns:
        bool: True if running in tests, False otherwise
    """
    return os.getenv("PYTEST_CURRENT_TEST") is not None or "pytest" in os.getenv("_", "")


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
        
        # Enable debug mode only when our application debug is enabled
        debug_enabled = os.getenv("DEBUG_LOGGING", "false").lower() == "true"
        posthog.debug = debug_enabled
        
        logger.info(
            "✅ PostHog client initialized: API key length=%s, host=%s, debug=%s",
            len(api_key) if api_key else 0,
            posthog.host,
            debug_enabled
        )
        
        # Send a debug startup event only when debug mode is enabled
        if debug_enabled:
            try:
                posthog.capture(
                    distinct_id="lambda_debug_test",
                    event="lambda_posthog_debug_startup",
                    properties={"debug": True, "environment": "lambda", "startup": True}
                )
                posthog.flush()
                logger.info("✅ Sent PostHog debug startup event from Lambda")
            except Exception as e:
                logger.error(f"❌ Failed to send PostHog debug startup event: {e}")
        else:
            logger.debug("PostHog debug startup event skipped (debug mode disabled)")
        
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
    # Skip capture in test environments
    if _is_test_environment():
        logger.debug(f"PostHog disabled in test environment: Event '{event_name}' not captured")
        return False
    
    client = get_posthog_client()
    
    if not client:
        logger.warning(f"PostHog disabled: Event '{event_name}' not captured - client is None")
        return False
    
    logger.info(f"PostHog capturing event: {event_name} with distinct_id: {distinct_id or 'anonymous'}")
    
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
        
        # Debug: Log detailed capture attempt
        logger.debug(f"About to call client.capture for {event_name}")
        logger.debug(f"user_id={user_id}")
        logger.debug(f"properties={event_properties}")
        logger.debug(f"client.api_key length={len(client.api_key) if hasattr(client, 'api_key') else 'no api_key'}")
        logger.debug(f"client.host={getattr(client, 'host', 'no host')}")
        
        # Capture the event
        capture_result = client.capture(
            distinct_id=user_id,
            event=event_name,
            properties=event_properties
        )
        
        logger.debug(f"client.capture returned: {capture_result}")
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
    
    Note: This is a synchronous flush that may impact performance.
    Consider batching events or using async flushing if performance becomes a concern.
    
    Returns:
        bool: True if events were flushed successfully, False otherwise
    """
    client = get_posthog_client()
    
    if not client:
        logger.warning("PostHog disabled: No events to flush - client is None")
        return False
    
    logger.info("PostHog flushing events...")
    
    try:
        # Debug: Check if client has any pending events
        if hasattr(client, '_queue') and hasattr(client._queue, 'qsize'):
            queue_size = client._queue.qsize()
            logger.debug(f"Queue size before flush: {queue_size}")
        elif hasattr(client, 'queue') and hasattr(client.queue, 'qsize'):
            queue_size = client.queue.qsize()
            logger.debug(f"Queue size before flush: {queue_size}")
        else:
            logger.debug("Cannot determine queue size")
            
        logger.debug(f"client.debug={getattr(client, 'debug', 'no debug attr')}")
        logger.debug(f"client.sync_mode={getattr(client, 'sync_mode', 'no sync_mode attr')}")
        logger.debug(f"client.send={getattr(client, 'send', 'no send attr')}")
        
        flush_result = client.flush()
        logger.debug(f"client.flush() returned: {flush_result}")
        logger.debug("PostHog events flushed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to flush PostHog events: {e}")
        return False


# Initialize the client lazily when first accessed
# This will be set by get_posthog_client() when called
