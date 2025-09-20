"""
TensorFlow Lite inference engine for speaker recognition
"""

import logging
import numpy as np
import tensorflow as tf
from typing import Optional, Dict, Any, List
from pathlib import Path
import json
import time

logger = logging.getLogger(__name__)

class TFLiteInferenceEngine:
    """TensorFlow Lite inference engine optimized for Raspberry Pi"""
    
    def __init__(self, model_path: str):
        self.model_path = Path(model_path)
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self.speaker_labels = {}
        self.embedding_cache = {}
        self.is_model_loaded = False
        
        # Performance metrics
        self.inference_stats = {
            "total_inferences": 0,
            "total_inference_time": 0.0,
            "average_inference_time": 0.0
        }
    
    async def load_model(self):
        """Load TensorFlow Lite model"""
        try:
            if not self.model_path.exists():
                logger.warning(f"Model file not found: {self.model_path}")
                # Create a dummy model for testing
                await self._create_dummy_model()
                return
            
            # Load TFLite model
            self.interpreter = tf.lite.Interpreter(model_path=str(self.model_path))
            self.interpreter.allocate_tensors()
            
            # Get input and output details
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            
            logger.info(f"Model loaded: {self.model_path}")
            logger.info(f"Input shape: {self.input_details[0]['shape']}")
            logger.info(f"Output shape: {self.output_details[0]['shape']}")
            
            # Load speaker labels if available
            await self._load_speaker_labels()
            
            self.is_model_loaded = True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            # Create dummy model for testing
            await self._create_dummy_model()
    
    async def _create_dummy_model(self):
        """Create a dummy model for testing when real model is not available"""
        logger.info("Creating dummy model for testing")
        
        # Simulate model details
        self.input_details = [{
            'shape': [1, 100, 40],  # batch, time, features
            'dtype': np.float32,
            'index': 0
        }]
        
        self.output_details = [{
            'shape': [1, 192],  # batch, embedding_size
            'dtype': np.float32,
            'index': 0
        }]
        
        # Default speaker labels
        self.speaker_labels = {
            0: "Unknown",
            1: "Speaker_1",
            2: "Speaker_2",
            3: "Speaker_3"
        }
        
        self.is_model_loaded = True
    
    async def _load_speaker_labels(self):
        """Load speaker labels from JSON file"""
        try:
            labels_path = self.model_path.parent / "speaker_labels.json"
            if labels_path.exists():
                with open(labels_path, 'r') as f:
                    self.speaker_labels = json.load(f)
                logger.info(f"Loaded {len(self.speaker_labels)} speaker labels")
            else:
                # Default labels
                self.speaker_labels = {0: "Unknown"}
                logger.info("Using default speaker labels")
        except Exception as e:
            logger.error(f"Error loading speaker labels: {e}")
            self.speaker_labels = {0: "Unknown"}
    
    async def predict(self, features: np.ndarray) -> Dict[str, Any]:
        """Run inference on audio features"""
        if not self.is_model_loaded:
            return {"speaker_name": "Unknown", "confidence": 0.0, "error": "Model not loaded"}
        
        start_time = time.time()
        
        try:
            # Prepare input
            input_data = self._prepare_input(features)
            
            if self.interpreter is None:
                # Use dummy inference for testing
                embedding = self._dummy_inference(input_data)
            else:
                # Real TFLite inference
                self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
                self.interpreter.invoke()
                embedding = self.interpreter.get_tensor(self.output_details[0]['index'])
            
            # Classify speaker
            speaker_result = await self._classify_speaker(embedding)
            
            # Update statistics
            inference_time = time.time() - start_time
            self._update_inference_stats(inference_time)
            
            speaker_result["inference_time"] = inference_time
            return speaker_result
            
        except Exception as e:
            logger.error(f"Inference error: {e}")
            return {"speaker_name": "Unknown", "confidence": 0.0, "error": str(e)}
    
    def _prepare_input(self, features: np.ndarray) -> np.ndarray:
        """Prepare input features for model"""
        try:
            target_shape = self.input_details[0]['shape']
            
            # Handle different input shapes
            if len(target_shape) == 3:  # [batch, time, features]
                batch_size, max_time, feature_dim = target_shape
                
                # Pad or truncate time dimension
                if features.shape[0] < max_time:
                    # Pad with zeros
                    pad_width = ((0, max_time - features.shape[0]), (0, 0))
                    features = np.pad(features, pad_width, mode='constant')
                elif features.shape[0] > max_time:
                    # Truncate
                    features = features[:max_time, :]
                
                # Ensure correct feature dimension
                if features.shape[1] != feature_dim:
                    if features.shape[1] < feature_dim:
                        # Pad features
                        pad_width = ((0, 0), (0, feature_dim - features.shape[1]))
                        features = np.pad(features, pad_width, mode='constant')
                    else:
                        # Truncate features
                        features = features[:, :feature_dim]
                
                # Add batch dimension
                input_data = np.expand_dims(features, axis=0).astype(np.float32)
                
            else:
                # Flatten features if model expects 1D input
                input_data = features.flatten()
                input_data = np.expand_dims(input_data, axis=0).astype(np.float32)
            
            return input_data
            
        except Exception as e:
            logger.error(f"Error preparing input: {e}")
            # Return dummy input
            return np.zeros(self.input_details[0]['shape'], dtype=np.float32)
    
    def _dummy_inference(self, input_data: np.ndarray) -> np.ndarray:
        """Dummy inference for testing"""
        # Generate random embedding
        embedding_size = self.output_details[0]['shape'][-1]
        embedding = np.random.randn(1, embedding_size).astype(np.float32)
        
        # Normalize embedding
        norm = np.linalg.norm(embedding, axis=1, keepdims=True)
        embedding = embedding / (norm + 1e-8)
        
        return embedding
    
    async def _classify_speaker(self, embedding: np.ndarray) -> Dict[str, Any]:
        """Classify speaker from embedding using cosine similarity"""
        try:
            if len(self.embedding_cache) == 0:
                # No enrolled speakers
                return {
                    "speaker_name": "Unknown",
                    "confidence": 0.0,
                    "speaker_id": None
                }
            
            # Normalize input embedding
            embedding_norm = embedding / (np.linalg.norm(embedding) + 1e-8)
            
            # Compute similarities with all enrolled speakers
            similarities = {}
            for speaker_id, cached_embedding in self.embedding_cache.items():
                cached_norm = cached_embedding / (np.linalg.norm(cached_embedding) + 1e-8)
                similarity = np.dot(embedding_norm.flatten(), cached_norm.flatten())
                similarities[speaker_id] = similarity
            
            # Find best match
            best_speaker_id = max(similarities.keys(), key=lambda k: similarities[k])
            best_confidence = similarities[best_speaker_id]
            
            # Apply confidence threshold
            if best_confidence < 0.7:  # Configurable threshold
                return {
                    "speaker_name": "Unknown",
                    "confidence": float(best_confidence),
                    "speaker_id": None
                }
            
            speaker_name = self.speaker_labels.get(best_speaker_id, f"Speaker_{best_speaker_id}")
            
            return {
                "speaker_name": speaker_name,
                "confidence": float(best_confidence),
                "speaker_id": int(best_speaker_id)
            }
            
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return {"speaker_name": "Unknown", "confidence": 0.0, "speaker_id": None}
    
    async def enroll_speaker(self, speaker_id: int, speaker_name: str, embeddings: List[np.ndarray]):
        """Enroll a new speaker with multiple embeddings"""
        try:
            # Average multiple embeddings
            if len(embeddings) > 1:
                stacked_embeddings = np.stack(embeddings, axis=0)
                averaged_embedding = np.mean(stacked_embeddings, axis=0)
            else:
                averaged_embedding = embeddings[0]
            
            # Normalize embedding
            averaged_embedding = averaged_embedding / (np.linalg.norm(averaged_embedding) + 1e-8)
            
            # Store in cache
            self.embedding_cache[speaker_id] = averaged_embedding
            self.speaker_labels[speaker_id] = speaker_name
            
            logger.info(f"Enrolled speaker: {speaker_name} (ID: {speaker_id})")
            
            return True
            
        except Exception as e:
            logger.error(f"Error enrolling speaker: {e}")
            return False
    
    def remove_speaker(self, speaker_id: int):
        """Remove enrolled speaker"""
        if speaker_id in self.embedding_cache:
            del self.embedding_cache[speaker_id]
        if speaker_id in self.speaker_labels:
            del self.speaker_labels[speaker_id]
        logger.info(f"Removed speaker ID: {speaker_id}")
    
    def _update_inference_stats(self, inference_time: float):
        """Update inference statistics"""
        self.inference_stats["total_inferences"] += 1
        self.inference_stats["total_inference_time"] += inference_time
        self.inference_stats["average_inference_time"] = (
            self.inference_stats["total_inference_time"] / 
            self.inference_stats["total_inferences"]
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get inference statistics"""
        return {
            "model_loaded": self.is_model_loaded,
            "enrolled_speakers": len(self.embedding_cache),
            "speaker_labels": self.speaker_labels.copy(),
            "inference_stats": self.inference_stats.copy()
        }
    
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self.is_model_loaded
    
    async def cleanup(self):
        """Cleanup resources"""
        self.interpreter = None
        self.embedding_cache.clear()
        self.is_model_loaded = False
        logger.info("TFLite inference engine cleaned up")