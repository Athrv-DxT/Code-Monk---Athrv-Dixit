import json
import logging
from typing import Dict, Any
from app.llm.router import generate_response
from app.core.prompts import MEANING_EXTRACTION_SYSTEM
from app.core.models import StructuredMeaningRepresentation, MeaningNode, MeaningRelationship
from app.utils.checkpoints import CheckpointLogger

logger = logging.getLogger("meridian.agents.meaning_extractor")

def extract_meaning(
    content: str, 
    run_id: str, 
    checkpoint_logger: CheckpointLogger
) -> StructuredMeaningRepresentation:
    """
    Extracts semantic meaning graph (claims, obligations, conditions, etc.) from the source text,
    resolves character offsets, and maps relationships.
    """
    checkpoint_logger.start_stage("MEANING_EXTRACTION_STARTED", input_summary=content)
    
    prompt = f"Source Text to extract structure from:\n\n{content}"
    
    # OpenAPI schema for structured meaning
    response_schema = {
      "type": "OBJECT",
      "properties": {
        "nodes": {
          "type": "ARRAY",
          "items": {
            "type": "OBJECT",
            "properties": {
              "id": {"type": "STRING"},
              "type": {"type": "STRING", "enum": ["Claim", "Obligation", "Right", "Condition", "Action", "Deadline", "Gap"]},
              "text": {"type": "STRING"},
              "source_span": {"type": "STRING"}
            },
            "required": ["id", "type", "text", "source_span"]
          }
        },
        "relationships": {
          "type": "ARRAY",
          "items": {
            "type": "OBJECT",
            "properties": {
              "source_id": {"type": "STRING"},
              "target_id": {"type": "STRING"},
              "type": {"type": "STRING", "enum": ["CONDITIONED_ON", "HAS_DEADLINE", "APPLIES_TO_ROLE", "CONFLICTS_WITH"]}
            },
            "required": ["source_id", "target_id", "type"]
          }
        }
      },
      "required": ["nodes", "relationships"]
    }
    
    try:
        response_text, provider = generate_response(
            prompt=prompt,
            system_instruction=MEANING_EXTRACTION_SYSTEM,
            json_mode=True,
            response_schema=response_schema
        )
        
        raw_data = json.loads(response_text)
        
        # 1. Resolve character offsets
        nodes = []
        for raw_node in raw_data.get("nodes", []):
            source_span = raw_node.get("source_span", "")
            # Find the substring in original content
            char_offsets = None
            if source_span:
                start_idx = content.find(source_span)
                if start_idx != -1:
                    char_offsets = (start_idx, start_idx + len(source_span))
                    
            nodes.append(MeaningNode(
                id=raw_node.get("id"),
                type=raw_node.get("type"),
                text=raw_node.get("text"),
                source_span=source_span,
                char_offsets=char_offsets
            ))
            
        # 2. Map relationships
        relationships = []
        for raw_rel in raw_data.get("relationships", []):
            relationships.append(MeaningRelationship(
                source_id=raw_rel.get("source_id"),
                target_id=raw_rel.get("target_id"),
                type=raw_rel.get("type")
            ))
            
        repr_obj = StructuredMeaningRepresentation(nodes=nodes, relationships=relationships)
        
        checkpoint_logger.complete_stage(
            "MEANING_EXTRACTION_COMPLETED",
            output_summary=f"Extracted {len(nodes)} nodes, {len(relationships)} relationships",
            model=provider,
            metadata=raw_data
        )
        return repr_obj
        
    except Exception as e:
        logger.error(f"Meaning extraction failed: {e}")
        checkpoint_logger.fail_stage("MEANING_EXTRACTION_STARTED", str(e))
        # Return empty representation
        return StructuredMeaningRepresentation(nodes=[], relationships=[])
