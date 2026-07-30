from typing import List
from app.privacy.recognizers import PIIDetection
from app.privacy.vault import PIIVault

class PIIMasker:
    def mask(self, text: str, detections: List[PIIDetection], vault: PIIVault) -> str:
        """
        Replaces sensitive character spans with request-scoped tokens from the vault.
        """
        if not text or not detections:
            return text

        parts = []
        last_idx = 0

        for det in detections:
            # Add text since last match
            parts.append(text[last_idx:det.start])
            # Store original value in vault and get masked token
            token = vault.store(det.entity_type, det.value)
            parts.append(token)
            last_idx = det.end

        # Add remaining text
        parts.append(text[last_idx:])
        
        return "".join(parts)
