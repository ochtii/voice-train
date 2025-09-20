"""
Feature extraction module for audio preprocessing
"""

import numpy as np
import librosa
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class FeatureExtractor:
    """Audio feature extraction for speaker recognition"""
    
    def __init__(self, sample_rate: int = 16000, n_mfcc: int = 40, n_fft: int = 512, hop_length: int = 160):
        self.sample_rate = sample_rate
        self.n_mfcc = n_mfcc
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.win_length = n_fft
        
        logger.info(f"FeatureExtractor initialized: sr={sample_rate}, mfcc={n_mfcc}, nfft={n_fft}")
    
    def extract_mfcc(self, audio: np.ndarray, normalize: bool = True) -> Optional[np.ndarray]:
        """Extract MFCC features from audio signal"""
        try:
            if len(audio) == 0:
                return None
            
            # Ensure audio is long enough
            min_length = self.n_fft
            if len(audio) < min_length:
                # Pad with zeros if too short
                audio = np.pad(audio, (0, min_length - len(audio)), mode='constant')
            
            # Extract MFCC features
            mfcc = librosa.feature.mfcc(
                y=audio,
                sr=self.sample_rate,
                n_mfcc=self.n_mfcc,
                n_fft=self.n_fft,
                hop_length=self.hop_length,
                win_length=self.win_length,
                center=True,
                pad_mode='reflect'
            )
            
            # Transpose to (time, features) format
            mfcc = mfcc.T
            
            if normalize:
                # Mean and variance normalization
                mean = np.mean(mfcc, axis=0, keepdims=True)
                std = np.std(mfcc, axis=0, keepdims=True)
                std = np.where(std == 0, 1.0, std)  # Avoid division by zero
                mfcc = (mfcc - mean) / std
            
            return mfcc.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Error extracting MFCC features: {e}")
            return None
    
    def extract_mel_spectrogram(self, audio: np.ndarray) -> Optional[np.ndarray]:
        """Extract mel spectrogram features"""
        try:
            if len(audio) == 0:
                return None
            
            # Extract mel spectrogram
            mel_spec = librosa.feature.melspectrogram(
                y=audio,
                sr=self.sample_rate,
                n_mels=80,
                n_fft=self.n_fft,
                hop_length=self.hop_length,
                win_length=self.win_length
            )
            
            # Convert to log scale
            log_mel_spec = librosa.power_to_db(mel_spec, ref=np.max)
            
            # Transpose to (time, features) format
            return log_mel_spec.T.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Error extracting mel spectrogram: {e}")
            return None
    
    def extract_spectral_features(self, audio: np.ndarray) -> Optional[dict]:
        """Extract additional spectral features"""
        try:
            if len(audio) == 0:
                return None
            
            # Spectral centroid
            spectral_centroids = librosa.feature.spectral_centroid(
                y=audio, sr=self.sample_rate, hop_length=self.hop_length
            )[0]
            
            # Spectral rolloff
            spectral_rolloff = librosa.feature.spectral_rolloff(
                y=audio, sr=self.sample_rate, hop_length=self.hop_length
            )[0]
            
            # Zero crossing rate
            zcr = librosa.feature.zero_crossing_rate(
                y=audio, hop_length=self.hop_length
            )[0]
            
            # Spectral bandwidth
            spectral_bandwidth = librosa.feature.spectral_bandwidth(
                y=audio, sr=self.sample_rate, hop_length=self.hop_length
            )[0]
            
            return {
                "spectral_centroid": spectral_centroids.astype(np.float32),
                "spectral_rolloff": spectral_rolloff.astype(np.float32),
                "zero_crossing_rate": zcr.astype(np.float32),
                "spectral_bandwidth": spectral_bandwidth.astype(np.float32)
            }
            
        except Exception as e:
            logger.error(f"Error extracting spectral features: {e}")
            return None
    
    def preprocess_audio(self, audio: np.ndarray) -> np.ndarray:
        """Preprocess audio signal"""
        try:
            # Normalize amplitude
            if np.max(np.abs(audio)) > 0:
                audio = audio / np.max(np.abs(audio))
            
            # Apply pre-emphasis filter
            pre_emphasis = 0.97
            audio = np.append(audio[0], audio[1:] - pre_emphasis * audio[:-1])
            
            return audio.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Error preprocessing audio: {e}")
            return audio
    
    def compute_delta_features(self, features: np.ndarray, width: int = 9) -> np.ndarray:
        """Compute delta (velocity) features"""
        try:
            delta = librosa.feature.delta(features, width=width, axis=0)
            return delta.astype(np.float32)
        except Exception as e:
            logger.error(f"Error computing delta features: {e}")
            return np.zeros_like(features)
    
    def extract_comprehensive_features(self, audio: np.ndarray) -> Optional[dict]:
        """Extract comprehensive feature set for speaker recognition"""
        try:
            # Preprocess audio
            audio = self.preprocess_audio(audio)
            
            # Extract MFCC
            mfcc = self.extract_mfcc(audio)
            if mfcc is None:
                return None
            
            # Compute delta and delta-delta features
            delta_mfcc = self.compute_delta_features(mfcc)
            delta2_mfcc = self.compute_delta_features(delta_mfcc)
            
            # Extract spectral features
            spectral_features = self.extract_spectral_features(audio)
            
            # Combine all features
            combined_features = np.concatenate([
                mfcc,
                delta_mfcc,
                delta2_mfcc
            ], axis=1)
            
            result = {
                "mfcc": mfcc,
                "delta_mfcc": delta_mfcc,
                "delta2_mfcc": delta2_mfcc,
                "combined": combined_features,
                "audio_length": len(audio) / self.sample_rate
            }
            
            if spectral_features:
                result.update(spectral_features)
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting comprehensive features: {e}")
            return None