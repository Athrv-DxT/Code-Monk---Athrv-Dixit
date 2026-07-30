import os
import asyncio
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger("meridian.tts")

async def _edge_tts_generate(text: str, output_path: str, role: str):
    """
    Asynchronously generates TTS audio using edge-tts.
    Maps profiles to appropriate neural voices for premium UX.
    """
    import edge_tts
    
    # Map role to fitting voice
    voice_map = {
        "child": "en-US-AnaNeural",         # Friendly child-like voice
        "patient": "en-US-JennyNeural",      # Warm, reassuring female voice (anxious/medical)
        "clinician": "en-US-GuyNeural",     # Professional male voice
        "caregiver": "en-US-JennyNeural",   # Patient and warm
        "general_adult": "en-US-ChristopherNeural" # Professional, clear standard
    }
    
    selected_voice = voice_map.get(role, "en-US-ChristopherNeural")
    logger.info(f"Generating voice with edge-tts using voice: {selected_voice}")
    
    communicate = edge_tts.Communicate(text, selected_voice)
    await communicate.save(output_path)

def generate_tts(text: str, run_id: str, role: str) -> Optional[str]:
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
    clean_text = re.sub(r'\*+\s*', '', clean_text) # Remove markdown bolding
    clean_text = clean_text.strip()
    
    # Restrict to first 1500 chars to save bandwidth and keep response snappy
    clean_text = clean_text[:1500]
    
    try:
        # Use edge-tts (recommended fallback which acts as primary due to quality)
        logger.info(f"Generating TTS for run {run_id}, role: {role}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_edge_tts_generate(clean_text, output_path, role))
        finally:
            loop.close()
            
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"Audio generated successfully: {output_path}")
            return output_path
            
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        
    return None
import re
