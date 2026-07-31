import logging
import re
from typing import Dict, Any, List, Optional, Generator
from app.llm.router import generate_response
from app.core.prompts import REWRITER_SYSTEM
from app.core.models import StructuredMeaningRepresentation, AudienceProfile, AdaptationStrategy
from app.retrieval.hybrid_search import hybrid_search
from app.retrieval.tavily_client import search_tavily
from app.utils.checkpoints import CheckpointLogger

logger = logging.getLogger("meridian.agents.rewriter")

def run_rewriter(
    content: str,
    representation: StructuredMeaningRepresentation,
    profile: AudienceProfile,
    strategy: AdaptationStrategy,
    enable_external_lookup: bool,
    run_id: str,
    checkpoint_logger: CheckpointLogger,
    planner_plan: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Runs the Rewrite phase. Consumes planner_plan JSON if provided, otherwise falls back to
    serialized structured meaning nodes.
    """
    checkpoint_logger.start_stage("REWRITE_STARTED", input_summary=f"Role: {profile.role}")
    
    # Combine explanations
    grounding_explanations = []
    
    lang_map = {
        "hi": "Hindi",
        "en": "English",
        "bn": "Bengali",
        "mr": "Marathi",
        "te": "Telugu",
        "ta": "Tamil",
        "gu": "Gujarati",
        "kn": "Kannada",
        "ml": "Malayalam",
        "pa": "Punjabi",
        "or": "Odia",
        "ur": "Urdu",
        "es": "Spanish",
        "fr": "French",
        "de": "German"
    }
    target_language = lang_map.get(profile.preferred_language.lower(), profile.preferred_language or "English")
    
    if planner_plan:
        import json
        prompt = f"""STRUCTURED DOCUMENT PLAN:
{json.dumps(planner_plan, indent=2)}

Please write the complete accessibility adapted document based on this plan.
"""
    else:
        # Fallback to direct extraction / hybrid search if planner is bypassed
        checkpoint_logger.log_event("RETRIEVAL_STARTED", "Starting hybrid search for document terminology grounding.")
        import re
        token_re = re.compile(r"^\[[A-Z_]+_[0-9]{3}\]$")
        matched_glossary_terms = set()
        distinct_nodes = [n for n in representation.nodes if len(n.text.strip()) > 10 and not token_re.match(n.text.strip())][:4]
        for node in distinct_nodes:
            hits = hybrid_search(node.text, top_k=1)
            for hit in hits:
                term_key = hit["term"].lower()
                if term_key not in matched_glossary_terms:
                    matched_glossary_terms.add(term_key)
                    grounding_explanations.append(f"- **{hit['term']}**: {hit['definition']} [Source: Local Glossary]")
                    
        if len(grounding_explanations) == 0 and enable_external_lookup:
            checkpoint_logger.log_event("RETRIEVAL_STARTED", "Local glossary empty. Invoking Tavily external fallback search.")
            tavily_query = f"definition of key terms in {profile.role} context"
            hits = search_tavily(tavily_query, max_results=2)
            for hit in hits:
                grounding_explanations.append(
                    f"- **{hit.get('title', 'External Resource')}**: {hit.get('content')} [Source: {hit.get('url')}]"
                )
                
        checkpoint_logger.log_event("RETRIEVAL_COMPLETED", f"Grounding context retrieved: {len(grounding_explanations)} explanations.")
        grounding_context_str = "\n".join(grounding_explanations) if grounding_explanations else "None available."
        
        meaning_serialized = ""
        for node in representation.nodes:
            meaning_serialized += f"- [{node.id}] ({node.type}): {node.text} (Source text: \"{node.source_span}\")\n"
            
        prompt = f"""ORIGINAL DOCUMENT FOR REFERENCE:
\"\"\"
{content}
\"\"\"

STRUCTURED MEANING NODES (ONLY SOURCE OF TRUTH):
{meaning_serialized}

GROUNDING CONTEXT (OPTIONAL TERMINOLOGY EXPLANATIONS):
{grounding_context_str}
"""
    
    system_prompt = REWRITER_SYSTEM.format(
        vocabulary_level=strategy.vocabulary_level,
        structure_format=strategy.structure_format,
        tone=strategy.tone,
        information_density=strategy.information_density,
        profile_role=profile.role,
        profile_access_needs=profile.cognitive_access_needs,
        target_language=target_language
    )
    
    try:
        response_text, provider = generate_response(
            prompt=prompt,
            system_instruction=system_prompt,
            json_mode=False
        )
        
        # Parse Response
        # The adapted content starts directly, and is ended by "--- PROFILE & STRATEGY USED ---"
        adapted_content = response_text
        if "--- PROFILE & STRATEGY USED ---" in response_text:
            adapted_content = response_text.split("--- PROFILE & STRATEGY USED ---")[0].strip()
            
        import re
        gaps_match = re.search(r'--- GAPS & UNCERTAINTIES ---\s*(.*?)\s*$', response_text, re.DOTALL | re.IGNORECASE)
        gaps_list = []
        if gaps_match:
            gaps_str = gaps_match.group(1).strip()
            gaps_list = [g.strip("- ").strip() for g in gaps_str.split("\n") if g.strip()]
            if gaps_list and "None identified." in gaps_list[0]:
                gaps_list = []
            
        # Explanations block
        explanations_text = ""
        explanation_section_match = re.search(r'(Difficult Words Explained|DIFFICULT WORDS EXPLAINED).*', adapted_content, re.DOTALL | re.IGNORECASE)
        if explanation_section_match:
            explanations_text = explanation_section_match.group(0).strip()
            
        checkpoint_logger.complete_stage(
            "REWRITE_COMPLETED",
            output_summary=f"Length: {len(adapted_content)} chars",
            gaps_detected=gaps_list,
            model=provider
        )
        
        return {
            "adapted_content": adapted_content,
            "gaps": gaps_list,
            "explanations_retrieved": explanations_text,
            "strategy_summary": f"Vocab={strategy.vocabulary_level}, Structure={strategy.structure_format}, Tone={strategy.tone}"
        }
        
    except Exception as e:
        logger.error(f"Rewrite failed: {e}")
        checkpoint_logger.fail_stage("REWRITE_STARTED", str(e))
        # LLM unavailable — use rule-based simplifier so the output is still useful
        try:
            from app.utils.document_simplifier import simplify_document
            lang_display = lang_map.get(profile.preferred_language.lower(), "English")
            simplified = simplify_document(content, profile.role, lang_display)
            logger.info("[Rewriter] Rule-based simplifier produced fallback accessibility output.")
        except Exception as e2:
            logger.error(f"Rule-based simplifier also failed: {e2}")
            simplified = content
        return {
            "adapted_content": simplified,
            "gaps": ["AI-based semantic rewriter was unavailable. Rule-based simplification was used instead."],
            "explanations_retrieved": "",
            "strategy_summary": "Fallback (Rule-Based Simplifier)"
        }

def run_rewriter_stream(
    profile: AudienceProfile,
    strategy: AdaptationStrategy,
    planner_plan: Dict[str, Any]
) -> Generator[Dict[str, Any], None, None]:
    """
    Runs rewriter in streaming mode. Yields completed sections one by one.
    Falls back to rule-based simplifier if LLM stream fails.
    Yields Dict: {"section": "Section Title", "content": "Section text body", "provider": "provider_name"}
    """
    lang_map = {
        "hi": "Hindi", "en": "English", "bn": "Bengali", "mr": "Marathi",
        "te": "Telugu", "ta": "Tamil", "gu": "Gujarati", "kn": "Kannada",
        "ml": "Malayalam", "pa": "Punjabi", "or": "Odia", "ur": "Urdu",
        "es": "Spanish", "fr": "French", "de": "German"
    }
    target_language = lang_map.get(profile.preferred_language.lower(), profile.preferred_language or "English")
    
    system_prompt = REWRITER_SYSTEM.format(
        vocabulary_level=strategy.vocabulary_level,
        structure_format=strategy.structure_format,
        tone=strategy.tone,
        information_density=strategy.information_density,
        profile_role=profile.role,
        profile_access_needs=profile.cognitive_access_needs,
        target_language=target_language
    )
    
    import json
    prompt = f"""STRUCTURED DOCUMENT PLAN:
{json.dumps(planner_plan, indent=2)}

Please write the complete accessibility adapted document based on this plan.
"""
    
    from app.llm.router import generate_response_stream
    
    import re
    buffer = ""
    sections_yielded = 0
    
    try:
        token_stream = generate_response_stream(prompt, system_instruction=system_prompt)
        
        for chunk, provider in token_stream:
            buffer += chunk
            
            while True:
                parts = buffer.split("### ")
                if len(parts) >= 3:
                    section_part = parts[1]
                    section_lines = section_part.split("\n", 1)
                    title = section_lines[0].strip().replace("---", "").strip()
                    content = section_lines[1] if len(section_lines) > 1 else ""
                    
                    content_clean = re.sub(r'-{10,}', '', content).strip()
                    
                    yield {
                        "section": title,
                        "content": content_clean,
                        "provider": provider
                    }
                    sections_yielded += 1
                    buffer = "### " + "### ".join(parts[2:])
                else:
                    break
                    
        if buffer.strip():
            parts = buffer.split("### ")
            for part in parts:
                if not part.strip():
                    continue
                section_lines = part.split("\n", 1)
                title = section_lines[0].strip().replace("---", "").strip()
                content = section_lines[1] if len(section_lines) > 1 else ""
                content_clean = re.sub(r'-{10,}', '', content).strip()
                
                if "PROFILE & STRATEGY" in title.upper():
                    continue
                if "GAPS & UNCERTAINTIES" in title.upper():
                    yield {
                        "section": "Gaps and Uncertainties",
                        "content": content_clean,
                        "is_gaps": True
                    }
                else:
                    yield {
                        "section": title,
                        "content": content_clean
                    }
                sections_yielded += 1

    except Exception as e:
        logger.error(f"[RewriterStream] LLM streaming failed: {e}. Using rule-based simplifier fallback.")
        
    # If no sections came through (LLM failed), use rule-based fallback
    if sections_yielded == 0:
        logger.info("[RewriterStream] No sections yielded. Activating rule-based simplifier.")
        try:
            from app.utils.document_simplifier import simplify_document
            # Extract raw content from the planner plan if possible
            raw_content = planner_plan.get("_raw_content", "") if planner_plan else ""
            if not raw_content:
                raw_content = planner_plan.get("summary", "") if planner_plan else ""
            simplified = simplify_document(raw_content or str(planner_plan), profile.role, target_language)
            
            # Parse the simplified text into sections by ### headers
            section_parts = simplified.split("### ")
            for part in section_parts:
                if not part.strip():
                    continue
                section_lines = part.split("\n", 1)
                title = section_lines[0].strip().replace("---", "").strip()
                content = section_lines[1] if len(section_lines) > 1 else ""
                content_clean = re.sub(r'-{10,}', '', content).strip()
                if title and content_clean:
                    yield {
                        "section": title,
                        "content": content_clean,
                        "provider": "rule_based_simplifier"
                    }
        except Exception as e2:
            logger.error(f"[RewriterStream] Rule-based simplifier also failed: {e2}")
            yield {
                "section": "Document Summary",
                "content": "The document adaptation service is temporarily unavailable. Please try again shortly.",
                "provider": "error_fallback"
            }

