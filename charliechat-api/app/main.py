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
from .ai_middleware import normalize_person_name, query_bedrock


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


def _get_session_attributes(resp: dict) -> dict:
    """
    Extract session attributes from Lex response for context.
    
    This allows Bedrock to access previous conversation context stored in Lex session state.
    
    Args:
        resp: Lex response dictionary
        
    Returns:
        Session attributes dictionary (empty dict if not available)
    """
    session_state = resp.get("sessionState", {})
    if isinstance(session_state, dict):
        session_attributes = session_state.get("sessionAttributes", {})
        if isinstance(session_attributes, dict):
            return session_attributes
    return {}


def _update_session_attributes(resp: dict, updated_attributes: dict) -> None:
    """
    Update session attributes in Lex response with new context.
    
    This persists the updated session attributes back to the response so they can be
    stored in Lex session state for the next turn.
    
    Args:
        resp: Lex response dictionary (modified in-place)
        updated_attributes: New session attributes to store
    """
    # Get or create sessionState
    session_state = resp.get("sessionState", {})
    if not isinstance(session_state, dict):
        session_state = {}
    
    # Update sessionAttributes with the new context
    session_state["sessionAttributes"] = updated_attributes
    resp["sessionState"] = session_state


def _get_bedrock_response(resp: dict) -> str:
    """
    Extract slots from Lex response and get Bedrock AI response.
    
    This function is called when Lex doesn't provide a direct response,
    allowing Bedrock AI to handle complex queries that require context.
    
    Args:
        resp: Lex response dictionary
        
    Returns:
        AI response string or fallback message
    """
    # Extract slots from Lex response with defensive defaults
    interpretations = resp.get("interpretations", [])
    person_slot = None
    question_slot = None
    
    # Safely extract slots without raising KeyErrors
    if interpretations and len(interpretations) > 0:
        intent = interpretations[0].get("intent", {})
        slots = intent.get("slots", {})
        
        # Extract person slot safely
        person_data = slots.get("person", {})
        if isinstance(person_data, dict):
            person_value = person_data.get("value", {})
            if isinstance(person_value, dict):
                person_slot = person_value.get("originalValue")
        
        # Extract question slot safely
        question_data = slots.get("question", {})
        if isinstance(question_data, dict):
            question_value = question_data.get("value", {})
            if isinstance(question_value, dict):
                question_slot = question_value.get("originalValue")
    
    # Normalize person name and get AI response
    person = normalize_person_name(person_slot)
    
    if question_slot and question_slot.strip():
        # Use Bedrock AI for response when we have a valid question
        # Extract session attributes for context and get updated attributes
        session_attributes = _get_session_attributes(resp)
        ai_response, updated_attributes = query_bedrock(person, question_slot.strip(), session_attributes)
        
        # Save updated session attributes back to the response for persistence
        # This enables multi-turn memory by storing last Q&A for follow-up context
        _update_session_attributes(resp, updated_attributes)
        
        return ai_response
    else:
        # No question detected - clear stale memory to avoid confusing context carry-over
        # This prevents irrelevant previous Q&A from affecting future conversations
        _update_session_attributes(resp, {})
        
        # Fallback message if no question detected
        return "I did not catch a question. Please ask me about experience, skills, or leadership style."


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

    Flow:
    1. Call Lex to process user input and extract slots/intents
    2. If Lex provides direct response (e.g., "test" intent), use it (saves costs)
    3. If no Lex response, use Bedrock AI for complex queries
    4. Save Bedrock responses to sessionAttributes for follow-up context
    5. Persist session_state for context carry-over across turns
    6. Clear stale memory when no question detected to avoid confusing context carry-over
    
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

            # Call Lex to extract slots and check for intents
            # Pass session_state to maintain context across turns
            resp = client.recognize_text(
                session_id=effective_session_id,
                text=effective_text,
                session_state=session_state,  # Pass existing session state for context
            )
            
            # Check if Lex has a direct response (intent fulfillment)
            # This handles intents like "test" that have direct responses to save costs
            messages = resp.get("messages", [])
            if messages:
                # Extract bot text from Lex messages (for intents like "test")
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
                if raw_bot_text:
                    # Lex provided a direct response (intent fulfilled), use it
                    # This saves costs by avoiding Bedrock calls for simple intents
                    # raw_bot_text is already set correctly, no additional processing needed
                    pass
                else:
                    # Lex messages exist but are empty, try Bedrock AI
                    raw_bot_text = _get_bedrock_response(resp)
            else:
                # No Lex messages, try Bedrock AI
                raw_bot_text = _get_bedrock_response(resp)

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
            session_state=req.session_state,  # Pass existing session state for context
        )
        
        # Check if Lex has a direct response (intent fulfillment)
        # This handles intents like "test" that have direct responses to save costs
        messages = resp.get("messages", [])
        if messages:
            # Extract bot text from Lex messages (for intents like "test")
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
            if raw_bot_text:
                # Lex provided a direct response (intent fulfilled), use it
                # This saves costs by avoiding Bedrock calls for simple intents
                # Keep the original Lex message format - messages are already correct
                pass
            else:
                # Lex messages exist but are empty, try Bedrock AI
                ai_response = _get_bedrock_response(resp)
                # Create a message with the AI response
                ai_message = {
                    "content": [{"text": ai_response}]
                }
                messages = [ai_message]
        else:
            # No Lex messages, try Bedrock AI
            ai_response = _get_bedrock_response(resp)
            # Create a message with the AI response
            ai_message = {
                "content": [{"text": ai_response}]
            }
            messages = [ai_message]
        
        return ChatResponse(
            messages=messages,
            session_state=resp.get("sessionState"),  # Return updated session state for next turn
        )
    except Exception as exc:  # noqa: BLE001 - bubble exact message for now
        raise HTTPException(status_code=500, detail=str(exc))

