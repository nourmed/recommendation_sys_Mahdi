from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os
from pathlib import Path

# --- 1. ROBUST PATH SETUP ---
current_file = Path(__file__).resolve()
backend_dir = current_file.parent.parent
frontend_dir = backend_dir.parent / "plant-advisor-frontend"
env_path = backend_dir / ".env"

# Load Environment variables
load_dotenv(dotenv_path=env_path)

# --- 2. Import API routes ---
from app.api.endpoints import router as api_router 

app = FastAPI(title="Plant Growing Advisor API")

import threading
import logging

def preload_models():
    """Preload the heavy AI models in a background thread."""
    logger = logging.getLogger("plant_advisor")
    logger.info("⏳ Background: Preloading BGE embedding model into RAM...")
    try:
        from sentence_transformers import SentenceTransformer
        # This downloads/loads the model into RAM and keeps it cached
        _ = SentenceTransformer("BAAI/bge-base-en-v1.5")
        logger.info("✅ Background: BGE model preloaded successfully! First request will be instant.")
    except Exception as e:
        logger.error(f"❌ Failed to preload model: {e}")

@app.on_event("startup")
async def startup_event():
    # Start the loading in a background thread so it doesn't block uvicorn startup
    threading.Thread(target=preload_models, daemon=True).start()

# Setup CORS - IMPORTANT: Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],  # Allow React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. Include API Routes ---
app.include_router(api_router, prefix="/api")

# --- 4. DEBUG INFO ---
@app.get("/")
async def root():
    return {
        "message": "Plant Advisor API",
        "status": "running",
        "endpoints": [
            "/api/languages",
            "/api/analyze",
            "/api/analyze-stream/{session_id}",
            "/api/download-pdf/{session_id}",
            "/api/diagnose"
        ]
    }

# --- 5. Create data directory if not exists ---
data_dir = backend_dir / "data" / "results"
data_dir.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)