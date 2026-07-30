import json
import logging
from typing import Dict, Any
from app.llm.router import generate_response
from app.core.prompts import VERIFIER_SYSTEM
from app.core.models import StructuredMeaningRepresentation
from app.utils.checkpoints import CheckpointLogger

logger = logging.getLogger("meridian.agents.verifier")

def run_verifier(
    adapted_content: str,
    representation: StructuredMeaningRepresentation,
    run_id: str,
    checkpoint_logger: CheckpointLogger
) -> Dict[str, Any]:
    """
    Runs the Verification phase. Queries the meaning graph, compares it to the adapted text,
    and returns a structured fidelity and coverage report.
    """
    checkpoint_logger.start_stage("VERIFICATION_STARTED", input_summary=f"Adapted text length: {len(adapted_content)}")
    
    # Serialize meaning nodes for comparison
    meaning_serialized = ""
    for node in representation.nodes:
        meaning_serialized += f"- [{node.id}] ({node.type}): {node.text}\n"
        
    prompt = f"""ADAPTED CONTENT:
\"\"\"
{adapted_content}
\"\"\"

STRUCTURED MEANING GRAPH NODES TO VERIFY COVERAGE AGAINST:
{meaning_serialized}
"""

    response_schema = {
      "type": "OBJECT",
      "properties": {
        "coverage_score": {"type": "INTEGER"},
        "node_status": {
          "type": "ARRAY",
          "items": {
            "type": "OBJECT",
            "properties": {
              "node_id": {"type": "STRING"},
              "status": {"type": "STRING", "enum": ["fully_represented", "partially_represented", "dropped", "drifted"]},
              "explanation": {"type": "STRING"}
            },
            "required": ["node_id", "status", "explanation"]
          }
        },
        "hallucinations_detected": {
          "type": "ARRAY",
          "items": {"type": "STRING"}
        },
        "is_fidelity_check_passed": {"type": "BOOLEAN"}
      },
      "required": ["coverage_score", "node_status", "hallucinations_detected", "is_fidelity_check_passed"]
    }
    
    try:
        response_text, provider = generate_response(
            prompt=prompt,
            system_instruction=VERIFIER_SYSTEM,
            json_mode=True,
            response_schema=response_schema
        )
        
        result = json.loads(response_text)
        
        # Determine overall verification status
        passed = result.get("is_fidelity_check_passed", False)
        status_text = "PASSED" if passed else "FAILED"
        
        checkpoint_logger.complete_stage(
            "VERIFICATION_COMPLETED",
            output_summary=f"Score: {result.get('coverage_score')}% | Status: {status_text}",
            model=provider,
            metadata=result
        )
        
        # Save verification node status directly to Neo4j if needed, or return to orchestrator
        return result
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        checkpoint_logger.fail_stage("VERIFICATION_STARTED", str(e))
        # Fallback verification result
        return {
            "coverage_score": 0,
            "node_status": [{"node_id": n.id, "status": "dropped", "explanation": "Verification pipeline failed."} for n in representation.nodes],
            "hallucinations_detected": ["Verification process failed."],
            "is_fidelity_check_passed": False
        }
