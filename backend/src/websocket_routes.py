"""
FastAPI routes for WebSocket connections and Web UI integration
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
import logging
import json
import asyncio
from pathlib import Path

from .websocket_manager_new import websocket_manager

logger = logging.getLogger(__name__)

# Create router for WebSocket and Web UI routes
websocket_router = APIRouter()

# Set up templates and static files
templates_dir = Path(__file__).parent.parent.parent / "webui" / "templates"
static_dir = Path(__file__).parent.parent.parent / "webui" / "static"

templates = Jinja2Templates(directory=str(templates_dir))

@websocket_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for dashboard communication"""
    await websocket_manager.connect_dashboard(websocket)
    
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await websocket_manager.handle_message(websocket, message)
                
                # Update message received counter
                if websocket in websocket_manager.client_info:
                    websocket_manager.client_info[websocket]["messages_received"] += 1
                    
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from WebSocket: {data}")
                await websocket_manager.send_to_client(websocket, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await websocket_manager.send_to_client(websocket, {
                    "type": "error", 
                    "message": str(e)
                })
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        websocket_manager.disconnect(websocket)

@websocket_router.websocket("/ws/audio")
async def audio_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for audio streaming from clients"""
    await websocket_manager.connect(websocket)
    
    try:
        while True:
            # Receive audio data
            data = await websocket.receive_bytes()
            
            # Process audio data here
            # This would integrate with your audio processing pipeline
            logger.debug(f"Received audio data: {len(data)} bytes")
            
            # For demo purposes, send fake audio visualization data
            import numpy as np
            
            # Generate demo waveform and spectrum data
            waveform = np.sin(np.linspace(0, 4*np.pi, 512)).tolist()
            spectrum = np.abs(np.random.normal(0, 0.1, 256)).tolist()
            
            await websocket_manager.send_audio_data(waveform, spectrum)
            
    except WebSocketDisconnect:
        logger.info("Audio WebSocket client disconnected normally")
    except Exception as e:
        logger.error(f"Audio WebSocket error: {e}")
    finally:
        websocket_manager.disconnect(websocket)

# Web UI Routes
@websocket_router.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Serve the main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@websocket_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_redirect(request: Request):
    """Redirect to main dashboard"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@websocket_router.get("/enrollment", response_class=HTMLResponse)
async def enrollment_page(request: Request):
    """Serve the speaker enrollment page"""
    return templates.TemplateResponse("enrollment.html", {"request": request})

@websocket_router.get("/devices", response_class=HTMLResponse)
async def devices_page(request: Request):
    """Serve the device management page"""
    return templates.TemplateResponse("devices.html", {"request": request})

@websocket_router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Serve the settings page"""
    return templates.TemplateResponse("settings.html", {"request": request})

# API Endpoints for dashboard data
@websocket_router.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """Get current dashboard statistics"""
    try:
        from dataclasses import asdict
        return {
            "status": "success",
            "data": asdict(websocket_manager.dashboard_data)
        }
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@websocket_router.get("/api/dashboard/connections")
async def get_connection_stats():
    """Get WebSocket connection statistics"""
    try:
        return {
            "status": "success",
            "data": websocket_manager.get_connection_stats()
        }
    except Exception as e:
        logger.error(f"Error getting connection stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@websocket_router.post("/api/dashboard/simulate-recognition")
async def simulate_recognition(speaker_name: str, confidence: float):
    """Simulate a speaker recognition event for testing"""
    try:
        if not 0 <= confidence <= 100:
            raise ValueError("Confidence must be between 0 and 100")
            
        await websocket_manager.update_speaker_recognition(speaker_name, confidence)
        
        return {
            "status": "success",
            "message": f"Simulated recognition: {speaker_name} ({confidence}%)"
        }
    except Exception as e:
        logger.error(f"Error simulating recognition: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@websocket_router.post("/api/dashboard/simulate-audio")
async def simulate_audio_metrics(input_level: float, quality_score: float, noise_level: float):
    """Simulate audio metrics for testing"""
    try:
        await websocket_manager.update_audio_metrics(input_level, quality_score, noise_level)
        
        return {
            "status": "success",
            "message": "Audio metrics updated"
        }
    except Exception as e:
        logger.error(f"Error simulating audio metrics: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Background task to simulate system activity for demo
async def demo_background_task():
    """Background task to simulate system activity"""
    import random
    import time
    
    demo_speakers = ["John Doe", "Jane Smith", "Bob Wilson", "Alice Brown", "Charlie Davis"]
    
    while True:
        try:
            # Simulate random speaker recognition
            if random.random() < 0.3:  # 30% chance every 10 seconds
                speaker = random.choice(demo_speakers)
                confidence = random.uniform(75, 98)
                await websocket_manager.update_speaker_recognition(speaker, confidence)
            
            # Simulate audio metrics
            input_level = random.uniform(50, 90)
            quality_score = random.uniform(70, 95)
            noise_level = random.uniform(5, 25)
            await websocket_manager.update_audio_metrics(input_level, quality_score, noise_level)
            
            # Simulate device counts
            bluetooth = random.randint(0, 3)
            usb = random.randint(0, 2)
            network = random.randint(1, 5)
            await websocket_manager.update_device_count(bluetooth, usb, network)
            
            await asyncio.sleep(10)  # Wait 10 seconds
            
        except asyncio.CancelledError:
            logger.info("Demo background task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in demo background task: {e}")
            await asyncio.sleep(10)

# Start demo task when module is imported
demo_task = None

def start_demo_task():
    """Start the demo background task"""
    global demo_task
    if demo_task is None:
        demo_task = asyncio.create_task(demo_background_task())

def stop_demo_task():
    """Stop the demo background task"""
    global demo_task
    if demo_task:
        demo_task.cancel()
        demo_task = None