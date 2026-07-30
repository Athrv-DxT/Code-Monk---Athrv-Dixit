import re
from typing import List, Dict, Any, Tuple
from app.privacy.validators import verify_verhoeff, verify_luhn, verify_pan_syntax

class PIIDetection:
    def __init__(self, entity_type: str, start: int, end: int, value: str, score: float = 1.0):
        self.entity_type = entity_type
        self.start = start
        self.end = end
        self.value = value
        self.score = score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "start": self.start,
            "end": self.end,
            "value": self.value,
            "score": self.score
        }

class BaseRecognizer:
    def __init__(self, name: str, entity_type: str):
        self.name = name
        self.entity_type = entity_type

    def analyze(self, text: str) -> List[PIIDetection]:
        raise NotImplementedError("Subclasses must implement analyze method.")

class RegexRecognizer(BaseRecognizer):
    def __init__(self, name: str, entity_type: str, pattern: str, score: float = 0.85):
        super().__init__(name, entity_type)
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.score = score

    def analyze(self, text: str) -> List[PIIDetection]:
        detections = []
        for match in self.pattern.finditer(text):
            val = match.group()
            detections.append(
                PIIDetection(
                    entity_type=self.entity_type,
                    start=match.start(),
                    end=match.end(),
                    value=val,
                    score=self.score
                )
            )
        return detections

class AadhaarRecognizer(BaseRecognizer):
    def __init__(self):
        super().__init__("AadhaarRecognizer", "AADHAAR")
        # Match standard 12 digit Aadhaar formats (with or without spaces/hyphens)
        self.pattern = re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b")

    def analyze(self, text: str) -> List[PIIDetection]:
        detections = []
        for match in self.pattern.finditer(text):
            val = match.group()
            # Verify checksum using Verhoeff
            if verify_verhoeff(val):
                detections.append(
                    PIIDetection(self.entity_type, match.start(), match.end(), val, 1.0)
                )
        return detections

class PANRecognizer(BaseRecognizer):
    def __init__(self):
        super().__init__("PANRecognizer", "PAN")
        self.pattern = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)

    def analyze(self, text: str) -> List[PIIDetection]:
        detections = []
        for match in self.pattern.finditer(text):
            val = match.group().upper()
            if verify_pan_syntax(val):
                detections.append(
                    PIIDetection(self.entity_type, match.start(), match.end(), val, 1.0)
                )
        return detections

class CreditCardRecognizer(BaseRecognizer):
    def __init__(self):
        super().__init__("CreditCardRecognizer", "CREDIT_CARD")
        self.pattern = re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4,7}\b")

    def analyze(self, text: str) -> List[PIIDetection]:
        detections = []
        for match in self.pattern.finditer(text):
            val = match.group()
            # Luhn validation to avoid matching random phone numbers or series
            if verify_luhn(val):
                detections.append(
                    PIIDetection(self.entity_type, match.start(), match.end(), val, 1.0)
                )
        return detections

class PropertyLegalRecognizer(BaseRecognizer):
    def __init__(self):
        super().__init__("PropertyLegalRecognizer", "PROPERTY_ID")
        # Match legal numbers (Registry No, Survey No, Plot No, Khata No, Encumbrance, Court Case, FIR)
        self.patterns = [
            (re.compile(r"\b(?:Survey|Plot|Khata|Mutation|Encumbrance|Dag|Patta|Khasra|Sheet)\s*(?:No\.?)?\s*([a-zA-Z0-9_\-/]+)\b", re.IGNORECASE), "PROPERTY_ID"),
            (re.compile(r"\b(?:Registry|Sale\s+Deed|Lease\s+Deed)\s*(?:No\.?)?\s*([a-zA-Z0-9_\-/]+)\b", re.IGNORECASE), "LEGAL_DOCUMENT_ID"),
            (re.compile(r"\b(?:Court\s+Case|Case|Suit|Petition|WP|PIL|FIR)\s*(?:No\.?)?\s*([a-zA-Z0-9_\-/]+)(?:\s*(?:of|/)\s*\d{4})?\b", re.IGNORECASE), "CASE_NUMBER")
        ]

    def analyze(self, text: str) -> List[PIIDetection]:
        detections = []
        for pattern, entity_type in self.patterns:
            for match in pattern.finditer(text):
                # We want to redact the whole identifier sequence
                detections.append(
                    PIIDetection(entity_type, match.start(), match.end(), match.group(), 0.9)
                )
        return detections

class PersonalNameRecognizer(BaseRecognizer):
    def __init__(self):
        super().__init__("PersonalNameRecognizer", "PERSON")
        # Heuristic title prefix recognizer
        self.title_pattern = re.compile(
            r"\b(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.|Shri|Smt\.|Sh\.|\bShree\b|\bLate\b)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b"
        )
        # Match capitalized word sequences that are likely names (e.g. "Rahul Sharma")
        self.generic_name = re.compile(
            r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b"
        )
        self.common_stop_words = {
            "The", "And", "For", "With", "From", "This", "That", "When", "Then", "Which", "Where",
            "Under", "Section", "Act", "Court", "State", "City", "District", "India", "August", "July",
            "safety", "Lease", "Safety", "Annual", "Tenant", "Safety", "Smoke", "Sprinkler", "August",
            "Municipal", "Ordinance", "Safety", "August", "Failure", "Surgical", "Laparoscopic", "Procedure",
            "Appendectomy", "Pharmacological", "Ibuprofen", "Oxycodone", "Acetaminophen", "Clinic", "Directive",
            "Patient", "Procedure", "Doctor", "Intervention"
        }

    def analyze(self, text: str) -> List[PIIDetection]:
        detections = []
        spans_matched = set()

        # 1. Match title prefixes first (high confidence)
        for match in self.title_pattern.finditer(text):
            full_span = match.group()
            name_part = match.group(1)
            # Skip if name part is standard document keyword
            if any(w in self.common_stop_words for w in name_part.split()):
                continue
            
            detections.append(
                PIIDetection(self.entity_type, match.start(), match.end(), full_span, 0.95)
            )
            # Record character indices to prevent double match
            for idx in range(match.start(), match.end()):
                spans_matched.add(idx)

        # 2. Generic Name matching (check against stop words)
        for match in self.generic_name.finditer(text):
            val = match.group()
            # Skip if overlapping with title names
            if match.start() in spans_matched or match.end() - 1 in spans_matched:
                continue
            # Skip if any word is in common English title case stop words
            words = val.split()
            if any(w in self.common_stop_words for w in words):
                continue
            # Double check all letters are normal letters
            if not all(w.isalpha() for w in words):
                continue

            detections.append(
                PIIDetection(self.entity_type, match.start(), match.end(), val, 0.8)
            )
            for idx in range(match.start(), match.end()):
                spans_matched.add(idx)

        return detections

class AddressRecognizer(BaseRecognizer):
    def __init__(self):
        super().__init__("AddressRecognizer", "ADDRESS")
        # Match common address phrases (e.g. flat, house, plot, street, road, nagar, layout, city, pin code)
        self.address_indicators = re.compile(
            r"\b(?:Flat|Plot|House|Survey|Khata|Shop|Nagar|Nagar|Colony|Enclave|Vihar|Apartments?|Road|Street|Lane|Building|Phase|Sector|Nagar|City|District|State|Ward)\s*(?:No\.?)?\s*[A-Z0-9_\-/]+(?:\s*,?\s*[A-Za-z0-9\s,\-\.\/]{5,150})?\s*(?:PIN\s*(?:Code)?)?\s*\d{6}\b",
            re.IGNORECASE
        )

    def analyze(self, text: str) -> List[PIIDetection]:
        detections = []
        for match in self.address_indicators.finditer(text):
            val = match.group()
            detections.append(
                PIIDetection(self.entity_type, match.start(), match.end(), val, 0.85)
            )
        return detections

def get_all_recognizers() -> List[BaseRecognizer]:
    """
    Returns the complete list of built-in pattern recognizers.
    """
    return [
        AadhaarRecognizer(),
        PANRecognizer(),
        CreditCardRecognizer(),
        PropertyLegalRecognizer(),
        PersonalNameRecognizer(),
        AddressRecognizer(),
        # Standard format IDs
        RegexRecognizer("EmailRecognizer", "EMAIL", r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"),
        RegexRecognizer("PhoneRecognizer", "PHONE", r"\b(?:\+91|0)?[6-9]\d{9}\b|\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
        RegexRecognizer("PINCodeRecognizer", "PIN_CODE", r"\b[1-9][0-9]{5}\b"),
        RegexRecognizer("PassportRecognizer", "PASSPORT", r"\b[A-Z]{1}[0-9]{7}\b"),
        RegexRecognizer("DrivingLicenceRecognizer", "DRIVING_LICENCE", r"\b[A-Z]{2}[- ]?[0-9]{2}[- ]?[0-9]{11}\b"),
        RegexRecognizer("VoterIDRecognizer", "VOTER_ID", r"\b[A-Z]{3}[0-9]{7}\b"),
        RegexRecognizer("GSTINRecognizer", "GSTIN", r"\b\d{2}[A-Z]{5}\d{4}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}\b"),
        RegexRecognizer("CINRecognizer", "CIN", r"\b[UoL]{1}\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b"),
        RegexRecognizer("IFSCRecognizer", "IFSC", r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
        RegexRecognizer("UPIIDRecognizer", "UPI_ID", r"\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b"),
        RegexRecognizer("PatientIDRecognizer", "PATIENT_ID", r"\b(?:Patient|MRN|MR|Claim)\s*(?:ID|No\.?|Number)?\s*(?:[:-]\s*)?([a-zA-Z0-9\-]{5,20})\b", 0.9)
    ]
