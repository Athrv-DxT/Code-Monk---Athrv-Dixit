import httpx
import json
import logging
from typing import Optional, Dict, Any
from app.config import settings

logger = logging.getLogger("intellix.gemini")

def call_gemini(
    prompt: str, 
    system_instruction: Optional[str] = None, 
    json_mode: bool = False,
    response_schema: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None
) -> str:
    """
    Calls the Google Gemini API (gemini-2.0-flash) using httpx.
    """
    target_key = api_key or settings.GEMINI_API_KEY
    if not target_key:
        raise ValueError("Gemini API key is not configured.")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={target_key}"
    
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

def call_gemini_stream(
    prompt: str,
    system_instruction: Optional[str] = None,
    api_key: Optional[str] = None
):
    """
    Calls Google Gemini API using streamGenerateContent and yields token chunks.
    """
    target_key = api_key or settings.GEMINI_API_KEY
    if not target_key:
        raise ValueError("Gemini API key is not configured.")
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:streamGenerateContent?key={target_key}"
    headers = {"Content-Type": "application/json"}
    
    contents = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }
    
    if system_instruction:
        contents["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }
        
    try:
        logger.info("Calling Gemini API (stream)...")
        with httpx.Client(timeout=30.0) as client:
            with client.stream("POST", url, json=contents, headers=headers) as response:
                response.raise_for_status()
                buffer = ""
                for chunk in response.iter_text():
                    buffer += chunk
                    while True:
                        buffer = buffer.strip()
                        if not buffer:
                            break
                        
                        if buffer.startswith("["):
                            buffer = buffer[1:].strip()
                        if buffer.startswith(","):
                            buffer = buffer[1:].strip()
                            
                        # Find matching closing bracket for first JSON object
                        bracket_count = 0
                        in_string = False
                        escape = False
                        end_idx = -1
                        
                        for idx, char in enumerate(buffer):
                            if char == '"' and not escape:
                                in_string = not in_string
                            elif char == '\\' and not escape:
                                escape = True
                                continue
                            elif not in_string:
                                if char == '{':
                                    bracket_count += 1
                                elif char == '}':
                                    bracket_count -= 1
                                    if bracket_count == 0:
                                        end_idx = idx
                                        break
                            escape = False
                            
                        if end_idx != -1:
                            obj_str = buffer[:end_idx+1]
                            buffer = buffer[end_idx+1:].strip()
                            try:
                                data = json.loads(obj_str)
                                text = data["candidates"][0]["content"]["parts"][0].get("text", "")
                                if text:
                                    yield text
                            except Exception:
                                pass
                        else:
                            break
    except Exception as e:
        logger.error(f"Gemini API stream call failed: {e}")
        raise e
