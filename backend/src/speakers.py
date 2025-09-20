"""
Speaker management API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import logging
import numpy as np
import pickle
from datetime import datetime

from .database import get_database, Speaker
from .auth import get_current_active_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Pydantic models
class SpeakerCreate(BaseModel):
    name: str
    confidence_threshold: Optional[float] = 0.7

class SpeakerResponse(BaseModel):
    id: int
    name: str
    enrollment_samples: int
    confidence_threshold: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class SpeakerUpdate(BaseModel):
    name: Optional[str] = None
    confidence_threshold: Optional[float] = None
    is_active: Optional[bool] = None

@router.get("/list", response_model=List[SpeakerResponse])
async def list_speakers(
    active_only: bool = True,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_database)
):
    """List all speakers"""
    try:
        query = db.query(Speaker)
        
        if active_only:
            query = query.filter(Speaker.is_active == True)
        
        speakers = query.all()
        return speakers
        
    except Exception as e:
        logger.error(f"Error listing speakers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/enroll", response_model=SpeakerResponse)
async def enroll_speaker(
    name: str,
    audio_files: List[UploadFile] = File(...),
    confidence_threshold: float = 0.7,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_database)
):
    """Enroll a new speaker with audio samples"""
    try:
        # Validate input
        if len(audio_files) < 3:
            raise HTTPException(
                status_code=400, 
                detail="At least 3 audio samples required for enrollment"
            )
        
        # Check if speaker already exists
        existing_speaker = db.query(Speaker).filter(Speaker.name == name).first()
        if existing_speaker:
            raise HTTPException(status_code=400, detail="Speaker already exists")
        
        # Process audio files and extract embeddings
        embeddings = []
        for audio_file in audio_files:
            if not audio_file.content_type.startswith('audio/'):
                raise HTTPException(status_code=400, detail="All files must be audio files")
            
            # TODO: Process audio file and extract embedding
            # For now, create dummy embedding
            dummy_embedding = np.random.randn(192).astype(np.float32)
            embeddings.append(dummy_embedding)
        
        # Average embeddings
        if len(embeddings) > 1:
            averaged_embedding = np.mean(embeddings, axis=0)
        else:
            averaged_embedding = embeddings[0]
        
        # Serialize embedding
        embedding_bytes = pickle.dumps(averaged_embedding)
        
        # Create speaker record
        db_speaker = Speaker(
            name=name,
            enrollment_samples=len(audio_files),
            embedding=embedding_bytes,
            confidence_threshold=confidence_threshold,
            is_active=True
        )
        
        db.add(db_speaker)
        db.commit()
        db.refresh(db_speaker)
        
        # TODO: Update inference engine with new speaker
        
        logger.info(f"Speaker enrolled: {name} with {len(audio_files)} samples")
        
        return db_speaker
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enrolling speaker: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{speaker_id}", response_model=SpeakerResponse)
async def get_speaker(
    speaker_id: int,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_database)
):
    """Get speaker by ID"""
    try:
        speaker = db.query(Speaker).filter(Speaker.id == speaker_id).first()
        if not speaker:
            raise HTTPException(status_code=404, detail="Speaker not found")
        
        return speaker
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting speaker: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{speaker_id}", response_model=SpeakerResponse)
async def update_speaker(
    speaker_id: int,
    speaker_update: SpeakerUpdate,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_database)
):
    """Update speaker information"""
    try:
        speaker = db.query(Speaker).filter(Speaker.id == speaker_id).first()
        if not speaker:
            raise HTTPException(status_code=404, detail="Speaker not found")
        
        # Update fields
        update_data = speaker_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(speaker, field, value)
        
        speaker.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(speaker)
        
        return speaker
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating speaker: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{speaker_id}")
async def delete_speaker(
    speaker_id: int,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_database)
):
    """Delete a speaker"""
    try:
        speaker = db.query(Speaker).filter(Speaker.id == speaker_id).first()
        if not speaker:
            raise HTTPException(status_code=404, detail="Speaker not found")
        
        speaker_name = speaker.name
        
        # TODO: Remove from inference engine
        
        db.delete(speaker)
        db.commit()
        
        logger.info(f"Speaker deleted: {speaker_name}")
        
        return {"message": f"Speaker {speaker_name} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting speaker: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{speaker_id}/retrain")
async def retrain_speaker(
    speaker_id: int,
    audio_files: List[UploadFile] = File(...),
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_database)
):
    """Retrain speaker with additional audio samples"""
    try:
        speaker = db.query(Speaker).filter(Speaker.id == speaker_id).first()
        if not speaker:
            raise HTTPException(status_code=404, detail="Speaker not found")
        
        # Validate input
        if len(audio_files) < 1:
            raise HTTPException(status_code=400, detail="At least 1 audio sample required")
        
        # Process new audio files
        new_embeddings = []
        for audio_file in audio_files:
            if not audio_file.content_type.startswith('audio/'):
                raise HTTPException(status_code=400, detail="All files must be audio files")
            
            # TODO: Process audio file and extract embedding
            dummy_embedding = np.random.randn(192).astype(np.float32)
            new_embeddings.append(dummy_embedding)
        
        # Load existing embedding
        existing_embedding = pickle.loads(speaker.embedding)
        
        # Combine with new embeddings
        all_embeddings = [existing_embedding] + new_embeddings
        averaged_embedding = np.mean(all_embeddings, axis=0)
        
        # Update speaker
        speaker.embedding = pickle.dumps(averaged_embedding)
        speaker.enrollment_samples += len(audio_files)
        speaker.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(speaker)
        
        # TODO: Update inference engine
        
        logger.info(f"Speaker retrained: {speaker.name} with {len(audio_files)} additional samples")
        
        return {
            "message": f"Speaker {speaker.name} retrained successfully",
            "total_samples": speaker.enrollment_samples
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retraining speaker: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{speaker_id}/embedding")
async def get_speaker_embedding(
    speaker_id: int,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_database)
):
    """Get speaker embedding for analysis"""
    try:
        speaker = db.query(Speaker).filter(Speaker.id == speaker_id).first()
        if not speaker:
            raise HTTPException(status_code=404, detail="Speaker not found")
        
        # Load embedding
        embedding = pickle.loads(speaker.embedding)
        
        return {
            "speaker_id": speaker_id,
            "speaker_name": speaker.name,
            "embedding_size": len(embedding),
            "embedding_norm": float(np.linalg.norm(embedding)),
            # Don't return the actual embedding for security
            "has_embedding": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting speaker embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))