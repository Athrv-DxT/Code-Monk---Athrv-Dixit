import re
from app.privacy.vault import PIIVault

class PIIReinserter:
    def __init__(self):
        # Match tokens like [PERSON_001], [AADHAAR_002], etc.
        self.token_pattern = re.compile(r"\[([A-Z]+_[0-9]{3})\]")

    def reinsert(self, text: str, vault: PIIVault) -> str:
        """
        Scans adapted text for tokens and replaces them with original values from the vault.
        """
        if not text:
            return text

        def replace_token(match):
            full_token = f"[{match.group(1)}]"
            if vault.contains(full_token):
                return vault.get(full_token)
            return full_token

        return self.token_pattern.sub(replace_token, text)
