import threading
import hashlib
from typing import Dict, Optional

class TranslationCache:
    def __init__(self):
        self._cache: Dict[str, str] = {}
        self._lock = threading.Lock()

    def _make_key(self, text: str, target_lang: str) -> str:
        # Standard hash key generation to save memory and handle long blocks
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{target_lang}:{h}"

    def get(self, text: str, target_lang: str) -> Optional[str]:
        """
        Retrieves a translated segment if cached.
        """
        key = self._make_key(text, target_lang)
        with self._lock:
            return self._cache.get(key)

    def set(self, text: str, target_lang: str, translated_text: str):
        """
        Caches a translated segment.
        """
        key = self._make_key(text, target_lang)
        with self._lock:
            self._cache[key] = translated_text

    def clear(self):
        """
        Clears translation cache.
        """
        with self._lock:
            self._cache.clear()

# Singleton instance for the application
translation_cache = TranslationCache()
