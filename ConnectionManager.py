import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List
import logging
import redis.asyncio as redis

logger = logging.getLogger("uvicorn.error")
REDIS_CONNECTIONS_KEY = "active_ws_connections"
REDIS_CHANNEL = "broadcast_channel"
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self.lock:
            self.active_connections.append(websocket)

        await redis_client.incr(REDIS_CONNECTIONS_KEY)
        count = await self.count_all()

        logger.info(f"Client connected. Local: {len(self.active_connections)}, Global: {count}")


    async def disconnect(self, websocket: WebSocket) -> None:
        async with self.lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        await redis_client.decr(REDIS_CONNECTIONS_KEY)
        count = await self.count_all()
        logger.info(f"Client disconnected. Local: {len(self.active_connections)}, Global: {count}")

    async def broadcast(self, message: str):
        # Publish msg in redis
        await redis_client.publish(REDIS_CHANNEL, message)

    async def local_broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                print("Local broadcast not working -----------")
                pass

    async def listen_to_channel(self):
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(REDIS_CHANNEL)

        async for msg in pubsub.listen():
            if msg["type"] == "message":
                await self.local_broadcast(msg["data"])

    async def count(self) -> int:
        async with self.lock:
            return len(self.active_connections)

    async def count_all(self) -> int:
        count = await redis_client.get(REDIS_CONNECTIONS_KEY)
        return int(count) if count else 0

    async def notify_shutdown(self, message: str):
        await self.broadcast(message)

    async def disconnect_timeout(self, timeout: int):
        start = asyncio.get_event_loop().time()
        while True:
            count = await self.count_all()
            elapsed = asyncio.get_event_loop().time() - start
            remaining = timeout - int(elapsed)

            logger.info(f"Waiting for stop: {count} client(s), remaining time: {remaining}")

            if count == 0:
                logger.info("All clients disconnected before timer")
                return True
            if elapsed >= timeout:
                logger.warning(f"Timeout. Remaining clients: {count}")
                return False
            await asyncio.sleep(1)