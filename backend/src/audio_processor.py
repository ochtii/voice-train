"""
Audio processing pipeline for voice activity detection, feature extraction, and recognition
"""

import asyncio
import logging
import numpy as np
import librosa
import webrtcvad
import io
import time
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

from .config import settings
from .tflite_inference import TFLiteInferenceEngine
from .feature_extractor import FeatureExtractor

logger = logging.getLogger(__name__)

class AudioProcessor:
    """Main audio processing pipeline"""
    
    def __init__(self):
        self.vad = None
        self.feature_extractor = None
        self.inference_engine = None
        self.is_initialized = False
        self.processing_stats = {
            "total_chunks_processed": 0,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0,
            "voice_activity_ratio": 0.0
        }
    
    async def initialize(self):
        """Initialize the audio processing pipeline"""
        try:
            # Initialize VAD
            self.vad = webrtcvad.Vad(settings.VAD_AGGRESSIVENESS)
            logger.info(f"VAD initialized with aggressiveness: {settings.VAD_AGGRESSIVENESS}")
            
            # Initialize feature extractor
            self.feature_extractor = FeatureExtractor(
                sample_rate=settings.SAMPLE_RATE,
                n_mfcc=40,
                n_fft=512,
                hop_length=160
            )
            logger.info("Feature extractor initialized")
            
            # Initialize TFLite inference engine
            self.inference_engine = TFLiteInferenceEngine(settings.MODEL_PATH)
            await self.inference_engine.load_model()
            logger.info("TFLite inference engine initialized")
            
            self.is_initialized = True
            logger.info("Audio processor initialization completed")
            
        except Exception as e:
            logger.error(f"Failed to initialize audio processor: {e}")
            raise
    
    async def process_audio_chunk(self, audio_data: bytes) -> Optional[Dict[str, Any]]:
        """Process a single audio chunk"""
        if not self.is_initialized:
            logger.warning("Audio processor not initialized")
            return None
        
        start_time = time.time()
        
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Normalize to float32
            audio_float = audio_array.astype(np.float32) / 32768.0
            
            # Check if audio chunk is long enough
            if len(audio_float) < settings.CHUNK_SIZE:
                return None
            
            # Voice Activity Detection
            has_voice = self._detect_voice_activity(audio_data)
            
            if not has_voice:
                return {
                    "type": "audio_processed",
                    "has_voice": False,
                    "processing_time": time.time() - start_time
                }
            
            # Extract features
            features = self.feature_extractor.extract_mfcc(audio_float)
            
            if features is None or features.size == 0:
                return None
            
            # Run inference
            speaker_result = await self.inference_engine.predict(features)
            
            # Update statistics
            processing_time = time.time() - start_time
            self._update_stats(processing_time, has_voice)
            
            return {
                "type": "recognition_result",
                "has_voice": True,
                "speaker": speaker_result.get("speaker_name", "Unknown"),
                "confidence": speaker_result.get("confidence", 0.0),
                "processing_time": processing_time,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
            return {
                "type": "error",
                "message": f"Processing error: {str(e)}"
            }
    
    def _detect_voice_activity(self, audio_data: bytes) -> bool:
        """Detect voice activity in audio chunk"""
        try:
            # VAD expects 16kHz, 16-bit, mono audio
            # Split into 10ms, 20ms, or 30ms frames
            frame_duration = 20  # ms
            frame_size = int(settings.SAMPLE_RATE * frame_duration / 1000) * 2  # 2 bytes per sample
            
            voice_frames = 0
            total_frames = 0
            
            for i in range(0, len(audio_data) - frame_size, frame_size):
                frame = audio_data[i:i + frame_size]
                if len(frame) == frame_size:
                    try:
                        is_speech = self.vad.is_speech(frame, settings.SAMPLE_RATE)
                        if is_speech:
                            voice_frames += 1
                        total_frames += 1
                    except:
                        continue
            
            if total_frames == 0:
                return False
            
            voice_ratio = voice_frames / total_frames
            return voice_ratio > 0.3  # At least 30% of frames should contain speech
            
        except Exception as e:
            logger.error(f"VAD error: {e}")
            return True  # Default to processing if VAD fails
    
    def _update_stats(self, processing_time: float, has_voice: bool):
        """Update processing statistics"""
        self.processing_stats["total_chunks_processed"] += 1
        self.processing_stats["total_processing_time"] += processing_time
        
        # Calculate rolling average
        total_chunks = self.processing_stats["total_chunks_processed"]
        self.processing_stats["average_processing_time"] = (
            self.processing_stats["total_processing_time"] / total_chunks
        )
        
        # Update voice activity ratio (simple moving average)
        current_ratio = self.processing_stats["voice_activity_ratio"]
        alpha = 0.1  # Smoothing factor
        self.processing_stats["voice_activity_ratio"] = (
            alpha * (1.0 if has_voice else 0.0) + (1 - alpha) * current_ratio
        )
    
    def get_audio_level(self, audio_data: bytes) -> float:
        """Calculate audio level (RMS) from raw audio data"""
        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            audio_float = audio_array.astype(np.float32) / 32768.0
            
            # Calculate RMS level
            rms = np.sqrt(np.mean(audio_float ** 2))
            
            # Convert to dB
            if rms > 0:
                db_level = 20 * np.log10(rms)
                # Normalize to 0-1 range (assuming -60dB to 0dB range)
                normalized_level = max(0.0, min(1.0, (db_level + 60) / 60))
                return normalized_level
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Error calculating audio level: {e}")
            return 0.0
    
    def get_status(self) -> Dict[str, Any]:
        """Get current processor status"""
        return {
            "initialized": self.is_initialized,
            "vad_enabled": self.vad is not None,
            "model_loaded": self.inference_engine.is_loaded() if self.inference_engine else False,
            "processing_stats": self.processing_stats.copy(),
            "config": {
                "sample_rate": settings.SAMPLE_RATE,
                "chunk_size": settings.CHUNK_SIZE,
                "vad_aggressiveness": settings.VAD_AGGRESSIVENESS,
                "confidence_threshold": settings.CONFIDENCE_THRESHOLD
            }
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.inference_engine:
            await self.inference_engine.cleanup()
        
        self.vad = None
        self.feature_extractor = None
        self.inference_engine = None
        self.is_initialized = False
        
        logger.info("Audio processor cleaned up")