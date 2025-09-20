// Toast Notification System
class NotificationManager {
    constructor() {
        this.container = null;
        this.notifications = [];
        this.maxNotifications = 5;
        this.defaultDuration = 5000; // 5 seconds
        
        this.init();
    }

    init() {
        // Create or find toast container
        this.container = document.getElementById('toastContainer');
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'toastContainer';
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
        
        console.log('Notification system initialized');
    }

    show(message, type = 'info', duration = null) {
        const toast = this.createToast(message, type, duration || this.defaultDuration);
        this.addToast(toast);
        return toast.id;
    }

    success(message, duration = null) {
        return this.show(message, 'success', duration);
    }

    error(message, duration = null) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration = null) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration = null) {
        return this.show(message, 'info', duration);
    }

    createToast(message, type, duration) {
        const toast = {
            id: Date.now() + Math.random(),
            message,
            type,
            duration,
            element: null,
            timeoutId: null
        };

        // Create toast element
        const toastEl = document.createElement('div');
        toastEl.className = `toast toast-${type}`;
        toastEl.setAttribute('data-toast-id', toast.id);
        
        // Toast content
        const contentEl = document.createElement('div');
        contentEl.className = 'toast-content';
        
        // Icon
        const iconEl = document.createElement('div');
        iconEl.className = 'toast-icon';
        iconEl.innerHTML = this.getIcon(type);
        
        // Message
        const messageEl = document.createElement('div');
        messageEl.className = 'toast-message';
        messageEl.textContent = message;
        
        // Close button
        const closeEl = document.createElement('button');
        closeEl.className = 'toast-close';
        closeEl.innerHTML = '×';
        closeEl.setAttribute('aria-label', 'Close notification');
        closeEl.addEventListener('click', () => this.dismiss(toast.id));
        
        // Assemble toast
        contentEl.appendChild(iconEl);
        contentEl.appendChild(messageEl);
        contentEl.appendChild(closeEl);
        toastEl.appendChild(contentEl);
        
        toast.element = toastEl;
        
        // Auto-dismiss after duration
        if (duration > 0) {
            toast.timeoutId = setTimeout(() => {
                this.dismiss(toast.id);
            }, duration);
        }
        
        // Pause auto-dismiss on hover
        toastEl.addEventListener('mouseenter', () => {
            if (toast.timeoutId) {
                clearTimeout(toast.timeoutId);
                toast.timeoutId = null;
            }
        });
        
        // Resume auto-dismiss on mouse leave
        toastEl.addEventListener('mouseleave', () => {
            if (duration > 0 && !toast.timeoutId) {
                toast.timeoutId = setTimeout(() => {
                    this.dismiss(toast.id);
                }, duration);
            }
        });
        
        return toast;
    }

    addToast(toast) {
        // Add to notifications array
        this.notifications.push(toast);
        
        // Remove oldest notifications if we exceed the limit
        while (this.notifications.length > this.maxNotifications) {
            const oldestToast = this.notifications.shift();
            this.removeToast(oldestToast);
        }
        
        // Add to DOM
        this.container.appendChild(toast.element);
        
        // Trigger animation
        setTimeout(() => {
            toast.element.classList.add('fade-in');
        }, 10);
        
        console.log(`Toast notification added: ${toast.type} - ${toast.message}`);
    }

    dismiss(toastId) {
        const toast = this.notifications.find(t => t.id === toastId);
        if (toast) {
            this.removeToast(toast);
        }
    }

    removeToast(toast) {
        // Clear timeout
        if (toast.timeoutId) {
            clearTimeout(toast.timeoutId);
        }
        
        // Remove from notifications array
        const index = this.notifications.indexOf(toast);
        if (index > -1) {
            this.notifications.splice(index, 1);
        }
        
        // Animate out and remove from DOM
        if (toast.element && toast.element.parentNode) {
            toast.element.style.transform = 'translateX(100%)';
            toast.element.style.opacity = '0';
            
            setTimeout(() => {
                if (toast.element && toast.element.parentNode) {
                    toast.element.parentNode.removeChild(toast.element);
                }
            }, 300);
        }
        
        console.log(`Toast notification removed: ${toast.type} - ${toast.message}`);
    }

    dismissAll() {
        // Create a copy of the array since we'll be modifying it
        const toastsToRemove = [...this.notifications];
        toastsToRemove.forEach(toast => this.removeToast(toast));
    }

    getIcon(type) {
        const icons = {
            success: `
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M9,20.42L2.79,14.21L5.62,11.38L9,14.77L18.88,4.88L21.71,7.71L9,20.42Z"/>
                </svg>
            `,
            error: `
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"/>
                </svg>
            `,
            warning: `
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M13,14H11V10H13M13,18H11V16H13M1,21H23L12,2L1,21Z"/>
                </svg>
            `,
            info: `
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M13,9H11V7H13M13,17H11V11H13M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z"/>
                </svg>
            `
        };
        
        return icons[type] || icons.info;
    }

    // Utility methods for common scenarios
    showConnectionStatus(isConnected) {
        if (isConnected) {
            this.success('Connected to voice recognition system');
        } else {
            this.error('Disconnected from voice recognition system');
        }
    }

    showLoadingComplete(message = 'Data loaded successfully') {
        this.success(message);
    }

    showError(error, context = '') {
        const message = context ? `${context}: ${error}` : error;
        this.error(message);
    }

    showSpeakerRecognized(speakerName, confidence) {
        this.success(`Speaker recognized: ${speakerName} (${confidence}% confidence)`);
    }

    showSystemStatus(status, message) {
        switch (status) {
            case 'online':
                this.success(message || 'System is online');
                break;
            case 'offline':
                this.error(message || 'System is offline');
                break;
            case 'warning':
                this.warning(message || 'System warning');
                break;
            default:
                this.info(message || 'System status update');
        }
    }

    // Configuration methods
    setMaxNotifications(max) {
        this.maxNotifications = max;
    }

    setDefaultDuration(duration) {
        this.defaultDuration = duration;
    }
}

// Global notification functions for easy access
function showNotification(message, type = 'info', duration = null) {
    return window.notificationManager.show(message, type, duration);
}

function showSuccess(message, duration = null) {
    return window.notificationManager.success(message, duration);
}

function showError(message, duration = null) {
    return window.notificationManager.error(message, duration);
}

function showWarning(message, duration = null) {
    return window.notificationManager.warning(message, duration);
}

function showInfo(message, duration = null) {
    return window.notificationManager.info(message, duration);
}

function dismissNotification(id) {
    window.notificationManager.dismiss(id);
}

function dismissAllNotifications() {
    window.notificationManager.dismissAll();
}

// Initialize notification manager
document.addEventListener('DOMContentLoaded', () => {
    window.notificationManager = new NotificationManager();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NotificationManager;
}