"""
ローカル Web サーバー + シリアル受信 → WebSocket 配信 (Python 版)
依存: fastapi, uvicorn[standard], pyserial
使用例:
    pip install -r requirements.txt
    python server.py COM5         # Windows 例
    python server.py /dev/ttyUSB0 # Linux/macOS 例
COM ポートは第 1 引数 or 環境変数 COM_PORT で指定可
"""

import asyncio, json, os, struct, sys, time, threading
from typing import List, Tuple
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
import serial

# -------------------- 可変部分: テレメトリ構造体 --------------------
# (name, struct_fmt) 形式  ※ struct_fmt は struct モジュール準拠
TELEMETRY_SCHEMA: List[Tuple[str, str]] = [
    ("counter", "B"),     # uint8  (1 バイト)
    ("temperature", "f"), # float32 (4 バイト, little‑endian)
    ("voltage", "f"),     # float32
]
# -------------------------------------------------------------------

STRUCT_FMT = "<" + "".join(f for _, f in TELEMETRY_SCHEMA)  # < = little‑endian
PACKET_SIZE = struct.calcsize(STRUCT_FMT)

SERIAL_PORT = sys.argv[1] if len(sys.argv) > 1 else os.getenv("COM_PORT", "COM3")
BAUD = int(os.getenv("BAUD", 115200))

# ─────────── FastAPI サーバ ───────────
app = FastAPI()
app.mount("/", StaticFiles(directory="public", html=True), name="static")

clients: set[WebSocket] = set()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            await asyncio.sleep(60)  # keep‑alive; クライアントからのメッセージは無視
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(ws)

async def broadcast(data: dict):
    if not clients:
        return
    msg = json.dumps(data)
    dead = set()
    for ws in clients:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.add(ws)
    clients.difference_update(dead)

# ─────────── シリアルリーダー (スレッド) ───────────
loop = asyncio.get_event_loop()

def serial_reader():
    ser = serial.Serial(SERIAL_PORT, BAUD, timeout=1)
    buf = b""
    while True:
        buf += ser.read(PACKET_SIZE - len(buf))
        if len(buf) >= PACKET_SIZE:
            packet, buf = buf[:PACKET_SIZE], buf[PACKET_SIZE:]
            values = struct.unpack(STRUCT_FMT, packet)
            payload = {name: v for (name, _), v in zip(TELEMETRY_SCHEMA, values)}
            payload["timestamp"] = int(time.time() * 1000)
            asyncio.run_coroutine_threadsafe(broadcast(payload), loop)

threading.Thread(target=serial_reader, daemon=True).start()

if __name__ == "__main__":
    import uvicorn
    print(f"★ Serial {SERIAL_PORT} {BAUD}bps, packet {PACKET_SIZE} bytes")
    print("▼ ブラウザで http://localhost:8000 を開いてください")
    uvicorn.run(app, host="0.0.0.0", port=8000)
