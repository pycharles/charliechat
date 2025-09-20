"""
Session Middleware for Charlie Chat

Provides cookie-based session management with automatic session ID generation
and refresh on every request to keep sessions alive.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import uuid
import random
import logging
from datetime import datetime, timedelta
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Human-readable word prefixes for session IDs
WORDS = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", 
         "golf", "hotel", "india", "juliet", "kilo", "lima", "mike"]


def generate_session_id():
    """Generate a human-readable session ID with word prefix and UUID"""
    word = random.choice(WORDS)
    return f"web-{word}-{uuid.uuid4()}"


class SessionMiddleware(BaseHTTPMiddleware):
    """
    Middleware that manages user sessions using HTTP cookies.
    
    Features:
    - Generates unique session IDs for new users
    - Refreshes session cookies on every request
    - Makes session_id available via request.state.session_id
    - Sets secure cookie attributes (httponly, samesite)
    """
    
    async def dispatch(self, request, call_next):
        try:
            if settings.debug:
                logger.debug(f"Processing request to {request.url.path}")
            
            # Get existing session ID from cookie or generate new one
            session_id = request.cookies.get("session_id")
            if not session_id:
                session_id = generate_session_id()
                if settings.debug:
                    logger.debug(f"Generated new session_id: {session_id}")
            else:
                if settings.debug:
                    logger.debug(f"Using existing session_id: {session_id}")
            
            # Make session_id available to all routes
            request.state.session_id = session_id

            # Process the request
            if settings.debug:
                logger.debug(f"Calling next middleware/route for {request.url.path}")
            response: Response = await call_next(request)
            if settings.debug:
                logger.debug(f"Got response for {request.url.path}")

            # Refresh cookie on every request to keep session alive
            try:
                expires = (datetime.utcnow() + timedelta(minutes=30)).strftime("%a, %d-%b-%Y %H:%M:%S GMT")
                response.set_cookie(
                    "session_id",
                    session_id,
                    httponly=True,  # Prevent XSS attacks
                    samesite="Lax",  # CSRF protection
                    expires=expires,
                    max_age=1800  # 30 minutes in seconds
                )
                if settings.debug:
                    logger.debug(f"Set session cookie successfully for {request.url.path}")
            except Exception as cookie_error:
                logger.error(f"Failed to set session cookie for {request.url.path}: {cookie_error}")
                # Don't fail the request if cookie setting fails
            
            return response
            
        except Exception as e:
            logger.error(f"Exception in session middleware for {request.url.path}: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Try to create a basic error response
            try:
                from starlette.responses import JSONResponse
                return JSONResponse(
                    status_code=500,
                    content={"error": "Session middleware error", "path": str(request.url.path)}
                )
            except Exception as response_error:
                logger.error(f"Failed to create error response: {response_error}")
                # Last resort - re-raise the original exception
                raise
