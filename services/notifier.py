from fastapi import WebSocket
from typing import List, Dict
import asyncio

connected: List[WebSocket] = []

async def register(ws: WebSocket):
    await ws.accept()
    connected.append(ws)

async def unregister(ws: WebSocket):
    try:
        connected.remove(ws)
    except ValueError:
        pass

async def broadcast(event: Dict):
    dead = []
    for ws in list(connected):
        try:
            await ws.send_json(event)
        except Exception:
            dead.append(ws)
    for d in dead:
        await unregister(d)
