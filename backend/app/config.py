import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # LLM Keys
    GEMINI_API_KEY: str
    GEMINI_API_KEY_1: Optional[str] = None
    GEMINI_API_KEY_2: Optional[str] = None
    GEMINI_API_KEY_3: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    GROQ_API_KEY_1: Optional[str] = None
    GROQ_API_KEY_2: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None

    def get_gemini_keys(self) -> list[str]:
        keys = []
        # Check standard defined attributes first
        for field in ["GEMINI_API_KEY", "GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"]:
            val = getattr(self, field, None)
            if val and val.strip():
                if val.strip() not in keys:
                    keys.append(val.strip())
        # Also dynamically scan environment for other GEMINI_API_KEY_x keys
        # We sort them by variable name to keep order consistent
        numbered_keys = []
        for k, v in os.environ.items():
            if k.startswith("GEMINI_API_KEY_") and v.strip():
                numbered_keys.append((k, v.strip()))
        numbered_keys.sort(key=lambda item: item[0])
        for _, val in numbered_keys:
            if val not in keys:
                keys.append(val)
        return keys

    def get_groq_keys(self) -> list[str]:
        keys = []
        for field in ["GROQ_API_KEY", "GROQ_API_KEY_1", "GROQ_API_KEY_2"]:
            val = getattr(self, field, None)
            if val and val.strip():
                if val.strip() not in keys:
                    keys.append(val.strip())
        numbered_keys = []
        for k, v in os.environ.items():
            if k.startswith("GROQ_API_KEY_") and v.strip():
                numbered_keys.append((k, v.strip()))
        numbered_keys.sort(key=lambda item: item[0])
        for _, val in numbered_keys:
            if val not in keys:
                keys.append(val)
        return keys

    # Neo4j Settings
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # API Settings
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    ENV: str = "development"
    
    # Render & Host Constraints (v4 features)
    DISABLE_LOCAL_MODELS: bool = False # set to True on 512MB RAM limits (like Render Free)
    DEMO_OFFLINE_MODE: bool = False     # set to True for offline judging fallback
    
    # Privacy & PII Masking Settings
    ENABLE_PII_MASKING: bool = True
    ENABLE_PII_LOGGING: bool = True
    ENABLED_RECOGNIZERS: str = "all"
    ENABLE_SPACY_NER: bool = False
    
    # Path settings
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    LOG_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")

    # Read from .env file if available
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure log directory exists
os.makedirs(settings.LOG_DIR, exist_ok=True)
