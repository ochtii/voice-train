// Audio Visualizer for Real-time Audio Data
class AudioVisualizer {
    constructor() {
        this.waveformCanvas = null;
        this.spectrumCanvas = null;
        this.waveformContext = null;
        this.spectrumContext = null;
        this.animationFrameId = null;
        this.isActive = true;
        
        // Audio data buffers
        this.waveformData = new Float32Array(512);
        this.spectrumData = new Float32Array(256);
        
        // Visualization settings
        this.waveformColor = '#3b82f6';
        this.spectrumColors = ['#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444'];
        
        this.init();
    }

    init() {
        // Initialize canvases
        this.waveformCanvas = document.getElementById('waveformCanvas');
        this.spectrumCanvas = document.getElementById('spectrumCanvas');
        
        if (this.waveformCanvas) {
            this.waveformContext = this.waveformCanvas.getContext('2d');
            this.setupCanvas(this.waveformCanvas, this.waveformContext);
        }
        
        if (this.spectrumCanvas) {
            this.spectrumContext = this.spectrumCanvas.getContext('2d');
            this.setupCanvas(this.spectrumCanvas, this.spectrumContext);
        }
        
        // Start animation loop
        this.animate();
        
        // Set up WebSocket listeners for audio data
        if (window.wsManager) {
            window.wsManager.on('audio_data', this.handleAudioData.bind(this));
            window.wsManager.on('waveform_data', this.handleWaveformData.bind(this));
            window.wsManager.on('spectrum_data', this.handleSpectrumData.bind(this));
        }
        
        // Handle theme changes
        document.addEventListener('themeChanged', () => {
            this.updateColors();
        });
    }

    setupCanvas(canvas, context) {
        const rect = canvas.getBoundingClientRect();
        const devicePixelRatio = window.devicePixelRatio || 1;
        
        // Set actual size in memory (scaled up for retina displays)
        canvas.width = rect.width * devicePixelRatio;
        canvas.height = rect.height * devicePixelRatio;
        
        // Scale the context to ensure correct drawing operations
        context.scale(devicePixelRatio, devicePixelRatio);
        
        // Set the size of the drawBuffer (the real size)
        canvas.style.width = rect.width + 'px';
        canvas.style.height = rect.height + 'px';
        
        // Set line properties
        context.lineWidth = 2;
        context.lineCap = 'round';
        context.lineJoin = 'round';
    }

    updateColors() {
        const theme = document.documentElement.getAttribute('data-theme');
        if (theme === 'dark') {
            this.waveformColor = '#60a5fa';
            this.spectrumColors = ['#60a5fa', '#22d3ee', '#34d399', '#fbbf24', '#f87171'];
        } else {
            this.waveformColor = '#3b82f6';
            this.spectrumColors = ['#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444'];
        }
    }

    handleAudioData(data) {
        if (data.waveform) {
            this.waveformData = new Float32Array(data.waveform);
        }
        if (data.spectrum) {
            this.spectrumData = new Float32Array(data.spectrum);
        }
    }

    handleWaveformData(data) {
        if (data.data) {
            this.waveformData = new Float32Array(data.data);
        }
    }

    handleSpectrumData(data) {
        if (data.data) {
            this.spectrumData = new Float32Array(data.data);
        }
    }

    drawWaveform() {
        if (!this.waveformCanvas || !this.waveformContext) return;
        
        const canvas = this.waveformCanvas;
        const ctx = this.waveformContext;
        const width = canvas.clientWidth;
        const height = canvas.clientHeight;
        
        // Clear canvas
        ctx.clearRect(0, 0, width, height);
        
        // Draw waveform
        ctx.strokeStyle = this.waveformColor;
        ctx.beginPath();
        
        const sliceWidth = width / this.waveformData.length;
        let x = 0;
        
        for (let i = 0; i < this.waveformData.length; i++) {
            const v = this.waveformData[i];
            const y = (v + 1) * height / 2; // Convert from [-1,1] to [0,height]
            
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
            
            x += sliceWidth;
        }
        
        ctx.stroke();
        
        // Draw center line
        ctx.strokeStyle = this.getThemedColor('--border-primary');
        ctx.globalAlpha = 0.3;
        ctx.beginPath();
        ctx.moveTo(0, height / 2);
        ctx.lineTo(width, height / 2);
        ctx.stroke();
        ctx.globalAlpha = 1.0;
    }

    drawSpectrum() {
        if (!this.spectrumCanvas || !this.spectrumContext) return;
        
        const canvas = this.spectrumCanvas;
        const ctx = this.spectrumContext;
        const width = canvas.clientWidth;
        const height = canvas.clientHeight;
        
        // Clear canvas
        ctx.clearRect(0, 0, width, height);
        
        // Draw spectrum bars
        const barWidth = width / this.spectrumData.length;
        
        for (let i = 0; i < this.spectrumData.length; i++) {
            const barHeight = (this.spectrumData[i] / 255) * height;
            const x = i * barWidth;
            const y = height - barHeight;
            
            // Create gradient for bar
            const gradient = ctx.createLinearGradient(0, height, 0, 0);
            const colorIndex = Math.floor((i / this.spectrumData.length) * this.spectrumColors.length);
            const color = this.spectrumColors[Math.min(colorIndex, this.spectrumColors.length - 1)];
            
            gradient.addColorStop(0, color + '80'); // 50% opacity
            gradient.addColorStop(1, color);
            
            ctx.fillStyle = gradient;
            ctx.fillRect(x, y, barWidth - 1, barHeight);
        }
        
        // Draw frequency grid lines
        ctx.strokeStyle = this.getThemedColor('--border-primary');
        ctx.globalAlpha = 0.2;
        ctx.lineWidth = 1;
        
        // Vertical lines for frequency markers
        for (let i = 0; i <= 4; i++) {
            const x = (i / 4) * width;
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, height);
            ctx.stroke();
        }
        
        // Horizontal lines for amplitude markers
        for (let i = 0; i <= 4; i++) {
            const y = (i / 4) * height;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }
        
        ctx.globalAlpha = 1.0;
        ctx.lineWidth = 2;
    }

    getThemedColor(cssVariable) {
        return getComputedStyle(document.documentElement)
            .getPropertyValue(cssVariable)
            .trim();
    }

    animate() {
        if (!this.isActive) return;
        
        this.drawWaveform();
        this.drawSpectrum();
        
        this.animationFrameId = requestAnimationFrame(() => this.animate());
    }

    generateDemoData() {
        // Generate demo waveform data (sine wave with noise)
        const time = Date.now() * 0.001;
        for (let i = 0; i < this.waveformData.length; i++) {
            const phase = (i / this.waveformData.length) * Math.PI * 4 + time;
            const noise = (Math.random() - 0.5) * 0.1;
            this.waveformData[i] = Math.sin(phase) * 0.5 + noise;
        }
        
        // Generate demo spectrum data
        for (let i = 0; i < this.spectrumData.length; i++) {
            const frequency = i / this.spectrumData.length;
            const amplitude = Math.max(0, 
                100 * Math.exp(-frequency * 5) + 
                50 * Math.sin(time * 2 + frequency * 10) +
                Math.random() * 20
            );
            this.spectrumData[i] = Math.min(255, amplitude);
        }
    }

    start() {
        this.isActive = true;
        if (!this.animationFrameId) {
            this.animate();
        }
    }

    stop() {
        this.isActive = false;
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
    }

    toggle() {
        if (this.isActive) {
            this.stop();
        } else {
            this.start();
        }
        return this.isActive;
    }

    resize() {
        if (this.waveformCanvas && this.waveformContext) {
            this.setupCanvas(this.waveformCanvas, this.waveformContext);
        }
        if (this.spectrumCanvas && this.spectrumContext) {
            this.setupCanvas(this.spectrumCanvas, this.spectrumContext);
        }
    }
}

// Initialize audio visualizer when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.audioVisualizer = new AudioVisualizer();
    
    // Handle window resize
    window.addEventListener('resize', () => {
        if (window.audioVisualizer) {
            window.audioVisualizer.resize();
        }
    });
    
    // Start demo data generation for testing
    setInterval(() => {
        if (window.audioVisualizer && !window.wsManager?.isConnected()) {
            window.audioVisualizer.generateDemoData();
        }
    }, 50); // 20 FPS for demo data
});