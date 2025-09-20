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
    
    def disconnect_dashboard(self, websocket: WebSocket):
        """Disconnect a dashboard client"""
        self.dashboard_connections.discard(websocket)
        self.client_info.pop(websocket, None)
        logger.info(f"Dashboard disconnected. Remaining dashboards: {len(self.dashboard_connections)}")
        
        # Stop metrics updates if no dashboard connections remain
        if len(self.dashboard_connections) == 0:
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
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def broadcast_to_dashboard(self, data: dict):
        """Broadcast data to all connected dashboard clients"""
        disconnected = []
        for websocket in self.dashboard_connections:
            try:
                await websocket.send_json(data)
                if websocket in self.client_info:
                    self.client_info[websocket]["messages_sent"] += 1
            except Exception as e:
                logger.error(f"Error broadcasting to dashboard: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected dashboards
        for websocket in disconnected:
            self.disconnect_dashboard(websocket)
    
    async def send_recognition_result(self, speaker_name: str, confidence: float, device_id: str = None):
        """Send recognition result to dashboard"""
        data = {
            "type": "recognition_result",
            "speaker": speaker_name,
            "confidence": confidence,
            "device_id": device_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_dashboard(data)
    
    async def send_audio_level(self, level: float, device_id: str = None):
        """Send audio level update to dashboard"""
        data = {
            "type": "audio_level",
            "level": level,
            "device_id": device_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_dashboard(data)
    
    async def send_device_status(self, device_id: str, status: str, device_type: str = None):
        """Send device status update to dashboard"""
        data = {
            "type": "device_status",
            "device_id": device_id,
            "status": status,
            "device_type": device_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_dashboard(data)
    
    async def send_system_metrics(self, metrics: dict):
        """Send system performance metrics to dashboard"""
        data = {
            "type": "system_metrics",
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_dashboard(data)
    
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
    
    async def heartbeat_task(self):
        """Background task to send periodic heartbeats"""
        while True:
            try:
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                
                if self.dashboard_connections:
                    stats = self.get_connection_stats()
                    await self.broadcast_to_dashboard({
                        "type": "heartbeat",
                        "stats": stats,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
            except Exception as e:
                logger.error(f"Heartbeat task error: {e}")
    
    async def cleanup(self):
        """Cleanup all connections"""
        # Close all audio connections
        for websocket in self.active_connections.copy():
            try:
                await websocket.close()
            except:
                pass
        
        # Close all dashboard connections
        for websocket in self.dashboard_connections.copy():
            try:
                await websocket.close()
            except:
                pass
        
        self.active_connections.clear()
        self.dashboard_connections.clear()
        self.client_info.clear()
        
        logger.info("WebSocket manager cleaned up")