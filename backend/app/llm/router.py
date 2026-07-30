import json
import logging
from typing import Optional, Dict, Any, Tuple
from app.llm.gemini_client import call_gemini
from app.llm.groq_client import call_groq
from app.config import settings

logger = logging.getLogger("meridian.router")

def generate_response(
    prompt: str, 
    system_instruction: Optional[str] = None, 
    json_mode: bool = False,
    response_schema: Optional[Dict[str, Any]] = None
) -> Tuple[str, str]:
    """
    Tries Gemini as primary provider. If it fails, falls back to Groq.
    Supports DEMO_OFFLINE_MODE for rate-limit insurance.
    Returns (response_text, provider_name).
    """
    if settings.DEMO_OFFLINE_MODE:
        logger.info("DEMO_OFFLINE_MODE active. Returning mock response.")
        return get_offline_mock_response(prompt, system_instruction, json_mode), "offline_mock"

    from app.llm.failover_manager import failover_manager
    return failover_manager.execute_with_failover(
        prompt=prompt,
        system_instruction=system_instruction,
        json_mode=json_mode,
        response_schema=response_schema
    )

def generate_response_stream(
    prompt: str, 
    system_instruction: Optional[str] = None
):
    """
    Tries to stream the response using primary/failover providers.
    Yields Tuple[chunk_text, provider_name].
    """
    if settings.DEMO_OFFLINE_MODE:
        logger.info("DEMO_OFFLINE_MODE active. Returning mock stream.")
        mock_res = get_offline_mock_response(prompt, system_instruction, False)
        # Yield the response in small chunks to simulate streaming
        chunk_size = 30
        for i in range(0, len(mock_res), chunk_size):
            yield mock_res[i:i+chunk_size], "offline_mock"
        return

    from app.llm.failover_manager import failover_manager
    yield from failover_manager.execute_with_failover_stream(
        prompt=prompt,
        system_instruction=system_instruction
    )

def get_offline_mock_response(prompt: str, system_instruction: Optional[str], json_mode: bool) -> str:
    """
    Returns high-fidelity mock JSON or text responses matching the system prompt context.
    """
    sys_lower = (system_instruction or "").lower()
    
    # 1. Content Understanding
    if "domain classifier" in sys_lower:
        return json.dumps({
            "domain": "legal",
            "document_type": "policy",
            "sensitivity_signals": ["PII", "legal liability"],
            "risk_level": "critical",
            "is_incomplete": False,
            "is_ambiguous": False,
            "gaps_detected": ["Contact person details are omitted in the original text"]
        })
        
    # 2. Meaning Extraction
    elif "information extraction agent" in sys_lower:
        return json.dumps({
            "nodes": [
                {
                    "id": "claim_1",
                    "type": "Claim",
                    "text": "Mandatory annual inspection starts on August 15, 2026.",
                    "source_span": "inspections are scheduled to commence on August 15, 2026"
                },
                {
                    "id": "obligation_1",
                    "type": "Obligation",
                    "text": "Residents must grant access to safety personnel.",
                    "source_span": "required to grant access to authorized safety personnel"
                },
                {
                    "id": "action_1",
                    "type": "Action",
                    "text": "Submit key-entry consent waiver to leasing office.",
                    "source_span": "consent waiver is executed and submitted"
                },
                {
                    "id": "deadline_1",
                    "type": "Deadline",
                    "text": "Submit waiver 48 hours prior to inspection.",
                    "source_span": "no later than 48 hours prior to the scheduled date"
                }
            ],
            "relationships": [
                {
                    "source_id": "obligation_1",
                    "target_id": "action_1",
                    "type": "CONDITIONED_ON"
                },
                {
                    "source_id": "action_1",
                    "target_id": "deadline_1",
                    "type": "HAS_DEADLINE"
                }
            ]
        })
        
    # 2.5. Accessibility Planner
    elif "accessibility planner" in sys_lower:
        return json.dumps({
            "purpose": "Explain safety inspection rules.",
            "summary": "Safety inspections commence on August 15, 2026. Access is mandatory unless a consent waiver is submitted 48 hours prior.",
            "actions": ["Residents must grant access", "Submit key-entry consent waiver"],
            "deadlines": ["Waiver must be submitted 48 hours prior to inspection"],
            "warnings": ["Penalties for non-compliance and missed deadlines"],
            "eligibility": ["All building residents"],
            "contacts": [
                {
                    "authority": "Leasing Office",
                    "email": "None",
                    "website": "None",
                    "office": "Main Desk",
                    "phone": "555-0199",
                    "address": "Lobby Area"
                }
            ],
            "documents_required": ["Consent Waiver"],
            "legal_terms": [
                {
                    "term": "Consent Waiver",
                    "explanation": "A document giving permission to enter and inspect."
                }
            ],
            "important_numbers": ["48 hours"],
            "next_steps": ["Check scheduled date", "Fill out and sign Consent Waiver", "Submit to main lobby desk"]
        })

    # 3. Verifier
    elif "strict semantic audit engine" in sys_lower:
        return json.dumps({
            "coverage_score": 100,
            "node_status": [
                {"node_id": "claim_1", "status": "fully_represented", "explanation": "Dates matched exactly."},
                {"node_id": "obligation_1", "status": "fully_represented", "explanation": "Obligation to grant access preserved."},
                {"node_id": "action_1", "status": "fully_represented", "explanation": "Waiver option explained."},
                {"node_id": "deadline_1", "status": "fully_represented", "explanation": "48 hour limit preserved."}
            ],
            "hallucinations_detected": [],
            "is_fidelity_check_passed": True
        })
        
    # 4. Rewriter (Default/Fallback text output)
    else:
        return """### Document Summary

The building safety inspections are scheduled to start on August 15, 2026. All residents must grant access to authorized safety personnel. Alternatively, residents can submit a key-entry consent waiver to the leasing office.

--------------------------------------------------
### Why am I receiving this document?

You are receiving this notice because mandatory annual safety inspections are starting in your building, and your apartment needs to be checked.

--------------------------------------------------
### What do I need to do?

Step 1: Be present on the inspection day or grant access.
Step 2: If you cannot be present, execute and submit the key-entry consent waiver.

--------------------------------------------------
### Important Dates

| Deadline | Effective Date | Issue Date | Renewal Date |
| --- | --- | --- | --- |
| 48 hours prior to inspection | August 15, 2026 | None | None |

--------------------------------------------------
### Important Information

Annual inspections are mandatory. You must grant access to authorized inspectors.

--------------------------------------------------
### Warnings

⚠ Failing to grant access or submit the waiver 48 hours prior will result in entry violation penalties.

--------------------------------------------------
### Difficult Words Explained

**Consent Waiver**
↓
A document giving permission to safety personnel to enter your apartment using a management key.

--------------------------------------------------
### Contact Information

**Authority**: Leasing Office
**Email**: None
**Website**: None
**Office**: Main Desk
**Phone**: 555-0199
**Address**: Lobby Area

--------------------------------------------------
### Quick Summary

✓ Safety inspections start August 15, 2026.
✓ Submit waiver at least 48 hours in advance if key-entry is needed.
✓ Mandatory access required.

--------------------------------------------------

--- PROFILE & STRATEGY USED ---
- Profile: general_adult (standard)
- Strategy: Vocab=intermediate, Structure=paragraph, Tone=practical, Language=English

--- GAPS & UNCERTAINTIES ---
- Contact person details are omitted in the original text."""
