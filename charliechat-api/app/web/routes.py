"""
Web routes for Charlie Chat

This module contains all FastAPI routes for the web interface.
"""

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os
from datetime import datetime
import markdown

from ..services import ChatService
from ..config import get_settings
from ..models.chat import ChatRequest, ChatResponse

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
            
            # Extract title from filename (remove .md and replace - with spaces)
            title = md_file.stem.replace('-', ' ').title()
            
            # Extract date from filename if it starts with YYYY-MM-DD
            date_str = None
            if len(md_file.stem) >= 10 and md_file.stem[:4].isdigit():
                try:
                    date_str = md_file.stem[:10]
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    date_str = date_obj.strftime('%B %d, %Y')
                except ValueError:
                    pass
            
            # Convert markdown to HTML
            html_content = markdown.markdown(content)
            
            entries.append({
                'title': title,
                'date': date_str,
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
    if not session_id or not text:
        raise HTTPException(status_code=400, detail="session_id and text are required")
    
    # Parse session state if provided
    parsed_session_state = None
    if session_state:
        try:
            import json
            parsed_session_state = json.loads(session_state)
        except json.JSONDecodeError:
            parsed_session_state = None
    
    # Process chat through service layer
    response_text, updated_session_state = chat_service.process_chat(
        session_id=session_id,
        text=text,
        session_state=parsed_session_state,
        voice_style=voice_style
    )
    
    # Check if this is an HTMX request
    if request.headers.get("HX-Request"):
        # Process Markdown in bot responses for formatting
        import markdown
        html_content = markdown.markdown(response_text, extensions=['nl2br'])
        
        # Return only bot message for HTMX (user message is added by JavaScript)
        return HTMLResponse(f"""
        <div class="message message-bot">
            <div class="bubble">{html_content}</div>
        </div>
        """)
    else:
        # Return JSON response for API
        return ChatResponse(
            messages=[{"contentType": "PlainText", "content": response_text}],
            session_state=updated_session_state
        )
