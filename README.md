A simple FastAPI application with WebSocket and Redis support.

# Install Dependencies
```bash
pip install -r requirements.txt
```

## Run Redis in Docker
```bash
docker run --name redis-server -p 6379:6379 redis
```

### Make sure Docker is running and port 6379 is not already in use.

## Run FastAPI Application
```bash
uvicorn main:app
```

## After starting, the server will be available at:
```text
http://localhost:8000/docs
```

# Test WebSocket Connection

## Open your browser console (F12 → Console) and paste the following code:
```js
const s = new WebSocket("ws://localhost:8000/ws");
s.onmessage = e => console.log("MSG:", e.data);
```

Once connected, you’ll see messages coming from the server.


Graceful Shutdown Logic


### 🔔 Signal Handling

- The server listens for termination signals: `SIGINT` (e.g. Ctrl+C)
- When a signal is received, `_signal_handler()` triggers the asynchronous `handle_shutdown()` coroutine.

### 🧩 What `handle_shutdown()` Does

1. **Sets shutdown flags:**
   - `shutdown_event.set()` signals that shutdown has started.
   - `stop_event.set()` stops the periodic broadcast loop.

2. **Notifies connected clients:**
   - If any WebSocket clients are connected, they receive:
     ```
     Server will shut down in {TIMEOUT} seconds, please disconnect.
     ```

3. **Waits for disconnection:**
   - Calls `manager.disconnect_timeout(TIMEOUT)` to wait for clients to disconnect voluntarily.

4. **Terminates the process:**
   - If all clients disconnect in time, the server exits cleanly.
   - If not, it logs a warning and forces shutdown after the timeout.
