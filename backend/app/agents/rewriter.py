import logging
import re
from typing import Dict, Any, List
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
    checkpoint_logger: CheckpointLogger
) -> Dict[str, Any]:
    """
    Runs the Rewrite phase. Fetches glossary/external definitions (Hybrid Search/Tavily),
    builds the rewriter prompt, and adapts the document content.
    """
    checkpoint_logger.start_stage("REWRITE_STARTED", input_summary=f"Role: {profile.role}")
    
    # 1. RETRIEVAL STEP: Local Hybrid Search
    checkpoint_logger.log_event("RETRIEVAL_STARTED", "Starting hybrid search for document terminology grounding.")
    grounding_explanations = []
    
    # Simple extraction of key words to query glossary (limit to top 4 distinct nodes for fast retrieval)
    matched_glossary_terms = set()
    distinct_nodes = [n for n in representation.nodes if len(n.text.strip()) > 10][:4]
    for node in distinct_nodes:
        # Search for node's text in hybrid index
        hits = hybrid_search(node.text, top_k=1)
        for hit in hits:
            # Prevent duplicates
            term_key = hit["term"].lower()
            if term_key not in matched_glossary_terms:
                matched_glossary_terms.add(term_key)
                grounding_explanations.append(f"- **{hit['term']}**: {hit['definition']} [Source: Local Glossary]")
                
    # 2. EXTERNAL FALLBACK STEP (Tavily)
    # If no local definitions matched, and external lookup is enabled, seek definitions externally
    if len(grounding_explanations) == 0 and enable_external_lookup:
        checkpoint_logger.log_event("RETRIEVAL_STARTED", "Local glossary empty. Invoking Tavily external fallback search.")
        # Search for domain terms
        tavily_query = f"definition of key terms in {profile.role} context"
        hits = search_tavily(tavily_query, max_results=2)
        for hit in hits:
            grounding_explanations.append(
                f"- **{hit.get('title', 'External Resource')}**: {hit.get('content')} [Source: {hit.get('url')}]"
            )
            
    checkpoint_logger.log_event("RETRIEVAL_COMPLETED", f"Grounding context retrieved: {len(grounding_explanations)} explanations.")
    
    # Combine explanations
    grounding_context_str = "\n".join(grounding_explanations) if grounding_explanations else "None available."
    
    # 3. CONSTRUCT PROMPT
    # Serialize meaning nodes for prompt
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
        # We split the sections based on the markdown formatting expected
        adapted_content = ""
        gaps_list = []
        
        content_match = re.search(r'--- ADAPTED CONTENT ---\s*(.*?)\s*(?=--- PROFILE|$)', response_text, re.DOTALL | re.IGNORECASE)
        gaps_match = re.search(r'--- GAPS & UNCERTAINTIES ---\s*(.*?)\s*$', response_text, re.DOTALL | re.IGNORECASE)
        
        if content_match:
            adapted_content = content_match.group(1).strip()
        else:
            # Fallback if parser fails
            adapted_content = response_text.split("--- PROFILE & STRATEGY USED ---")[0].strip()
            
        gaps_str = ""
        if gaps_match:
            gaps_str = gaps_match.group(1).strip()
            # Clean up gaps string to list
            gaps_list = [g.strip("- ").strip() for g in gaps_str.split("\n") if g.strip()]
            if gaps_list and "None identified." in gaps_list[0]:
                gaps_list = []
        else:
            # Fallback check
            gaps_list = []
            
        # Separate the explanations block if it was mixed (even though we asked the model to keep it inside adapted content)
        # We can extract the Explanations & Definitions section and save it in a clean property
        explanations_text = ""
        explanation_section_match = re.search(r'(Explanations & Definitions|EXPLANATIONS & DEFINITIONS).*', adapted_content, re.DOTALL | re.IGNORECASE)
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
        return {
            "adapted_content": content,  # Return original as fallback
            "gaps": ["Error running rewriter. Outputting original text."],
            "explanations_retrieved": "",
            "strategy_summary": "Fallback (Original Text)"
        }
