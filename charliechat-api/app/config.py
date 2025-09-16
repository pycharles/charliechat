import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()


class Settings(BaseModel):
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    lex_bot_id: str = os.getenv("LEX_BOT_ID", "")
    lex_bot_alias_id: str = os.getenv("LEX_BOT_ALIAS_ID", "")
    lex_bot_locale_id: str = os.getenv("LEX_BOT_LOCALE_ID", "en_US")
    bedrock_kb_id: Optional[str] = os.getenv("BEDROCK_KB_ID")

    aws_access_key_id: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_session_token: Optional[str] = os.getenv("AWS_SESSION_TOKEN")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


