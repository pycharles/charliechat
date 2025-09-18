"""
AWS Lambda handler for Charlie Chat API

This module provides the Lambda handler for FastAPI requests.
It routes all requests through the FastAPI application.
"""

from mangum import Mangum
from app.main import app
from app.utils.debug_logger import debug_logger

# Create Mangum adapter for FastAPI
handler = Mangum(app, lifespan="off")