import json
import logging
from typing import Dict, Any
from app.llm.router import generate_response
from app.core.prompts import CONTENT_UNDERSTANDING_SYSTEM
from app.utils.checkpoints import CheckpointLogger

logger = logging.getLogger("intellix.agents.content_understanding")

def analyze_content(content: str, run_id: str, checkpoint_logger: CheckpointLogger) -> Dict[str, Any]:
    """
    Executes Content Understanding stage. Classifies domain, document type, risk,
    and identifies initial gaps/PII sensitivity signals.
    """
    checkpoint_logger.start_stage("CONTENT_UNDERSTANDING_STARTED", input_summary=content)
    
    prompt = f"Analyze this source text:\n\n{content}"
    
    # We can inject schema for structured JSON output
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "domain": {
                "type": "STRING",
                "enum": ["administrative", "legal", "medical", "educational", "financial", "general"]
            },
            "document_type": {
                "type": "STRING",
                "enum": ["form", "announcement", "instruction_set", "contract", "policy", "report", "consent", "other"]
            },
            "sensitivity_signals": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            },
            "risk_level": {
                "type": "STRING",
                "enum": ["low", "medium", "high", "critical"]
            },
            "is_incomplete": {"type": "BOOLEAN"},
            "is_ambiguous": {"type": "BOOLEAN"},
            "gaps_detected": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            }
        },
        "required": ["domain", "document_type", "sensitivity_signals", "risk_level", "is_incomplete", "is_ambiguous", "gaps_detected"]
    }
    
    try:
        response_text, provider = generate_response(
            prompt=prompt,
            system_instruction=CONTENT_UNDERSTANDING_SYSTEM,
            json_mode=True,
            response_schema=response_schema
        )
        
        # Parse JSON
        result = json.loads(response_text)
        
        checkpoint_logger.complete_stage(
            "CONTENT_UNDERSTANDING_COMPLETED", 
            output_summary=f"Domain: {result.get('domain')}, Risk: {result.get('risk_level')}",
            gaps_detected=result.get("gaps_detected", []),
            model=provider,
            metadata=result
        )
        return result
        
    except Exception as e:
        logger.error(f"Content understanding failed: {e}")
        checkpoint_logger.fail_stage("CONTENT_UNDERSTANDING_STARTED", str(e))
        # Return fallback values
        fallback = {
            "domain": "general",
            "document_type": "other",
            "sensitivity_signals": [],
            "risk_level": "medium",
            "is_incomplete": False,
            "is_ambiguous": False,
            "gaps_detected": ["Failed to analyze content structure. Processing in fallback mode."]
        }
        return fallback
