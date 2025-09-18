"""
Debug logging utility with timing support

Provides centralized debug logging with request timing and consistent formatting.
"""

import time
import os
from typing import Optional, Any
from fastapi import Request


class DebugLogger:
    """Centralized debug logging with timing support"""
    
    def __init__(self):
        # Check if we're running in Lambda (production) or locally (development)
        is_lambda = os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None
        
        if is_lambda:
            # Production: use DEBUG_LOGGING_PROD
            self.debug_enabled = os.getenv("DEBUG_LOGGING_PROD", "false").lower() == "true"
        else:
            # Development: use DEBUG_LOGGING_DEV
            self.debug_enabled = os.getenv("DEBUG_LOGGING_DEV", "false").lower() == "true"
    
    def log(self, 
            request_id: str, 
            service: str, 
            message: str, 
            request: Optional[Request] = None,
            **kwargs) -> None:
        """
        Log a debug message with optional timing information
        
        Args:
            request_id: Unique request identifier
            service: Service/component name (e.g., 'ROUTE', 'CHAT', 'AI')
            message: Debug message
            request: FastAPI request object for timing
            **kwargs: Additional context to include in log
        """
        if not self.debug_enabled:
            return
        
        # Calculate elapsed time if request is provided
        elapsed_seconds = None
        if request and hasattr(request.state, 'start_time'):
            elapsed_seconds = time.perf_counter() - request.state.start_time
            elapsed_seconds = f"{elapsed_seconds:.3f}s"
        
        # Build the log message
        timing_part = f" [{elapsed_seconds}]" if elapsed_seconds else ""
        context_part = f" [{request_id}]" if request_id else ""
        
        # Add any additional context
        context_str = ""
        if kwargs:
            context_items = [f"{k}={v}" for k, v in kwargs.items()]
            context_str = f" {' '.join(context_items)}"
        
        # Format: [DEBUG] [service] [timing] [request_id] message [context]
        log_message = f"[DEBUG] [{service}]{timing_part}{context_part} {message}{context_str}"
        
        print(log_message)
    
    def log_route(self, request_id: str, message: str, request: Optional[Request] = None, **kwargs):
        """Log a route-related debug message"""
        self.log(request_id, "ROUTE", message, request, **kwargs)
    
    def log_chat(self, request_id: str, message: str, request: Optional[Request] = None, **kwargs):
        """Log a chat service debug message"""
        self.log(request_id, "CHAT", message, request, **kwargs)
    
    def log_ai(self, request_id: str, message: str, request: Optional[Request] = None, **kwargs):
        """Log an AI service debug message"""
        self.log(request_id, "AI", message, request, **kwargs)
    
    def log_lex(self, request_id: str, message: str, request: Optional[Request] = None, **kwargs):
        """Log a Lex service debug message (for compatibility)"""
        self.log(request_id, "LEX", message, request, **kwargs)
    
    def log_lambda(self, request_id: str, message: str, request: Optional[Request] = None, **kwargs):
        """Log a Lambda debug message"""
        self.log(request_id, "LAMBDA", message, request, **kwargs)
    
    def log_timing(self, request_id: str, operation: str, duration_ms: float, **kwargs):
        """Log a specific timing measurement"""
        self.log(request_id, "TIMING", f"{operation} completed in {duration_ms:.3f}ms", **kwargs)


# Global debug logger instance
debug_logger = DebugLogger()
