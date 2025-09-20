"""
Database configuration and models
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text, Boolean, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from datetime import datetime

from .config import settings

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    """User model for authentication"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    last_login = Column(DateTime)

class Speaker(Base):
    """Speaker model for voice recognition"""
    __tablename__ = "speakers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    enrollment_samples = Column(Integer, default=0)
    embedding = Column(LargeBinary)  # Serialized numpy array
    confidence_threshold = Column(Float, default=0.7)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Device(Base):
    """Connected device model"""
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(100), unique=True, nullable=False)
    device_type = Column(String(50), nullable=False)  # bluetooth, usb, network
    device_name = Column(String(100))
    mac_address = Column(String(17))  # For Bluetooth devices
    ip_address = Column(String(15))   # For network devices
    is_paired = Column(Boolean, default=False)
    is_connected = Column(Boolean, default=False)
    last_seen = Column(DateTime, default=func.now())
    audio_quality = Column(Float, default=0.0)

class RecognitionEvent(Base):
    """Recognition event log"""
    __tablename__ = "recognition_events"
    
    id = Column(Integer, primary_key=True, index=True)
    speaker_id = Column(Integer, nullable=True)  # NULL for unknown speakers
    speaker_name = Column(String(100))
    confidence = Column(Float, nullable=False)
    device_id = Column(String(100))
    audio_duration = Column(Float)  # In seconds
    timestamp = Column(DateTime, default=func.now())
    
class SystemLog(Base):
    """System log entries"""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(10), nullable=False)  # INFO, WARNING, ERROR
    component = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(Text)  # JSON string for additional details
    timestamp = Column(DateTime, default=func.now())

# Create all tables
def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

# Dependency to get database session
def get_database():
    """Get database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()