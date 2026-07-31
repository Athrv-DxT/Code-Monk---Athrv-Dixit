import os
import re
import asyncio
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger("meridian.tts")

async def _edge_tts_generate(text: str, output_path: str, role: str, language: Optional[str] = "en"):
    """
    Asynchronously generates TTS audio using edge-tts.
    Maps profiles to appropriate neural voices for premium UX.
    """
    import edge_tts
    
    lang = (language or "en").lower().strip()
    
    voices = {
        "en": {
            "child": "en-US-AnaNeural",
            "patient": "en-US-JennyNeural",
            "clinician": "en-US-GuyNeural",
            "caregiver": "en-US-JennyNeural",
            "general_adult": "en-US-ChristopherNeural"
        },
        "hi": {
            "child": "hi-IN-SwaraNeural",
            "patient": "hi-IN-SwaraNeural",
            "clinician": "hi-IN-MadhurNeural",
            "caregiver": "hi-IN-SwaraNeural",
            "general_adult": "hi-IN-MadhurNeural"
        },
        "bn": {
            "general_adult": "bn-IN-BashkarNeural",
            "patient": "bn-IN-TanishaNeural",
            "child": "bn-IN-TanishaNeural"
        },
        "mr": {
            "general_adult": "mr-IN-ManoharNeural",
            "patient": "mr-IN-AarohiNeural",
            "child": "mr-IN-AarohiNeural"
        },
        "te": {
            "general_adult": "te-IN-MohanNeural",
            "patient": "te-IN-ShrutiNeural",
            "child": "te-IN-ShrutiNeural"
        },
        "ta": {
            "general_adult": "ta-IN-ValluvarNeural",
            "patient": "ta-IN-PallaviNeural",
            "child": "ta-IN-PallaviNeural"
        },
        "gu": {
            "general_adult": "gu-IN-NiranjanNeural",
            "patient": "gu-IN-DhwaniNeural",
            "child": "gu-IN-DhwaniNeural"
        },
        "kn": {
            "general_adult": "kn-IN-GaganNeural",
            "patient": "kn-IN-SapnaNeural",
            "child": "kn-IN-SapnaNeural"
        },
        "ml": {
            "general_adult": "ml-IN-MidhunNeural",
            "patient": "ml-IN-SobhanaNeural",
            "child": "ml-IN-SobhanaNeural"
        },
        "pa": {
            "general_adult": "pa-IN-HarjitNeural",
            "patient": "pa-IN-OjasNeural",
            "child": "pa-IN-OjasNeural"
        },
        "or": {
            "general_adult": "or-IN-SubhasiniNeural",
            "patient": "or-IN-SubhasiniNeural",
            "child": "or-IN-SubhasiniNeural"
        },
        "ur": {
            "general_adult": "ur-IN-SalmanNeural",
            "patient": "ur-IN-GulNeural",
            "child": "ur-IN-GulNeural"
        },
        "es": {
            "child": "es-ES-ElviraNeural",
            "patient": "es-ES-ElviraNeural",
            "clinician": "es-ES-AlvaroNeural",
            "caregiver": "es-ES-ElviraNeural",
            "general_adult": "es-ES-AlvaroNeural"
        },
        "fr": {
            "child": "fr-FR-DeniseNeural",
            "patient": "fr-FR-DeniseNeural",
            "clinician": "fr-FR-HenriNeural",
            "caregiver": "fr-FR-DeniseNeural",
            "general_adult": "fr-FR-HenriNeural"
        }
    }
    
    lang_voices = voices.get(lang, voices["en"])
    selected_voice = lang_voices.get(role, list(lang_voices.values())[0])
    logger.info(f"Generating voice with edge-tts using voice {selected_voice} for language {lang}")
    
    communicate = edge_tts.Communicate(text, selected_voice)
    await communicate.save(output_path)


async def generate_tts(text: str, run_id: str, role: str, language: Optional[str] = "en") -> Optional[str]:
    """
    Generates TTS audio file for the adapted text.
    First tries edge-tts (as the high-quality, zero-dependency default).
    Saves file in log directory under audio/ folder.
    """
    audio_dir = os.path.join(settings.LOG_DIR, "audio", run_id)
    os.makedirs(audio_dir, exist_ok=True)
    output_path = os.path.join(audio_dir, f"{role}.mp3")
    
    # Clean text to remove raw markdown headers/tags that sound weird in TTS
    clean_text = text.replace("--- ADAPTED CONTENT ---", "")
    clean_text = re.sub(r'#+\s*', '', clean_text)  # Remove markdown headers
    clean_text = re.sub(r'\*+\s*', '', clean_text)  # Remove markdown bolding
    clean_text = clean_text.strip()
    
    # Restrict to first 1500 chars to save bandwidth and keep response snappy
    clean_text = clean_text[:1500]
    
    try:
        logger.info(f"Generating TTS for run {run_id}, role: {role}, language: {language}")
        await _edge_tts_generate(clean_text, output_path, role, language)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"Audio generated successfully: {output_path}")
            return output_path
            
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        
    return None
