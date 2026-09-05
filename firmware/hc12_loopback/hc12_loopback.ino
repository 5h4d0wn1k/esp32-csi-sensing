/*
 * hc12_loopback.ino — point-to-point link test for the HC-12 433 MHz pair
 *
 * Purpose: step 3 of tonight's smoke-test order. Proves UART2 wiring,
 * module health, and RF link before anything depends on it.
 *
 * Run this SAME sketch on both NodeMCU boards (each with its own HC-12).
 * Each board broadcasts a counter every second and prints anything heard.
 * Success = both Serial Monitors show the OTHER board's counters.
 * Single-board sanity mode: if no peer ever answers you still see your
 * own TX lines — that proves MCU->HC-12 UART is good but not the air link.
 *
 * Wiring recap (NodeMCU ESP32):
 *   HC-12 VCC -> VIN (5V pin)   GND -> GND
 *   HC-12 TXD -> GPIO16 (RX2)
 *   HC-12 RXD -> GPIO17 (TX2)
 *   SET pin   -> unconnected (default mode, 9600 baud, channel CH001)
 *   Antenna MUST be attached before powering on.
 */

#define RX2_PIN 16
#define TX2_PIN 17

uint32_t counter = 0;
uint32_t last_tx = 0;
uint32_t last_rx = 0;
String rxbuf = "";

void setup() {
  Serial.begin(115200);
  Serial2.begin(9600, SERIAL_8N1, RX2_PIN, TX2_PIN);
  delay(300);
  Serial.println("\n[hc12_loopback] boot, sending pings on HC-12 default cfg");
}

void loop() {
  // TX: one ping per second
  if (millis() - last_tx >= 1000) {
    last_tx = millis();
    counter++;
    Serial2.printf("PING %lu\n", (unsigned long)counter);
    Serial.printf("[TX] PING %lu\n", (unsigned long)counter);
  }

  // RX: line-buffered
  while (Serial2.available()) {
    char c = (char)Serial2.read();
    if (c == '\n') {
      rxbuf.trim();
      if (rxbuf.length()) {
        Serial.printf("[RX] %s\n", rxbuf.c_str());
        last_rx = millis();
      }
      rxbuf = "";
    } else if (c != '\r') {
      rxbuf += c;
    }
  }

  // Health nag
  static uint32_t last_nag = 0;
  if (millis() - last_rx > 10000 && millis() - last_nag > 15000) {
    last_nag = millis();
    Serial.println("[..] no peer traffic for 10s — check: antennas fitted,"
                   " both boards powered, same channel/baud");
  }
}
