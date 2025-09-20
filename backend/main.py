#!/usr/bin/env python3
"""
Voice Recognition Backend Server for Raspberry Pi Zero W
FastAPI application with WebSocket audio streaming, speaker recognition, and device management.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from src.database import engine, SessionLocal, Base
from src.auth import router as auth_router
from src.audio import router as audio_router
from src.devices import router as devices_router
from src.speakers import router as speakers_router
from src.recognition import router as recognition_router
from src.system import router as system_router
from src.websocket_routes import websocket_router, start_demo_task, stop_demo_task
from src.audio_processor import AudioProcessor
from src.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
audio_processor = AudioProcessor()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Voice Recognition Backend Server")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Initialize audio processor
    await audio_processor.initialize()
    
    # Start demo background task
    start_demo_task()
    
    logger.info("Server initialized successfully")
    yield
    
    # Cleanup
    logger.info("Shutting down server")
    await audio_processor.cleanup()
    stop_demo_task()

# Create FastAPI app
app = FastAPI(
    title="Voice Recognition Backend",
    description="Raspberry Pi Zero W Speaker Recognition System",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["authentication"])
app.include_router(audio_router, prefix="/audio", tags=["audio"])
app.include_router(devices_router, prefix="/devices", tags=["devices"])
app.include_router(speakers_router, prefix="/speakers", tags=["speakers"])
app.include_router(recognition_router, prefix="/recognition", tags=["recognition"])
app.include_router(system_router, prefix="/system", tags=["system"])

# Include WebSocket and Web UI routes
app.include_router(websocket_router, tags=["websocket", "webui"])

# Mount static files for Web UI
webui_static_path = Path(__file__).parent / "webui" / "static"
if webui_static_path.exists():
    app.mount("/static", StaticFiles(directory=str(webui_static_path)), name="static")
else:
    # Fallback to relative path
    webui_static_path = Path(__file__).parent.parent / "webui" / "static"
    if webui_static_path.exists():
        app.mount("/static", StaticFiles(directory=str(webui_static_path)), name="static")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "audio_processor_status": audio_processor.get_status() if hasattr(audio_processor, 'get_status') else "unknown"
    }

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        access_log=True
    )