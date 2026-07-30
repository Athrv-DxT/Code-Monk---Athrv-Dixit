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
            "is_incomplete": false,
            "is_ambiguous": false,
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
        return """--- ADAPTED CONTENT ---
### IMPORTANT NOTICE: SAFETY INSPECTION INFORMATION

Dear Resident,

Please read this important notice regarding safety inspections in our building.

**What is happening?**
We are running our annual safety checks. We will test fire sprinklers and smoke detectors in every apartment.

**When?**
Between August 15, 2026, and August 22, 2026. Workers will arrive between 9:00 AM and 5:00 PM.

**What do you need to do?**
1. You must let the safety workers inside your home.
2. If you cannot be home, you can sign a paper that allows workers to enter using our key. You must submit this paper to the leasing office at least 48 hours before your scheduled day.

**Important Warning:**
If you do not let workers enter or fail to submit the signed paper on time, you will be fined $150.00 or could face eviction.

--- PROFILE & STRATEGY USED ---
- Profile: general_adult (standard)
- Strategy: Vocab=simple, Structure=checklist, Tone=practical

--- GAPS & UNCERTAINTIES ---
- Contact person details are omitted in the original text.
"""
import json
