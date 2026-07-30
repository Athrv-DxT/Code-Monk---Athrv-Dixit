import httpx
import json
import logging
from typing import Optional, Dict, Any
from app.config import settings

logger = logging.getLogger("meridian.groq")

def call_groq(
    prompt: str, 
    system_instruction: Optional[str] = None, 
    json_mode: bool = False
) -> str:
    """
    Calls Groq API (llama-3.3-70b-versatile) using OpenAI-compatible endpoint.
    """
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set.")
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.GROQ_API_KEY}"
    }
    
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.1
    }
    
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
        
    try:
        logger.info("Calling Groq API (fallback)...")
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            res_data = response.json()
            
            choices = res_data.get("choices", [])
            if not choices:
                raise ValueError(f"No choices returned by Groq: {res_data}")
                
            text = choices[0].get("message", {}).get("content", "")
            return text.strip()
            
    except Exception as e:
        logger.error(f"Groq API call failed: {e}")
        raise e
