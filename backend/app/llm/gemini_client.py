import httpx
import json
import logging
from typing import Optional, Dict, Any
from app.config import settings

logger = logging.getLogger("meridian.gemini")

def call_gemini(
    prompt: str, 
    system_instruction: Optional[str] = None, 
    json_mode: bool = False,
    response_schema: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None
) -> str:
    """
    Calls the Google Gemini API (gemini-1.5-flash) using httpx.
    """
    target_key = api_key or settings.GEMINI_API_KEY
    if not target_key:
        raise ValueError("Gemini API key is not configured.")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={target_key}"
    
    headers = {"Content-Type": "application/json"}
    
    contents = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }
    
    # If system instruction is provided
    if system_instruction:
        contents["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }
        
    generation_config = {}
    if json_mode:
        generation_config["responseMimeType"] = "application/json"
        if response_schema:
            generation_config["responseSchema"] = response_schema
            
    if generation_config:
        contents["generationConfig"] = generation_config
        
    try:
        logger.info("Calling Gemini API...")
        with httpx.Client(timeout=8.0) as client:
            response = client.post(url, json=contents, headers=headers)
            response.raise_for_status()
            res_data = response.json()
            
            # Extract text response
            candidates = res_data.get("candidates", [])
            if not candidates:
                raise ValueError(f"No candidates returned by Gemini: {res_data}")
                
            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return text.strip()
            
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        raise e
