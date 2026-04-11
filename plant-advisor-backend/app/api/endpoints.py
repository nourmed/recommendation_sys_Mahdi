from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List
from fastapi.responses import FileResponse, StreamingResponse
from uuid import uuid4
from typing import Dict
import os
import json
import asyncio

from app.schemas.models import AnalyzeRequest, AnalysisResponse, AnalysisResult
from app.services.analyzer import analyzer_service

try:
    from app.services.llm_client import call_gpt
except ImportError:
    call_gpt = None

router = APIRouter()

# In-Memory Session Storage
sessions: Dict[str, dict] = {}
session_locks: Dict[str, asyncio.Lock] = {}

@router.get("/languages")
def get_languages():
    from app.services.language_manager import LanguageManager
    lang_manager = LanguageManager()
    available = lang_manager.get_available_languages()
    
    return {
        "languages": [
            {"code": code, "name": name} 
            for code, name in available.items()
        ]
    }

@router.get("/form-labels/{language}")
def get_form_labels(language: str = "en"):
    """Get ALL form labels and questions in the specified language."""
    from app.services.language_manager import LanguageManager
    lang_manager = LanguageManager()
    lang_manager.set_language(language)
    
    # Return ALL translations for the selected language
    # This gives the frontend access to every translated string
    all_translations = lang_manager.translations.get(language, lang_manager.translations.get("en", {}))
    
    return {"labels": all_translations}

class TranslateRequest(BaseModel):
    texts: List[str]
    target_lang: str

@router.post("/translate-locations")
def translate_locations(request: TranslateRequest):
    """Translate a list of location strings to the target language via GoogleTranslator."""
    if request.target_lang == 'en' or not request.texts:
        return {"translated": request.texts}
        
    try:
        from deep_translator import GoogleTranslator
        # For simplicity, convert our language codes (e.g. zh) if needed, but deep_translator handles standard ISOs well.
        # Fallback to returning original on failure.
        translator = GoogleTranslator(source='en', target=request.target_lang)
        
        DELIMITER = " --- "
        chunks = []
        current_chunk = []
        current_len = 0
        
        for text in request.texts:
            added_len = len(text) + len(DELIMITER)
            if current_len + added_len > 4000:
                chunks.append(current_chunk)
                current_chunk = [text]
                current_len = added_len
            else:
                current_chunk.append(text)
                current_len += added_len
        if current_chunk:
            chunks.append(current_chunk)
            
        translated_results = []
        for chunk in chunks:
            text_to_translate = DELIMITER.join(chunk)
            translated_text = translator.translate(text_to_translate)
            
            # Reconstruct the list cleanly
            parts = [p.strip() for p in translated_text.split("---")]
            
            # Replace missing parts with original if delimiter count broke slightly
            if len(parts) < len(chunk):
                parts.extend(chunk[len(parts):])
            
            translated_results.extend(parts[:len(chunk)])
            
        return {"translated": translated_results}
    except Exception as e:
        print(f"Translation Error: {e}")
        return {"translated": request.texts}

@router.post("/analyze", response_model=AnalysisResponse)
async def start_analysis(request: AnalyzeRequest):
    """
    Start analysis and return session ID immediately.
    The actual analysis will stream via /analyze-stream/{session_id}
    """
    plant_name = request.plant_name.strip()
    
    # Pre-validate plant name if call_gpt is available & not bypassing
    if call_gpt and plant_name and not request.ignore_typo:
        try:
            prompt = (
                f"The user typed: '{plant_name}'.\n"
                f"Rules:\n"
                f"1. If it is a valid plant name in ANY language → VALID: yes\n"
                f"2. If it looks like a misspelling/abbreviation of a plant (e.g. 'appl'→Apple, 'orang'→Orange, 'tomatto'→Tomato, 'banan'→Banana) → VALID: typo\n"
                f"3. Only if it has NO resemblance to any plant at all (e.g. 'xkzqw', 'hello', 'car') → VALID: no\n"
                f"When in doubt, prefer 'typo' over 'no'. Always provide the corrected English name.\n"
                f"Answer EXACTLY:\n"
                f"VALID: yes / typo / no\n"
                f"ENGLISH: <correct English plant name, or Unknown if VALID is no>"
            )
            result = call_gpt(
                prompt,
                system_message="You are a botanist. Be generous: treat partial words and near-typos as 'typo', not 'no'.",
                temperature=0.0,
                max_tokens=30
            )
            if result:
                lines = result.strip().lower().splitlines()
                valid_status = "yes"
                english_name = plant_name.title()
                for l in lines:
                    if l.startswith('valid:'):
                        valid_status = l.replace('valid:', '').strip()
                for l in lines:
                    if l.startswith('english:'):
                        english_name = l.replace('english:', '').strip().title()

                if valid_status in ("no", "typo") and english_name.lower() != "unknown":
                    # Both 'no' and 'typo' → show inline suggestion (never block with alert)
                    return AnalysisResponse(
                        session_id="",
                        status="typo",
                        message="Did you mean this plant?",
                        suggested_name=english_name
                    )
                elif valid_status == "no" and english_name.lower() == "unknown":
                    # Completely unrecognisable — return typo with None so frontend shows generic message
                    return AnalysisResponse(
                        session_id="",
                        status="invalid",
                        message="Not a plant",
                        suggested_name=None
                    )

                # Valid — use the corrected English name going forward
                request.plant_name = english_name
                plant_name = english_name
        except Exception:
            pass  # On any failure just proceed normally

    session_id = str(uuid4())
    
    # Store request data for streaming endpoint
    sessions[session_id] = {
        "status": "ready",
        "request_data": request.dict(),
        "plant_name": plant_name  # Direct access to plant_name
    }
    
    return AnalysisResponse(
        session_id=session_id,
        status="ready",
        message="Ready to stream analysis"
    )

@router.get("/analyze-stream/{session_id}")
async def stream_analysis(session_id: str):
    """
    Stream the AI analysis in real-time
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get or create lock for this session
    if session_id not in session_locks:
        session_locks[session_id] = asyncio.Lock()
    
    lock = session_locks[session_id]
    
    # If already running, return error or wait
    if lock.locked():
        raise HTTPException(status_code=409, detail="Analysis already in progress for this session")
    
    async with lock:
        session_data = sessions[session_id]
        request_data = session_data["request_data"]
        
        async def generate():
            try:
                # Send initial message
                yield f"data: {json.dumps({'type': 'start', 'message': 'Starting analysis...'})}\n\n"
                
                # Run the actual analysis with streaming
                full_response = ""
                async for chunk in analyzer_service.run_analysis_stream(request_data, session_id):
                    full_response += chunk
                    # Send each chunk as it arrives
                    yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                    await asyncio.sleep(0.01)  # Small delay for smooth streaming
                
                # Store the complete response
                sessions[session_id]["full_response"] = full_response
                sessions[session_id]["status"] = "completed"
                
                # Send completion message
                yield f"data: {json.dumps({'type': 'complete', 'message': 'Analysis completed'})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
        return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

@router.get("/download-report/{session_id}")
async def download_pdf(session_id: str):
    """
    Generate and download PDF report
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = sessions[session_id]
    
    # Save the markdown response to a file
    pdf_path = os.path.join("data", "results", f"{session_data.get('plant_name', 'plant').replace(' ', '_')}_report.md")
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    with open(pdf_path, "w", encoding="utf-8") as f:
        f.write(session_data.get("full_response", "No analysis available"))
    
    return FileResponse(
        path=pdf_path,
        filename=f"{session_data.get('plant_name', 'plant')}_report.md",
        media_type="text/markdown"
    )

@router.get("/results/{session_id}", response_model=AnalysisResult)
def get_results(session_id: str):
    """
    Get analysis status (kept for compatibility)
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return AnalysisResult(
        session_id=session_id,
        status=sessions[session_id].get("status", "unknown"),
        plant_name=sessions[session_id].get("plant_name", None)
    )

# Image diagnosis endpoints
@router.post("/diagnose")
async def diagnose_plant(file: UploadFile = File(...)):
    """
    Plant disease diagnosis endpoint
    Upload an image for disease analysis using YOLO (leaf detection) and ViT (disease classification).
    """
    if not file:
        raise HTTPException(status_code=400, detail="No image provided")
    
    # Read file content
    contents = await file.read()
    file_size = len(contents)
    
    # Run the ML pipeline
    from app.services.ml_diagnostics import ml_service
    diagnosis_result = ml_service.diagnose_image(contents)
    
    if diagnosis_result["status"] == "error":
        raise HTTPException(status_code=500, detail=diagnosis_result["message"])
        
    return {
        "status": "success",
        "message": "Image diagnosed successfully.",
        "filename": file.filename,
        "image_size": file_size,
        "diagnosis": diagnosis_result["diagnosis"]
    }
