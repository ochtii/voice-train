// Dashboard Main JavaScript
class Dashboard {
    constructor() {
        this.isRecognitionPaused = false;
        this.updateInterval = null;
        this.speakerData = [];
        this.activityLog = [];
        this.maxActivityItems = 50;
        
        this.init();
    }

    init() {
        console.log('Initializing Dashboard...');
        
        // Bind event handlers
        this.bindEvents();
        
        // Set up WebSocket listeners
        this.setupWebSocketListeners();
        
        // Start periodic updates
        this.startPeriodicUpdates();
        
        // Load initial data
        this.loadInitialData();
        
        console.log('Dashboard initialized successfully');
    }

    bindEvents() {
        // Refresh button
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshData());
        }

        // Pause/Resume recognition
        const pauseBtn = document.getElementById('pauseRecognition');
        if (pauseBtn) {
            pauseBtn.addEventListener('click', () => this.toggleRecognition());
        }

        // Toggle spectrum visualizer
        const toggleSpectrumBtn = document.getElementById('toggleSpectrum');
        if (toggleSpectrumBtn) {
            toggleSpectrumBtn.addEventListener('click', () => this.toggleSpectrum());
        }

        // Clear activity log
        const clearLogBtn = document.getElementById('clearLog');
        if (clearLogBtn) {
            clearLogBtn.addEventListener('click', () => this.clearActivityLog());
        }
    }

    setupWebSocketListeners() {
        if (!window.wsManager) return;

        // Speaker recognition events
        window.wsManager.on('speaker_recognized', (data) => {
            this.updateCurrentSpeaker(data);
            this.addActivity('success', 'Speaker Recognized', `${data.speaker_name} identified with ${data.confidence}% confidence`);
        });

        // Audio level updates
        window.wsManager.on('audio_level', (data) => {
            this.updateAudioMetrics(data);
        });

        // System status updates
        window.wsManager.on('system_status', (data) => {
            this.updateSystemStatus(data);
        });

        // Device updates
        window.wsManager.on('device_update', (data) => {
            this.updateDeviceCount(data);
        });

        // Error events
        window.wsManager.on('error', (data) => {
            this.addActivity('error', 'System Error', data.message || 'Unknown error occurred');
        });

        // Connection status
        window.wsManager.on('connection', () => {
            this.addActivity('success', 'Connected', 'WebSocket connection established');
        });

        window.wsManager.on('disconnection', () => {
            this.addActivity('warning', 'Disconnected', 'WebSocket connection lost');
        });
    }

    startPeriodicUpdates() {
        // Update every 5 seconds
        this.updateInterval = setInterval(() => {
            this.updateMetrics();
        }, 5000);
    }

    loadInitialData() {
        // Show loading state
        this.showLoadingState();
        
        // Request initial data via WebSocket
        if (window.wsManager?.isConnected()) {
            window.wsManager.send({
                type: 'request_dashboard_data'
            });
        } else {
            // Load demo data if not connected
            setTimeout(() => {
                this.loadDemoData();
                this.hideLoadingState();
            }, 1000);
        }
    }

    loadDemoData() {
        // Demo system status
        this.updateSystemStatus({
            uptime: '2d 14h 32m',
            cpu_usage: 45,
            memory_usage: 67,
            status: 'active'
        });

        // Demo recognition stats
        this.updateRecognitionStats({
            total_sessions: 1247,
            success_rate: 94.2,
            active_sessions: 3
        });

        // Demo audio metrics
        this.updateAudioMetrics({
            input_level: 75,
            quality_score: 88,
            noise_level: 12
        });

        // Demo device counts
        this.updateDeviceCount({
            bluetooth: 2,
            usb: 1,
            network: 4
        });

        // Demo speakers
        this.speakerData = [
            { id: 1, name: 'John Doe', sessions: 45, last_seen: '2 minutes ago', status: 'active' },
            { id: 2, name: 'Jane Smith', sessions: 32, last_seen: '1 hour ago', status: 'inactive' },
            { id: 3, name: 'Bob Wilson', sessions: 18, last_seen: '3 hours ago', status: 'inactive' },
            { id: 4, name: 'Alice Brown', sessions: 67, last_seen: '5 minutes ago', status: 'active' }
        ];
        this.updateSpeakerList();

        // Demo activity
        this.addActivity('success', 'Speaker Enrolled', 'New speaker "John Doe" has been enrolled');
        this.addActivity('info', 'System Started', 'Voice recognition system is now active');
        this.addActivity('warning', 'Low Audio Quality', 'Audio input quality is below optimal threshold');
    }

    showLoadingState() {
        // Add loading class to metric values
        document.querySelectorAll('.metric-value').forEach(el => {
            el.classList.add('loading');
            el.textContent = 'Loading...';
        });
    }

    hideLoadingState() {
        // Remove loading class from metric values
        document.querySelectorAll('.metric-value').forEach(el => {
            el.classList.remove('loading');
        });
    }

    updateSystemStatus(data) {
        const statusBadge = document.getElementById('systemStatus');
        const uptimeEl = document.getElementById('systemUptime');
        const cpuEl = document.getElementById('cpuUsage');
        const memoryEl = document.getElementById('memoryUsage');

        if (statusBadge) {
            const statusDot = statusBadge.querySelector('.status-dot');
            const statusText = statusBadge.querySelector('span');
            
            statusBadge.className = 'status-badge';
            
            switch (data.status) {
                case 'active':
                    statusBadge.classList.add('success');
                    statusText.textContent = 'Active';
                    break;
                case 'warning':
                    statusBadge.classList.add('warning');
                    statusText.textContent = 'Warning';
                    break;
                case 'error':
                    statusBadge.classList.add('error');
                    statusText.textContent = 'Error';
                    break;
                default:
                    statusText.textContent = 'Unknown';
            }
        }

        if (uptimeEl) uptimeEl.textContent = data.uptime || '--';
        if (cpuEl) cpuEl.textContent = data.cpu_usage ? `${data.cpu_usage}%` : '--';
        if (memoryEl) memoryEl.textContent = data.memory_usage ? `${data.memory_usage}%` : '--';
    }

    updateRecognitionStats(data) {
        const totalEl = document.getElementById('totalSessions');
        const successEl = document.getElementById('successRate');
        const activeEl = document.getElementById('activeSessions');

        if (totalEl) totalEl.textContent = data.total_sessions?.toLocaleString() || '--';
        if (successEl) successEl.textContent = data.success_rate ? `${data.success_rate}%` : '--';
        if (activeEl) activeEl.textContent = data.active_sessions || '--';
    }

    updateAudioMetrics(data) {
        const levelEl = document.getElementById('audioLevel');
        const qualityEl = document.getElementById('audioQuality');
        const noiseEl = document.getElementById('noiseLevel');

        if (levelEl) levelEl.textContent = data.input_level ? `${data.input_level}%` : '--';
        if (qualityEl) qualityEl.textContent = data.quality_score ? `${data.quality_score}%` : '--';
        if (noiseEl) noiseEl.textContent = data.noise_level ? `${data.noise_level}%` : '--';
    }

    updateDeviceCount(data) {
        const bluetoothEl = document.getElementById('bluetoothDevices');
        const usbEl = document.getElementById('usbDevices');
        const networkEl = document.getElementById('networkDevices');

        if (bluetoothEl) bluetoothEl.textContent = data.bluetooth || '0';
        if (usbEl) usbEl.textContent = data.usb || '0';
        if (networkEl) networkEl.textContent = data.network || '0';
    }

    updateCurrentSpeaker(data) {
        const speakerEl = document.getElementById('currentSpeaker');
        if (!speakerEl) return;

        const nameEl = speakerEl.querySelector('.speaker-name');
        const confidenceEl = speakerEl.querySelector('.confidence-score');
        const avatarEl = speakerEl.querySelector('.speaker-avatar');

        if (nameEl) nameEl.textContent = data.speaker_name || 'Unknown Speaker';
        if (confidenceEl) confidenceEl.textContent = `Confidence: ${data.confidence || '--'}%`;
        
        // Update avatar color based on confidence
        if (avatarEl && data.confidence) {
            if (data.confidence > 80) {
                avatarEl.style.backgroundColor = 'var(--color-success)';
            } else if (data.confidence > 60) {
                avatarEl.style.backgroundColor = 'var(--color-warning)';
            } else {
                avatarEl.style.backgroundColor = 'var(--color-error)';
            }
        }
    }

    updateSpeakerList() {
        const speakerListEl = document.getElementById('speakerList');
        if (!speakerListEl) return;

        speakerListEl.innerHTML = '';

        if (this.speakerData.length === 0) {
            speakerListEl.innerHTML = `
                <div class="text-center" style="color: var(--text-tertiary); padding: var(--spacing-4);">
                    No speakers enrolled yet.
                    <a href="/enrollment" style="color: var(--color-primary);">Enroll your first speaker</a>
                </div>
            `;
            return;
        }

        this.speakerData.forEach(speaker => {
            const speakerEl = document.createElement('div');
            speakerEl.className = 'speaker-item';
            
            const initials = speaker.name.split(' ').map(n => n[0]).join('').substring(0, 2);
            
            speakerEl.innerHTML = `
                <div class="speaker-item-avatar">${initials}</div>
                <div class="speaker-item-info">
                    <div class="speaker-item-name">${speaker.name}</div>
                    <div class="speaker-item-stats">${speaker.sessions} sessions • ${speaker.last_seen}</div>
                </div>
                <div class="speaker-item-status">
                    <div class="speaker-status-dot ${speaker.status === 'active' ? '' : 'inactive'}"></div>
                    ${speaker.status}
                </div>
            `;
            
            speakerListEl.appendChild(speakerEl);
        });
    }

    addActivity(type, title, details) {
        const activity = {
            id: Date.now(),
            type,
            title,
            details,
            timestamp: new Date()
        };

        this.activityLog.unshift(activity);
        
        // Limit activity log size
        if (this.activityLog.length > this.maxActivityItems) {
            this.activityLog = this.activityLog.slice(0, this.maxActivityItems);
        }

        this.updateActivityLog();
    }

    updateActivityLog() {
        const activityLogEl = document.getElementById('activityLog');
        if (!activityLogEl) return;

        activityLogEl.innerHTML = '';

        if (this.activityLog.length === 0) {
            activityLogEl.innerHTML = `
                <div class="text-center" style="color: var(--text-tertiary); padding: var(--spacing-4);">
                    No recent activity
                </div>
            `;
            return;
        }

        this.activityLog.forEach(activity => {
            const activityEl = document.createElement('div');
            activityEl.className = 'activity-item fade-in';
            
            const iconMap = {
                success: '<path d="M9,20.42L2.79,14.21L5.62,11.38L9,14.77L18.88,4.88L21.71,7.71L9,20.42Z"/>',
                warning: '<path d="M13,14H11V10H13M13,18H11V16H13M1,21H23L12,2L1,21Z"/>',
                error: '<path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"/>',
                info: '<path d="M13,9H11V7H13M13,17H11V11H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z"/>'
            };
            
            const timeAgo = this.getTimeAgo(activity.timestamp);
            
            activityEl.innerHTML = `
                <div class="activity-icon ${activity.type}">
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        ${iconMap[activity.type] || iconMap.info}
                    </svg>
                </div>
                <div class="activity-content">
                    <div class="activity-title">${activity.title}</div>
                    <div class="activity-details">${activity.details}</div>
                    <div class="activity-time">${timeAgo}</div>
                </div>
            `;
            
            activityLogEl.appendChild(activityEl);
        });
    }

    getTimeAgo(timestamp) {
        const now = new Date();
        const diffMs = now - timestamp;
        const diffSecs = Math.floor(diffMs / 1000);
        const diffMins = Math.floor(diffSecs / 60);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffSecs < 60) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        return `${diffDays}d ago`;
    }

    toggleRecognition() {
        this.isRecognitionPaused = !this.isRecognitionPaused;
        const pauseBtn = document.getElementById('pauseRecognition');
        
        if (pauseBtn) {
            if (this.isRecognitionPaused) {
                pauseBtn.innerHTML = `
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        <path d="M8,5.14V19.14L19,12.14L8,5.14Z"/>
                    </svg>
                    Resume
                `;
                pauseBtn.classList.remove('btn-secondary');
                pauseBtn.classList.add('btn-primary');
            } else {
                pauseBtn.innerHTML = `
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        <path d="M14,19H18V5H14M6,19H10V5H6V19Z"/>
                    </svg>
                    Pause
                `;
                pauseBtn.classList.remove('btn-primary');
                pauseBtn.classList.add('btn-secondary');
            }
        }

        // Send pause/resume command via WebSocket
        if (window.wsManager?.isConnected()) {
            window.wsManager.send({
                type: 'toggle_recognition',
                paused: this.isRecognitionPaused
            });
        }

        this.addActivity(
            this.isRecognitionPaused ? 'warning' : 'success',
            this.isRecognitionPaused ? 'Recognition Paused' : 'Recognition Resumed',
            this.isRecognitionPaused ? 'Speaker recognition has been paused' : 'Speaker recognition has been resumed'
        );
    }

    toggleSpectrum() {
        if (window.audioVisualizer) {
            const isActive = window.audioVisualizer.toggle();
            const toggleBtn = document.getElementById('toggleSpectrum');
            
            if (toggleBtn) {
                toggleBtn.classList.toggle('btn-primary', !isActive);
                toggleBtn.classList.toggle('btn-secondary', isActive);
            }
        }
    }

    clearActivityLog() {
        this.activityLog = [];
        this.updateActivityLog();
        this.addActivity('info', 'Activity Log Cleared', 'All previous activity has been cleared');
    }

    refreshData() {
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="currentColor" style="animation: spin 1s linear infinite;">
                    <path d="M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z"/>
                </svg>
                Refreshing...
            `;
        }

        // Request fresh data
        if (window.wsManager?.isConnected()) {
            window.wsManager.send({
                type: 'request_dashboard_data'
            });
        }

        // Reset button after 2 seconds
        setTimeout(() => {
            if (refreshBtn) {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = `
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        <path d="M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z"/>
                    </svg>
                    Refresh
                `;
            }
            this.addActivity('info', 'Data Refreshed', 'Dashboard data has been updated');
        }, 2000);
    }

    updateMetrics() {
        // This would typically request updated metrics from the server
        if (window.wsManager?.isConnected()) {
            window.wsManager.send({
                type: 'request_metrics_update'
            });
        }
    }

    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.dashboard) {
        window.dashboard.destroy();
    }
});