# Hardware guide

What to buy, how to flash it, where to put it, and how to power it. Physics
and measured numbers live in `docs/PLACEMENT.md`; firmware details in
`firmware/README.md`.

## Signal chain at a glance

```
[ESP32-C6 csi_send] --ESP-NOW ch6--> \
                                      [ESP32 NodeMCU receiver] --CSV UART--> [sensorhub.py] --> [viewer]
[2.4 GHz AP/router] ----802.11------> /
```

The receiver tags every frame with its source MAC, so both illuminators (and
anything else on the channel) are sensed simultaneously.

## Bill of materials

| Part | Qty | Role | Notes |
|------|-----|------|-------|
| ESP32 NodeMCU dev board | 1 | Receiver — runs `csi_recv_router` (primary demo) or `csi_recv`; streams CSI CSV over UART @921600 | Classic ESP32 (not S3/C6) for the 192-subcarrier HT40 capture |
| ESP32-C6 dev kit | 1 | Sender / near-field illuminator — `csi_send`, ESP-NOW beacons @100/s on ch6 | Native USB (`/dev/ttyACM0`); power from a power bank to place it away from the receiver |
| Any 2.4 GHz consumer AP / router | 1 | Whole-room illuminator for the primary demo | Receiver joins it and self-pings; any AP on a fixed 2.4 GHz channel works |
| SSD1306 0.96" OLED, I2C | 1 | Optional status display for the receiver (motion/fps/RSSI/breath) | Needs the `csi_recv_router_oled` firmware variant |
| USB data cables | 2 | Flashing + serial CSI stream + power | Use good data-rated cables; the receiver's CSV runs at 921600 baud |
| USB power bank | 1 | Cordless power for the C6 sender (and field deployments) | Enables the ≥5 m sender–receiver separation the direct link needs |

Total cost is dominated by the two boards; everything else is generic.

## Flashing

Builds happen in the upstream esp-csi tree (`~/esp/esp-csi/examples/...`) with
ESP-IDF v5.5; the copies under `firmware/` are reference snapshots. Open a
terminal and load the toolchain first:

```bash
source ~/esp/esp-idf/export.sh
```

Receiver — primary demo, joins the AP and self-pings it (ESP32 NodeMCU):

```bash
cd ~/esp/esp-csi/examples/get-started/csi_recv_router && idf.py set-target esp32 && idf.py build && idf.py -p /dev/ttyUSB0 flash
```

Receiver — same plus SSD1306 OLED status display:

```bash
cd ~/esp/esp-csi/examples/get-started/csi_recv_router_oled && idf.py set-target esp32 && idf.py build && idf.py -p /dev/ttyUSB0 flash
```

Sender / illuminator (ESP32-C6):

```bash
cd ~/esp/esp-csi/examples/get-started/csi_send && idf.py set-target esp32c6 && idf.py build && idf.py -p /dev/ttyACM0 flash
```

The all-MAC sniffer variant (`csi_recv`) flashes identically to
`csi_recv_router` (same board, same port). If your serial ports differ, adjust
`-p` accordingly. Port troubleshooting: check `ls /dev/ttyUSB* /dev/ttyACM*`;
a C6 showing as ttyUSB usually means the cable is a UART bridge, not native
USB; "permission denied" means add yourself to the `dialout` group.

## OLED wiring (optional display)

Only needed for `csi_recv_router_oled`. Summary — full driver/config details
in `docs/OLED_DISPLAY.md`:

| OLED pin | ESP32 pin | Notes |
|----------|-----------|-------|
| VCC      | 3V3       | Do not use 5V pins |
| GND      | GND       | Common ground |
| SDA      | GPIO21    | I2C master @ 400 kHz |
| SCL      | GPIO22    | Address 0x3C (default) |

No external pull-ups or other components are required with the typical 4-pin
module; address and pins are configurable via menuconfig
(`CONFIG_OLED_SDA`, `CONFIG_OLED_SCL`, `CONFIG_OLED_I2C_ADDR`), and everything
compiles out cleanly when `CONFIG_OLED_ENABLE` is disabled.

## Placement quick rules

Full physics, measured tables, and the calibration ritual: `docs/PLACEMENT.md`.

- **Direct two-node link needs ≥5 m separation.** The desk demo at 1–2 m does
  not work — the direct path dominates and body motion vanishes into the noise
  floor.
- **Room-scale sensing comes from router illumination.** Run `csi_recv_router`
  so the receiver self-pings the AP; the whole room becomes the sensed volume.
- **Calibrate in a quiet room.** The 5 s auto-calibration needs an empty,
  still room; press Recalibrate after any big environment change.

Antenna orientation: NodeMCU PCB antenna edge-on to the room, vertical, away
from laptop metal; C6 chip antenna toward the receiver but physically far from
it.

## Power notes

- **Receiver (NodeMCU):** its USB cable is both power and the CSI data path
  (UART @921600) — use a data-rated cable into the host running
  `tools/sensorhub.py`. Charge-only cables will flash nothing and stream
  nothing.
- **Sender (C6):** flashing uses native USB (`/dev/ttyACM0`); after flashing it
  can run from any USB source. A power bank lets you park it ≥5 m away, which
  is exactly what makes direct-link sensing work.
- **OLED:** adds negligible current (~10–20 mA); no separate supply needed.
- **Field deployments:** either board alone draws well under what any phone
  power bank supplies; expect runtime limited by the bank, not the boards.
- **Brown-out symptoms** (random resets on flashing or Wi-Fi connect) almost
  always mean a weak cable or hub — plug boards directly into the host.

## Photos

The documentation photo shot list (what to photograph, angles, annotations)
lives in `docs/photos/README.md`.
