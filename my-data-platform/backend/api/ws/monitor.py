from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime, timezone
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send welcome event immediately on connect
        await websocket.send_json({
            "type": "system:connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "message": "Real-time monitor connected",
                "active_connections": len(manager.active_connections),
            }
        })

        # Seed with recent activity from DB (last 10 events)
        try:
            from database import SessionLocal
            from models import UserActivity
            with SessionLocal() as db:
                recent = db.query(UserActivity).order_by(
                    UserActivity.timestamp.desc()
                ).limit(10).all()
            for act in reversed(recent):
                await websocket.send_json({
                    "type": "activity:history",
                    "timestamp": act.timestamp.isoformat() if act.timestamp else datetime.now(timezone.utc).isoformat(),
                    "payload": {
                        "action": act.action,
                        "username": act.username,
                        "resource": act.resource,
                        "status": act.metadata_info.get("status_code", 200) if act.metadata_info else 200,
                        "duration_ms": act.metadata_info.get("duration_ms", 0) if act.metadata_info else 0,
                    }
                })
        except Exception as seed_exc:
            logger.warning(f"Could not seed activity on WS connect: {seed_exc}")

        # Heartbeat loop — ping every 10 seconds
        tick = 0
        while True:
            await asyncio.sleep(10)
            tick += 1
            await websocket.send_json({
                "type": "system:heartbeat",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "tick": tick,
                    "active_connections": len(manager.active_connections),
                }
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

async def broadcast_event(event: dict):
    await manager.broadcast(event)
