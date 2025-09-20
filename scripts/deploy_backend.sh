#!/bin/bash

# Voice Recognition Pi - Deployment Script
# Dieses Skript installiert das Backend auf dem Raspberry Pi Zero W

set -e  # Exit on error

# Konfiguration
PI_HOST="192.168.188.92"
PI_USER="ochtii"
SSH_KEY="$HOME/.ssh/id_ed25519_pi"
REMOTE_DIR="/home/ochtii/voice-recog-pi"
LOCAL_BACKEND_DIR="./backend"

echo "🚀 Voice Recognition Pi - Backend Deployment"
echo "=============================================="
echo "Target: $PI_USER@$PI_HOST"
echo "Remote Directory: $REMOTE_DIR"
echo ""

# Funktion für SSH-Befehle
ssh_exec() {
    ssh -i "$SSH_KEY" "$PI_USER@$PI_HOST" "$1"
}

# Funktion für SCP-Übertragung
scp_copy() {
    scp -i "$SSH_KEY" -r "$1" "$PI_USER@$PI_HOST:$2"
}

echo "📋 Step 1: Checking SSH connection..."
if ssh_exec "echo 'SSH connection successful'"; then
    echo "✅ SSH connection established"
else
    echo "❌ SSH connection failed"
    exit 1
fi

echo ""
echo "📋 Step 2: System information..."
ssh_exec "echo 'Hostname:' && hostname && echo 'OS:' && cat /etc/os-release | grep PRETTY_NAME"

echo ""
echo "📋 Step 3: Creating remote directory..."
ssh_exec "mkdir -p $REMOTE_DIR/backend"
ssh_exec "mkdir -p $REMOTE_DIR/logs"
ssh_exec "mkdir -p $REMOTE_DIR/models"
ssh_exec "mkdir -p $REMOTE_DIR/audio_samples"

echo ""
echo "📋 Step 4: Installing system dependencies..."
ssh_exec "sudo apt update"
ssh_exec "sudo apt install -y python3 python3-pip python3-venv python3-dev"
ssh_exec "sudo apt install -y portaudio19-dev libasound2-dev"
ssh_exec "sudo apt install -y redis-server"
ssh_exec "sudo apt install -y git curl wget"

echo ""
echo "📋 Step 5: Copying backend files..."
echo "Copying source code..."
scp_copy "$LOCAL_BACKEND_DIR/src" "$REMOTE_DIR/backend/"
scp_copy "$LOCAL_BACKEND_DIR/requirements.txt" "$REMOTE_DIR/backend/"
scp_copy "$LOCAL_BACKEND_DIR/main.py" "$REMOTE_DIR/backend/"
scp_copy "$LOCAL_BACKEND_DIR/config.py" "$REMOTE_DIR/backend/"

echo ""
echo "📋 Step 6: Setting up Python virtual environment..."
ssh_exec "cd $REMOTE_DIR/backend && python3 -m venv venv"
ssh_exec "cd $REMOTE_DIR/backend && source venv/bin/activate && pip install --upgrade pip"
ssh_exec "cd $REMOTE_DIR/backend && source venv/bin/activate && pip install -r requirements.txt"

echo ""
echo "📋 Step 7: Creating configuration files..."

# Erstelle Produktions-Konfiguration
ssh_exec "cat > $REMOTE_DIR/backend/.env << 'EOF'
# Voice Recognition Pi - Production Configuration
DEBUG=false
HOST=0.0.0.0
PORT=8000
WORKERS=1

# Database
DATABASE_URL=sqlite:///./voice_recog.db

# JWT
SECRET_KEY=your-super-secret-jwt-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Audio
SAMPLE_RATE=16000
CHANNELS=1
CHUNK_SIZE=1024

# ML Model
MODEL_PATH=./models/speaker_recognition.tflite
CONFIDENCE_THRESHOLD=0.7

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/voice_recog.log
EOF"

echo ""
echo "📋 Step 8: Creating systemd service..."
ssh_exec "sudo tee /etc/systemd/system/voice-recog.service > /dev/null << 'EOF'
[Unit]
Description=Voice Recognition Pi Backend
After=network.target

[Service]
Type=simple
User=ochtii
WorkingDirectory=/home/ochtii/voice-recog-pi/backend
Environment=PATH=/home/ochtii/voice-recog-pi/backend/venv/bin
ExecStart=/home/ochtii/voice-recog-pi/backend/venv/bin/python main.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF"

echo ""
echo "📋 Step 9: Setting up service..."
ssh_exec "sudo systemctl daemon-reload"
ssh_exec "sudo systemctl enable voice-recog.service"

echo ""
echo "📋 Step 10: Testing installation..."
echo "Testing Python imports..."
ssh_exec "cd $REMOTE_DIR/backend && source venv/bin/activate && python -c 'import fastapi, uvicorn, numpy, librosa; print(\"All dependencies imported successfully\")'"

echo ""
echo "📋 Step 11: Starting service..."
ssh_exec "sudo systemctl start voice-recog.service"
sleep 3
ssh_exec "sudo systemctl status voice-recog.service --no-pager"

echo ""
echo "📋 Step 12: Testing API endpoint..."
sleep 5
if ssh_exec "curl -s http://localhost:8000/health | grep -q 'healthy'"; then
    echo "✅ API endpoint is responding"
else
    echo "⚠️  API endpoint check failed, checking logs..."
    ssh_exec "sudo journalctl -u voice-recog.service --no-pager -n 20"
fi

echo ""
echo "🎉 Deployment completed!"
echo "=============================================="
echo "Backend is running on: http://$PI_HOST:8000"
echo "Health check: curl http://$PI_HOST:8000/health"
echo "Service status: sudo systemctl status voice-recog.service"
echo "Service logs: sudo journalctl -u voice-recog.service -f"
echo ""
echo "Next steps:"
echo "1. Test the API endpoints"
echo "2. Upload ML models to $REMOTE_DIR/models/"
echo "3. Configure audio devices"
echo "4. Test client connections"