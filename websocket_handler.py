"""
WebSocket Handler for Real-time Updates
"""
from typing import Dict, Set
import json
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set] = {}  # job_id -> set of websockets
        
    async def connect(self, websocket, job_id: str):
        """Register new WebSocket connection for a job"""
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        self.active_connections[job_id].add(websocket)
        logger.info(f"Client connected to job {job_id}")
        
    def disconnect(self, websocket, job_id: str):
        """Remove WebSocket connection"""
        if job_id in self.active_connections:
            self.active_connections[job_id].discard(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
        logger.info(f"Client disconnected from job {job_id}")
        
    async def send_update(self, job_id: str, message: dict):
        """Send update to all clients watching this job"""
        if job_id not in self.active_connections:
            return
            
        # Add timestamp
        message['timestamp'] = datetime.now().isoformat()
        
        # Send to all connected clients
        disconnected = set()
        for connection in self.active_connections[job_id]:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                disconnected.add(connection)
        
        # Clean up dead connections
        for conn in disconnected:
            self.disconnect(conn, job_id)
    
    async def broadcast_progress(self, job_id: str, current: int, total: int, status: str = "processing"):
        """Send progress update"""
        message = {
            'type': 'progress',
            'job_id': job_id,
            'current': current,
            'total': total,
            'percentage': round((current / total * 100), 1) if total > 0 else 0,
            'status': status
        }
        await self.send_update(job_id, message)
    
    async def broadcast_invoice_complete(self, job_id: str, invoice_data: dict):
        """Notify when single invoice is processed"""
        message = {
            'type': 'invoice_complete',
            'job_id': job_id,
            'invoice': invoice_data
        }
        await self.send_update(job_id, message)
    
    async def broadcast_job_complete(self, job_id: str, summary: dict):
        """Notify when entire job is complete"""
        message = {
            'type': 'job_complete',
            'job_id': job_id,
            'summary': summary
        }
        await self.send_update(job_id, message)
    
    async def broadcast_error(self, job_id: str, error: str, file_name: str = None):
        """Send error notification"""
        message = {
            'type': 'error',
            'job_id': job_id,
            'error': error,
            'file_name': file_name
        }
        await self.send_update(job_id, message)

# Global connection manager
manager = ConnectionManager()
