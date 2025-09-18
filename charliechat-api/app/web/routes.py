"""
Web routes for Charlie Chat

This module contains all FastAPI routes for the web interface.
"""

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os
import uuid
import traceback
from datetime import datetime
import markdown

from ..services import ChatService
from ..config import get_settings
from ..models.chat import ChatRequest, ChatResponse
from ..utils.debug_logger import debug_logger

# Initialize router
router = APIRouter()

# Templates setup
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Initialize services
settings = get_settings()
chat_service = ChatService(settings)


def load_journal_entries() -> list:
    """Load and parse journal entries from markdown files"""
    journal_dir = Path(__file__).parent.parent.parent / "journal-md"
    entries = []
    
    if not journal_dir.exists():
        return entries
    
    for md_file in sorted(journal_dir.glob("*.md"), reverse=True):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract title and date from filename
            # Handle date format: 2024-01-15-title -> Title (for blog) and 2024 (for nav)
            nav_title = None
            blog_title = None
            date_str = None
            nav_date = None
            
            if len(md_file.stem) >= 10 and md_file.stem[:4].isdigit():
                # Split date and title parts
                parts = md_file.stem.split('-', 3)  # Split into max 4 parts
                if len(parts) >= 4:
                    date_part = f"{parts[0]}-{parts[1]}-{parts[2]}"
                    title_part = parts[3].replace('-', ' ').title()
                    blog_title = title_part  # Just the title for blog
                    nav_title = title_part  # Just the title for nav
                    nav_date = date_part  # Full YYYY-MM-DD for nav
                    
                    # Full date for blog display
                    try:
                        date_obj = datetime.strptime(date_part, '%Y-%m-%d')
                        date_str = date_obj.strftime('%B %d, %Y')
                    except ValueError:
                        pass
                else:
                    blog_title = md_file.stem.replace('-', ' ').title()
                    nav_title = md_file.stem.replace('-', ' ').title()
            else:
                blog_title = md_file.stem.replace('-', ' ').title()
                nav_title = md_file.stem.replace('-', ' ').title()
            
            # Convert markdown to HTML
            html_content = markdown.markdown(content)
            
            entries.append({
                'title': blog_title,  # For blog display (no date)
                'nav_title': nav_title,  # For navigation display
                'date': date_str,  # Full date for blog display
                'nav_date': nav_date,  # Year only for navigation
                'content': html_content,
                'filename': md_file.name
            })
        except Exception as e:
            print(f"Error loading {md_file}: {e}")
            continue
    
    return entries


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    """Serve the main chat interface"""
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/favicon.ico")
def favicon():
    """Redirect favicon requests to the SVG icon"""
    return RedirectResponse(url="/static/favicon.svg")


@router.get("/blog", response_class=HTMLResponse)
def blog(request: Request) -> HTMLResponse:
    """Serve the dev journal page"""
    journal_entries = load_journal_entries()
    return templates.TemplateResponse("blog.html", {
        "request": request,
        "journal_entries": journal_entries
    })


@router.post("/chat")
async def chat(
    request: Request,
    session_id: str | None = Form(None),
    text: str | None = Form(None),
    session_state: str | None = Form(None),
    voice_style: str | None = Form("normal")
):
    """
    Handle chat requests (both HTMX and JSON)
    
    - If HX-Request header is present (HTMX), returns HTML fragment
    - Otherwise, returns JSON response
    """
    # Use request ID from middleware or generate one
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4())[:8])
    
    debug_logger.log_route(
        request_id,
        f"Received chat request - Session: {session_id}, Text: '{text[:50] if text else 'None'}{'...' if text and len(text) > 50 else ''}', Voice: {voice_style}",
        request
    )
    
    if not session_id or not text:
        debug_logger.log_route(
            request_id,
            f"Missing required parameters - session_id: {session_id}, text: {text}",
            request
        )
        raise HTTPException(status_code=400, detail="session_id and text are required")
    
    # Parse session state if provided
    parsed_session_state = None
    if session_state:
        try:
            import json
            parsed_session_state = json.loads(session_state)
            debug_logger.log_route(
                request_id,
                f"Received session state: {str(parsed_session_state)[:200]}{'...' if len(str(parsed_session_state)) > 200 else ''}",
                request
            )
        except json.JSONDecodeError as e:
            debug_logger.log_route(
                request_id,
                f"Failed to parse session state JSON: {e}. Raw: {session_state[:100]}...",
                request
            )
            parsed_session_state = None
    else:
        debug_logger.log_route(
            request_id,
            "No session state provided - starting new conversation",
            request
        )
    
    # Process chat through service layer
    debug_logger.log_route(
        request_id,
        f"Calling chat_service.process_chat for session {session_id}",
        request
    )
    response_text, updated_session_state = await chat_service.process_chat(
        request_id=request_id,
        session_id=session_id,
        text=text,
        session_state=parsed_session_state,
        voice_style=voice_style,
        request=request
    )
    debug_logger.log_route(
        request_id,
        f"Chat service completed for session {session_id}",
        request
    )
    
    # Check if this is an HTMX request
    if request.headers.get("HX-Request"):
        debug_logger.log_route(
            request_id,
            "Processing HTMX response",
            request
        )
        
        # Debug: Log the actual response text being sent to frontend
        debug_logger.log_route(
            request_id,
            f"=== SENDING TO BROWSER ===",
            request
        )
        debug_logger.log_route(
            request_id,
            f"Browser response length: {len(response_text)} characters",
            request
        )
        debug_logger.log_route(
            request_id,
            f"Browser response content: {response_text}",
            request
        )
        
        # Verify response matches what was stored in last_answer
        if updated_session_state and "last_answer" in updated_session_state:
            last_answer = updated_session_state["last_answer"]
            if response_text == last_answer:
                debug_logger.log_route(
                    request_id,
                    f"✅ VERIFICATION: Browser response matches last_answer exactly",
                    request
                )
            else:
                debug_logger.log_route(
                    request_id,
                    f"❌ VERIFICATION FAILED: Browser response differs from last_answer",
                    request
                )
                debug_logger.log_route(
                    request_id,
                    f"last_answer length: {len(last_answer)}, Browser length: {len(response_text)}",
                    request
                )
        else:
            debug_logger.log_route(
                request_id,
                f"⚠️ No last_answer found in session state for verification",
                request
            )
            
        debug_logger.log_route(
            request_id,
            f"=== END BROWSER RESPONSE ===",
            request
        )
        
        # Process Markdown in bot responses for formatting
        import markdown
        html_content = markdown.markdown(response_text, extensions=['nl2br'])
        
        # Debug: Log the HTML content after markdown processing
        debug_logger.log_route(
            request_id,
            f"HTML content after markdown: {html_content[:200]}{'...' if len(html_content) > 200 else ''}",
            request
        )
        
        # Return only bot message for HTMX (user message is added by JavaScript)
        # Include session state as a data attribute for JavaScript to read
        import json
        session_state_json = json.dumps(updated_session_state) if updated_session_state else "{}"
        
        # Log session state for debugging
        debug_logger.log_route(
            request_id,
            f"Returning session state: {session_state_json[:200]}{'...' if len(session_state_json) > 200 else ''}",
            request
        )
        
        # Properly escape the JSON for HTML attribute
        import html
        escaped_session_state = html.escape(session_state_json, quote=True)
        
        return HTMLResponse(f"""
        <div class="message message-bot" data-session-state="{escaped_session_state}">
            <div class="bubble">{html_content}</div>
        </div>
        """)
    else:
        debug_logger.log_route(
            request_id,
            "Processing JSON response",
            request
        )
        # Return JSON response for API
        return ChatResponse(
            messages=[{"contentType": "PlainText", "content": response_text}],
            session_state=updated_session_state
        )
