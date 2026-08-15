# esp32-csi-sensing

WiFi channel-state (CSI) sensing on ESP32: raw capture, live visualization,
and presence/motion detection.

Part of the [`wireless-security-toolkit`](https://github.com/5h4d0wn1k/wireless-security-toolkit)
umbrella. Repo is **private**; will be made public on request.

## Hardware
- **Sender:** ESP32-C6 WROOM — `csi_send` firmware (esp-csi get-started), ESP-NOW beacons
- **Receiver:** ESP32 NodeMCU — `csi_recv` firmware, streams CSI CSV over UART @921600

## Quick start
```bash
# 1. Firmware (ESP-IDF v5.5 toolchain must be installed; lives on Linux FS)
cd ~/esp/esp-csi/examples/get-started/csi_send && idf.py set-target esp32c6 && idf.py build && idf.py -p /dev/ttyACM0 flash
cd ~/esp/esp-csi/examples/get-started/csi_recv && idf.py set-target esp32   && idf.py build && idf.py -p /dev/ttyUSB0 flash

# 2. See it live
pip install pyserial matplotlib numpy
python tools/csi_visualizer.py -p /dev/ttyUSB0 -b 921600 -t 8 -o heatmap.png

# 3. Re-render a saved capture
python tools/csi_visualizer.py --csv data/captures/2026-08-15-nodemcu-csi-sample.csv -o heatmap.png
```

## Layout
- `tools/csi_visualizer.py` — serial capture + subcarrier-amplitude heatmap + RSSI strip
- `data/captures/` — sample captures and rendered plots
- `docs/` — firmware/build notes, presence-detection status

## Notes
- Classic ESP32 frame: 192 subcarrier (im,re) pairs; `len=384` reported per frame
- ~69 frames/s capture rate at 921600 baud
- Presence detection (`esp_wifi_sensing` component) WIP — see `docs/`
