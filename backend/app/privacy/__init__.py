from typing import Tuple, List
from app.privacy.detector import PIIDetector
from app.privacy.masker import PIIMasker
from app.privacy.vault import PIIVault
from app.privacy.reinserter import PIIReinserter
from app.privacy.logger import PIILogger
from app.privacy.recognizers import PIIDetection

def mask_document(text: str) -> Tuple[str, List[PIIDetection], PIIVault]:
    """
    Convenience wrapper to run detector and masker on a document.
    """
    detector = PIIDetector()
    masker = PIIMasker()
    vault = PIIVault()
    
    detections = detector.detect(text)
    masked_text = masker.mask(text, detections, vault)
    
    # Safe log summary
    PIILogger.log_detections(detections)
    
    return masked_text, detections, vault

def reinsert_document(text: str, vault: PIIVault) -> str:
    """
    Convenience wrapper to restore original values using reinserter.
    """
    reinserter = PIIReinserter()
    return reinserter.reinsert(text, vault)

def get_pii_summary(detections: List[PIIDetection]) -> str:
    """
    Convenience wrapper to get a safe log summary of detected items.
    """
    return PIILogger.get_summary(detections)
