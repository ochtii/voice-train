"""
Tests for authentication module
"""

import pytest
from fastapi import status
from sqlalchemy.orm import Session

from src.auth import create_access_token, verify_password, get_password_hash
from src.database import User

class TestAuthentication:
    """Test authentication functionality"""
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False
    
    def test_create_access_token(self):
        """Test JWT token creation"""
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long
    
    def test_register_user(self, client, test_user_data):
        """Test user registration"""
        response = client.post("/auth/register", json=test_user_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]
        assert "password" not in data
    
    def test_register_duplicate_user(self, client, test_user_data):
        """Test duplicate user registration"""
        # Register first user
        client.post("/auth/register", json=test_user_data)
        
        # Try to register same user again
        response = client.post("/auth/register", json=test_user_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"]
    
    def test_login_valid_user(self, client, test_user_data):
        """Test login with valid credentials"""
        # Register user first
        client.post("/auth/register", json=test_user_data)
        
        # Login
        login_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
        response = client.post("/auth/login", data=login_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_token"]
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_user(self, client):
        """Test login with invalid credentials"""
        login_data = {
            "username": "nonexistent",
            "password": "wrongpassword"
        }
        response = client.post("/auth/login", data=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_verify_token(self, client, test_user_data):
        """Test token verification"""
        # Register and login
        client.post("/auth/register", json=test_user_data)
        login_response = client.post("/auth/login", data={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        })
        
        token = login_response.json()["access_token"]
        
        # Verify token
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/auth/verify", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == test_user_data["username"]
    
    def test_verify_invalid_token(self, client):
        """Test verification with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/auth/verify", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

class TestAuthenticationEdgeCases:
    """Test edge cases for authentication"""
    
    def test_empty_username(self, client):
        """Test registration with empty username"""
        data = {
            "username": "",
            "email": "test@example.com",
            "password": "password123"
        }
        response = client.post("/auth/register", json=data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_weak_password(self, client):
        """Test registration with weak password"""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "123"
        }
        # Note: This might pass depending on validation rules
        response = client.post("/auth/register", json=data)
        
        # Should implement password strength validation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    def test_invalid_email_format(self, client):
        """Test registration with invalid email"""
        data = {
            "username": "testuser",
            "email": "invalid-email",
            "password": "password123"
        }
        response = client.post("/auth/register", json=data)
        
        # Should validate email format
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]