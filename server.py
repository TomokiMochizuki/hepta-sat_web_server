"""
ASCII CSV Telemetry → WebSocket → Chart.js
Sample Usage:  python server.py COM5 9600
"""

import asyncio, json, sys, threading, time
from pathlib import Path
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import serial                    # PySerial

# ==== Definition of the telemetry ====
# Users only need to change this part.
COLUMNS: List[str] = ["counter", "temperature", "voltage"]

# ==== 起動引数 ====
SERIAL_PORT = sys.argv[1] if len(sys.argv) > 1 else "COM5"
BAUD        = int(sys.argv[2]) if len(sys.argv) > 2 else 9600

# ------------------------------------------------------------------------------
app     = FastAPI()
clients: set[WebSocket] = set()

#--- WebSocket ---------------------------------------------------------------
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            await asyncio.sleep(3600)   # Keep the connection alive
    except WebSocketDisconnect:
        clients.discard(ws)

#--- 静的ファイル ------------------------------------------------------------
app.mount("/static", StaticFiles(directory="public"), name="static")
@app.get("/")
async def index():
    return FileResponse(Path("public/index.html"))

#--- 共有関数 ---------------------------------------------------------------
async def broadcast(msg: str):
    for ws in list(clients):
        try:
            await ws.send_text(msg)
            # print("[TX]", msg[:60])          # For debug
        except Exception:
            clients.discard(ws)

#--- シリアル読み取りスレッド -----------------------------------------------
def serial_reader(loop: asyncio.AbstractEventLoop):
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD, timeout=1)
        print(f"[SER] open {SERIAL_PORT} {BAUD}")
    except serial.SerialException as e:
        print(f"[SER] open failed: {e}")
        return

    prev_u8 = None
    overflow = 0

    while True:
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) != len(COLUMNS):
            print("[SER] malformed:", line)
            continue
        try:
            counter_u8 = int(parts[0]) & 0xFF
            values = [counter_u8] + [float(x) for x in parts[1:]]
        except ValueError:
            print("[SER] parse err:", line)
            continue

        if prev_u8 is not None and counter_u8 < prev_u8:
            overflow += 1
        prev_u8 = counter_u8
        counter_ext = overflow * 256 + counter_u8

        payload = {
            **dict(zip(COLUMNS, values)),
            "counter_ext": counter_ext,
            "timestamp": int(time.time()*1000),
        }
        # print("payload:", payload)           # For debug
        asyncio.run_coroutine_threadsafe(
            broadcast(json.dumps(payload)), loop)

#--- FastAPI: Pass the “correct” loop at startup -------------------------------------
@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_running_loop()          # Main loop for uvicorn
    threading.Thread(target=serial_reader, args=(loop,),
                     daemon=True).start()
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, log_level="info")
