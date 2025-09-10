from __future__ import annotations

import boto3

from .config import Settings


class LexChatClient:
    def __init__(self, settings: Settings) -> None:
        session = boto3.Session(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            aws_session_token=settings.aws_session_token,
            region_name=settings.aws_region,
        )
        self.client = session.client("lexv2-runtime", region_name=settings.aws_region)
        self.bot_id = settings.lex_bot_id
        self.bot_alias_id = settings.lex_bot_alias_id
        self.locale_id = settings.lex_bot_locale_id

    def recognize_text(self, session_id: str, text: str, session_state: dict | None = None) -> dict:
        kwargs: dict = {
            "botId": self.bot_id,
            "botAliasId": self.bot_alias_id,
            "localeId": self.locale_id,
            "sessionId": session_id,
            "text": text,
        }
        if session_state:
            kwargs["sessionState"] = session_state
        response = self.client.recognize_text(**kwargs)
        # Return only the relevant bits to the API layer
        return {
            "messages": response.get("messages", []),
            "sessionState": response.get("sessionState"),
            "interpretations": response.get("interpretations", []),
        }



