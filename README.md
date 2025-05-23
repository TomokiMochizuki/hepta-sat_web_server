# Telemetry-to-Web Trend Viewer

Real-time **ASCII-CSV telemetry → WebSocket → Chart.js**  
A tiny FastAPI server plus a static front-end that turns the data stream from your
micro-controller into a live trend graph in any browser.

```

MCU  ->  counter,temperature,voltage\n  ->  server.py  ->  WebSocket  ->  Chart.js

```

---

## Features

| ✔ | Feature |
|---|---------|
| **Zero-config front-end** &nbsp;| open <http://localhost:8000> and watch the graph grow |
| **Hot-plug schema** | edit `COLUMNS = [...]` in `server.py`; restart; new fields appear automatically |
| **8-bit overflow handling** | `counter` (uint8) is auto-expanded to `counter_ext` (monotonic) |
| **Plain ASCII input** | no binary structs; just `17,25.5,3.30\n` |
| **Slim dependency set** | only `fastapi`, `uvicorn[standard]`, `pyserial` |

---

## Directory Layout

```

project/
├─ server.py            # FastAPI + serial reader + WS broadcaster
├─ requirements.txt     # Python dependencies
└─ public/
├─ index.html        # loads Chart.js + adapter
└─ main.js           # WebSocket → chart

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
python server.py COM5 115200
#              │    └─ baud rate   (default 115200)
#              └───── serial port (default COM5)
```

Then open **[http://localhost:8000](http://localhost:8000)** in your browser.

---

## Telemetry Format (MCU → PC)

* **Delimiter**: comma (`,`)

* **Frame terminator**: LF (`\n`)

* **Example**

  ```
  0,25.4,3.30\n
  1,25.5,3.29\n
  2,25.6,3.30\n
  ```

* Column order must equal `COLUMNS` in `server.py`:

  ```python
  COLUMNS = ["counter", "temperature", "voltage"]
  ```

* The first column is assumed to be an **8-bit counter**; the server
  adds `counter_ext`, which rolls over smoothly past 255.

---

## Customization Tips

| Goal                          | How                                                           |
| ----------------------------- | ------------------------------------------------------------- |
| Add / remove telemetry fields | Update `COLUMNS`, restart server; front-end updates itself    |
| Change colours / background   | tweak inline CSS or the `hsl()` generator in `public/main.js` |
| Higher sample rates           | hundreds Hz fine; for >1 kHz down-sample before sending       |
| Persistent logging            | inside `serial_reader()` write `payload` to a file / DB       |
| Test without hardware         | `python server.py --dummy` generates synthetic data           |

---

## Troubleshooting

| Symptom                                                     | Suggestion                                                                                                       |
| ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `AttributeError: module 'serial' has no attribute 'Serial'` | `pip uninstall serial && pip install pyserial`                                                                   |
| Browser shows black page, no graph                          | open DevTools → Console & Network; ensure JSON messages arrive; use latest `server.py` with **startup-loop fix** |
| `404 /main.js`                                              | make sure the `public/` folder is present and mounted at `/static`                                               |
| `Unsupported upgrade request`                               | reinstall: `pip install "uvicorn[standard]"`                                                                     |

---

## License

MIT — use it, fork it, hack it.
Attribution is nice but not required. Have fun! 😊

```
