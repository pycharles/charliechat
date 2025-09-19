"""
Analytics module for Charlie Chat API

This module provides a clean interface for analytics providers like PostHog.
It's designed to be easily extensible for additional analytics providers.
"""

from .posthog_client import get_posthog_client, capture_event

# Get the PostHog client instance
analytics_posthog_fastapi = get_posthog_client()

__all__ = ["analytics_posthog_fastapi", "capture_event"]
