from typing import List, Dict
from app.privacy.recognizers import PIIDetection
from app.config import settings
import logging

logger = logging.getLogger("intellix.privacy")

class PIILogger:
    @staticmethod
    def get_summary(detections: List[PIIDetection]) -> str:
        """
        Creates a safe, clean summary count of detected PII without exposing values.
        """
        if not detections:
            return "No sensitive data detected."

        counts: Dict[str, int] = {}
        for det in detections:
            # Human readable names
            friendly_name = det.entity_type.replace("_", " ").title()
            counts[friendly_name] = counts.get(friendly_name, 0) + 1

        summary_parts = [f"{count} {label}{'s' if count > 1 else ''}" for label, count in counts.items()]
        return "PII Summary: " + ", ".join(summary_parts)

    @staticmethod
    def log_detections(detections: List[PIIDetection]):
        """
        Logs PII summary to standard logger if PII logging is enabled.
        """
        if not settings.ENABLE_PII_LOGGING:
            return
            
        summary = PIILogger.get_summary(detections)
        logger.info(summary)
