"""
Request timing middleware

Captures high-resolution start time for each request and logs total request time.
"""

import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from ..utils.debug_logger import debug_logger
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to capture request timing and log total request duration"""
    
    async def dispatch(self, request: Request, call_next):
        try:
            if settings.debug:
                logger.debug(f"Processing request to {request.url.path}")
            
            # Capture high-resolution start time
            request.state.start_time = time.perf_counter()
            
            # Generate request ID if not present
            if not hasattr(request.state, 'request_id'):
                import uuid
                request.state.request_id = str(uuid.uuid4())[:8]
            
            if settings.debug:
                logger.debug(f"Request ID: {request.state.request_id}")
            
            # Log request start
            try:
                debug_logger.log_route(
                    request.state.request_id,
                    f"Request started: {request.method} {request.url.path}",
                    request
                )
                if settings.debug:
                    logger.debug(f"Logged request start for {request.url.path}")
            except Exception as log_error:
                logger.error(f"Failed to log request start for {request.url.path}: {log_error}")
            
            # Process the request
            if settings.debug:
                logger.debug(f"Calling next middleware/route for {request.url.path}")
            response = await call_next(request)
            if settings.debug:
                logger.debug(f"Got response for {request.url.path}")
            
            # Calculate total request time
            total_time = time.perf_counter() - request.state.start_time
            total_time_ms = total_time * 1000
            
            # Log total request time
            try:
                debug_logger.log_route(
                    request.state.request_id,
                    f"Request completed: {response.status_code} in {total_time_ms:.3f}ms",
                    request
                )
                if settings.debug:
                    logger.debug(f"Logged request completion for {request.url.path} in {total_time_ms:.3f}ms")
            except Exception as log_error:
                logger.error(f"Failed to log request completion for {request.url.path}: {log_error}")
            
            return response
            
        except Exception as e:
            logger.error(f"Exception in timing middleware for {request.url.path}: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Try to create a basic error response
            try:
                from starlette.responses import JSONResponse
                return JSONResponse(
                    status_code=500,
                    content={"error": "Timing middleware error", "path": str(request.url.path)}
                )
            except Exception as response_error:
                logger.error(f"Failed to create error response: {response_error}")
                # Last resort - re-raise the original exception
                raise
