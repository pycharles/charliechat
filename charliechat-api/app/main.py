"""
Charlie Chat FastAPI Application

This is the main FastAPI application entry point.
It sets up the app, middleware, and includes all routes.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import json

from .web.routes import router as web_router

# Create FastAPI app
app = FastAPI(
    title="Charlie Chat API",
    version="0.1.0",
    description="AI-powered chat application with Lex V2 and Bedrock integration"
)

# Middleware to redirect www.charlesob.com to charlesob.com for SEO normalization
@app.middleware("http")
async def redirect_to_root(request: Request, call_next):
    """Redirect www subdomain to root domain for SEO"""
    host = request.headers.get("host", "")
    if host == "www.charlesob.com":
        # Redirect to root domain with 301 (permanent redirect)
        url = str(request.url).replace("www.charlesob.com", "charlesob.com")
        return RedirectResponse(url=url, status_code=301)
    return await call_next(request)

# Static files setup
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "web" / "static"), name="static")

# Include web routes
app.include_router(web_router)

# Simple rate limiting storage (in production, use Redis or similar)
feedback_submissions = defaultdict(list)

def check_rate_limit(ip_address: str) -> bool:
    """Check if IP has exceeded rate limit (3 submissions per 10 minutes)"""
    now = datetime.now()
    ten_minutes_ago = now - timedelta(minutes=10)
    
    # Clean old submissions
    feedback_submissions[ip_address] = [
        timestamp for timestamp in feedback_submissions[ip_address]
        if timestamp > ten_minutes_ago
    ]
    
    # Check if under limit
    return len(feedback_submissions[ip_address]) < 3

@app.post("/feedback")
async def submit_feedback(request: Request):
    """Submit user feedback with rate limiting"""
    # Get client IP
    client_ip = request.client.host
    
    # Check rate limit
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429, 
            detail="Rate limit exceeded. Maximum 3 feedback submissions per 10 minutes."
        )
    
    # Parse request body
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Validate required fields
    text = body.get("text", "").strip()
    sentiment = body.get("sentiment", "")
    session_id = body.get("session_id", "")
    
    if not text or not sentiment:
        raise HTTPException(status_code=400, detail="Text and sentiment are required")
    
    if sentiment not in ["positive", "neutral", "negative"]:
        raise HTTPException(status_code=400, detail="Invalid sentiment value")
    
    if len(text) > 300:
        raise HTTPException(status_code=400, detail="Text exceeds 300 character limit")
    
    # Record submission for rate limiting
    feedback_submissions[client_ip].append(datetime.now())
    
    # Prepare feedback data
    feedback_data = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "sentiment": sentiment,
        "text": text,
        "ip_address": client_ip
    }
    
    # Log feedback (in production, send to CloudWatch, DynamoDB, or S3)
    print(f"Feedback received: {json.dumps(feedback_data)}")
    
    # TODO: Store in DynamoDB or S3 in production
    # For now, just log to console
    
    return {"message": "Feedback submitted successfully", "status": "success"}

# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "service": "charlie-chat-api"}
