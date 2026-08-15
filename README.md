# esp32-csi-sensing

WiFi channel-state (CSI) sensing on ESP32: raw capture, live 3D visualization,
and presence/motion detection. **Multi-transmitter**: the receiver tags every
frame with the source MAC, so it can sense CSI from the ESP-NOW sender, the
house Wi-Fi router, and any other transmitter on the channel at once.

Part of the [`wireless-security-toolkit`](https://github.com/5h4d0wn1k/wireless-security-toolkit)
umbrella. Repo is **private**; will be made public on request.

## Hardware
- **Sender / illuminator:** ESP32-C6 WROOM — `csi_send` firmware, ESP-NOW beacons @100/s on ch6
- **Router (2nd illuminator):** Digisol DHR-3400 (Airtel_Xstream, ch6) — captured via the receiver's promiscuous all-MAC mode (needs OFDM traffic; see `docs/PLACEMENT.md`)
- **Receiver:** ESP32 NodeMCU — `csi_recv` firmware, ch6, **all-MAC capture**, streams CSI CSV over UART @921600

## Quick start
```bash
# 1. Firmware (ESP-IDF v5.5; build on Linux FS, copy under firmware/)
cd ~/esp/esp-csi/examples/get-started/csi_send && idf.py set-target esp32c6 && idf.py build && idf.py -p /dev/ttyACM0 flash
cd ~/esp/esp-csi/examples/get-started/csi_recv && idf.py set-target esp32   && idf.py build && idf.py -p /dev/ttyUSB0 flash
# both examples already modified in-tree: channel 6 + csi_recv captures ALL MACs

# 2. Bridge + viewer (browser needs no Web Serial)
python tools/sensorhub.py -p 8765 -s /dev/ttyUSB0:921600 &
python -m http.server 8000 --directory tools &
# open http://127.0.0.1:8000/csi_3d_viewer.html?auto=1

# 3. Offline tools
python tools/csi_visualizer.py -p /dev/ttyUSB0 -b 921600 -t 8 -o heatmap.png
python tools/motion_detector.py --csv data/captures/2026-08-15-nodemcu-csi-sample.csv
```

## Layout
- `firmware/` — modified `app_main.c` for `csi_send` (ch6) and `csi_recv` (ch6, all-MAC)
- `tools/sensorhub.py` — WebSocket bridge: parses CSI CSV, tags MAC, emits `{amp,ph}` per frame
- `tools/csi_3d_viewer.html` — v5.2: 3D surface, dominant-source selection, phase-aware gain-normalized motion, adaptive subcarrier count (64/192)
- `tools/csi_visualizer.py` / `tools/motion_detector.py` — heatmap + presence detector
- `data/captures/` — sample captures and rendered plots
- `docs/` — firmware/build notes, placement guide

## Notes
- Classic ESP32 link: 192 subcarrier (im,re) pairs (`len=384`); router LLTF capture: 64 (`len=128`) — the hub/viewer adapt automatically
- ~69 frames/s ESP-NOW @ ch6; 74/s router mode
- Motion metric = per-frame gain-normalized complex deviation (phase+amplitude), median+MAD threshold
