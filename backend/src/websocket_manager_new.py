"""
WebSocket connection manager for real-time communication
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Set
from datetime import datetime
import psutil
from dataclasses import dataclass, asdict

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    cpu_usage: float
    memory_usage: float
    uptime: str
    status: str = "active"

@dataclass
class AudioMetrics:
    input_level: float
    quality_score: float
    noise_level: float

@dataclass
class DeviceCount:
    bluetooth: int = 0
    usb: int = 0
    network: int = 0

@dataclass
class RecognitionResult:
    speaker_name: str
    confidence: float
    timestamp: datetime

@dataclass
class DashboardData:
    system_status: SystemMetrics
    recognition_stats: dict
    audio_metrics: AudioMetrics
    device_count: DeviceCount
    current_speaker: Optional[RecognitionResult] = None

class WebSocketManager:
    """Manages WebSocket connections for audio streaming and dashboard updates"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.dashboard_connections: Set[WebSocket] = set()
        self.client_info: Dict[WebSocket, dict] = {}
        self.dashboard_data = DashboardData(
            system_status=SystemMetrics(0, 0, "0m"),
            recognition_stats={
                "total_sessions": 0,
                "success_rate": 0.0,
                "active_sessions": 0
            },
            audio_metrics=AudioMetrics(0, 0, 0),
            device_count=DeviceCount()
        )
        self.metrics_update_task = None
        self.start_time = time.time()
        
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
        
        # Send initial dashboard data
        await self.send_to_client(websocket, {
            "type": "dashboard_data",
            "data": asdict(self.dashboard_data)
        })
        
        # Start metrics updates if this is the first connection
        if len(self.active_connections) == 1:
            self.start_metrics_updates()
    
    async def connect_dashboard(self, websocket: WebSocket):
        """Connect a dashboard client"""
        await websocket.accept()
        self.dashboard_connections.add(websocket)
        self.client_info[websocket] = {
            "connected_at": datetime.utcnow(),
            "client_type": "dashboard",
            "messages_sent": 0,
            "messages_received": 0
        }
        logger.info(f"Dashboard connected. Total dashboards: {len(self.dashboard_connections)}")
        
        # Send initial dashboard data
        await self.send_to_client(websocket, {
            "type": "dashboard_data",
            "data": asdict(self.dashboard_data)
        })
        
        # Start metrics updates if this is the first connection
        if len(self.dashboard_connections) == 1:
            self.start_metrics_updates()
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        self.active_connections.discard(websocket)
        self.dashboard_connections.discard(websocket)
        self.client_info.pop(websocket, None)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections) + len(self.dashboard_connections)}")
        
        # Stop metrics updates if no connections remain
        if len(self.active_connections) == 0 and len(self.dashboard_connections) == 0:
            self.stop_metrics_updates()
    
    async def send_to_client(self, websocket: WebSocket, message: dict):
        """Send message to a specific client"""
        try:
            await websocket.send_text(json.dumps(message))
            if websocket in self.client_info:
                self.client_info[websocket]["messages_sent"] += 1
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections and not self.dashboard_connections:
            return
            
        all_connections = self.active_connections | self.dashboard_connections
        disconnected = set()
        
        for connection in all_connections:
            try:
                await connection.send_text(json.dumps(message))
                if connection in self.client_info:
                    self.client_info[connection]["messages_sent"] += 1
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.add(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_to_dashboard(self, message: dict):
        """Broadcast message to dashboard connections only"""
        if not self.dashboard_connections:
            return
            
        disconnected = set()
        for connection in self.dashboard_connections:
            try:
                await connection.send_text(json.dumps(message))
                if connection in self.client_info:
                    self.client_info[connection]["messages_sent"] += 1
            except Exception as e:
                logger.error(f"Error broadcasting to dashboard: {e}")
                disconnected.add(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    async def handle_message(self, websocket: WebSocket, message: dict):
        """Handle incoming WebSocket messages"""
        message_type = message.get("type")
        
        if message_type == "ping":
            await self.send_to_client(websocket, {
                "type": "pong",
                "timestamp": message.get("timestamp")
            })
        
        elif message_type == "request_dashboard_data":
            await self.send_to_client(websocket, {
                "type": "dashboard_data",
                "data": asdict(self.dashboard_data)
            })
        
        elif message_type == "request_metrics_update":
            await self.update_system_metrics()
            await self.send_to_client(websocket, {
                "type": "system_status",
                "data": asdict(self.dashboard_data.system_status)
            })
        
        elif message_type == "toggle_recognition":
            paused = message.get("paused", False)
            logger.info(f"Recognition {'paused' if paused else 'resumed'}")
            await self.broadcast_to_dashboard({
                "type": "recognition_status",
                "paused": paused
            })
    
    def start_metrics_updates(self):
        """Start periodic metrics updates"""
        if self.metrics_update_task is None:
            self.metrics_update_task = asyncio.create_task(self._metrics_update_loop())
    
    def stop_metrics_updates(self):
        """Stop periodic metrics updates"""
        if self.metrics_update_task:
            self.metrics_update_task.cancel()
            self.metrics_update_task = None
    
    async def _metrics_update_loop(self):
        """Periodic metrics update loop"""
        try:
            while True:
                await self.update_system_metrics()
                await self.broadcast_to_dashboard({
                    "type": "system_status",
                    "data": asdict(self.dashboard_data.system_status)
                })
                await asyncio.sleep(5)  # Update every 5 seconds
        except asyncio.CancelledError:
            logger.info("Metrics update loop cancelled")
        except Exception as e:
            logger.error(f"Error in metrics update loop: {e}")
    
    async def update_system_metrics(self):
        """Update system metrics"""
        try:
            # Get CPU and memory usage
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            
            # Calculate uptime
            uptime_seconds = time.time() - self.start_time
            uptime_str = self.format_uptime(uptime_seconds)
            
            # Determine system status
            status = "active"
            if cpu_percent > 90 or memory.percent > 90:
                status = "warning"
            if cpu_percent > 95 or memory.percent > 95:
                status = "error"
            
            self.dashboard_data.system_status = SystemMetrics(
                cpu_usage=round(cpu_percent, 1),
                memory_usage=round(memory.percent, 1),
                uptime=uptime_str,
                status=status
            )
            
        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")
    
    def format_uptime(self, seconds: float) -> str:
        """Format uptime in human readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    async def update_speaker_recognition(self, speaker_name: str, confidence: float):
        """Update current speaker recognition"""
        self.dashboard_data.current_speaker = RecognitionResult(
            speaker_name=speaker_name,
            confidence=confidence,
            timestamp=datetime.now()
        )
        
        # Update recognition stats
        self.dashboard_data.recognition_stats["total_sessions"] += 1
        
        await self.broadcast_to_dashboard({
            "type": "speaker_recognized",
            "speaker_name": speaker_name,
            "confidence": confidence,
            "timestamp": self.dashboard_data.current_speaker.timestamp.isoformat()
        })
    
    async def update_audio_metrics(self, input_level: float, quality_score: float, noise_level: float):
        """Update audio metrics"""
        self.dashboard_data.audio_metrics = AudioMetrics(
            input_level=input_level,
            quality_score=quality_score,
            noise_level=noise_level
        )
        
        await self.broadcast_to_dashboard({
            "type": "audio_level",
            "input_level": input_level,
            "quality_score": quality_score,
            "noise_level": noise_level
        })
    
    async def update_device_count(self, bluetooth: int = None, usb: int = None, network: int = None):
        """Update device counts"""
        if bluetooth is not None:
            self.dashboard_data.device_count.bluetooth = bluetooth
        if usb is not None:
            self.dashboard_data.device_count.usb = usb
        if network is not None:
            self.dashboard_data.device_count.network = network
        
        await self.broadcast_to_dashboard({
            "type": "device_update",
            "bluetooth": self.dashboard_data.device_count.bluetooth,
            "usb": self.dashboard_data.device_count.usb,
            "network": self.dashboard_data.device_count.network
        })
    
    async def send_audio_data(self, waveform_data: List[float], spectrum_data: List[float]):
        """Send real-time audio visualization data"""
        await self.broadcast_to_dashboard({
            "type": "audio_data",
            "waveform": waveform_data,
            "spectrum": spectrum_data
        })
    
    async def send_error(self, error_message: str, error_type: str = "error"):
        """Send error notification"""
        await self.broadcast_to_dashboard({
            "type": "error",
            "message": error_message,
            "error_type": error_type,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_connection_stats(self) -> dict:
        """Get connection statistics"""
        return {
            "active_audio_clients": len(self.active_connections),
            "active_dashboards": len(self.dashboard_connections),
            "total_clients": len(self.client_info),
            "client_details": [
                {
                    "client_type": info["client_type"],
                    "connected_at": info["connected_at"].isoformat(),
                    "messages_sent": info["messages_sent"],
                    "messages_received": info["messages_received"]
                }
                for info in self.client_info.values()
            ]
        }

# Global WebSocket manager instance
websocket_manager = WebSocketManager()