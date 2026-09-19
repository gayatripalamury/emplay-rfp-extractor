"""Environment-driven configuration. API keys are never logged or serialized."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    provider: str = os.getenv("LLM_PROVIDER", "none").lower()
    model: str = os.getenv("LLM_MODEL") or os.getenv("MODEL", "")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    max_chars: int = int(os.getenv("MAX_DOCUMENT_CHARS", "100000"))


settings = Settings()