from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import get_settings
from .lex_client import LexChatClient


app = FastAPI(title="Charlie Chat API", version="0.1.0")


class ChatRequest(BaseModel):
    session_id: str
    text: str
    session_state: dict | None = None


class ChatResponse(BaseModel):
    messages: list
    session_state: dict | None = None


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    settings = get_settings()
    client = LexChatClient(settings)
    try:
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



