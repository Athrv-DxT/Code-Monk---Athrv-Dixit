import logging
from typing import List
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("meridian.embeddings")

_model = None

from app.config import settings
import hashlib

def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        try:
            logger.info("Initializing BGE-small-en-v1.5 embedding model...")
            # Loads from Hugging Face cache (pre-downloaded during docker build)
            _model = SentenceTransformer('BAAI/bge-small-en-v1.5')
            logger.info("BGE model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise e
    return _model

def get_mock_vector(text: str) -> List[float]:
    # Return a deterministic mock 384-dimensional normalized vector to save 400MB RAM in production
    h = hashlib.sha256(text.encode('utf-8')).digest()
    floats = []
    for i in range(384):
        byte_idx = (i * 7) % len(h)
        val = (h[byte_idx] / 255.0) - 0.5
        floats.append(val)
    norm = sum(x*x for x in floats) ** 0.5 or 1.0
    return [x/norm for x in floats]

def get_embedding(text: str) -> List[float]:
    """
    Computes dense embedding vector for given text.
    """
    if settings.DISABLE_LOCAL_MODELS:
        return get_mock_vector(text)
        
    model = get_model()
    # Normalize to enable simple dot product similarity check
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()

def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Computes dense embedding vectors for a list of texts.
    """
    if settings.DISABLE_LOCAL_MODELS:
        return [get_mock_vector(t) for t in texts]
        
    model = get_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return vectors.tolist()
