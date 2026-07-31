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
        
    # 4. Translator Mock
    elif "translator" in sys_lower or "translate" in sys_lower:
        prompt_lower = prompt.lower()
        if "hindi" in prompt_lower:
            return """### दस्तावेज़ सारांश

भवन सुरक्षा निरीक्षण 15 अगस्त, 2026 से शुरू होने वाले हैं। सभी निवासियों को अधिकृत सुरक्षा कर्मियों को प्रवेश देना होगा। वैकल्पिक रूप से, निवासी लीजिंग कार्यालय में एक कुंजी-प्रवेश सहमति छूट जमा कर सकते हैं।

--------------------------------------------------
### मुझे यह दस्तावेज़ क्यों मिल रहा है?

आपको यह नोटिस इसलिए मिल रहा है क्योंकि आपके भवन में अनिवार्य वार्षिक सुरक्षा निरीक्षण शुरू हो रहे हैं, और आपके अपार्टमेंट की जाँच की जानी आवश्यक है।

--------------------------------------------------
### मुझे क्या करने की ज़रूरत है?

कदम 1: निरीक्षण के दिन उपस्थित रहें या प्रवेश प्रदान करें।
कदम 2: यदि आप उपस्थित नहीं हो सकते हैं, तो कुंजी-प्रवेश सहमति छूट निष्पादित करें और जमा करें।

--------------------------------------------------
### महत्वपूर्ण तिथियां

| समय सीमा | प्रभावी तिथि | जारी होने की तिथि | नवीनीकरण तिथि |
| --- | --- | --- | --- |
| निरीक्षण से 48 घंटे पहले | 15 अगस्त, 2026 | कोई नहीं | कोई नहीं |

--------------------------------------------------
### महत्वपूर्ण जानकारी

वार्षिक निरीक्षण अनिवार्य हैं। आपको अधिकृत निरीक्षकों को प्रवेश देना होगा।

--------------------------------------------------
### चेतावनी

⚠ निरीक्षण से 48 घंटे पहले प्रवेश प्रदान करने या छूट जमा करने में विफल रहने पर प्रवेश उल्लंघन दंड भुगतना होगा।

--------------------------------------------------
### कठिन शब्दों की व्याख्या

**सहमति छूट (Consent Waiver)**
↓
एक दस्तावेज़ जो सुरक्षा कर्मियों को प्रबंधन कुंजी का उपयोग करके आपके अपार्टमेंट में प्रवेश करने और निरीक्षण करने की अनुमति देता है।

--------------------------------------------------
### संपर्क जानकारी

**प्राधिकरण**: लीजिंग कार्यालय
**कार्यालय**: मुख्य डेस्क
**फोन**: 555-0199
**पता**: लॉबी क्षेत्र

--------------------------------------------------
### त्वरित सारांश

✓ सुरक्षा निरीक्षण 15 अगस्त, 2026 से शुरू।
✓ यदि कुंजी-प्रवेश की आवश्यकता है, तो कम से कम 48 घंटे पहले छूट जमा करें।
✓ अनिवार्य प्रवेश आवश्यक।"""
        elif "spanish" in prompt_lower:
            return """### Resumen del Documento

Las inspecciones obligatorias de seguridad del edificio están programadas para comenzar el 15 de agosto de 2026. Todos los residentes deben permitir el acceso al personal del edificio.

--------------------------------------------------
### ¿Por qué recibo este documento?

Recibe este aviso porque están comenzando las inspecciones anuales obligatorias en su edificio.

--------------------------------------------------
### ¿Qué tengo que hacer?

Paso 1: Estar presente el día de la inspección.
Paso 2: Si no puede estar presente, firme el consentimiento de entrada.

--------------------------------------------------
### Fechas Importantes

| Fecha Límite | Fecha de Inicio |
| --- | --- |
| 48 horas antes | 15 de agosto de 2026 |"""
        elif "french" in prompt_lower:
            return """### Résumé du Document

Les inspections obligatoires de sécurité du bâtiment doivent commencer le 15 août 2026. Tous les résidents doivent accorder l'accès aux inspecteurs.

--------------------------------------------------
### Pourquoi est-ce que je reçois ce document?

Vous recevez cet avis car les inspections de sécurité commencent dans votre immeuble.

--------------------------------------------------
### Qu'est-ce que je dois faire?

Étape 1: Être présent le jour de l'inspection.
Étape 2: Si vous ne pouvez pas être présent, signez la dérogation.

--------------------------------------------------
### Dates Importantes

| Date Limite | Date d'inspection |
| --- | --- |
| 48 heures avant | 15 août 2026 |"""
        else:
            lang_token = target_lang if 'target_lang' in locals() else "Target Language"
            return f"[{lang_token} Translation Mock]\n\n" + """### Document Summary

The building safety inspections are scheduled to start on August 15, 2026. All residents must grant access to authorized safety personnel. Alternatively, residents can submit a key-entry consent waiver to the leasing office."""

    # 5. Rewriter (Default/Fallback text output)
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
