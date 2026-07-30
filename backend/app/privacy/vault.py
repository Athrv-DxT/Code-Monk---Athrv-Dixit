from typing import Dict

class PIIVault:
    def __init__(self):
        # Maps token -> original_value
        self._token_to_value: Dict[str, str] = {}
        # Maps original_value -> token (to reuse same token for identical values)
        self._value_to_token: Dict[str, str] = {}
        # Counter per entity type to generate index sequence: e.g. PERSON_001
        self._counters: Dict[str, int] = {}

    def store(self, entity_type: str, original_value: str) -> str:
        """
        Stores PII mapping in memory, returns a clean token like [PERSON_001].
        """
        norm_val = original_value.strip()
        
        # If value already has a token, return it to preserve reference consistency
        if norm_val in self._value_to_token:
            return self._value_to_token[norm_val]

        # Increment index for this entity type
        entity_key = entity_type.upper()
        curr_idx = self._counters.get(entity_key, 0) + 1
        self._counters[entity_key] = curr_idx

        # Format: e.g. [PERSON_001]
        token = f"[{entity_key}_{curr_idx:03d}]"
        
        self._token_to_value[token] = original_value
        self._value_to_token[norm_val] = token
        
        return token

    def get(self, token: str) -> str:
        """
        Retrieves original value for a given token.
        """
        return self._token_to_value.get(token, token)

    def contains(self, token: str) -> bool:
        """
        Checks if the token exists in the vault.
        """
        return token in self._token_to_value

    def clear(self):
        """
        Completely clears mappings from memory to destroy PII links.
        """
        self._token_to_value.clear()
        self._value_to_token.clear()
        self._counters.clear()
