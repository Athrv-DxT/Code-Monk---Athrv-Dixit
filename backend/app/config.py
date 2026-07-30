import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # LLM Keys
    GEMINI_API_KEY: str
    GROQ_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None

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
