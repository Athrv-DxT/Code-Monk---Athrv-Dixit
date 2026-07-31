import logging
from app.core.models import AudienceProfile, AdaptationStrategy
from app.utils.checkpoints import CheckpointLogger

logger = logging.getLogger("intellix.agents.strategy_engine")

def resolve_strategy(
    domain: str, 
    profile: AudienceProfile, 
    run_id: str, 
    checkpoint_logger: CheckpointLogger
) -> AdaptationStrategy:
    """
    Computes adaptation controls (information density, vocabulary level, structure format, etc.)
    as a function of both Domain and Audience Profile.
    """
    checkpoint_logger.start_stage("AUDIENCE_PROFILE_RESOLVED", input_summary=profile.model_dump_json())
    
    # Defaults
    density = "medium"
    vocab = "intermediate"
    structure = "paragraph"
    tone = "practical"
    safety = ["Preserve original obligations without adding new rules."]
    foreground = ["Main requirements", "Direct actions needed"]
    background = ["Boilerplate legal definitions", "Historical contexts"]
    gap_intensity = "medium"

    # Domain specific constraints
    if domain == "medical":
        tone = "reassuring"
        safety.append("Preserve all clinical findings, warnings, and qualifiers.")
        safety.append("Never invent medical diagnoses or reassurance not in the source.")
        gap_intensity = "high"
        
        # Audience overrides
        if profile.role in ["patient", "caregiver", "child"]:
            vocab = "simple"
            density = "low"
            structure = "qa"
            foreground = ["Dosage and timing", "Urgent warning signs", "Required care steps"]
        elif profile.role == "clinician":
            vocab = "technical"
            density = "high"
            structure = "obligations_matrix"
            tone = "precise"
            
    elif domain == "legal":
        tone = "precise"
        safety.append("Never soften 'shall' or 'must' obligations into 'should' or optional actions.")
        safety.append("Never generate legal advice or invent liabilities.")
        gap_intensity = "high"
        
        if profile.domain_familiarity == "novice":
            vocab = "intermediate"
            structure = "obligations_matrix"
            foreground = ["What you must do", "What happens if you miss a deadline", "Your rights"]
        elif profile.cognitive_access_needs == "low_cognitive_load":
            vocab = "simple"
            density = "low"
            structure = "checklist"
            tone = "directive"
            
    elif domain == "administrative":
        structure = "checklist"
        foreground = ["Action items", "Submission deadlines", "Contact details"]
        
        if profile.cognitive_access_needs == "dyslexia_friendly":
            vocab = "simple"
            density = "low"
            structure = "checklist"
            tone = "practical"
            
    # Universal Audience adjustments
    if profile.cognitive_access_needs == "low_cognitive_load":
        density = "low"
        vocab = "simple"
        structure = "step-by-step"
    elif profile.cognitive_access_needs == "anxiety_aware":
        tone = "reassuring"
        density = "low"
        structure = "qa"
        
    if profile.modality == "audio_optimized":
        density = "low"
        structure = "paragraph"
        foreground.append("Phonetically clear instructions and summaries")
        
    strategy = AdaptationStrategy(
        information_density=density,
        vocabulary_level=vocab,
        structure_format=structure,
        tone=tone,
        safety_constraints=safety,
        foreground_aspects=foreground,
        background_aspects=background,
        gap_reporting_intensity=gap_intensity
    )
    
    checkpoint_logger.complete_stage(
        "STRATEGY_SELECTED", 
        output_summary=f"Vocab={vocab}, Structure={structure}, Tone={tone}",
        model="Deterministic Strategy Engine"
    )
    return strategy
