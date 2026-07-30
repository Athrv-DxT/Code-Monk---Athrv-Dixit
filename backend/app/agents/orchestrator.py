import uuid
import logging
import time
import asyncio
import threading
from typing import Dict, Any, List, Optional, Generator, AsyncGenerator
from app.core.models import AudienceProfile
from app.utils.checkpoints import CheckpointLogger
from app.agents.content_understanding import analyze_content
from app.agents.meaning_extractor import extract_meaning
from app.agents.strategy_engine import resolve_strategy
from app.agents.rewriter import run_rewriter, run_rewriter_stream
from app.agents.verifier import run_verifier
from app.agents.accessibility_planner import plan_accessibility
from app.graph.neo4j_client import save_meaning_representation
from app.voice.tts_piper import generate_tts
from app.utils.translation_cache import translation_cache
from app.llm.router import generate_response

logger = logging.getLogger("meridian.orchestrator")

def translate_text(text: str, target_lang: str) -> str:
    """
    Translates text to the target language using failover manager.
    Uses TranslationCache to avoid redundant calls.
    """
    if not text.strip() or not target_lang or target_lang.lower() == "en":
        return text
        
    cached = translation_cache.get(text, target_lang)
    if cached:
        logger.info(f"Translation cache HIT for language {target_lang}")
        return cached
        
    lang_names = {
        "hi": "Hindi", "bn": "Bengali", "mr": "Marathi", "te": "Telugu",
        "ta": "Tamil", "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam",
        "pa": "Punjabi", "or": "Odia", "ur": "Urdu", "es": "Spanish",
        "fr": "French", "de": "German"
    }
    lang_name = lang_names.get(target_lang.lower(), target_lang)
    
    system_prompt = f"You are a professional translator. Translate the given text into {lang_name}. Keep all markdown headers, lists, table columns, and formatting identical. Do not add any conversational text or filler."
    prompt = f"Translate the following text into {lang_name}:\n\n{text}"
    
    try:
        translated, _ = generate_response(prompt, system_instruction=system_prompt)
        translation_cache.set(text, target_lang, translated)
        return translated
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return text

async def run_pipeline(
    content: str,
    audience_profile_dict: Dict[str, Any],
    options: Dict[str, Any],
    voice_narration: Optional[str] = None
) -> Dict[str, Any]:
    """
    Orchestrates the entire Project Meridian pipeline asynchronously:
    1. PII Redaction/Masking.
    2. Parallel Content Classifier & Meaning Extraction (asyncio.gather).
    3. Neo4j Graph write (Background Thread).
    4. Accessibility Planning Stage (New Agent).
    5. English-First Adaptation (Generator).
    6. Parallel Cached Translation (if regional).
    7. Semantic Compliance Verification.
    8. TTS Audio Gen.
    """
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    checkpoint_logger = CheckpointLogger(run_id)
    start_total = time.time()
    
    checkpoint_logger.log_event("RUN_STARTED", f"Pipeline initiated with {len(content)} character input.")
    
    vault = None
    from app.config import settings
    if settings.ENABLE_PII_MASKING:
        from app.privacy.detector import PIIDetector
        from app.privacy.masker import PIIMasker
        from app.privacy.vault import PIIVault
        from app.privacy.logger import PIILogger
        
        detector = PIIDetector()
        masker = PIIMasker()
        vault = PIIVault()
        
        detections = detector.detect(content)
        content = masker.mask(content, detections, vault)
        
        pii_summary = PIILogger.get_summary(detections)
        checkpoint_logger.log_event("PII_REDACTION_COMPLETED", f"Main document masked. {pii_summary}")
        
        if voice_narration:
            narration_dets = detector.detect(voice_narration)
            voice_narration = masker.mask(voice_narration, narration_dets, vault)
            checkpoint_logger.log_event("PII_REDACTION_COMPLETED", "Voice narration masked.")
            
    try:
        # 0. Voice-driven profile extraction override
        voice_profile = None
        if voice_narration:
            checkpoint_logger.log_event("VOICE_PROFILE_EXTRACTION_STARTED", f"Extracting audience profile from narration: '{voice_narration}'")
            voice_profile = extract_profile_from_narration(voice_narration)
            voice_profile.modality = "audio_optimized"
            options["tts_output"] = True
            checkpoint_logger.log_event("VOICE_PROFILE_EXTRACTION_COMPLETED", f"Extracted role: {voice_profile.role}, needs: {voice_profile.cognitive_access_needs}")

        # 1 & 2. Concurrently execute Content Classifier & Meaning Extraction (asyncio.gather)
        start_parallel = time.time()
        
        async def run_parallel_agents():
            task_understanding = asyncio.to_thread(analyze_content, content, run_id, checkpoint_logger)
            task_meaning = asyncio.to_thread(extract_meaning, content, run_id, checkpoint_logger)
            return await asyncio.gather(task_understanding, task_meaning)
            
        understanding, representation = await run_parallel_agents()
        parallel_time = time.time() - start_parallel
        
        classification_time = parallel_time
        extraction_time = parallel_time
        
        domain = understanding.get("domain", "general")
        doc_type = understanding.get("document_type", "other")
        risk_level = understanding.get("risk_level", "medium")
        initial_gaps = understanding.get("gaps_detected", [])
        
        # 3. Neo4j persistence in background thread
        start_graph = time.time()
        def bg_save():
            try:
                save_meaning_representation(run_id, representation)
            except Exception as ex:
                logger.error(f"Background Neo4j write failed: {ex}")
        threading.Thread(target=bg_save, daemon=True).start()
        graph_time = time.time() - start_graph
        
        # 4. Resolve Target Profiles
        target_profiles_raw = []
        if voice_profile:
            target_profiles_raw = [voice_profile]
        elif options.get("generate_multiple_profiles") and options.get("profiles"):
            target_profiles_raw = options["profiles"]
        else:
            target_profiles_raw = [audience_profile_dict]
            
        versions = []
        
        for idx, profile_dict in enumerate(target_profiles_raw):
            if isinstance(profile_dict, AudienceProfile):
                profile = profile_dict
            elif isinstance(profile_dict, str):
                profile = _resolve_preset_profile(profile_dict)
            else:
                profile = AudienceProfile(**profile_dict)
                
            if options.get("language") and (options["language"] != "en" or profile.preferred_language == "en"):
                profile.preferred_language = options["language"]
                
            # 5. Strategy Engine
            strategy = resolve_strategy(domain, profile, run_id, checkpoint_logger)
            
            # 6. New Accessibility Planner Agent
            from app.agents.accessibility_planner import plan_accessibility
            start_planner = time.time()
            planner_plan = plan_accessibility(content, representation, profile, run_id, checkpoint_logger)
            planner_time = time.time() - start_planner
            
            # 7. Rewriter (using planner JSON, in English first)
            start_rewrite = time.time()
            enable_external = options.get("enable_external_lookup", False)
            
            # Copy profile for English generation
            english_profile = AudienceProfile(
                role=profile.role,
                domain_familiarity=profile.domain_familiarity,
                cognitive_access_needs=profile.cognitive_access_needs,
                preferred_language="en",
                modality=profile.modality,
                age_band=profile.age_band
            )
            
            rewrite_result = run_rewriter(
                content=content,
                representation=representation,
                profile=english_profile,
                strategy=strategy,
                enable_external_lookup=enable_external,
                run_id=run_id,
                checkpoint_logger=checkpoint_logger,
                planner_plan=planner_plan
            )
            
            adapted_text = rewrite_result["adapted_content"]
            strategy_summary = rewrite_result["strategy_summary"]
            rewrite_gaps = rewrite_result["gaps"]
            explanations = rewrite_result["explanations_retrieved"]
            rewrite_time = time.time() - start_rewrite
            
            # 8. Translation stage (parallel + cached if target is regional)
            start_translation = time.time()
            target_lang = profile.preferred_language
            
            if target_lang and target_lang.lower() != "en":
                async def run_translations():
                    t_text = asyncio.to_thread(translate_text, adapted_text, target_lang)
                    t_exp = asyncio.to_thread(translate_text, explanations, target_lang)
                    return await asyncio.gather(t_text, t_exp)
                adapted_text, explanations = await run_translations()
            translation_time = time.time() - start_translation
            
            # 9. Verification
            verification = run_verifier(adapted_text, representation, run_id, checkpoint_logger)
            
            # Reinsert PII
            unmasked_adapted_text = adapted_text
            unmasked_explanations = explanations
            if settings.ENABLE_PII_MASKING and vault:
                from app.privacy.reinserter import PIIReinserter
                reinserter = PIIReinserter()
                unmasked_adapted_text = reinserter.reinsert(adapted_text, vault)
                if explanations:
                    unmasked_explanations = [reinserter.reinsert(exp, vault) for exp in explanations]
                    
            all_gaps = list(set(initial_gaps + rewrite_gaps))
            
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
                    
            # 10. Text-to-Speech
            audio_url = ""
            if options.get("tts_output", False):
                checkpoint_logger.log_event("TTS_GENERATION_STARTED", f"Generating audio for profile {profile.role}...")
                audio_path = generate_tts(unmasked_adapted_text, run_id, profile.role, profile.preferred_language)
                if audio_path:
                    audio_url = f"/api/v1/audio/{run_id}/{profile.role}.mp3"
                    checkpoint_logger.log_event("TTS_GENERATION_COMPLETED", f"Audio generated at {audio_path}")
                else:
                    checkpoint_logger.log_event("TTS_GENERATION_FAILED", "TTS engine failed to produce file.")
            
            version_response = {
                "profile": profile.role,
                "adapted_content": unmasked_adapted_text,
                "strategy_summary": strategy_summary,
                "gaps": all_gaps,
                "fidelity_note": fidelity_note,
                "audio_url": audio_url,
                "explanations": unmasked_explanations
            }
            versions.append(version_response)
            
        checkpoint_logger.log_event("GAP_REPORT_READY", f"Final gap list compiled across {len(versions)} versions.")
        checkpoint_logger.log_event("RUN_COMPLETED", f"Pipeline finished successfully for run: {run_id}")
        
        total_time = time.time() - start_total
        
        # Timing Metrics
        timing_metrics = {
            "classification_sec": round(classification_time, 3),
            "extraction_sec": round(extraction_time, 3),
            "planning_sec": round(planner_time, 3),
            "rewrite_sec": round(rewrite_time, 3),
            "translation_sec": round(translation_time, 3),
            "graph_sec": round(graph_time, 3),
            "total_sec": round(total_time, 3)
        }
        
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
            "graph_run_node_id": run_id,
            "metrics": timing_metrics
        }
        
    except Exception as e:
        logger.exception("Pipeline execution failed:")
        checkpoint_logger.log_event("RUN_FAILED", f"Pipeline crashed with error: {str(e)}")
        raise e
    finally:
        if vault:
            vault.clear()

async def run_pipeline_stream(
    content: str,
    audience_profile_dict: Dict[str, Any],
    options: Dict[str, Any],
    voice_narration: Optional[str] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Asynchronous streaming pipeline. Yields completed sections one by one.
    """
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    checkpoint_logger = CheckpointLogger(run_id)
    
    vault = None
    from app.config import settings
    if settings.ENABLE_PII_MASKING:
        from app.privacy.detector import PIIDetector
        from app.privacy.masker import PIIMasker
        from app.privacy.vault import PIIVault
        
        detector = PIIDetector()
        masker = PIIMasker()
        vault = PIIVault()
        
        detections = detector.detect(content)
        content = masker.mask(content, detections, vault)
        
    try:
        # Step 1 & 2. Concurrently execute Classifier & Meaning Extraction
        async def run_parallel_agents():
            task_understanding = asyncio.to_thread(analyze_content, content, run_id, checkpoint_logger)
            task_meaning = asyncio.to_thread(extract_meaning, content, run_id, checkpoint_logger)
            return await asyncio.gather(task_understanding, task_meaning)
            
        understanding, representation = await run_parallel_agents()
        domain = understanding.get("domain", "general")
        
        # Neo4j in background
        def bg_save():
            try:
                save_meaning_representation(run_id, representation)
            except Exception:
                pass
        threading.Thread(target=bg_save, daemon=True).start()
        
        # Profile & Strategy Setup
        if isinstance(audience_profile_dict, AudienceProfile):
            profile = audience_profile_dict
        else:
            profile = AudienceProfile(**audience_profile_dict)
            
        if options.get("language"):
            profile.preferred_language = options["language"]
            
        strategy = resolve_strategy(domain, profile, run_id, checkpoint_logger)
        
        # Accessibility Planning
        planner_plan = plan_accessibility(content, representation, profile, run_id, checkpoint_logger)
        
        # Yield metadata early
        yield {
            "status": "metadata",
            "run_id": run_id,
            "domain": domain,
            "document_type": understanding.get("document_type", "other"),
            "risk_level": understanding.get("risk_level", "medium")
        }
        
        # Stream Rewriter (English)
        section_generator = run_rewriter_stream(profile, strategy, planner_plan)
        
        from app.privacy.reinserter import PIIReinserter
        reinserter = PIIReinserter() if (settings.ENABLE_PII_MASKING and vault) else None
        
        # We read from generator inside asyncio.to_thread since generator does synchronous I/O
        def get_sections():
            return list(section_generator)
            
        sections = await asyncio.to_thread(get_sections)
        
        for section in sections:
            sect_title = section["section"]
            sect_content = section["content"]
            
            # Translate if regional
            target_lang = profile.preferred_language
            if target_lang and target_lang.lower() != "en":
                sect_title = translate_text(sect_title, target_lang)
                sect_content = translate_text(sect_content, target_lang)
                
            # Reinsert PII
            if reinserter and vault:
                sect_content = reinserter.reinsert(sect_content, vault)
                
            yield {
                "status": "section_update",
                "section": sect_title,
                "content": sect_content
            }
            
        yield {"status": "completed"}
        
    except Exception as e:
        logger.error(f"Streaming pipeline failed: {e}")
        yield {"status": "error", "detail": str(e)}
    finally:
        if vault:
            vault.clear()

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
