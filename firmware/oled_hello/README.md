# OLED bring-up (6-pin SPI, 0.96" SSD1306)

Step 1 of the smoke-test order. Nothing else needs to be on the breadboard.

## Wiring

| Panel | NodeMCU |
|-------|---------|
| GND   | GND rail |
| VCC   | 3V3 rail |
| D0    | GPIO18 |
| D1    | GPIO23 |
| RES   | GPIO4 |
| DC    | GPIO2 |

## Flash

Library Manager: **Adafruit SSD1306** + **Adafruit GFX Library**, then upload
`oled_hello.ino` (esp32 board package), Serial Monitor @115200.

```
arduino-cli lib install "Adafruit SSD1306" "Adafruit GFX Library"
arduino-cli compile --fqbn esp32:esp32:esp32 firmware/oled_hello
```

## Pass criteria

- Panel shows `ESP32 CSI LAB` + ticking uptime counter.
- Serial: `[OK] OLED online`.

Fail → read the `[FAIL]` hints on Serial; most common: VCC on 5V, or
RES/DC swapped.
