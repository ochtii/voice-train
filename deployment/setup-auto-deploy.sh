#!/bin/bash
# Auto-Deployment Setup Script for Raspberry Pi
# This script sets up the complete auto-deployment system

set -e

echo "🚀 Setting up Auto-Deployment System for Voice Recognition Pi"

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

# Install Node.js and PM2 if not present
log_info "Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    log_info "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
    sudo apt-get install -y nodejs
    log_success "Node.js installed"
else
    log_success "Node.js already installed: $(node --version)"
fi

# Install PM2 globally
log_info "Installing PM2..."
if ! command -v pm2 &> /dev/null; then
    sudo npm install -g pm2
    log_success "PM2 installed"
else
    log_success "PM2 already installed: $(pm2 --version)"
fi

# Setup PM2 startup
log_info "Setting up PM2 startup..."
sudo pm2 startup systemd -u ochtii --hp /home/ochtii
pm2 save

# Install Python dependencies for auto-deployer
log_info "Installing Python dependencies..."
cd "$PROJECT_ROOT"
source "$VENV_PATH/bin/activate"
pip install requests colorama gitpython

# Make auto-deployer executable
chmod +x "$DEPLOYMENT_DIR/auto-deployer.py"

# Create systemd service for auto-deployer (backup to PM2)
log_info "Creating systemd service..."
sudo tee /etc/systemd/system/voice-recog-deployer.service > /dev/null << EOF
[Unit]
Description=Voice Recognition Auto-Deployer
After=network.target

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

[Install]
WantedBy=multi-user.target
EOF

# Enable and start services
log_info "Enabling services..."
sudo systemctl daemon-reload
sudo systemctl enable voice-recog-deployer.service

# Start PM2 ecosystem
log_info "Starting PM2 ecosystem..."
cd "$PROJECT_ROOT"
pm2 start ecosystem.config.js --env production
pm2 save

log_success "Auto-deployment system setup completed!"
log_info "Services status:"
echo "PM2 processes:"
pm2 list
echo ""
echo "Systemd services:"
sudo systemctl status voice-recog-deployer.service --no-pager -l

log_info "Log files location: $LOGS_DIR"
log_info "To monitor logs: pm2 logs or tail -f $LOGS_DIR/*.log"

echo ""
log_success "🎉 Setup complete! Auto-deployment is now active."
log_info "Changes to the 'live' branch will be automatically deployed every 5 seconds."