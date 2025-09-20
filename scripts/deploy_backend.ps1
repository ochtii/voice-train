# Voice Recognition Pi - Backend Deployment Script (PowerShell)
# Dieses Skript installiert das Backend auf dem Raspberry Pi Zero W

param(
    [string]$PiHost = "192.168.188.92",
    [string]$PiUser = "ochtii",
    [string]$SshKey = "$env:USERPROFILE\.ssh\id_ed25519_pi",
    [string]$RemoteDir = "/home/ochtii/voice-recog-pi",
    [string]$LocalBackendDir = ".\backend"
)

# Farben für Output
$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"
$Cyan = "Cyan"

function Write-Step {
    param([string]$Message)
    Write-Host "`n📋 $Message" -ForegroundColor $Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor $Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor $Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor $Yellow
}

function Invoke-SshCommand {
    param([string]$Command)
    $result = ssh -i $SshKey "$PiUser@$PiHost" $Command
    if ($LASTEXITCODE -ne 0) {
        throw "SSH command failed: $Command"
    }
    return $result
}

function Copy-ToRaspberryPi {
    param([string]$Source, [string]$Destination)
    scp -i $SshKey -r $Source "$PiUser@${PiHost}:$Destination"
    if ($LASTEXITCODE -ne 0) {
        throw "SCP copy failed: $Source to $Destination"
    }
}

Write-Host "🚀 Voice Recognition Pi - Backend Deployment" -ForegroundColor $Cyan
Write-Host "===============================================" -ForegroundColor $Cyan
Write-Host "Target: $PiUser@$PiHost"
Write-Host "Remote Directory: $RemoteDir"
Write-Host "SSH Key: $SshKey"

try {
    Write-Step "Step 1: Checking SSH connection..."
    $sshTest = Invoke-SshCommand "echo 'SSH connection successful'"
    Write-Success "SSH connection established"

    Write-Step "Step 2: Getting system information..."
    $hostname = Invoke-SshCommand "hostname"
    $osInfo = Invoke-SshCommand "cat /etc/os-release | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '\"'"
    Write-Host "Hostname: $hostname"
    Write-Host "OS: $osInfo"

    Write-Step "Step 3: Creating remote directories..."
    Invoke-SshCommand "mkdir -p $RemoteDir/backend"
    Invoke-SshCommand "mkdir -p $RemoteDir/logs"
    Invoke-SshCommand "mkdir -p $RemoteDir/models"
    Invoke-SshCommand "mkdir -p $RemoteDir/audio_samples"
    Write-Success "Directories created"

    Write-Step "Step 4: Installing system dependencies..."
    Write-Host "Updating package list..."
    Invoke-SshCommand "sudo apt update -qq"
    
    Write-Host "Installing Python and audio dependencies..."
    Invoke-SshCommand "sudo apt install -y python3 python3-pip python3-venv python3-dev portaudio19-dev libasound2-dev redis-server git curl wget"
    Write-Success "System dependencies installed"

    Write-Step "Step 5: Copying backend files..."
    if (Test-Path $LocalBackendDir) {
        Write-Host "Copying source code..."
        Copy-ToRaspberryPi "$LocalBackendDir\src" "$RemoteDir/backend/"
        Copy-ToRaspberryPi "$LocalBackendDir\requirements.txt" "$RemoteDir/backend/"
        Copy-ToRaspberryPi "$LocalBackendDir\main.py" "$RemoteDir/backend/"
        Copy-ToRaspberryPi "$LocalBackendDir\config.py" "$RemoteDir/backend/"
        Write-Success "Backend files copied"
    } else {
        Write-Error "Local backend directory not found: $LocalBackendDir"
        exit 1
    }

    Write-Step "Step 6: Setting up Python virtual environment..."
    Invoke-SshCommand "cd $RemoteDir/backend && python3 -m venv venv"
    Invoke-SshCommand "cd $RemoteDir/backend && source venv/bin/activate && pip install --upgrade pip"
    Invoke-SshCommand "cd $RemoteDir/backend && source venv/bin/activate && pip install -r requirements.txt"
    Write-Success "Python environment configured"

    Write-Step "Step 7: Creating configuration files..."
    $envConfig = @"
# Voice Recognition Pi - Production Configuration
DEBUG=false
HOST=0.0.0.0
PORT=8000
WORKERS=1

# Database
DATABASE_URL=sqlite:///./voice_recog.db

# JWT
SECRET_KEY=your-super-secret-jwt-key-change-in-production-$(Get-Random)
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
"@

    Invoke-SshCommand "cat > $RemoteDir/backend/.env << 'EOF'`n$envConfig`nEOF"
    Write-Success "Configuration files created"

    Write-Step "Step 8: Creating systemd service..."
    $serviceConfig = @"
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
"@

    Invoke-SshCommand "sudo tee /etc/systemd/system/voice-recog.service > /dev/null << 'EOF'`n$serviceConfig`nEOF"
    Write-Success "Systemd service created"

    Write-Step "Step 9: Enabling service..."
    Invoke-SshCommand "sudo systemctl daemon-reload"
    Invoke-SshCommand "sudo systemctl enable voice-recog.service"
    Write-Success "Service enabled"

    Write-Step "Step 10: Testing Python installation..."
    $testResult = Invoke-SshCommand "cd $RemoteDir/backend && source venv/bin/activate && python -c 'import fastapi, uvicorn, numpy; print(`"Dependencies OK`")'"
    Write-Success "Python dependencies verified: $testResult"

    Write-Step "Step 11: Starting service..."
    Invoke-SshCommand "sudo systemctl start voice-recog.service"
    Start-Sleep -Seconds 3
    
    $serviceStatus = Invoke-SshCommand "sudo systemctl is-active voice-recog.service"
    if ($serviceStatus -eq "active") {
        Write-Success "Service started successfully"
    } else {
        Write-Warning "Service status: $serviceStatus"
        Write-Host "Checking service logs..."
        Invoke-SshCommand "sudo journalctl -u voice-recog.service --no-pager -n 10"
    }

    Write-Step "Step 12: Testing API endpoint..."
    Start-Sleep -Seconds 5
    try {
        $healthCheck = Invoke-SshCommand "curl -s http://localhost:8000/health"
        if ($healthCheck -match "healthy") {
            Write-Success "API endpoint is responding correctly"
        } else {
            Write-Warning "Health check returned: $healthCheck"
        }
    } catch {
        Write-Warning "API endpoint test failed, checking service logs..."
        Invoke-SshCommand "sudo journalctl -u voice-recog.service --no-pager -n 20"
    }

    Write-Host "`n🎉 Deployment completed successfully!" -ForegroundColor $Green
    Write-Host "===============================================" -ForegroundColor $Cyan
    Write-Host "Backend is running on: http://$PiHost`:8000"
    Write-Host "Health check: curl http://$PiHost`:8000/health"
    Write-Host "`nUseful commands:"
    Write-Host "Service status: ssh -i $SshKey $PiUser@$PiHost 'sudo systemctl status voice-recog.service'"
    Write-Host "Service logs: ssh -i $SshKey $PiUser@$PiHost 'sudo journalctl -u voice-recog.service -f'"
    Write-Host "Restart service: ssh -i $SshKey $PiUser@$PiHost 'sudo systemctl restart voice-recog.service'"
    
    Write-Host "`nNext steps:" -ForegroundColor $Yellow
    Write-Host "1. Test the API endpoints from your Windows client"
    Write-Host "2. Upload ML models to $RemoteDir/models/"
    Write-Host "3. Configure audio devices on the Raspberry Pi"
    Write-Host "4. Test client connections from Android and Windows apps"
    
} catch {
    Write-Error "Deployment failed: $($_.Exception.Message)"
    Write-Host "Error details: $($_.Exception)" -ForegroundColor $Red
    exit 1
}