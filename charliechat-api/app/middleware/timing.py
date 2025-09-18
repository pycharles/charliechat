"""
Request timing middleware

Captures high-resolution start time for each request and logs total request time.
"""

import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from ..utils.debug_logger import debug_logger


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to capture request timing and log total request duration"""
    
    async def dispatch(self, request: Request, call_next):
        # Capture high-resolution start time
        request.state.start_time = time.perf_counter()
        
        # Generate request ID if not present
        if not hasattr(request.state, 'request_id'):
            import uuid
            request.state.request_id = str(uuid.uuid4())[:8]
        
        # Log request start
        debug_logger.log_route(
            request.state.request_id,
            f"Request started: {request.method} {request.url.path}",
            request
        )
        
        # Process the request
        response = await call_next(request)
        
        # Calculate total request time
        total_time = time.perf_counter() - request.state.start_time
        total_time_ms = total_time * 1000
        
        # Log total request time
        debug_logger.log_route(
            request.state.request_id,
            f"Request completed: {response.status_code} in {total_time_ms:.3f}ms",
            request
        )
        
        return response
