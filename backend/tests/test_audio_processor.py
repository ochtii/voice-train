"""
Tests for audio processing module
"""

import pytest
import numpy as np
import io
import wave
import asyncio
from unittest.mock import Mock, patch

from src.audio_processor import AudioProcessor
from src.feature_extractor import FeatureExtractor
from src.tflite_inference import TFLiteInferenceEngine

class TestAudioProcessor:
    """Test audio processing functionality"""
    
    @pytest.fixture
    async def audio_processor(self):
        """Create audio processor instance"""
        processor = AudioProcessor()
        await processor.initialize()
        yield processor
        await processor.cleanup()
    
    @pytest.fixture
    def sample_audio_data(self):
        """Generate sample audio data"""
        # Generate 1 second of 16kHz sine wave
        sample_rate = 16000
        duration = 1.0
        frequency = 440  # A4 note
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio = 0.3 * np.sin(2 * np.pi * frequency * t)
        
        # Convert to int16
        audio_int16 = (audio * 32767).astype(np.int16)
        return audio_int16.tobytes()
    
    def test_get_audio_level(self, sample_audio_data):
        """Test audio level calculation"""
        processor = AudioProcessor()
        level = processor.get_audio_level(sample_audio_data)
        
        assert 0.0 <= level <= 1.0
        assert level > 0.0  # Should detect some level from sine wave
    
    def test_get_audio_level_silence(self):
        """Test audio level with silence"""
        processor = AudioProcessor()
        
        # Generate silent audio
        silence = np.zeros(1024, dtype=np.int16).tobytes()
        level = processor.get_audio_level(silence)
        
        assert level == 0.0
    
    @pytest.mark.asyncio
    async def test_process_audio_chunk(self, audio_processor, sample_audio_data):
        """Test processing of audio chunk"""
        result = await audio_processor.process_audio_chunk(sample_audio_data)
        
        assert result is not None
        assert "type" in result
        assert result["type"] in ["audio_processed", "recognition_result", "error"]
        
        if result["type"] == "recognition_result":
            assert "speaker" in result
            assert "confidence" in result
            assert "processing_time" in result
    
    @pytest.mark.asyncio
    async def test_process_empty_audio(self, audio_processor):
        """Test processing empty audio"""
        empty_audio = b""
        result = await audio_processor.process_audio_chunk(empty_audio)
        
        # Should handle empty audio gracefully
        assert result is None or result["type"] == "error"
    
    def test_get_status(self, audio_processor):
        """Test getting processor status"""
        status = audio_processor.get_status()
        
        assert isinstance(status, dict)
        assert "initialized" in status
        assert "processing_stats" in status
        assert "config" in status
        
        # Check config structure
        config = status["config"]
        assert "sample_rate" in config
        assert "chunk_size" in config
        assert "confidence_threshold" in config

class TestFeatureExtractor:
    """Test feature extraction functionality"""
    
    @pytest.fixture
    def feature_extractor(self):
        """Create feature extractor instance"""
        return FeatureExtractor(sample_rate=16000, n_mfcc=40)
    
    @pytest.fixture
    def sample_audio_float(self):
        """Generate sample audio as float array"""
        sample_rate = 16000
        duration = 1.0
        frequency = 440
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio = 0.3 * np.sin(2 * np.pi * frequency * t)
        return audio.astype(np.float32)
    
    def test_extract_mfcc(self, feature_extractor, sample_audio_float):
        """Test MFCC feature extraction"""
        mfcc = feature_extractor.extract_mfcc(sample_audio_float)
        
        assert mfcc is not None
        assert mfcc.ndim == 2  # Should be 2D array (time, features)
        assert mfcc.shape[1] == 40  # Should have 40 MFCC coefficients
        assert mfcc.dtype == np.float32
    
    def test_extract_mfcc_short_audio(self, feature_extractor):
        """Test MFCC extraction with very short audio"""
        short_audio = np.random.randn(100).astype(np.float32)
        mfcc = feature_extractor.extract_mfcc(short_audio)
        
        assert mfcc is not None  # Should handle short audio by padding
        assert mfcc.shape[1] == 40
    
    def test_preprocess_audio(self, feature_extractor, sample_audio_float):
        """Test audio preprocessing"""
        processed = feature_extractor.preprocess_audio(sample_audio_float)
        
        assert processed is not None
        assert processed.dtype == np.float32
        assert len(processed) >= len(sample_audio_float)  # May be padded
    
    def test_extract_comprehensive_features(self, feature_extractor, sample_audio_float):
        """Test comprehensive feature extraction"""
        features = feature_extractor.extract_comprehensive_features(sample_audio_float)
        
        assert features is not None
        assert isinstance(features, dict)
        assert "mfcc" in features
        assert "delta_mfcc" in features
        assert "delta2_mfcc" in features
        assert "combined" in features
        assert "audio_length" in features

class TestTFLiteInferenceEngine:
    """Test TensorFlow Lite inference engine"""
    
    @pytest.fixture
    async def inference_engine(self):
        """Create inference engine instance"""
        engine = TFLiteInferenceEngine("models/dummy_model.tflite")
        await engine.load_model()  # Will create dummy model
        yield engine
        await engine.cleanup()
    
    @pytest.fixture
    def sample_features(self):
        """Generate sample MFCC features"""
        # Generate features that match expected input shape
        return np.random.randn(100, 40).astype(np.float32)
    
    @pytest.mark.asyncio
    async def test_load_dummy_model(self, inference_engine):
        """Test loading dummy model when real model doesn't exist"""
        assert inference_engine.is_loaded()
        assert inference_engine.input_details is not None
        assert inference_engine.output_details is not None
    
    @pytest.mark.asyncio
    async def test_predict(self, inference_engine, sample_features):
        """Test prediction with sample features"""
        result = await inference_engine.predict(sample_features)
        
        assert isinstance(result, dict)
        assert "speaker_name" in result
        assert "confidence" in result
        assert "inference_time" in result
        
        # Check data types
        assert isinstance(result["speaker_name"], str)
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_enroll_speaker(self, inference_engine, sample_features):
        """Test speaker enrollment"""
        embeddings = [np.random.randn(192).astype(np.float32) for _ in range(3)]
        
        success = await inference_engine.enroll_speaker(
            speaker_id=1,
            speaker_name="Test Speaker",
            embeddings=embeddings
        )
        
        assert success is True
        assert 1 in inference_engine.embedding_cache
        assert inference_engine.speaker_labels[1] == "Test Speaker"
    
    def test_remove_speaker(self, inference_engine):
        """Test speaker removal"""
        # Add a speaker first
        inference_engine.embedding_cache[1] = np.random.randn(192).astype(np.float32)
        inference_engine.speaker_labels[1] = "Test Speaker"
        
        # Remove speaker
        inference_engine.remove_speaker(1)
        
        assert 1 not in inference_engine.embedding_cache
        assert 1 not in inference_engine.speaker_labels
    
    def test_get_stats(self, inference_engine):
        """Test getting inference statistics"""
        stats = inference_engine.get_stats()
        
        assert isinstance(stats, dict)
        assert "model_loaded" in stats
        assert "enrolled_speakers" in stats
        assert "speaker_labels" in stats
        assert "inference_stats" in stats

class TestAudioIntegration:
    """Test full audio processing pipeline integration"""
    
    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """Test complete audio processing pipeline"""
        # Create components
        processor = AudioProcessor()
        await processor.initialize()
        
        try:
            # Generate test audio
            sample_rate = 16000
            duration = 2.0
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            audio = 0.3 * np.sin(2 * np.pi * 440 * t)
            audio_int16 = (audio * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()
            
            # Process audio in chunks
            chunk_size = 1024 * 2  # 1024 samples * 2 bytes per sample
            results = []
            
            for i in range(0, len(audio_bytes), chunk_size):
                chunk = audio_bytes[i:i + chunk_size]
                if len(chunk) >= chunk_size:  # Only process full chunks
                    result = await processor.process_audio_chunk(chunk)
                    if result:
                        results.append(result)
            
            # Should have some results
            assert len(results) > 0
            
            # Check if any recognition results
            recognition_results = [r for r in results if r.get("type") == "recognition_result"]
            
            # At least some chunks should be processed
            processed_results = [r for r in results if r.get("type") in ["audio_processed", "recognition_result"]]
            assert len(processed_results) > 0
            
        finally:
            await processor.cleanup()
    
    def test_wav_file_processing(self):
        """Test processing WAV file format"""
        # Create a WAV file in memory
        sample_rate = 16000
        duration = 1.0
        frequency = 440
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio = 0.3 * np.sin(2 * np.pi * frequency * t)
        audio_int16 = (audio * 32767).astype(np.int16)
        
        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 2 bytes per sample
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
        
        wav_data = wav_buffer.getvalue()
        
        # Test processing (would be called from API)
        assert len(wav_data) > 44  # WAV header + data
        assert wav_data[:4] == b'RIFF'  # WAV file signature