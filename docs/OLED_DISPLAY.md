# OLED status display (SSD1306 0.96")

Add a small display to the receiver node so the system works standalone:
no browser needed to see motion state.

```
+---------------------------+
|  CSI SENTINEL             |
|                           |
|  MOTION: ACTIVE           |
|  BREATH: 15/min           |
|  76fps -46dBm             |
+---------------------------+
```

The whole screen inverts for 200 ms on every motion transition so a change is
visible from across the room.

## Which board gets the display

The **receiver NodeMCU** (ESP32, `/dev/ttyUSB0`). It already has the state
context: the host hub computes detection and writes one-letter command lines
back down the USB serial link (`M1` = motion active, `M0` = clear,
`F<fps>`, `R<rssi>`, `B<bpm>`). The sender (ESP32-C6) stays untouched.

## Identify your module variant

Look at the pin count and silk labels on the back:

| Pins | Silk labels | Variant |
|------|-------------|---------|
| 4 | `GND VCC SCL SDA` | I2C - use this if you have the choice |
| 6-7 | `GND VCC CLK DIN DC RES [CS]` | SPI |

Both are SSD1306-class controllers; only the wiring differs.

## Wiring

### I2C variant (4 pins) - recommended, matches shipped firmware

| OLED | NodeMCU | Note |
|------|---------|------|
| VCC | 3V3 | never 5V (level + regulator headroom) |
| GND | GND | |
| SCL | D22 (GPIO22) | I2C clock, 400 kHz |
| SDA | D21 (GPIO21) | I2C data, address 0x3C |

I2C shares nothing with the 921600 baud UART stream; there is no interference.

### SPI variant (6/7 pins)

| OLED | NodeMCU | Note |
|------|---------|------|
| VCC | 3V3 | |
| GND | GND | |
| CLK / D0 | D18 (GPIO18) | VSPI clock |
| DIN / D1 / MOSI | D23 (GPIO23) | VSPI MOSI |
| DC | D2 (GPIO2) | data/command select |
| RES | D4 (GPIO4) | reset |
| CS (if present) | D5 (GPIO5) | 6-pin boards tie CS low internally |

Rules that apply to both variants:

- Wires shorter than 30 cm.
- Never use GPIO12 for anything (strapping pin - board will not boot).
- Do not power the OLED from 5V/VIN: the logic is 3.3 V.

## Firmware

`firmware/csi_recv_router_oled/` is `csi_recv_router` plus:

- `ssd1306.c/h` - self-contained I2C SSD1306 driver (no external components)
- `oled_task.c/h` - 100 ms task parsing `M0/M1/F/R/B` lines from UART0 RX
- Kconfig options: `CONFIG_OLED_ENABLE` (default y), `CONFIG_OLED_SDA 21`,
  `CONFIG_OLED_SCL 22`, `CONFIG_OLED_I2C_ADDR 0x3C`

Build and flash (from the upstream tree, not this snapshot):

```bash
source ~/esp/esp-idf/export.sh
cd ~/esp/esp-csi/examples/get-started/csi_recv_router_oled
idf.py set-target esp32 && idf.py build && idf.py -p /dev/ttyUSB0 flash
```

Boot states: `BOOT...` while connecting, `NO WIFI` on failure (the app no
longer aborts when the AP is unreachable - it retries).

Note: the shipped driver is I2C-only. If your module is the SPI variant,
either use a 4-pin I2C module or extend `ssd1306.c` with an SPI backend
(VSPI + GPIO2/4 as listed above) before flashing.

## Hub side

Run the hub with detector + OLED feedback enabled:

```bash
python tools/sensorhub.py -p 8765 -s /dev/ttyUSB0:921600 --detector --oled
```

`--oled` writes `M0\n`/`M1\n` on every state change plus `F<fps>\n` and
`R<rssi>\n` every 5 s. It implies `--detector`, which also publishes
`{"type":"motion",...}` messages on the websocket for other clients.

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| Nothing displayed | Wrong variant wired as I2C; check address 0x3C vs 0x3D; swap SDA/SCL |
| Garbage blocks | Loose Dupont wire, keep under 30 cm |
| Display dies when WiFi connects | Power dip - confirm VCC is on 3V3, not VIN |
| MOTION never changes | Hub must run with `--detector --oled`; check hub log for serial writes |
| Board boot-loops after wiring | Something on GPIO12, or VCC shorted to 5V |
