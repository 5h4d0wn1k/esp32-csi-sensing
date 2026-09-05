/*
 * nrf24_scanner.ino — 2.4 GHz activity spectrum scanner for the unified rig
 *
 * Purpose: prove the nRF24L01+ wiring (and give the lab its first
 * independent-outside-the-Wi-Fi-stack instrument, W5 seed).
 *
 * Expected result on this bench: a tall spike on CHANNEL 6 — the router
 * illuminator AND csi_send both live there. Any Wi-Fi traffic shows up too.
 *
 * Toolchain: Arduino IDE 2.x or arduino-cli (NOT ESP-IDF).
 *   Boards : "esp32 by Espressif" package
 *   Library: "RF24 by TMRh20" (Library Manager)
 *
 * Wiring recap (NodeMCU ESP32):
 *   nRF24 VCC->3V3 (NEVER 5V)  GND->GND
 *   SCK ->GPIO18  MOSI->GPIO23  MISO->GPIO19
 *   CSN ->GPIO27 (default; change to 5 if you used D5 per wiring doc)
 *   CE  ->GPIO26
 *   IRQ ->unconnected
 *   10uF-100uF cap across VCC/GND at the module is MANDATORY.
 */

#include <SPI.h>
#include <nRF24L01.h>
#include <RF24.h>

#define CE_PIN  26
#define CSN_PIN 27   // <- set to 5 if you wired CSN to D5 instead

RF24 radio(CE_PIN, CSN_PIN);

const uint8_t  N_CH      = 126;   // channels 0..125
const uint32_t SWEEP_MS  = 1000;  // histogram window
uint16_t hits[N_CH];
uint8_t  bar[40];

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n[nrf24_scanner] boot");

  if (!radio.begin()) {
    Serial.println("[FAIL] radio.begin() == false");
    Serial.println("  -> check: 3V3 only, cap fitted, CSN/CE pins match");
    Serial.println("  -> MISO/MOSI/SCK swapped is the usual culprit");
    while (true) { delay(1000); }
  }

  radio.stopListening();
  radio.setPALevel(RF24_PA_MIN);   // detection only; no need to transmit loud
  radio.setDataRate(RF24_2MBPS);
  radio.setRetries(0, 0);
  radio.setAutoAck(false);

  Serial.println("[OK] nRF24L01+ online, scanning 2400-2527 MHz");
  Serial.println("[i]  expect a spike on ch 06 (router + csi_send)\n");
}

void loop() {
  memset(hits, 0, sizeof(hits));
  uint32_t t0 = millis();

  // Sweep channels inside the window, latching carrier-detect per channel.
  while (millis() - t0 < SWEEP_MS) {
    for (uint8_t ch = 0; ch < N_CH; ch++) {
      radio.setChannel(ch);
      radio.startListening();
      delayMicroseconds(150);        // settle window per channel
      radio.stopListening();
      if (radio.testCarrier() || radio.testRPD()) {
        if (hits[ch] < 65000) hits[ch]++;
      }
    }
  }

  render();
}

void render() {
  uint16_t peak = 0;
  for (uint8_t ch = 0; ch < N_CH; ch++) peak = max(peak, hits[ch]);
  if (peak == 0) { Serial.println("(silent window)"); return; }

  // Top-3 busiest channels
  uint8_t t[3] = {255, 255, 255};
  for (uint8_t ch = 0; ch < N_CH; ch++) {
    for (uint8_t k = 0; k < 3; k++) {
      if (t[k] == 255 || hits[ch] > hits[t[k]]) {
        for (uint8_t j = 2; j > k; j--) t[j] = t[j - 1];
        t[k] = ch;
        break;
      }
    }
  }

  Serial.printf("top: ch%02u=%u ch%02u=%u ch%02u=%u\n",
                t[0], hits[t[0]], t[1], hits[t[1]], t[2], hits[t[2]]);

  // Histogram rows for channels with any activity
  for (uint8_t ch = 0; ch < N_CH; ch++) {
    if (hits[ch] == 0) continue;
    uint8_t len = (uint32_t)hits[ch] * 39 / peak + 1;
    for (uint8_t i = 0; i < len; i++) bar[i] = '#';
    bar[len] = '\0';
    Serial.printf("ch%02u %5u %s\n", ch, hits[ch], bar);
  }
  Serial.println();
}
