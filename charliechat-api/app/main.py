from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
from html import escape as html_escape
import markdown # type: ignore - linter issue
import os
from datetime import datetime

from .config import get_settings
from .lex_client import LexChatClient


app = FastAPI(title="Charlie Chat API", version="0.1.0")

# Middleware to redirect www.charlesob.com to charlesob.com for SEO normalization
@app.middleware("http")
async def redirect_to_root(request: Request, call_next):
    host = request.headers.get("host", "")
    if host == "www.charlesob.com":
        # Redirect to root domain with 301 (permanent redirect)
        url = str(request.url).replace("www.charlesob.com", "charlesob.com")
        return RedirectResponse(url=url, status_code=301)
    return await call_next(request)

# Static files and templates setup
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


class ChatRequest(BaseModel):
    session_id: str
    text: str
    session_state: dict | None = None


class ChatResponse(BaseModel):
    messages: list
    session_state: dict | None = None


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


def load_journal_entries():
    """Load and parse journal markdown files"""
    journal_dir = BASE_DIR.parent / "journal-md"
    entries = []
    
    if not journal_dir.exists():
        return entries
    
    # Get all markdown files and sort by filename (which includes date)
    md_files = sorted([f for f in journal_dir.glob("*.md")], reverse=True)
    
    for md_file in md_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract title from first line (assumes # Title format)
            lines = content.split('\n')
            title = lines[0].lstrip('# ').strip() if lines[0].startswith('#') else md_file.stem
            
            # Extract date from filename (assumes YYYY-MM-DD format)
            date_str = md_file.stem.split('-', 3)[:3]  # Get first 3 parts
            if len(date_str) >= 3:
                try:
                    date_obj = datetime.strptime('-'.join(date_str), '%Y-%m-%d')
                    formatted_date = date_obj.strftime('%B %d, %Y')
                except ValueError:
                    formatted_date = md_file.stem
            else:
                formatted_date = md_file.stem
            
            # Convert markdown to HTML
            html_content = markdown.markdown(content, extensions=['fenced_code', 'tables'])
            
            entries.append({
                'title': title,
                'date': formatted_date,
                'content': html_content,
                'filename': md_file.name
            })
        except Exception as e:
            print(f"Error loading {md_file}: {e}")
            continue
    
    return entries


@app.get("/blog", response_class=HTMLResponse)
def blog(request: Request) -> HTMLResponse:
    journal_entries = load_journal_entries()
    return templates.TemplateResponse("blog.html", {
        "request": request,
        "journal_entries": journal_entries
    })


@app.get("/favicon.ico", include_in_schema=False)
def favicon_redirect():
    return RedirectResponse(url="/static/favicon.svg")


@app.post("/chat")
async def chat(request: Request, session_id: str | None = Form(None), text: str | None = Form(None), session_state: str | None = Form(None)):
    """Single endpoint supports both JSON API and HTMX form posts.

    - If HX-Request header is present (HTMX), returns HTML fragment with user and bot bubbles.
    - Otherwise, returns JSON matching ChatResponse.
    """
    settings = get_settings()
    client = LexChatClient(settings)

    try:
        is_htmx = request.headers.get("hx-request", "false").lower() == "true" or session_id is not None

        if is_htmx:
            # Handle HTMX form post
            effective_session_id = session_id or "default"
            effective_text = text or ""

            resp = client.recognize_text(
                session_id=effective_session_id,
                text=effective_text,
                session_state=None,
            )
            messages = resp.get("messages", [])

            # Extract a simple bot text from messages (robust across common shapes)
            bot_texts: list[str] = []
            for msg in messages:
                if isinstance(msg, dict):
                    # Lex V2 rich content list
                    content_val = msg.get("content")
                    if isinstance(content_val, list):
                        for c in content_val:
                            if isinstance(c, dict):
                                content_str = c.get("content") or c.get("text")
                                if content_str:
                                    bot_texts.append(str(content_str))
                    # Simple dict with text
                    elif isinstance(content_val, (str, int, float)):
                        bot_texts.append(str(content_val))
                    elif "text" in msg and msg["text"]:
                        bot_texts.append(str(msg["text"]))
                elif isinstance(msg, (str, int, float)):
                    bot_texts.append(str(msg))

            raw_bot_text = "\n".join(bot_texts).strip()
            if not raw_bot_text:
                raw_bot_text = "..."  # Fallback so the UI shows something

            # Escape to prevent HTML injection
            user_safe = html_escape(effective_text)
            bot_safe = html_escape(raw_bot_text)

            # Return ONLY bot bubble to replace pending placeholder (targeted by hx-target)
            html = f'<div class="message message-bot fade-in"><div class="bubble">{bot_safe}</div></div>'
            return HTMLResponse(content=html)

        # Handle JSON API
        payload = await request.json()
        req = ChatRequest(**payload)
        resp = client.recognize_text(
            session_id=req.session_id,
            text=req.text,
            session_state=req.session_state,
        )
        return ChatResponse(
            messages=resp.get("messages", []),
            session_state=resp.get("sessionState"),
        )
    except Exception as exc:  # noqa: BLE001 - bubble exact message for now
        raise HTTPException(status_code=500, detail=str(exc))

