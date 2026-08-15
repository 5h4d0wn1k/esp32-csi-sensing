# CSI Visualization

## Architecture: dumb sensor board, smart host
The NodeMCU runs `csi_recv` — it **only streams raw CSI** and does no
analysis. All processing (3D surface, heatmaps, motion/presence detection,
logging) happens on the host: in the browser via Web Serial, or in Python.
This keeps the ESP32 CPU free for capture throughput (45–70 frames/s) and
lets the analysis evolve without reflashing firmware.

## 3D Viewer (`tools/csi_3d_viewer.html`)
Proper-3D amplitude surface (Three.js), **all processing in the browser**:
- **X** = time, **Z** = subcarrier index, **Y** = amplitude, colored viridis
- Drag = rotate, wheel = zoom, right-drag = pan
- **MOTION badge**: host-side presence detection — auto-calibrates its
  threshold on the first 30 static frames, then flags ACTIVE/INACTIVE with
  debounce, with a live deviation-metric sparkline
- **Live mode**: Chrome/Edge → "Connect (Web Serial)" → pick `/dev/ttyUSB0`
  (921600 baud) → scrolling surface
- **Replay**: "Load capture" → any `CSI_DATA` CSV from `data/captures/`

To open:
- Direct: `file://.../csi_3d_viewer.html` (works in Chrome/Edge), or
- `http://127.0.0.1:8000/csi_3d_viewer.html` (local server, Web Serial needs
  https/localhost; a server is already running on port 8000)

## 2D heatmap (`tools/csi_visualizer.py`)
```
python csi_visualizer.py -p /dev/ttyUSB0 -b 921600 -t 8 -o heatmap.png   # live
python csi_visualizer.py --csv data/captures/x.csv -o heatmap.png         # replay
```

## Motion detector (`tools/motion_detector.py`)
Host-side presence detection on the raw stream: sliding baseline, auto
threshold (median + 3σ of the first 30 static frames), debounced ACTIVE/INACTIVE.
```
python motion_detector.py -p /dev/ttyUSB0 -b 921600 -t 30 -o motion.png
```

## On-device presence (`esp_wifi_sensing` demo)
Alternative that moves processing onto the ESP32 (higher power/CPU cost; only
needed if there's no host). `~/esp/esp-csi/examples/esp-radar/wifi_sensing_demo`
— built + flashed to the NodeMCU, joins **Airtel_Xstream** (open network, ch6),
senses the AP channel + 2 peer MACs, emits `HMS:` JSON (jitter/wander/motion_status).
Verified live: sensing the Digisol AP `00:17:7c:74:1d:35` with updating jitter values.
Reflash `csi_recv` afterwards to return the board to raw-streaming mode.

## Capture data format
Classic ESP32: 192 subcarriers, each (imag, real) pair → `len=384` ints.
~45–70 frames/s at 921600 baud.
