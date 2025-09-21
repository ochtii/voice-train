#!/bin/bash
# Simplified Auto-Deployment Setup for Raspberry Pi Zero W
# Uses systemd instead of PM2 due to ARM compatibility issues

set -e

echo "🚀 Setting up Auto-Deployment System for Voice Recognition Pi (Systemd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
RESET='\033[0m'

log_info() {
    echo -e "${CYAN}[INFO]${RESET} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${RESET} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${RESET} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${RESET} $1"
}

# Project paths
PROJECT_ROOT="/home/ochtii/voice-recog-pi"
VENV_PATH="$PROJECT_ROOT/venv"
LOGS_DIR="$PROJECT_ROOT/logs"
DEPLOYMENT_DIR="$PROJECT_ROOT/deployment"

log_info "Creating directory structure..."
mkdir -p "$LOGS_DIR"
mkdir -p "$DEPLOYMENT_DIR"

# Install Python dependencies for auto-deployer
log_info "Installing Python dependencies..."
cd "$PROJECT_ROOT"
source "$VENV_PATH/bin/activate"
pip install requests colorama

# Make auto-deployer executable
chmod +x "$DEPLOYMENT_DIR/auto-deployer.py"

# Stop existing services
log_info "Stopping existing services..."
sudo systemctl stop voice-recog.service || true
sudo systemctl stop voice-recog-deployer.service || true

# Create systemd service for voice recognition backend
log_info "Creating voice recognition service..."
sudo tee /etc/systemd/system/voice-recog.service > /dev/null << EOF
[Unit]
Description=Voice Recognition Backend
After=network.target
Wants=voice-recog-deployer.service

[Service]
Type=simple
User=ochtii
WorkingDirectory=$PROJECT_ROOT/backend
Environment=PATH=$VENV_PATH/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=$PROJECT_ROOT/backend
ExecStart=$VENV_PATH/bin/python main.py
Restart=always
RestartSec=3
StandardOutput=append:$LOGS_DIR/backend.log
StandardError=append:$LOGS_DIR/backend-error.log

[Install]
WantedBy=multi-user.target
EOF

# Create systemd service for auto-deployer
log_info "Creating auto-deployer service..."
sudo tee /etc/systemd/system/voice-recog-deployer.service > /dev/null << EOF
[Unit]
Description=Voice Recognition Auto-Deployer
After=network.target
Before=voice-recog.service

[Service]
Type=simple
User=ochtii
WorkingDirectory=$DEPLOYMENT_DIR
Environment=PATH=$VENV_PATH/bin:/usr/local/bin:/usr/bin:/bin
Environment=GITHUB_REPO=https://github.com/ochtii/voice-train.git
Environment=BRANCH=live
Environment=CHECK_INTERVAL=5
ExecStart=$VENV_PATH/bin/python auto-deployer.py
Restart=always
RestartSec=10
StandardOutput=append:$LOGS_DIR/deployer.log
StandardError=append:$LOGS_DIR/deployer-error.log

[Install]
WantedBy=multi-user.target
EOF

# Enable and start services
log_info "Enabling and starting services..."
sudo systemctl daemon-reload
sudo systemctl enable voice-recog.service
sudo systemctl enable voice-recog-deployer.service

# Start services
sudo systemctl start voice-recog-deployer.service
sleep 2
sudo systemctl start voice-recog.service

log_success "Auto-deployment system setup completed!"
log_info "Services status:"
echo "Voice Recognition Backend:"
sudo systemctl status voice-recog.service --no-pager -l
echo ""
echo "Auto-Deployer:"
sudo systemctl status voice-recog-deployer.service --no-pager -l

log_info "Log files location: $LOGS_DIR"
log_info "To monitor logs:"
log_info "  Backend: tail -f $LOGS_DIR/backend.log"
log_info "  Deployer: tail -f $LOGS_DIR/deployer.log"
log_info "  Live monitoring: watch 'sudo systemctl status voice-recog*.service'"

echo ""
log_success "🎉 Setup complete! Auto-deployment is now active."
log_info "Changes to the 'live' branch will be automatically deployed every 5 seconds."

# Show current status
log_info "Current system status:"
echo "Active services:"
sudo systemctl list-units --state=active | grep voice-recog