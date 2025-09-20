# Voice Recognition Backend

## Overview

FastAPI-based backend server for Raspberry Pi Zero W speaker recognition system. Provides real-time audio processing, speaker enrollment, device management, and WebSocket-based audio streaming.

## Features

- **Real-time Audio Processing**: WebSocket-based audio streaming with VAD and MFCC feature extraction
- **Speaker Recognition**: TensorFlow Lite inference with cosine similarity classification
- **Device Management**: Bluetooth, USB, and network client management
- **Authentication**: JWT-based authentication with bcrypt password hashing
- **Web Interface**: REST API with OpenAPI documentation
- **System Monitoring**: Health checks, performance metrics, and logging

## Hardware Requirements

- Raspberry Pi Zero W (minimum)
- 512MB RAM
- 8GB microSD card
- USB microphone (optional)
- Bluetooth 4.0+ support

## Software Requirements

- Python 3.11+
- Linux-based OS (Raspbian recommended)
- ALSA audio system
- BlueZ Bluetooth stack

## Installation

### Quick Install

```bash
# Clone repository
git clone https://github.com/your-org/voice-recog-pi.git
cd voice-recog-pi/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Production Install

```bash
# Install system dependencies (Debian/Ubuntu)
sudo apt update
sudo apt install -y python3-dev python3-pip portaudio19-dev libasound2-dev
sudo apt install -y bluetooth bluez libbluetooth-dev
sudo apt install -y sqlite3

# Install Python package
pip install voice-recognition-backend

# Run database migrations
alembic upgrade head
```

## Configuration

Create a `.env` file in the backend directory:

```env
# Server configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Security
SECRET_KEY=your-super-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Audio settings
SAMPLE_RATE=16000
CONFIDENCE_THRESHOLD=0.7
VAD_AGGRESSIVENESS=2

# Database
DATABASE_URL=sqlite:///./voice_recognition.db

# Bluetooth
BLUETOOTH_DEVICE_NAME=VoiceRecog-Pi
```

## Usage

### Start the Server

```bash
# Development
python main.py

# Production with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000

# With systemd service
sudo systemctl start voice-recog
```

### Create First User

```bash
# Using the API
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "secure_password"
  }'
```

### Access Web Interface

- Open http://your-pi-ip:8000 in a web browser
- API Documentation: http://your-pi-ip:8000/docs
- Health Check: http://your-pi-ip:8000/health

## Testing

### Run All Tests

```bash
# Install test dependencies
pip install -e .[dev]

# Run tests with coverage
pytest tests/ --cov=src/ --cov-report=html

# Run specific test modules
pytest tests/test_auth.py -v
pytest tests/test_audio_processor.py -v
```

### Integration Tests

```bash
# Test WebSocket connections
pytest tests/test_websockets.py -v

# Test audio processing pipeline
pytest tests/test_audio_integration.py -v

# Test device management
pytest tests/test_device_management.py -v
```

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `GET /auth/verify` - Token verification

### Audio Processing
- `WebSocket /ws/audio` - Real-time audio streaming
- `POST /audio/upload` - Upload audio files
- `GET /audio/status` - Audio system status

### Speaker Management
- `GET /speakers/list` - List enrolled speakers
- `POST /speakers/enroll` - Enroll new speaker
- `PUT /speakers/{id}` - Update speaker
- `DELETE /speakers/{id}` - Delete speaker

### Device Management
- `GET /devices/list` - List paired devices
- `POST /devices/pair` - Pair new device
- `POST /devices/scan` - Scan for devices

### Recognition
- `POST /recognition/start` - Start recognition
- `POST /recognition/stop` - Stop recognition
- `GET /recognition/events` - Get recognition history
- `GET /recognition/stats` - Get statistics

### System Monitoring
- `GET /system/health` - System health metrics
- `GET /system/info` - System information
- `GET /system/logs` - System logs

## Performance Optimization

### Raspberry Pi Zero W Tuning

```bash
# Increase GPU memory split
echo "gpu_mem=128" >> /boot/config.txt

# Optimize audio buffer
echo "snd_bcm2835.enable_compat_alsa=0" >> /boot/config.txt

# CPU governor
echo "performance" > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
```

### Application Tuning

- Set `uvicorn --workers 1` (single core optimization)
- Use `--loop uvloop` for better async performance
- Configure audio buffer sizes in settings
- Enable TensorFlow Lite GPU delegation if available

## Troubleshooting

### Common Issues

1. **Audio Permission Errors**
   ```bash
   sudo usermod -a -G audio $USER
   sudo systemctl restart voice-recog
   ```

2. **Bluetooth Pairing Issues**
   ```bash
   sudo systemctl restart bluetooth
   sudo bluetoothctl
   > power on
   > discoverable on
   ```

3. **WebSocket Connection Errors**
   - Check firewall settings
   - Verify network connectivity
   - Check CORS configuration

4. **High CPU Usage**
   - Reduce VAD aggressiveness
   - Increase audio chunk size
   - Lower sample rate if possible

### Logging

Logs are available at:
- Application logs: `/var/log/voice-recog/app.log`
- System logs: `journalctl -u voice-recog`
- Database logs: Check `system_logs` table

## Development

### Code Style

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Adding New Features

1. Create feature branch
2. Add API endpoints in appropriate module
3. Add database models if needed
4. Write comprehensive tests
5. Update documentation
6. Submit pull request

## License

MIT License - see LICENSE file for details.

## Support

- GitHub Issues: https://github.com/your-org/voice-recog-pi/issues
- Documentation: https://voice-recog-docs.example.com
- Community: https://discord.gg/voice-recog