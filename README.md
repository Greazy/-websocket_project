A simple FastAPI application with WebSocket and Redis support.

📦 Install Dependencies
pip install -r requirements.txt

🧱 Run Redis in Docker
docker run --name redis-server -p 6379:6379 redis


⚠️ Make sure Docker is running and port 6379 is not already in use.

▶️ Run FastAPI Application
uvicorn main:app --reload


After starting, the server will be available at:
👉 http://localhost:8000/docs

💬 Test WebSocket Connection

Open your browser console (F12 → Console) and paste the following code:

const s = new WebSocket("ws://localhost:8000/ws");
s.onmessage = e => console.log("MSG:", e.data);