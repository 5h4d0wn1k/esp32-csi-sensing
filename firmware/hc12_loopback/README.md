# HC-12 loopback — bring-up notes

Step 3 of the smoke-test order: proves UART2 wiring, module health, and the
433 MHz air link before anything depends on it.

## Flash

Same toolchain as nrf24_scanner (esp32 package; no extra library needed).
Upload `hc12_loopback.ino` to **both** NodeMCU boards, Serial Monitor @115200.

## Wiring recap

| HC-12 | NodeMCU ESP32 |
|-------|---------------|
| VCC   | **VIN (5V pin)** |
| GND   | GND           |
| TXD   | GPIO16 (RX2)  |
| RXD   | GPIO17 (TX2)  |
| SET   | unconnected (default: 9600 baud, CH001) |

**Antenna must be attached before power-on** — powering an HC-12 without an
antenna can kill its PA.

## Expected output

```
[TX] PING 1
[RX] PING 7      <- the OTHER board's counter
[TX] PING 2
[RX] PING 8
```

- Both boards see each other's counters → link good.
- Only your own `[TX]` lines → MCU→HC-12 UART fine, air link broken:
  check antennas fitted, same channel/baud, range/power.
