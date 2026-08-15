# Modified firmware (esp-csi get-started)

Snapshots of the two example programs as flashed in the current setup. Build
them in the upstream tree (`~/esp/esp-csi/examples/get-started/...`) with
ESP-IDF v5.5 — these copies are for reference/audit only.

## csi_recv (receiver, ESP32 NodeMCU) — `main/app_main.c`
Changes vs upstream:
- `CONFIG_LESS_INTERFERENCE_CHANNEL` `11` → `6` (join the router channel so the
  router + ESP-NOW sender are both visible)
- Removed the `memcmp(info->mac, CONFIG_CSI_SEND_MAC, 6)` filter in
  `wifi_csi_rx_cb` → **captures CSI from ANY transmitter** on the channel. Each
  frame is tagged with the source MAC in the `CSI_DATA,<id>,<mac>,...` header.
- Output unchanged: 23 CSV fields + quoted `[im,re,...]` data.

Notes: the ESP32's CSI only triggers on OFDM frames — the router's 1 Mbps DSSS
beacons do NOT produce CSI, so generate OFDM traffic to the router (e.g. a ping
flood from a client on the same AP) to illuminate via the router. ESP-NOW
beacons from `csi_send` (HT40, 192 subcarriers) are captured directly.

## csi_send (sender, ESP32-C6) — `main/app_main.c`
Changes vs upstream:
- `CONFIG_LESS_INTERFERENCE_CHANNEL` `11` → `6`
- Sends ESP-NOW beacons at `CONFIG_SEND_FREQUENCY` (100 Hz) from
  `1a:00:00:00:00:00` → the controllable near-field illuminator for the
  walk-between-the-nodes demo. Power it from a power bank to place it away from
  the receiver.

## Build/flash
```bash
source ~/esp/esp-idf/export.sh
cd ~/esp/esp-csi/examples/get-started/csi_recv && idf.py set-target esp32   && idf.py build && idf.py -p /dev/ttyUSB0 flash
cd ~/esp/esp-csi/examples/get-started/csi_send && idf.py set-target esp32c6 && idf.py build && idf.py -p /dev/ttyACM0 flash
```
