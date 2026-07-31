import json
import logging
from typing import Dict, Any
from app.llm.router import generate_response
from app.core.prompts import ACCESSIBILITY_PLANNER_SYSTEM
from app.core.models import StructuredMeaningRepresentation, AudienceProfile
from app.utils.checkpoints import CheckpointLogger

logger = logging.getLogger("intellix.agents.accessibility_planner")

def plan_accessibility(
    content: str,
    representation: StructuredMeaningRepresentation,
    profile: AudienceProfile,
    run_id: str,
    checkpoint_logger: CheckpointLogger
) -> Dict[str, Any]:
    """
    Executes the Accessibility Planning stage.
    Generates a structured plan (purpose, summary, actions, deadlines, warnings, etc.) in JSON format.
    """
    checkpoint_logger.start_stage("ACCESSIBILITY_PLANNING_STARTED", input_summary=f"Role: {profile.role}")
    
    # Serialize meaning nodes to feed to the planner
    meaning_serialized = ""
    for node in representation.nodes:
        meaning_serialized += f"- [{node.id}] ({node.type}): {node.text} (Source text: \"{node.source_span}\")\n"
        
    prompt = f"""SOURCE DOCUMENT:
{content}

STRUCTURED MEANING NODES:
{meaning_serialized}

AUDIENCE PROFILE:
- Role: {profile.role}
- Access Needs: {profile.cognitive_access_needs}
- Modality: {profile.modality}
"""

    # We enforce JSON mode with a strict schema
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "purpose": {"type": "STRING"},
            "summary": {"type": "STRING"},
            "actions": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            },
            "deadlines": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            },
            "warnings": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            },
            "eligibility": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            },
            "contacts": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "authority": {"type": "STRING"},
                        "email": {"type": "STRING"},
                        "website": {"type": "STRING"},
                        "office": {"type": "STRING"},
                        "phone": {"type": "STRING"},
                        "address": {"type": "STRING"}
                    },
                    "required": ["authority", "email", "website", "office", "phone", "address"]
                }
            },
            "documents_required": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            },
            "legal_terms": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "term": {"type": "STRING"},
                        "explanation": {"type": "STRING"}
                    },
                    "required": ["term", "explanation"]
                }
            },
            "important_numbers": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            },
            "next_steps": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            }
        },
        "required": [
            "purpose", "summary", "actions", "deadlines", "warnings", "eligibility", 
            "contacts", "documents_required", "legal_terms", "important_numbers", "next_steps"
        ]
    }

    try:
        response_text, provider = generate_response(
            prompt=prompt,
            system_instruction=ACCESSIBILITY_PLANNER_SYSTEM,
            json_mode=True,
            response_schema=response_schema
        )
        
        result = json.loads(response_text)
        checkpoint_logger.complete_stage(
            "ACCESSIBILITY_PLANNING_COMPLETED",
            output_summary=f"Purpose: {result.get('purpose')[:60]}...",
            model=provider,
            metadata=result
        )
        return result
    except Exception as e:
        logger.error(f"Accessibility planning failed: {e}")
        checkpoint_logger.fail_stage("ACCESSIBILITY_PLANNING_STARTED", str(e))
        # Fallback values
        return {
            "purpose": "Explain the document's terms and requirements.",
            "summary": "This document contains details that require action. Please review the steps below.",
            "actions": [n.text for n in representation.nodes if n.type == "Action"],
            "deadlines": [n.text for n in representation.nodes if n.type == "Deadline"],
            "warnings": [n.text for n in representation.nodes if n.type == "Obligation"],
            "eligibility": [],
            "contacts": [],
            "documents_required": [],
            "legal_terms": [],
            "important_numbers": [],
            "next_steps": []
        }
