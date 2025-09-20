"""
Test configuration and fixtures
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base, get_database
from src.auth import get_current_active_user
from main import app

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def db_session():
    """Create a test database session"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def override_get_db():
    """Override database dependency for testing"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def override_get_current_user():
    """Override auth dependency for testing"""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "is_active": True
    }

# Override dependencies
app.dependency_overrides[get_database] = override_get_db
app.dependency_overrides[get_current_active_user] = override_get_current_user

@pytest.fixture
def client():
    """Create a test client"""
    with TestClient(app) as c:
        yield c

@pytest.fixture
def test_user_data():
    """Test user data"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }

@pytest.fixture
def test_speaker_data():
    """Test speaker data"""
    return {
        "name": "Test Speaker",
        "confidence_threshold": 0.75
    }

@pytest.fixture
def test_device_data():
    """Test device data"""
    return {
        "device_id": "test_device_001",
        "device_type": "bluetooth",
        "device_name": "Test Android Phone",
        "mac_address": "AA:BB:CC:DD:EE:FF"
    }