import httpx
import json
import logging
from typing import Optional, Dict, Any
from app.config import settings

logger = logging.getLogger("meridian.groq")

def call_groq(
    prompt: str, 
    system_instruction: Optional[str] = None, 
    json_mode: bool = False,
    api_key: Optional[str] = None
) -> str:
    """
    Calls Groq API (llama-3.3-70b-versatile) using OpenAI-compatible endpoint.
    """
    target_key = api_key or settings.GROQ_API_KEY
    if not target_key:
        raise ValueError("Groq API key is not configured.")
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {target_key}"
    }
    
    messages = []
    # Truncate prompt to avoid Groq 413 Payload Too Large (context limit ~6000 tokens)
    max_prompt_chars = 24000
    if len(prompt) > max_prompt_chars:
        logger.warning(f"[Groq] Prompt truncated from {len(prompt)} to {max_prompt_chars} chars for payload limit.")
        prompt = prompt[:max_prompt_chars] + "\n\n[Content truncated for processing]"
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

def call_groq_stream(
    prompt: str, 
    system_instruction: Optional[str] = None, 
    api_key: Optional[str] = None
):
    """
    Calls Groq API (llama-3.3-70b-versatile) with stream=True and yields token chunks.
    """
    target_key = api_key or settings.GROQ_API_KEY
    if not target_key:
        raise ValueError("Groq API key is not configured.")
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {target_key}"
    }
    
    messages = []
    # Truncate prompt to avoid Groq 413 Payload Too Large (context limit ~6000 tokens)
    max_prompt_chars = 24000
    if len(prompt) > max_prompt_chars:
        logger.warning(f"[Groq Stream] Prompt truncated from {len(prompt)} to {max_prompt_chars} chars for payload limit.")
        prompt = prompt[:max_prompt_chars] + "\n\n[Content truncated for processing]"
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.1,
        "stream": True
    }
    
    try:
        logger.info("Calling Groq API (stream)...")
        with httpx.Client(timeout=30.0) as client:
            with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            chunk = data["choices"][0]["delta"].get("content", "")
                            if chunk:
                                yield chunk
                        except Exception:
                            pass
    except Exception as e:
        logger.error(f"Groq API stream call failed: {e}")
        raise e
