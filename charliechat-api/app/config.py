import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()


class Settings(BaseModel):
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    bedrock_kb_id: Optional[str] = os.getenv("BEDROCK_KB_ID")
    default_person: str = os.getenv("DEFAULT_PERSON", "Charles")
    debug: bool = os.getenv("DEBUG_LOGGING", "false").lower() == "true"

    aws_access_key_id: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_session_token: Optional[str] = os.getenv("AWS_SESSION_TOKEN")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


