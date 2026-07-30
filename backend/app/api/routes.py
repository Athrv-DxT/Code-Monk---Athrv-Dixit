import os
import shutil
import logging
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from app.api.schemas import AdaptRequest, AdaptResponse, FetchUrlRequest
from app.agents.orchestrator import run_pipeline
from app.graph.neo4j_client import get_driver, get_meaning_representation
from app.voice.stt_whisper import transcribe_audio
from app.config import settings
import httpx
import re

logger = logging.getLogger("meridian.api")
router = APIRouter(prefix="/api/v1")

@router.post("/adapt", response_model=AdaptResponse)
def adapt_document(request: AdaptRequest):
    """
    Core pipeline endpoint. Takes a document, extracts semantic representation,
    stores in Neo4j, simplifies/adapts to audience and verifies fidelity.
    """
    try:
        logger.info("Received request on /adapt")
        result = run_pipeline(
            content=request.content,
            audience_profile_dict=request.audience_profile or {},
            options=request.options.model_dump() if request.options else {},
            voice_narration=request.voice_narration
        )
        return result
    except Exception as e:
        logger.error(f"Error executing adaptation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
def health_check():
    """
    Checks backend health and connection status to Neo4j.
    """
    neo4j_driver = get_driver()
    neo4j_status = "connected" if neo4j_driver else "offline"
    return {
        "status": "ok",
        "neo4j": neo4j_status,
        "env": settings.ENV
    }

@router.post("/transcribe")
async def transcribe_audio_endpoint(file: UploadFile = File(...)):
    """
    Upload an audio file (e.g. WAV/MP3) and transcribe it using Whisper.
    """
    logger.info(f"Received audio transcription request: {file.filename}")
    
    # Check file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".wav", ".mp3", ".m4a", ".ogg", ".webm"]:
        raise HTTPException(status_code=400, detail="Unsupported audio file format.")
        
    try:
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_audio:
            shutil.copyfileobj(file.file, temp_audio)
            temp_path = temp_audio.name
            
        # Transcribe
        result = transcribe_audio(temp_path)
        
        # Clean up
        os.remove(temp_path)
        
        return result
    except Exception as e:
        logger.error(f"Error during audio transcription: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/runs/{run_id}/logs", response_class=PlainTextResponse)
def get_run_logs(run_id: str):
    """
    Returns the markdown log for a specific run.
    """
    # Sanitize run_id to prevent path traversal
    clean_id = "".join(c for c in run_id if c.isalnum() or c == '_')
    log_path = os.path.join(settings.LOG_DIR, f"agent_run_{clean_id}.md")
    
    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail="Run log file not found.")
        
    with open(log_path, "r", encoding="utf-8") as f:
        return f.read()

@router.get("/runs/{run_id}/graph")
def get_run_graph(run_id: str):
    """
    Retrieves the extracted meaning graph from Neo4j for visualization.
    """
    clean_id = "".join(c for c in run_id if c.isalnum() or c == '_')
    representation = get_meaning_representation(clean_id)
    
    # Format graph nodes and links for vis.js / D3 representation
    nodes = []
    for node in representation.nodes:
        nodes.append({
            "id": node.id,
            "label": f"{node.type}: {node.text[:40]}...",
            "title": node.text,
            "group": node.type
        })
        
    edges = []
    for rel in representation.relationships:
        edges.append({
            "from": rel.source_id,
            "to": rel.target_id,
            "label": rel.type
        })
        
    return {"nodes": nodes, "edges": edges}

@router.get("/audio/{run_id}/{role}.mp3")
def get_audio_file(run_id: str, role: str):
    """
    Serves generated TTS MP3 file.
    """
    clean_id = "".join(c for c in run_id if c.isalnum() or c == '_')
    clean_role = "".join(c for c in role if c.isalnum() or c == '_')
    audio_path = os.path.join(settings.LOG_DIR, "audio", clean_id, f"{clean_role}.mp3")
    
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found.")
        
    return FileResponse(audio_path, media_type="audio/mpeg", filename=f"{clean_role}.mp3")

def clean_html(html: str) -> str:
    # Remove script and style elements
    html = re.sub(r'<(script|style).*?>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Remove all HTML tags
    text = re.sub(r'<.*?>', '', html)
    # Replace standard HTML entities
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    # Remove excessive blank lines
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()

@router.post("/fetch-url")
def fetch_url(request: FetchUrlRequest):
    """
    Fetches HTML content from a URL, strips tags, and returns the cleaned text.
    """
    try:
        logger.info(f"Fetching URL content from: {request.url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
            res = client.get(request.url)
            res.raise_for_status()
            
        content_type = res.headers.get("content-type", "").lower()
        if "html" in content_type or res.text.strip().startswith("<"):
            cleaned_text = clean_html(res.text)
        else:
            cleaned_text = res.text
            
        return {"text": cleaned_text}
    except Exception as e:
        logger.error(f"Failed to fetch content from URL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch URL: {str(e)}")

@router.post("/upload-file")
async def upload_file(file: UploadFile = File(...)):
    """
    Accepts text or HTML files, extracts, and returns the cleaned text content.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".html", ".htm", ".txt"]:
        raise HTTPException(status_code=400, detail="Only plain text (.txt) and HTML (.html) files are currently supported.")
        
    try:
        logger.info(f"Processing uploaded file: {file.filename}")
        content_bytes = await file.read()
        content_text = content_bytes.decode("utf-8", errors="ignore")
        
        if ext in [".html", ".htm"]:
            cleaned_text = clean_html(content_text)
        else:
            cleaned_text = content_text
            
        return {"text": cleaned_text}
    except Exception as e:
        logger.error(f"Error processing uploaded file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")
