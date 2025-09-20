"""
Device management API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import logging
from datetime import datetime

from .database import get_database, Device
from .auth import get_current_active_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Pydantic models
class DeviceCreate(BaseModel):
    device_id: str
    device_type: str
    device_name: Optional[str] = None
    mac_address: Optional[str] = None
    ip_address: Optional[str] = None

class DeviceResponse(BaseModel):
    id: int
    device_id: str
    device_type: str
    device_name: Optional[str]
    mac_address: Optional[str]
    ip_address: Optional[str]
    is_paired: bool
    is_connected: bool
    last_seen: datetime
    audio_quality: float
    
    class Config:
        from_attributes = True

class DeviceUpdate(BaseModel):
    device_name: Optional[str] = None
    is_paired: Optional[bool] = None
    is_connected: Optional[bool] = None
    audio_quality: Optional[float] = None

@router.get("/list", response_model=List[DeviceResponse])
async def list_devices(
    device_type: Optional[str] = None,
    connected_only: bool = False,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_database)
):
    """List all devices"""
    try:
        query = db.query(Device)
        
        if device_type:
            query = query.filter(Device.device_type == device_type)
        
        if connected_only:
            query = query.filter(Device.is_connected == True)
        
        devices = query.all()
        return devices
        
    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pair", response_model=DeviceResponse)
async def pair_device(
    device: DeviceCreate,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_database)
):
    """Pair a new device"""
    try:
        # Check if device already exists
        existing_device = db.query(Device).filter(Device.device_id == device.device_id).first()
        if existing_device:
            raise HTTPException(status_code=400, detail="Device already exists")
        
        # Create new device
        db_device = Device(
            device_id=device.device_id,
            device_type=device.device_type,
            device_name=device.device_name,
            mac_address=device.mac_address,
            ip_address=device.ip_address,
            is_paired=True,
            is_connected=False,
            last_seen=datetime.utcnow(),
            audio_quality=0.0
        )
        
        db.add(db_device)
        db.commit()
        db.refresh(db_device)
        
        logger.info(f"Device paired: {device.device_id} ({device.device_type})")
        
        return db_device
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pairing device: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    device_update: DeviceUpdate,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_database)
):
    """Update device information"""
    try:
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Update fields
        update_data = device_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(device, field, value)
        
        device.last_seen = datetime.utcnow()
        
        db.commit()
        db.refresh(device)
        
        return device
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating device: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{device_id}")
async def remove_device(
    device_id: str,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_database)
):
    """Remove a paired device"""
    try:
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        db.delete(device)
        db.commit()
        
        logger.info(f"Device removed: {device_id}")
        
        return {"message": "Device removed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing device: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scan")
async def scan_devices(
    device_type: str = "all",
    current_user = Depends(get_current_active_user)
):
    """Scan for available devices"""
    try:
        # This would implement actual device discovery
        # For now, return mock data
        discovered_devices = []
        
        if device_type in ["all", "bluetooth"]:
            # Mock Bluetooth devices
            discovered_devices.extend([
                {
                    "device_id": "bt_device_001",
                    "device_type": "bluetooth",
                    "device_name": "Android Phone",
                    "mac_address": "AA:BB:CC:DD:EE:FF",
                    "signal_strength": -45
                }
            ])
        
        if device_type in ["all", "network"]:
            # Mock network devices
            discovered_devices.extend([
                {
                    "device_id": "net_device_001",
                    "device_type": "network",
                    "device_name": "Windows Client",
                    "ip_address": "192.168.1.100",
                    "signal_strength": -30
                }
            ])
        
        if device_type in ["all", "usb"]:
            # Mock USB devices
            discovered_devices.extend([
                {
                    "device_id": "usb_mic_001",
                    "device_type": "usb",
                    "device_name": "USB Microphone",
                    "vendor_id": "0x1234",
                    "product_id": "0x5678"
                }
            ])
        
        return {
            "discovered_devices": discovered_devices,
            "scan_time": datetime.utcnow().isoformat(),
            "device_type": device_type
        }
        
    except Exception as e:
        logger.error(f"Error scanning devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/types")
async def get_device_types():
    """Get supported device types"""
    return {
        "device_types": [
            {
                "type": "bluetooth",
                "name": "Bluetooth Audio",
                "description": "Bluetooth SCO audio devices (Android phones, headsets)"
            },
            {
                "type": "usb",
                "name": "USB Microphone",
                "description": "USB audio input devices"
            },
            {
                "type": "network",
                "name": "Network Client",
                "description": "WiFi/Ethernet connected clients (Windows app, web clients)"
            }
        ]
    }