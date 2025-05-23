"""
ASCII-CSV telemetry *and* command bridge
  MCU  <--- (commands)  WebSocket  browser
  MCU  ---> (telemetry) WebSocket  browser

Start:
    python server.py [SERIAL_PORT] [BAUD] [--dummy]

Dependencies: fastapi, uvicorn[standard], pyserial   (see requirements.txt)
"""

from __future__ import annotations
import asyncio, json, sys, threading, time
from pathlib import Path
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import serial  # PySerial

# ── user-editable telemetry columns ────────────────────────────────────────────
COLUMNS: List[str] = ["counter", "temperature", "voltage"]  # must match CSV order

# ── CLI args ──────────────────────────────────────────────────────────────────
SERIAL_PORT = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "COM5"
BAUD        = int(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else 9600
USE_DUMMY   = "--dummy" in sys.argv

# ── FastAPI & globals ─────────────────────────────────────────────────────────
app     = FastAPI()
clients: set[WebSocket] = set()
cmd_queue: asyncio.Queue[str] = asyncio.Queue()

# ── WebSocket endpoint (both directions) ─────────────────────────────────────
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            data = await ws.receive_text()          # ← command from browser
            msg = json.loads(data)
            if msg.get("kind") == "command":
                await cmd_queue.put(msg["body"])    # enqueue for serial
    except WebSocketDisconnect:
        clients.discard(ws)

# ── static files ─────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="public"), name="static")
@app.get("/")
async def index():
    return FileResponse(Path("public/index.html"))

# ── broadcast helper ─────────────────────────────────────────────────────────
async def broadcast(text: str):
    for ws in list(clients):
        try:
            await ws.send_text(text)
        except Exception:
            clients.discard(ws)

# ── telemetry generator: real serial or dummy wave ───────────────────────────
def serial_reader(loop: asyncio.AbstractEventLoop):

    if USE_DUMMY:
        print("[DUMMY] mode – no serial port used")
        cnt = 0
        while True:
            payload = {
                "counter": cnt & 0xFF,
                "temperature": 25.0 + 5 * (cnt % 60) / 60,
                "voltage": 3.3 + 0.1 * ((cnt // 30) % 2),
                "counter_ext": cnt,
                "timestamp": int(time.time() * 1000),
            }
            asyncio.run_coroutine_threadsafe(
                broadcast(json.dumps({"kind": "telemetry", **payload})), loop)
            cnt += 1
            time.sleep(1)
        # unreachable

    # ── real serial port ──
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD, timeout=1)
        print(f"[SER] opened {SERIAL_PORT} @ {BAUD}")
    except serial.SerialException as e:
        print(f"[SER] open failed: {e}")
        return

    prev_u8 = None
    overflow = 0

    while True:
        # ⇢ telemetry RX -------------------------------------------------------
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if line:
            parts = line.split(",")
            if len(parts) == len(COLUMNS):
                try:
                    counter_u8 = int(parts[0]) & 0xFF
                    values = [counter_u8] + [float(x) for x in parts[1:]]
                except ValueError:
                    print("[SER] parse error:", line)
                    values = None
                if values:
                    if prev_u8 is not None and counter_u8 < prev_u8:
                        overflow += 1
                    prev_u8 = counter_u8
                    payload = {
                        **dict(zip(COLUMNS, values)),
                        "counter_ext": overflow * 256 + counter_u8,
                        "timestamp": int(time.time() * 1000),
                    }
                    asyncio.run_coroutine_threadsafe(
                        broadcast(json.dumps({"kind": "telemetry", **payload})), loop)
        # ⇢ command TX ---------------------------------------------------------
        try:
            cmd = cmd_queue.get_nowait()
            ser.write((cmd + "\n").encode("ascii"))
            print("[SER←CMD]", cmd)
            asyncio.run_coroutine_threadsafe(
                broadcast(json.dumps({"kind": "ack", "body": cmd})), loop)
        except asyncio.QueueEmpty:
            pass

# ── FastAPI startup: launch the reader with the *same* event-loop ────────────
@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_running_loop()
    threading.Thread(target=serial_reader, args=(loop,), daemon=True).start()

# ── run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, log_level="info")
