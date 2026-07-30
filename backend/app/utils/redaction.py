import re

# Regex patterns for common PII
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
PHONE_REGEX = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
SSN_REGEX = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
CREDIT_CARD_REGEX = re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b')

def redact_pii(text: str) -> str:
    """
    Redacts standard PII from text before external calls to preserve privacy.
    """
    if not text:
        return text
    
    redacted = text
    redacted = EMAIL_REGEX.sub("[REDACTED_EMAIL]", redacted)
    redacted = PHONE_REGEX.sub("[REDACTED_PHONE]", redacted)
    redacted = SSN_REGEX.sub("[REDACTED_SSN]", redacted)
    redacted = CREDIT_CARD_REGEX.sub("[REDACTED_CREDIT_CARD]", redacted)
    
    return redacted
