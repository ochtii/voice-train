// WebSocket Manager for Real-time Communication
class WebSocketManager {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        this.listeners = new Map();
        this.connectionStatus = 'disconnected';
        this.heartbeatInterval = null;
        this.lastHeartbeat = null;
    }

    connect(url = null) {
        try {
            // Default WebSocket URL
            const wsUrl = url || `ws://${window.location.host}/ws`;
            
            console.log(`Attempting to connect to WebSocket: ${wsUrl}`);
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = this.handleOpen.bind(this);
            this.ws.onmessage = this.handleMessage.bind(this);
            this.ws.onclose = this.handleClose.bind(this);
            this.ws.onerror = this.handleError.bind(this);
            
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.updateConnectionStatus('error');
            this.scheduleReconnect();
        }
    }

    handleOpen(event) {
        console.log('WebSocket connected');
        this.connectionStatus = 'connected';
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        this.updateConnectionStatus('connected');
        
        // Start heartbeat
        this.startHeartbeat();
        
        // Trigger connection event
        this.emit('connection', { status: 'connected' });
    }

    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('WebSocket message received:', data);
            
            // Handle heartbeat response
            if (data.type === 'pong') {
                this.lastHeartbeat = Date.now();
                return;
            }
            
            // Emit the message to listeners
            this.emit(data.type || 'message', data);
            
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    }

    handleClose(event) {
        console.log('WebSocket connection closed:', event.code, event.reason);
        this.connectionStatus = 'disconnected';
        this.updateConnectionStatus('disconnected');
        this.stopHeartbeat();
        
        // Emit disconnection event
        this.emit('disconnection', { code: event.code, reason: event.reason });
        
        // Only attempt reconnection if it wasn't a clean close
        if (event.code !== 1000) {
            this.scheduleReconnect();
        }
    }

    handleError(error) {
        console.error('WebSocket error:', error);
        this.connectionStatus = 'error';
        this.updateConnectionStatus('error');
        this.emit('error', { error });
    }

    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('Max reconnection attempts reached');
            this.updateConnectionStatus('failed');
            return;
        }

        this.reconnectAttempts++;
        this.updateConnectionStatus('reconnecting');
        
        console.log(`Scheduling reconnection attempt ${this.reconnectAttempts} in ${this.reconnectDelay}ms`);
        
        setTimeout(() => {
            this.connect();
        }, this.reconnectDelay);
        
        // Exponential backoff with jitter
        this.reconnectDelay = Math.min(
            this.reconnectDelay * 2 + Math.random() * 1000,
            30000
        );
    }

    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.send({ type: 'ping', timestamp: Date.now() });
                
                // Check if we've received a recent pong
                if (this.lastHeartbeat && Date.now() - this.lastHeartbeat > 30000) {
                    console.warn('Heartbeat timeout, closing connection');
                    this.ws.close();
                }
            }
        }, 10000); // Send ping every 10 seconds
    }

    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            try {
                this.ws.send(JSON.stringify(data));
                return true;
            } catch (error) {
                console.error('Error sending WebSocket message:', error);
                return false;
            }
        } else {
            console.warn('WebSocket not connected, cannot send message');
            return false;
        }
    }

    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }

    off(event, callback) {
        if (this.listeners.has(event)) {
            const callbacks = this.listeners.get(event);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    }

    emit(event, data) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in event listener for ${event}:`, error);
                }
            });
        }
    }

    updateConnectionStatus(status) {
        const statusIndicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        
        if (!statusIndicator || !statusText) return;
        
        // Remove all status classes
        statusIndicator.classList.remove('connected', 'disconnected', 'reconnecting');
        
        switch (status) {
            case 'connected':
                statusIndicator.classList.add('connected');
                statusText.textContent = 'Connected';
                break;
            case 'disconnected':
                statusIndicator.classList.add('disconnected');
                statusText.textContent = 'Disconnected';
                break;
            case 'reconnecting':
                statusText.textContent = 'Reconnecting...';
                break;
            case 'error':
                statusIndicator.classList.add('disconnected');
                statusText.textContent = 'Connection Error';
                break;
            case 'failed':
                statusIndicator.classList.add('disconnected');
                statusText.textContent = 'Connection Failed';
                break;
            default:
                statusText.textContent = 'Unknown';
        }
    }

    disconnect() {
        this.stopHeartbeat();
        if (this.ws) {
            this.ws.close(1000, 'Client disconnecting');
            this.ws = null;
        }
    }

    getConnectionStatus() {
        return this.connectionStatus;
    }

    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }
}

// Create global WebSocket manager instance
window.wsManager = new WebSocketManager();

// Auto-connect when the script loads
document.addEventListener('DOMContentLoaded', () => {
    window.wsManager.connect();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.wsManager) {
        window.wsManager.disconnect();
    }
});