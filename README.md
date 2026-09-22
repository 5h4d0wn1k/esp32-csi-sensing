> **⚠️ EDUCATIONAL USE ONLY — AUTHORIZED TESTING ONLY.**
> This project exists for education, research, and **defense of systems you own
> or hold explicit written authorization to assess**. Unauthorized use is
> prohibited and may be illegal. Read [ETHICS.md](ETHICS.md) and
> [SCOPE.md](SCOPE.md) before use. Use at your own risk; **AS IS**, no warranty.

# esp32-csi-sensing

ESP32-CSI WiFi sensing: raw channel-state (CSI) capture, live 3D visualization,
and presence/motion detection — the first project of the wireless-security-toolkit
umbrella.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](#license)
[![CI](https://github.com/5h4d0wn1k/esp32-csi-sensing/actions/workflows/ci.yml/badge.svg)](https://github.com/5h4d0wn1k/esp32-csi-sensing/actions/workflows/ci.yml)
[![GitHub stars](https://img.shields.io/github/stars/5h4d0wn1k/esp32-csi-sensing)](#)
[![Last commit](https://img.shields.io/github/last-commit/5h4d0wn1k/esp32-csi-sensing)](#)

> Part of the `wireless-security-toolkit` umbrella. Repo is **private**; will be
> made public on request.

## Why this project

Channel State Information (CSI) describes how Wi-Fi signals interact with their
environment — it lets a receiver sense who or what is moving in a room using
the Wi-Fi spectrum, without cameras or wearables. Understanding CSI capture and
analysis matters for wireless security research, privacy-aware sensing, and
building presence detection on commodity ESP32 hardware. This project explores
raw CSI capture from the ESP32's radio, live visualization, and
privacy-preserving motion detection, and it is the first project of a broader
wireless-security toolkit focused on understanding the RF spectrum you operate.
Everything here is built for lab use on networks and hardware you own or are
authorized to analyze.

## Features

- **Multi-transmitter sensing** — receiver tags every frame with source MAC and
  senses CSI from ESP-NOW peers, the home router, and any transmitter on the
  channel at once
- **Firmware** — `csi_send` (ESP32-C6 beacon), `csi_recv` (all-MAC capture),
  `csi_recv_router` (joins AP + self-pings), `csi_recv_router_oled`
  (OLED-display variant), plus nRF24 observer/HC-12 Arduino sketches
- **Live bridge** — `tools/sensorhub.py` parses CSI CSV over UART @921600 and
  streams `{amp, ph}` WebSocket frames
- **3D viewer** — `tools/csi_3d_viewer.html` renders live 3D surfaces with
  dominant-source selection and adaptive subcarrier count (64/192)
- **Motion detection** — `tools/motion_detector.py` uses
  gain-normalized, AGC-transient-rejected amplitude variance (p95 tail)
- **Offline tools** — heatmap via `csi_visualizer.py`; session replay via
  `analyze_session.py` on `examples/sample_session/session.jsonl`
- **CI**: JS syntax check, Python byte-compile + smoke test, and a
  personal-data privacy guard

## Quickstart

Prerequisites: ESP32 NodeMCU + ESP32-C6 receiver/sender, ESP-IDF v5.5.

```bash
# 1. Firmware (ESP-IDF v5.5; build on Linux FS, copy under firmware/)
cd ~/esp/esp-csi/examples/get-started/csi_send && idf.py set-target esp32c6 && idf.py build && idf.py -p /dev/ttyACM0 flash
# primary demo — receiver illuminates the room via the AP (see docs/PLACEMENT.md):
cd ~/esp/esp-csi/examples/get-started/csi_recv_router && idf.py set-target esp32 && idf.py build && idf.py -p /dev/ttyUSB0 flash
# alternative: all-MAC ESP-NOW sniffer (>=5 m sender-receiver separation)
cd ~/esp/esp-csi/examples/get-started/csi_recv && idf.py set-target esp32 && idf.py build && idf.py -p /dev/ttyUSB0 flash

# 2. Bridge + viewer (browser needs no Web Serial)
python tools/sensorhub.py -p 8765 -s /dev/ttyUSB0:921600 &
python -m http.server 8000 --directory tools &
# open http://127.0.0.1:8000/csi_3d_viewer.html?auto=1

# 3. Offline tools
python tools/csi_visualizer.py -p /dev/ttyUSB0 -b 921600 -t 8 -o heatmap.png
python tools/motion_detector.py --csv data/captures/2026-08-15-nodemcu-csi-sample.csv
python tools/analyze_session.py examples/sample_session/session.jsonl
```

## Examples

- `examples/sample_session/session.jsonl` — example capture session
- `data/captures/` — sample CSV captures and rendered plots (heatmap, motion)

## Project structure

- `firmware/` — ESP-IDF sources (`csi_send`, `csi_recv`, `csi_recv_router`,
  `csi_recv_router_oled`) + Arduino sketches (nRF24 observer, HC-12, OLED diag)
- `tools/` — Python bridge/analysis/visualization plus the 3D viewer
- `docs/` — architecture, capabilities, hardware, placement, privacy, roadmap
- `data/captures/`, `examples/` — sample datasets

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system design
- [docs/CAPABILITIES.md](docs/CAPABILITIES.md) — what the toolkit can do
- [docs/HARDWARE.md](docs/HARDWARE.md) — board/BOM guidance
- [docs/PLACEMENT.md](docs/PLACEMENT.md) — placement physics and tuning
- [docs/VISUALIZATION.md](docs/VISUALIZATION.md) — viewer walkthrough
- [docs/OLED_DISPLAY.md](docs/OLED_DISPLAY.md) — OLED firmware
- [docs/PRIVACY.md](docs/PRIVACY.md) — data handling; there is a CI guard that
  fails on personal-data strings in tracked files
- [docs/ROADMAP.md](docs/ROADMAP.md) — next steps

## Contributing

Contributions for legitimate lab, education, and research use are welcome. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE). Educational and authorized-use only; provided
**AS IS**, without warranty.