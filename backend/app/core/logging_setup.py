import logging
import sys
import os
from app.config import settings

def setup_logging():
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Ensure logs folder exists if possible
    try:
        os.makedirs(settings.LOG_DIR, exist_ok=True)
    except Exception:
        pass
        
    handlers = [logging.StreamHandler(sys.stdout)]
    
    # Only add FileHandler in non-production environments to avoid disk write crashes
    if settings.ENV != "production":
        try:
            handlers.append(logging.FileHandler(os.path.join(settings.LOG_DIR, "app.log"), encoding="utf-8"))
        except Exception:
            pass # fallback to stdout only

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=handlers
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("neo4j").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    
    logger = logging.getLogger("meridian")
    logger.info("Logging configured successfully.")
    return logger

logger = setup_logging()
