"""
Telemetry Dashboard
  • ASCII-CSV telemetry → WebSocket → Chart.js
  • Command console  ← WebSocket ← browser
  • Serial monitor with RX / TX lines
  • Auto-detects serial port on macOS / Linux / Windows

Run:
    python server.py [PORT] [BAUD] [--dummy]

Dependencies: fastapi, uvicorn[standard], pyserial
"""

from __future__ import annotations
import asyncio, glob, json, platform, sys, threading, time
from pathlib import Path
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import serial  # PySerial

# ── telemetry schema (edit freely) ────────────────────────────────────────────
COLUMNS: List[str] = ["counter", "temperature", "voltage"]

# ── port / baud / dummy via CLI ──────────────────────────────────────────────
def auto_port() -> str:
    if platform.system() == "Windows":
        return "COM5"
    # macOS / Linux
    for pattern in ("/dev/tty.usb*", "/dev/cu.usb*", "/dev/ttyUSB*"):
        ports = glob.glob(pattern)
        if ports:
            return ports[0]
    return "/dev/ttyUSB0"  # fallback

SERIAL_PORT = (
    sys.argv[1]
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--")
    else auto_port()
)
BAUD       = int(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else 115200
USE_DUMMY  = "--dummy" in sys.argv

# ── FastAPI + WebSocket setup ────────────────────────────────────────────────
app = FastAPI()
clients: set[WebSocket]       = set()
cmd_queue: asyncio.Queue[str] = asyncio.Queue()

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    # send current port / baud so the UI can show it
    await ws.send_text(json.dumps({"kind": "config", "port": SERIAL_PORT, "baud": BAUD}))
    clients.add(ws)
    try:
        while True:
            text = await ws.receive_text()
            msg  = json.loads(text)
            if msg.get("kind") == "command":
                await cmd_queue.put(msg["body"])
    except WebSocketDisconnect:
        clients.discard(ws)

app.mount("/static", StaticFiles(directory="public"), name="static")
@app.get("/")
async def index():
    return FileResponse(Path("public/index.html"))

async def broadcast(text: str):
    for ws in list(clients):
        try:
            await ws.send_text(text)
        except Exception:
            clients.discard(ws)

# ── serial / dummy thread ────────────────────────────────────────────────────
def serial_thread(loop: asyncio.AbstractEventLoop):
    if USE_DUMMY:
        print("[DUMMY] running (no serial port)")
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
            asyncio.run_coroutine_threadsafe(
                broadcast(json.dumps({"kind": "serial", "dir": "in", "body": f"DUMMY {cnt}"})), loop)
            cnt += 1
            time.sleep(1)
        # never returns

    # real serial port
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD, timeout=1)
        print(f"[SER] opened {SERIAL_PORT} @ {BAUD}")
    except serial.SerialException as e:
        print(f"[SER] OPEN FAILED: {e}")
        return

    prev_u8 = None
    overflow = 0

    while True:
        # ── telemetry RX ───────────────────────────────────────────────
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if line:
            asyncio.run_coroutine_threadsafe(
                broadcast(json.dumps({"kind": "serial", "dir": "in", "body": line})), loop)

            parts = line.split(",")
            if len(parts) == len(COLUMNS):
                try:
                    counter_u8 = int(parts[0]) & 0xFF
                    values = [counter_u8] + [float(x) for x in parts[1:]]
                except ValueError:
                    continue
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

        # ── pending commands TX ───────────────────────────────────────
        try:
            cmd = cmd_queue.get_nowait()
            ser.write((cmd).encode("ascii"))
            print("[SER←CMD]", cmd)
            asyncio.run_coroutine_threadsafe(
                broadcast(json.dumps({"kind": "serial", "dir": "out", "body": cmd})), loop)
            asyncio.run_coroutine_threadsafe(
                broadcast(json.dumps({"kind": "ack", "body": cmd})), loop)
        except asyncio.QueueEmpty:
            pass

@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_running_loop()
    threading.Thread(target=serial_thread, args=(loop,), daemon=True).start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, log_level="info")
