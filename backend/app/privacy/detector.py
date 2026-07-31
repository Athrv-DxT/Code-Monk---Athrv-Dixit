from typing import List, Set
from app.privacy.recognizers import BaseRecognizer, PIIDetection, get_all_recognizers
from app.config import settings

class PIIDetector:
    def __init__(self):
        self.recognizers: List[BaseRecognizer] = []
        self._load_recognizers()

    def _load_recognizers(self):
        """
        Loads and filters recognizers based on configuration.
        """
        all_recs = get_all_recognizers()
        enabled_setting = settings.ENABLED_RECOGNIZERS.lower().strip()
        
        if enabled_setting == "all":
            self.recognizers = all_recs
        else:
            # Comma separated list of active recognizers
            enabled_names = {name.strip().lower() for name in enabled_setting.split(",")}
            self.recognizers = [r for r in all_recs if r.name.lower() in enabled_names or r.entity_type.lower() in enabled_names]

    def detect(self, text: str) -> List[PIIDetection]:
        """
        Scans document text, resolves overlapping detections, and returns clean detections list.
        """
        if not text:
            return []

        all_detections: List[PIIDetection] = []
        for recognizer in self.recognizers:
            try:
                detections = recognizer.analyze(text)
                all_detections.extend(detections)
            except Exception as e:
                # Log error but don't crash the pipeline
                import logging
                logger = logging.getLogger("intellix.privacy.detector")
                logger.error(f"Error running recognizer {recognizer.name}: {e}")

        # Resolve overlaps: sort by match span length (descending) then score (descending)
        sorted_detections = sorted(
            all_detections,
            key=lambda d: (d.end - d.start, d.score),
            reverse=True
        )

        accepted_detections: List[PIIDetection] = []
        matched_indices: Set[int] = set()

        for det in sorted_detections:
            # Check overlap
            span_range = set(range(det.start, det.end))
            if not span_range.intersection(matched_indices):
                accepted_detections.append(det)
                matched_indices.update(span_range)

        # Re-sort accepted detections by start index for sequential masking
        return sorted(accepted_detections, key=lambda d: d.start)
