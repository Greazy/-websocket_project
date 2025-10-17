import asyncio
import logging
import signal
import sys
import pprint
from typing import List
from fastapi import Request, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
from pydantic import BaseModel
from fastapi import HTTPException

from ConnectionManager import ConnectionManager


TIMEOUT = 10

logger = logging.getLogger("uvicorn.error")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
REDIS_CONNECTIONS_KEY = "active_ws_connections"

REDIS_CHANNEL = "broadcast_channel"

clients = set()
manager = ConnectionManager()
shutdown_event = asyncio.Event()
shutdown_in_progress = False

broadcast_task: asyncio.Task | None = None
stop_event = asyncio.Event()


class BroadcastMessage(BaseModel):
    message: str


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        await manager.disconnect(websocket)

@app.post("/broadcast")
async def manual_broadcast(payload: BroadcastMessage):
    if not payload.message.strip():
        raise HTTPException(status_code=422, detail="Message cannot be empty")

    await manager.broadcast(payload.message)
    return {"status": "sent", "message": payload.message}

async def periodic_broadcast():
    """Send notifications every 10 seconds until stopped"""
    try:
        while not stop_event.is_set():
            count = await manager.count_all()
            if count > 0:
                await manager.broadcast(f"Hello from server, time: timeeee")
            await asyncio.sleep(10)
    except asyncio.CancelledError:
        logger.info("Broadcaster task cancelled gracefully")
    finally:
        logger.info("Broadcaster stopped")

def _signal_handler():
    loop = asyncio.get_event_loop()
    if not shutdown_event.is_set():
        logger.warning("Shutdown signal received. Graceful shutdown")
        loop.create_task(handle_shutdown())
    else:
        logger.warning("Not allowed.")

@app.on_event("startup")
def setup_signal_handlers():
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            import signal as sigmod
            sigmod.signal(sig, lambda s, f: _signal_handler())

async def handle_shutdown():
    global shutdown_in_progress
    if shutdown_in_progress:
        return
    shutdown_in_progress = True

    stop_event.set()
    shutdown_event.set()

    count = await manager.count_all()
    if count > 0:
        await manager.notify_shutdown(f"Server will shut down in {TIMEOUT} seconds, please disconnect.")
        logger.info(f"Sent shutdown notification to {count} clients")
    else:
        logger.info("No active clients — shutting down immediately")

    result = await manager.disconnect_timeout(timeout=TIMEOUT)
    if result:
        logger.info("All clients have disconnected. Shutting down.")
    else:
        logger.warning("Client wait timeout. Forcing shutdown.")

    logger.info("Terminating process")
    sys.exit(0)


@app.on_event("startup")
async def startup_event():
    await redis_client.set(REDIS_CONNECTIONS_KEY, 0)
    global broadcast_task
    broadcast_task = asyncio.create_task(periodic_broadcast())
    asyncio.create_task(manager.listen_to_channel())
    logger.info("Server is running. ))")


@app.on_event("shutdown")
async def shutdown_broadcast_task():
    """Properly stop background broadcaster"""
    print("Shutdown event: stopping broadcaster...")
    stop_event.set()

    global broadcast_task
    if broadcast_task and not broadcast_task.done():
        broadcast_task.cancel()
        try:
            await broadcast_task

        except asyncio.CancelledError:
            print("Broadcast task finished cleanly")
