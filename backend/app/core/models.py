from pydantic import BaseModel, Field
from typing import List, Optional, Tuple, Dict, Any

class AudienceProfile(BaseModel):
    role: str = Field(..., description="Role: patient | parent_guardian | child | caregiver | clinician | student | employee | general_adult | other")
    domain_familiarity: str = Field("novice", description="Familiarity: novice | intermediate | expert")
    cognitive_access_needs: str = Field("standard", description="Access needs: standard | low_cognitive_load | dyslexia_friendly | anxiety_aware | child_appropriate | other")
    preferred_language: str = Field("en", description="ISO language code or full name")
    modality: str = Field("text", description="Preferred output: text | audio_optimized | highly_structured | sign_language_friendly_script")
    age_band: Optional[str] = Field("adult", description="Age band: child | adolescent | adult | older_adult")

class MeaningNode(BaseModel):
    id: str = Field(..., description="Unique identifier for the node, e.g. Node_1, Obligation_2")
    type: str = Field(..., description="Node type: Claim | Obligation | Right | Condition | Action | Deadline | Gap")
    text: str = Field(..., description="Faithful textual extraction of the claim or obligation from source")
    source_span: str = Field(..., description="The exact substring in the source document")
    char_offsets: Optional[Tuple[int, int]] = Field(None, description="Start and end character indices in source document")

class MeaningRelationship(BaseModel):
    source_id: str = Field(..., description="Source node ID")
    target_id: str = Field(..., description="Target node ID")
    type: str = Field(..., description="Relationship type: CONDITIONED_ON | HAS_DEADLINE | APPLIES_TO_ROLE | DERIVED_FROM_SPAN | CONFLICTS_WITH")

class StructuredMeaningRepresentation(BaseModel):
    nodes: List[MeaningNode] = Field(default_factory=list)
    relationships: List[MeaningRelationship] = Field(default_factory=list)

class AdaptationStrategy(BaseModel):
    information_density: str = Field(..., description="low | medium | high")
    vocabulary_level: str = Field(..., description="simple | intermediate | technical")
    structure_format: str = Field(..., description="paragraph | checklist | step-by-step | obligations_matrix | qa")
    tone: str = Field(..., description="directive | reassuring | practical | precise")
    safety_constraints: List[str] = Field(default_factory=list)
    foreground_aspects: List[str] = Field(default_factory=list)
    background_aspects: List[str] = Field(default_factory=list)
    gap_reporting_intensity: str = Field(..., description="low | medium | high")
