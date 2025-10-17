import asyncio
import signal
import sys
import redis.asyncio as redis

REDIS_CHANNEL = "shutdown_channel"
shutdown_event = asyncio.Event()

async def publish_shutdown():
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)
    await r.publish(REDIS_CHANNEL, "shutdown")
    print("🔴 Published shutdown signal to Redis")

def signal_handler(sig, frame):
    print("🛑 Ctrl+C received. Initiating shutdown...")
    shutdown_event.set()

async def main():
    signal.signal(signal.SIGINT, signal_handler)
    await shutdown_event.wait()
    await publish_shutdown()
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
