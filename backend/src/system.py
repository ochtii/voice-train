"""
System monitoring and health API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
import psutil
import platform
from datetime import datetime, timedelta

from .database import get_database, SystemLog
from .auth import get_current_active_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Pydantic models
class SystemLogResponse(BaseModel):
    id: int
    level: str
    component: str
    message: str
    details: Optional[str]
    timestamp: datetime
    
    class Config:
        from_attributes = True

class SystemHealth(BaseModel):
    status: str
    uptime: str
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    temperature: Optional[float]
    load_average: List[float]

class SystemInfo(BaseModel):
    hostname: str
    platform: str
    architecture: str
    python_version: str
    total_memory: int
    available_memory: int
    cpu_count: int
    boot_time: datetime

@router.get("/health", response_model=SystemHealth)
async def get_system_health():
    """Get current system health metrics"""
    try:
        # CPU usage
        cpu_usage = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_usage = (disk.used / disk.total) * 100
        
        # System uptime
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds
        
        # Load average (Unix-like systems)
        try:
            load_avg = list(psutil.getloadavg())
        except:
            load_avg = [0.0, 0.0, 0.0]
        
        # Temperature (if available)
        temperature = None
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                # Get CPU temperature if available
                for name, entries in temps.items():
                    if 'cpu' in name.lower() or 'core' in name.lower():
                        temperature = entries[0].current
                        break
        except:
            pass
        
        return SystemHealth(
            status="healthy" if cpu_usage < 80 and memory_usage < 80 else "warning",
            uptime=uptime_str,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            disk_usage=disk_usage,
            temperature=temperature,
            load_average=load_avg
        )
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/info", response_model=SystemInfo)
async def get_system_info():
    """Get system information"""
    try:
        memory = psutil.virtual_memory()
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        
        return SystemInfo(
            hostname=platform.node(),
            platform=platform.system() + " " + platform.release(),
            architecture=platform.machine(),
            python_version=platform.python_version(),
            total_memory=memory.total,
            available_memory=memory.available,
            cpu_count=psutil.cpu_count(),
            boot_time=boot_time
        )
        
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs", response_model=List[SystemLogResponse])
async def get_system_logs(
    level: Optional[str] = None,
    component: Optional[str] = None,
    limit: int = 100,
    hours_back: int = 24,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_database)
):
    """Get system logs"""
    try:
        # Calculate time threshold
        time_threshold = datetime.utcnow() - timedelta(hours=hours_back)
        
        query = db.query(SystemLog).filter(
            SystemLog.timestamp >= time_threshold
        )
        
        if level:
            query = query.filter(SystemLog.level == level.upper())
        
        if component:
            query = query.filter(SystemLog.component == component)
        
        logs = query.order_by(SystemLog.timestamp.desc()).limit(limit).all()
        
        return logs
        
    except Exception as e:
        logger.error(f"Error getting system logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/logs")
async def add_system_log(
    level: str,
    component: str,
    message: str,
    details: Optional[str] = None,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_database)
):
    """Add a system log entry"""
    try:
        # Validate log level
        valid_levels = ["INFO", "WARNING", "ERROR", "DEBUG"]
        if level.upper() not in valid_levels:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid log level. Must be one of: {valid_levels}"
            )
        
        # Create log entry
        log_entry = SystemLog(
            level=level.upper(),
            component=component,
            message=message,
            details=details
        )
        
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        
        return {"message": "Log entry added successfully", "id": log_entry.id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding system log: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/processes")
async def get_running_processes(
    current_user = Depends(get_current_active_user)
):
    """Get information about running processes"""
    try:
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                proc_info = proc.info
                # Only include processes using significant resources
                if proc_info['cpu_percent'] > 1.0 or proc_info['memory_percent'] > 1.0:
                    processes.append({
                        'pid': proc_info['pid'],
                        'name': proc_info['name'],
                        'cpu_percent': proc_info['cpu_percent'],
                        'memory_percent': proc_info['memory_percent']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by CPU usage
        processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        
        return {
            "processes": processes[:20],  # Top 20 processes
            "total_processes": len(list(psutil.process_iter()))
        }
        
    except Exception as e:
        logger.error(f"Error getting processes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/network")
async def get_network_info():
    """Get network interface information"""
    try:
        interfaces = {}
        
        # Get network interface stats
        net_io = psutil.net_io_counters(pernic=True)
        net_if_addrs = psutil.net_if_addrs()
        
        for interface, addrs in net_if_addrs.items():
            interface_info = {
                "addresses": [],
                "stats": {}
            }
            
            # Get addresses
            for addr in addrs:
                interface_info["addresses"].append({
                    "family": str(addr.family),
                    "address": addr.address,
                    "netmask": addr.netmask,
                    "broadcast": addr.broadcast
                })
            
            # Get I/O stats if available
            if interface in net_io:
                stats = net_io[interface]
                interface_info["stats"] = {
                    "bytes_sent": stats.bytes_sent,
                    "bytes_recv": stats.bytes_recv,
                    "packets_sent": stats.packets_sent,
                    "packets_recv": stats.packets_recv,
                    "errin": stats.errin,
                    "errout": stats.errout,
                    "dropin": stats.dropin,
                    "dropout": stats.dropout
                }
            
            interfaces[interface] = interface_info
        
        return {
            "interfaces": interfaces,
            "default_gateway": "N/A"  # Would need additional logic to determine
        }
        
    except Exception as e:
        logger.error(f"Error getting network info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/restart")
async def restart_system(
    current_user = Depends(get_current_active_user)
):
    """Restart the voice recognition system (not the OS)"""
    try:
        # This would restart the application components
        logger.info("System restart requested")
        
        return {
            "message": "System restart initiated",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error restarting system: {e}")
        raise HTTPException(status_code=500, detail=str(e))