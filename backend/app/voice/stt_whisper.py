import os
import logging
from typing import Optional

logger = logging.getLogger("meridian.stt")
_model = None

from app.config import settings

def get_whisper_model():
    global _model
    if settings.DISABLE_LOCAL_MODELS:
        logger.info("Local models are disabled via configuration.")
        return None
        
    if _model is None:
        try:
            from faster_whisper import WhisperModel
            logger.info("Initializing faster-whisper 'small' model on CPU (int8)...")
            # Loads the model on demand, caching it locally
            _model = WhisperModel("small", device="cpu", compute_type="int8")
            logger.info("Whisper model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Whisper STT: {e}")
            _model = None
    return _model

def transcribe_audio(file_path: str) -> str:
    """
    Transcribes audio file to text using faster-whisper.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")
        
    model = get_whisper_model()
    if not model:
        if settings.DISABLE_LOCAL_MODELS:
            return "[STT Mock: Hello. I am writing to submit a consent form for access to my apartment on August 15.]"
        return "[STT Engine offline or libraries missing. Could not transcribe audio.]"
        
    try:
        logger.info(f"Transcribing audio file: {file_path}")
        segments, info = model.transcribe(file_path, beam_size=5)
        
        # Combine text segments
        full_text = " ".join([segment.text for segment in segments])
        logger.info("Transcription completed successfully.")
        return full_text.strip()
        
    except Exception as e:
        logger.error(f"Speech transcription failed: {e}")
        return f"[Transcription error: {str(e)}]"
