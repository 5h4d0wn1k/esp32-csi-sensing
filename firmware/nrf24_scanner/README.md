# nRF24 scanner — bring-up notes

First independent 2.4 GHz instrument for the rig (seed of W5). Proves the
nRF24L01+ wiring and gives an instant end-to-end validation: your whole
existing setup transmits on **channel 6** (router illuminator + csi_send),
so a healthy build shows a tall spike at `ch06`.

## Flash (Arduino IDE 2.x or arduino-cli)

1. Boards: install **esp32 by Espressif** package.
2. Library Manager: install **RF24 by TMRh20**.
3. Board: "NodeMCU-32S" / generic ESP32 Dev Module, 115200 upload.
4. Open `nrf24_scanner.ino` → Upload → Serial Monitor @115200.

```
arduino-cli lib install RF24
arduino-cli compile --fqbn esp32:esp32:esp32 firmware/nrf24_scanner
arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32 firmware/nrf24_scanner
```

## Wiring recap

| nRF24L01+ | NodeMCU ESP32 |
|-----------|---------------|
| VCC       | **3V3 only — never 5V** |
| GND       | GND           |
| SCK       | GPIO18        |
| MOSI      | GPIO23        |
| MISO      | GPIO19        |
| CSN       | GPIO27 (default in sketch) *or* D5 per wiring doc — one constant to flip |
| CE        | GPIO26        |
| IRQ       | unconnected   |

**Mandatory:** 10–100 µF cap across VCC/GND right at the module. Brown-out
without it is the #1 cause of `radio.begin()` failures.

## Expected output

```
[OK] nRF24L01+ online, scanning 2400-2527 MHz
top: ch06=812 ch01=45 ch11=30
ch06   812 ###############################
ch01    45 ##
```

- Spike on ch06 → rig confirmed working end-to-end.
- Flat silence everywhere → antenna/cap/wiring; check MISO/MOSI swap first.
- `radio.begin()` false → power problem; cap missing or 5V accidentally used.
