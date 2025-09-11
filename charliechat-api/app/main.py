from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
from html import escape as html_escape

from .config import get_settings
from .lex_client import LexChatClient


app = FastAPI(title="Charlie Chat API", version="0.1.0")

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

