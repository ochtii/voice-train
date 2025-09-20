"""
Audio-related API endpoints
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
import numpy as np
import io
import wave
import logging

from .database import get_database
from .auth import get_current_active_user
from .audio_processor import AudioProcessor

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload")
async def upload_audio(
    file: UploadFile = File(...),
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_database)
):
    """Upload audio file for processing"""
    try:
        # Validate file type
        if not file.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="File must be an audio file")
        
        # Read audio file
        content = await file.read()
        
        # Process audio based on format
        if file.content_type == 'audio/wav':
            audio_data = process_wav_file(content)
        else:
            raise HTTPException(status_code=400, detail="Only WAV files are supported currently")
        
        # TODO: Process audio with AudioProcessor
        # This would typically extract features and run inference
        
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(content),
            "status": "processed"
        }
        
    except Exception as e:
        logger.error(f"Error uploading audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def process_wav_file(content: bytes) -> np.ndarray:
    """Process WAV file content"""
    try:
        # Read WAV file from bytes
        with io.BytesIO(content) as wav_io:
            with wave.open(wav_io, 'rb') as wav_file:
                frames = wav_file.readframes(-1)
                audio_data = np.frombuffer(frames, dtype=np.int16)
                
                # Get audio parameters
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                
                logger.info(f"WAV file: {sample_rate}Hz, {channels} channels, {len(audio_data)} samples")
                
                return audio_data
                
    except Exception as e:
        logger.error(f"Error processing WAV file: {e}")
        raise

@router.get("/formats")
async def get_supported_formats():
    """Get supported audio formats"""
    return {
        "supported_formats": [
            {
                "format": "wav",
                "mime_type": "audio/wav",
                "description": "WAV uncompressed audio"
            }
        ],
        "recommended_settings": {
            "sample_rate": 16000,
            "channels": 1,
            "bit_depth": 16
        }
    }

@router.get("/status")
async def get_audio_status():
    """Get audio processing status"""
    # This would get status from the AudioProcessor instance
    return {
        "status": "ready",
        "processing_enabled": True,
        "current_sample_rate": 16000,
        "current_channels": 1
    }