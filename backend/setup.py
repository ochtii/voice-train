"""
Setup script for Voice Recognition Backend
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="voice-recognition-backend",
    version="1.0.0",
    author="Voice Recognition Team",
    author_email="team@voicerecog.local",
    description="Raspberry Pi Zero W Speaker Recognition Backend",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/voice-recog-pi",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
    ],
    python_requires=">=3.11",
    install_requires=[
        "fastapi==0.104.1",
        "uvicorn[standard]==0.24.0",
        "websockets==12.0",
        "python-multipart==0.0.6",
        "sqlalchemy==2.0.23",
        "alembic==1.13.1",
        "python-jose[cryptography]==3.3.0",
        "passlib[bcrypt]==1.7.4",
        "sounddevice==0.4.6",
        "librosa==0.10.1",
        "webrtcvad==2.0.10",
        "pyaudio==0.2.11",
        "numpy==1.24.4",
        "scipy==1.11.4",
        "tensorflow==2.15.0",
        "scikit-learn==1.3.2",
        "pybluez==0.23",
        "pyserial==3.5",
        "httpx==0.25.2",
        "aiofiles==23.2.0",
        "pydantic==2.5.0",
        "python-dotenv==1.0.0",
        "structlog==23.2.0",
        "prometheus-client==0.19.0",
        "psutil==5.9.6",
    ],
    extras_require={
        "dev": [
            "pytest==7.4.3",
            "pytest-asyncio==0.21.1",
            "pytest-cov==4.1.0",
            "black==23.11.0",
            "flake8==6.1.0",
            "mypy==1.7.1",
        ],
        "pi": [
            # Raspberry Pi specific dependencies
            "RPi.GPIO==0.7.1",
            "gpiozero==1.6.2",
        ]
    },
    entry_points={
        "console_scripts": [
            "voice-recog-backend=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.txt", "*.md", "*.cfg", "*.json"],
    },
)