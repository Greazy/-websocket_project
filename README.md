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
