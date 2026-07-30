import uuid
import logging
from typing import Dict, Any, List
from app.core.models import AudienceProfile
from app.utils.checkpoints import CheckpointLogger
from app.agents.content_understanding import analyze_content
from app.agents.meaning_extractor import extract_meaning
from app.agents.strategy_engine import resolve_strategy
from app.agents.rewriter import run_rewriter
from app.agents.verifier import run_verifier
from app.graph.neo4j_client import save_meaning_representation
from app.voice.tts_piper import generate_tts  # We will implement this shortly

logger = logging.getLogger("meridian.orchestrator")

from typing import Dict, Any, List, Optional

def run_pipeline(
    content: str,
    audience_profile_dict: Dict[str, Any],
    options: Dict[str, Any],
    voice_narration: Optional[str] = None
) -> Dict[str, Any]:
    """
    Orchestrates the entire Project Meridian pipeline:
    Content Understanding -> Meaning Extraction -> Neo4j Graph Write ->
    Strategy Resolution -> Adaptation Rewrite -> Verification -> Audio Gen (Optional).
    """
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    checkpoint_logger = CheckpointLogger(run_id)
    
    checkpoint_logger.log_event("RUN_STARTED", f"Pipeline initiated with {len(content)} character input.")
    
    try:
        # 0. Voice-driven profile extraction override (v4 Accessibility)
        voice_profile = None
        if voice_narration:
            checkpoint_logger.log_event("VOICE_PROFILE_EXTRACTION_STARTED", f"Extracting audience profile from narration: '{voice_narration}'")
            voice_profile = extract_profile_from_narration(voice_narration)
            # Force TTS audio output and audio optimization since they dictated it
            voice_profile.modality = "audio_optimized"
            options["tts_output"] = True
            checkpoint_logger.log_event("VOICE_PROFILE_EXTRACTION_COMPLETED", f"Extracted role: {voice_profile.role}, needs: {voice_profile.cognitive_access_needs}")

        # 1. Content Understanding
        understanding = analyze_content(content, run_id, checkpoint_logger)
        domain = understanding.get("domain", "general")
        doc_type = understanding.get("document_type", "other")
        risk_level = understanding.get("risk_level", "medium")
        initial_gaps = understanding.get("gaps_detected", [])
        
        # 2. Structured Meaning Extraction
        representation = extract_meaning(content, run_id, checkpoint_logger)
        
        # 3. Neo4j Graph Persistence
        checkpoint_logger.start_stage("GRAPH_WRITE_STARTED", input_summary=f"Nodes to write: {len(representation.nodes)}")
        db_success = save_meaning_representation(run_id, representation)
        checkpoint_logger.complete_stage(
            "GRAPH_WRITE_COMPLETED", 
            output_summary="Graph saved successfully" if db_success else "Bypassed (Neo4j offline)"
        )
        
        # 4. Resolve Target Profiles
        target_profiles_raw = []
        if voice_profile:
            # Override target profile with extracted voice profile object directly
            target_profiles_raw = [voice_profile]
        elif options.get("generate_multiple_profiles") and options.get("profiles"):
            target_profiles_raw = options["profiles"]
        else:
            target_profiles_raw = [audience_profile_dict]
            
        versions = []
        
        for idx, profile_dict in enumerate(target_profiles_raw):
            # Parse or create profile
            if isinstance(profile_dict, AudienceProfile):
                profile = profile_dict
            elif isinstance(profile_dict, str):
                # Preset maps
                profile = _resolve_preset_profile(profile_dict)
            else:
                profile = AudienceProfile(**profile_dict)
                
            # 5. Strategy Engine
            strategy = resolve_strategy(domain, profile, run_id, checkpoint_logger)
            
            # 6. Rewriter
            enable_external = options.get("enable_external_lookup", False)
            rewrite_result = run_rewriter(
                content=content,
                representation=representation,
                profile=profile,
                strategy=strategy,
                enable_external_lookup=enable_external,
                run_id=run_id,
                checkpoint_logger=checkpoint_logger
            )
            
            adapted_text = rewrite_result["adapted_content"]
            strategy_summary = rewrite_result["strategy_summary"]
            rewrite_gaps = rewrite_result["gaps"]
            explanations = rewrite_result["explanations_retrieved"]
            
            # 7. Verification
            verification = run_verifier(adapted_text, representation, run_id, checkpoint_logger)
            
            # Combine gaps (initial understanding + rewrite gaps)
            all_gaps = list(set(initial_gaps + rewrite_gaps))
            
            # Optional fidelity note
            fidelity_note = ""
            if options.get("include_fidelity_note", True):
                fidelity_note = (
                    f"Fidelity check: {verification.get('coverage_score')}% coverage. "
                    f"Hallucinations: {len(verification.get('hallucinations_detected', []))}. "
                )
                if verification.get("is_fidelity_check_passed"):
                    fidelity_note += "Semantic compliance verified."
                else:
                    fidelity_note += "Warning: Some obligations/meanings might be dropped or modified."
                    
            # 8. Text-to-Speech (Optional)
            audio_url = ""
            if options.get("tts_output", False):
                checkpoint_logger.log_event("TTS_GENERATION_STARTED", f"Generating audio for profile {profile.role}...")
                audio_path = generate_tts(adapted_text, run_id, profile.role)
                if audio_path:
                    audio_url = f"/api/v1/audio/{run_id}/{profile.role}.mp3"
                    checkpoint_logger.log_event("TTS_GENERATION_COMPLETED", f"Audio generated at {audio_path}")
                else:
                    checkpoint_logger.log_event("TTS_GENERATION_FAILED", "TTS engine failed to produce file.")
            
            # Build version response
            version_response = {
                "profile": profile.role,
                "adapted_content": adapted_text,
                "strategy_summary": strategy_summary,
                "gaps": all_gaps,
                "fidelity_note": fidelity_note,
                "audio_url": audio_url,
                "explanations": explanations
            }
            versions.append(version_response)
            
        checkpoint_logger.log_event("GAP_REPORT_READY", f"Final gap list compiled across {len(versions)} versions.")
        checkpoint_logger.log_event("RUN_COMPLETED", f"Pipeline finished successfully for run: {run_id}")
        
        # Assemble complete response contract
        return {
            "run_id": run_id,
            "domain": domain,
            "document_type": doc_type,
            "risk_level": risk_level,
            "versions": versions,
            "content_understanding": understanding,
            "meaning_summary": {
                "node_count": len(representation.nodes),
                "relationship_count": len(representation.relationships)
            },
            "graph_run_node_id": run_id
        }
        
    except Exception as e:
        logger.exception("Pipeline execution failed:")
        checkpoint_logger.log_event("RUN_FAILED", f"Pipeline crashed with error: {str(e)}")
        raise e

def _resolve_preset_profile(profile_name: str) -> AudienceProfile:
    """
    Maps profile string IDs to AudienceProfile objects.
    """
    presets = {
        "general_adult": AudienceProfile(role="general_adult", domain_familiarity="intermediate", cognitive_access_needs="standard", preferred_language="en", modality="text"),
        "child": AudienceProfile(role="child", domain_familiarity="novice", cognitive_access_needs="child_appropriate", preferred_language="en", modality="text", age_band="child"),
        "anxious": AudienceProfile(role="patient", domain_familiarity="novice", cognitive_access_needs="anxiety_aware", preferred_language="en", modality="text"),
        "dyslexia_friendly": AudienceProfile(role="general_adult", domain_familiarity="intermediate", cognitive_access_needs="dyslexia_friendly", preferred_language="en", modality="highly_structured"),
        "caregiver": AudienceProfile(role="caregiver", domain_familiarity="intermediate", cognitive_access_needs="standard", preferred_language="en", modality="text"),
        "clinician": AudienceProfile(role="clinician", domain_familiarity="expert", cognitive_access_needs="standard", preferred_language="en", modality="text")
    }
    return presets.get(profile_name, presets["general_adult"])

def extract_profile_from_narration(narration: str) -> AudienceProfile:
    """
    Calls the LLM router to parse a conversational request and output a structured AudienceProfile.
    """
    from app.llm.router import generate_response
    from app.core.prompts import PROFILE_EXTRACTION_SYSTEM
    import json
    
    prompt = f"Extract accessibility profile details from this request:\n\n\"{narration}\""
    
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "role": {
                "type": "STRING",
                "enum": ["patient", "parent_guardian", "child", "caregiver", "clinician", "student", "employee", "general_adult", "other"]
            },
            "domain_familiarity": {
                "type": "STRING",
                "enum": ["novice", "intermediate", "expert"]
            },
            "cognitive_access_needs": {
                "type": "STRING",
                "enum": ["standard", "low_cognitive_load", "dyslexia_friendly", "anxiety_aware", "child_appropriate", "other"]
            },
            "preferred_language": {"type": "STRING"},
            "modality": {
                "type": "STRING",
                "enum": ["text", "audio_optimized", "highly_structured", "sign_language_friendly_script"]
            }
        },
        "required": ["role", "domain_familiarity", "cognitive_access_needs", "preferred_language", "modality"]
    }
    
    try:
        response_text, provider = generate_response(
            prompt=prompt,
            system_instruction=PROFILE_EXTRACTION_SYSTEM,
            json_mode=True,
            response_schema=response_schema
        )
        data = json.loads(response_text)
        logger.info(f"Extracted voice profile successfully: {data}")
        return AudienceProfile(**data)
    except Exception as e:
        logger.error(f"Failed to extract profile from voice narration: {e}")
        # Default fallback
        return AudienceProfile(
            role="general_adult",
            domain_familiarity="intermediate",
            cognitive_access_needs="standard",
            preferred_language="en",
            modality="text"
        )
