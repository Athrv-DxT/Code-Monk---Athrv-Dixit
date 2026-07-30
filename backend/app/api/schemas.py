from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class AdaptOptions(BaseModel):
    generate_multiple_profiles: bool = Field(False, description="Whether to ignore single audience_profile and generate multiple versions")
    profiles: Optional[List[str]] = Field(None, description="List of profile presets to generate if generate_multiple_profiles is true")
    include_fidelity_note: bool = Field(True, description="Whether to include the verifier coverage note")
    language: str = Field("en", description="Target ISO language code")
    enable_external_lookup: bool = Field(False, description="Gates external Tavily lookups")
    tts_output: bool = Field(False, description="If true, generates speech audio path using TTS engine")

class FetchUrlRequest(BaseModel):
    url: str = Field(..., description="The HTTP URL to fetch document text from")

class AdaptRequest(BaseModel):
    content: str = Field(..., description="The raw source document text to adapt")
    audience_profile: Optional[Dict[str, Any]] = Field(None, description="Target Audience Profile details (role, familiarity, needs) or empty")
    voice_narration: Optional[str] = Field(None, description="Audio transcription of user narrating their role/needs, e.g., 'I am an anxious caregiver.'")
    options: Optional[AdaptOptions] = Field(default_factory=AdaptOptions)

class AdaptedVersion(BaseModel):
    profile: str
    adapted_content: str
    strategy_summary: str
    gaps: List[str]
    fidelity_note: str
    audio_url: Optional[str] = None
    explanations: Optional[str] = None

class ContentUnderstandingSummary(BaseModel):
    domain: str
    document_type: str
    risk_level: str
    sensitivity_signals: List[str]
    is_incomplete: bool
    is_ambiguous: bool
    gaps_detected: List[str]

class MeaningSummary(BaseModel):
    node_count: int
    relationship_count: int

class AdaptResponse(BaseModel):
    run_id: str
    domain: str
    document_type: str
    risk_level: str
    versions: List[AdaptedVersion]
    content_understanding: ContentUnderstandingSummary
    meaning_summary: MeaningSummary
    graph_run_node_id: str
