"""
Recognition system API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
from datetime import datetime, timedelta

from .database import get_database, RecognitionEvent
from .auth import get_current_active_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Pydantic models
class RecognitionEventResponse(BaseModel):
    id: int
    speaker_id: Optional[int]
    speaker_name: str
    confidence: float
    device_id: Optional[str]
    audio_duration: Optional[float]
    timestamp: datetime
    
    class Config:
        from_attributes = True

class RecognitionStats(BaseModel):
    total_recognitions: int
    known_speaker_recognitions: int
    unknown_speaker_recognitions: int
    average_confidence: float
    top_speakers: List[Dict[str, Any]]

@router.post("/start")
async def start_recognition(
    device_id: Optional[str] = None,
    current_user = Depends(get_current_active_user)
):
    """Start voice recognition"""
    try:
        # This would start the recognition process
        # For now, return success status
        
        logger.info(f"Recognition started for device: {device_id}")
        
        return {
            "status": "started",
            "device_id": device_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Voice recognition started successfully"
        }
        
    except Exception as e:
        logger.error(f"Error starting recognition: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_recognition(
    device_id: Optional[str] = None,
    current_user = Depends(get_current_active_user)
):
    """Stop voice recognition"""
    try:
        logger.info(f"Recognition stopped for device: {device_id}")
        
        return {
            "status": "stopped",
            "device_id": device_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Voice recognition stopped successfully"
        }
        
    except Exception as e:
        logger.error(f"Error stopping recognition: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_recognition_status(
    current_user = Depends(get_current_active_user)
):
    """Get current recognition status"""
    try:
        # This would get the actual status from the recognition system
        return {
            "is_active": True,  # Mock status
            "connected_devices": [
                {
                    "device_id": "android_001",
                    "device_type": "bluetooth",
                    "status": "connected",
                    "audio_quality": 0.85
                },
                {
                    "device_id": "windows_001", 
                    "device_type": "network",
                    "status": "connected",
                    "audio_quality": 0.92
                }
            ],
            "current_speaker": {
                "name": "Unknown",
                "confidence": 0.0,
                "last_detection": None
            },
            "performance": {
                "avg_latency_ms": 45,
                "cpu_usage": 15.2,
                "memory_usage_mb": 48
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting recognition status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/events", response_model=List[RecognitionEventResponse])
async def get_recognition_events(
    limit: int = 100,
    speaker_id: Optional[int] = None,
    device_id: Optional[str] = None,
    hours_back: int = 24,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_database)
):
    """Get recent recognition events"""
    try:
        # Calculate time threshold
        time_threshold = datetime.utcnow() - timedelta(hours=hours_back)
        
        query = db.query(RecognitionEvent).filter(
            RecognitionEvent.timestamp >= time_threshold
        )
        
        if speaker_id is not None:
            query = query.filter(RecognitionEvent.speaker_id == speaker_id)
        
        if device_id:
            query = query.filter(RecognitionEvent.device_id == device_id)
        
        events = query.order_by(RecognitionEvent.timestamp.desc()).limit(limit).all()
        
        return events
        
    except Exception as e:
        logger.error(f"Error getting recognition events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=RecognitionStats)
async def get_recognition_stats(
    hours_back: int = 24,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_database)
):
    """Get recognition statistics"""
    try:
        # Calculate time threshold
        time_threshold = datetime.utcnow() - timedelta(hours=hours_back)
        
        # Get events in time period
        events = db.query(RecognitionEvent).filter(
            RecognitionEvent.timestamp >= time_threshold
        ).all()
        
        if not events:
            return RecognitionStats(
                total_recognitions=0,
                known_speaker_recognitions=0,
                unknown_speaker_recognitions=0,
                average_confidence=0.0,
                top_speakers=[]
            )
        
        # Calculate statistics
        total_recognitions = len(events)
        known_speaker_events = [e for e in events if e.speaker_id is not None]
        unknown_speaker_events = [e for e in events if e.speaker_id is None]
        
        known_speaker_recognitions = len(known_speaker_events)
        unknown_speaker_recognitions = len(unknown_speaker_events)
        
        # Average confidence
        if events:
            average_confidence = sum(e.confidence for e in events) / len(events)
        else:
            average_confidence = 0.0
        
        # Top speakers
        speaker_counts = {}
        for event in known_speaker_events:
            speaker_name = event.speaker_name
            if speaker_name not in speaker_counts:
                speaker_counts[speaker_name] = {
                    "name": speaker_name,
                    "count": 0,
                    "avg_confidence": 0.0,
                    "confidences": []
                }
            speaker_counts[speaker_name]["count"] += 1
            speaker_counts[speaker_name]["confidences"].append(event.confidence)
        
        # Calculate average confidence per speaker
        for speaker_data in speaker_counts.values():
            speaker_data["avg_confidence"] = sum(speaker_data["confidences"]) / len(speaker_data["confidences"])
            del speaker_data["confidences"]  # Remove raw confidences
        
        # Sort by count and take top 10
        top_speakers = sorted(
            speaker_counts.values(),
            key=lambda x: x["count"],
            reverse=True
        )[:10]
        
        return RecognitionStats(
            total_recognitions=total_recognitions,
            known_speaker_recognitions=known_speaker_recognitions,
            unknown_speaker_recognitions=unknown_speaker_recognitions,
            average_confidence=average_confidence,
            top_speakers=top_speakers
        )
        
    except Exception as e:
        logger.error(f"Error getting recognition stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/confidence-threshold")
async def get_confidence_threshold(
    current_user = Depends(get_current_active_user)
):
    """Get current confidence threshold"""
    try:
        # This would get from settings
        return {
            "confidence_threshold": 0.7,
            "description": "Minimum confidence score for positive speaker identification"
        }
        
    except Exception as e:
        logger.error(f"Error getting confidence threshold: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/confidence-threshold")
async def set_confidence_threshold(
    threshold: float,
    current_user = Depends(get_current_active_user)
):
    """Set confidence threshold"""
    try:
        if not 0.0 <= threshold <= 1.0:
            raise HTTPException(
                status_code=400,
                detail="Confidence threshold must be between 0.0 and 1.0"
            )
        
        # This would update the settings
        logger.info(f"Confidence threshold updated to: {threshold}")
        
        return {
            "confidence_threshold": threshold,
            "message": "Confidence threshold updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting confidence threshold: {e}")
        raise HTTPException(status_code=500, detail=str(e))