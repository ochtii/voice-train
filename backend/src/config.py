"""
Configuration settings for the Voice Recognition Backend
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "sqlite:///./voice_recognition.db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Audio settings
    SAMPLE_RATE: int = 16000
    CHANNELS: int = 1
    CHUNK_SIZE: int = 1024
    AUDIO_FORMAT: str = "int16"
    
    # Recognition settings
    CONFIDENCE_THRESHOLD: float = 0.7
    VAD_AGGRESSIVENESS: int = 2
    
    # Bluetooth settings
    BLUETOOTH_DEVICE_NAME: str = "VoiceRecog-Pi"
    BLUETOOTH_UUID: str = "1e0ca4ea-299d-4335-93eb-27fcfe7fa848"
    
    # Cloud backup
    BACKUP_ENABLED: bool = True
    BACKUP_PROVIDER: str = "gdrive"  # gdrive, dropbox, onedrive
    BACKUP_INTERVAL_HOURS: int = 24
    
    # Performance
    MAX_CONCURRENT_CONNECTIONS: int = 10
    AUDIO_BUFFER_SIZE: int = 4096
    
    # File paths
    MODEL_PATH: str = "models/speaker_recognition.tflite"
    SPEAKERS_DB_PATH: str = "data/speakers.db"
    LOGS_PATH: str = "logs/"
    
    class Config:
        env_file = ".env"

# Global settings instance
settings = Settings()