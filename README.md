# Telemetry Dashboard — Trend Graph ◀︎▶︎ Serial Monitor ＋ Command Console

A zero-install browser UI, backed by **FastAPI + PySerial**, that lets you

* stream ASCII-CSV telemetry from your micro-controller  
* visualise it live with Chart.js **(graph fixed to the left half of the screen)**  
* type commands from the browser and forward them to the MCU  
* watch a colour-coded serial console  
* see **PORT / BAUD** at a glance

```

```
MCU  --(telemetry)-->  server.py  --(WebSocket)-->  browser  [graph ⬅︎ │ ➡︎ console]
MCU  <--(command)---┘                             └---(command)--- browser
```

```

---

## Features

| ✔ | Capability |
|---|------------|
| Live trend graph (Chart.js, auto-adds new series) |
| Info bar showing **COM port & baud rate** |
| Scrollable serial monitor (green RX, yellow TX) |
| Command panel with _Send_ box |
| 8-bit counter automatically “unwrapped” to long counter |
| Dummy mode (`--dummy`) for development w/o hardware |
| One-touch schema editing (`COLUMNS = […]` in `server.py`) |

---

## Directory Layout

```

project/
├─ server.py          # FastAPI + WebSocket bridge
├─ requirements.txt   # Python deps
└─ public/
├─ index.html      # two-column UI (graph | console+cmd)
└─ main.js         # browser logic

````

---

## Installation

```bash
# 1) clone / copy the repo
# 2) (optional) create venv
python -m venv venv
venv\Scripts\activate        # Windows; use source venv/bin/activate on *nix
# 3) install deps
pip install -r requirements.txt
````

> `uvicorn[standard]` bundles `websockets`, `wsproto`, `httptools` and friends, so
> WebSocket support works out of the box.

---
## Running

```bash
# real hardware
python server.py COM5 115200
#                  │    └─ baud rate   (default 115200)
#                  └───── serial port (default COM5)

# OR dummy data (no serial port needed)
python server.py --dummy
````

Open **[http://localhost:8000](http://localhost:8000)** in your browser.

---

## MCU → PC telemetry format

* **ASCII CSV**, comma-separated, **LF** terminated
  Example: `17,25.5,3.30\n`
  
* Columns *must* match **`COLUMNS`** in `server.py`:

  ```python
  COLUMNS = ["counter", "temperature", "voltage"]
  ```
* First field is treated as uint8 counter and published as `counter_ext`
  (0-based, monotonic).

---

## 5 · Browser UI map

```
┌──────── LEFT 50 % ────────┬────────── RIGHT 50 % ──────────┐
│                           │  PORT: COM5   BAUD: 115200     │
│   Trend Graph (canvas)    │  ────────────────────────────  │
│                           │  Serial Monitor (scroll)       │
│                           │       > telemetry line         │
│                           │       < command sent           │
│                           │  ────────────────────────────  │
│                           │  [command box]  [Send]         │
└───────────────────────────┴────────────────────────────────┘
```

---

## Customization tips

| Need                        | Change                                                      |
| --------------------------- | ----------------------------------------------------------- |
| Add/remove telemetry fields | edit `COLUMNS` and restart server                           |
| Re-position panes           | tweak CSS grid in `public/index.html`                       |
| Persistent CSV log          | write `payload` to file inside `serial_thread`              |
| Binary commands             | Base64-encode in JSON or open a second binary serial stream |
| Security (remote)           | wrap FastAPI with HTTPS / add token auth                    |

---

## Troubleshooting

| Symptom                                                     | Remedy                                                                                     |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `AttributeError: module 'serial' has no attribute 'Serial'` | `pip uninstall serial && pip install pyserial`                                             |
| Web page blank, JS console empty                            | ensure `python server.py --dummy` yields frames in **Network → WS → Frames**               |
| Graph still full-screen                                     | clear cache (`Ctrl+F5`); make sure you’re using the two-column grid layout in `index.html` |
| `Unsupported upgrade request`                               | reinstall: `pip install "uvicorn[standard]"`                                               |

---

## License

MIT — use it, bend it, ship it. Attribution is welcome but optional.

```
