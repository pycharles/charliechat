"""
Amplitude Analytics Client for Charlie Chat API

This is an example of how to add another analytics provider
following the same pattern as PostHog.
"""

import os
import logging
from typing import Optional, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

# Global Amplitude client instance (lazy initialized)
analytics_amplitude_fastapi: Optional[Any] = None


def _is_lambda_environment() -> bool:
    """Check if we're running in AWS Lambda environment."""
    return bool(os.getenv("AWS_EXECUTION_ENV"))


def _initialize_amplitude() -> Optional[Any]:
    """
    Initialize Amplitude client if running in Lambda environment.
    
    Returns:
        Amplitude client instance or None if not in Lambda or missing API key
    """
    if not _is_lambda_environment():
        logger.info("Amplitude disabled: Not running in AWS Lambda environment")
        return None
    
    api_key = os.getenv("AMPLITUDE_API_KEY")
    if not api_key:
        logger.warning("Amplitude disabled: AMPLITUDE_API_KEY environment variable not set")
        return None
    
    try:
        # Import Amplitude SDK (would need to be added to requirements.txt)
        # from amplitude import Amplitude
        # 
        # client = Amplitude(api_key)
        # logger.info("Amplitude initialized successfully for FastAPI Lambda")
        # return client
        
        logger.info("Amplitude client would be initialized here (package not installed)")
        return None
        
    except ImportError:
        logger.error("Amplitude disabled: amplitude package not installed")
        return None
    except Exception as e:
        logger.error(f"Amplitude initialization failed: {e}")
        return None


def get_amplitude_client() -> Optional[Any]:
    """Get Amplitude client instance with lazy initialization."""
    global analytics_amplitude_fastapi
    
    if analytics_amplitude_fastapi is None:
        analytics_amplitude_fastapi = _initialize_amplitude()
    
    return analytics_amplitude_fastapi


def capture_event(event_name: str, properties: Optional[Dict[str, Any]] = None, distinct_id: Optional[str] = None) -> bool:
    """Safely capture an event with Amplitude."""
    client = get_amplitude_client()
    
    if not client:
        logger.debug(f"Amplitude disabled: Event '{event_name}' not captured")
        return False
    
    try:
        # Amplitude event capture logic would go here
        logger.debug(f"Amplitude event captured: '{event_name}' for user '{distinct_id or 'anonymous'}'")
        return True
        
    except Exception as e:
        logger.error(f"Failed to capture Amplitude event '{event_name}': {e}")
        return False
