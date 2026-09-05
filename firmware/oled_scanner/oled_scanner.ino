/*
 * oled_scanner.ino — nRF24 spectrum scanner + OLED display
 * OLED on software SPI (D14/D13) — avoids bus conflict with nRF24 on VSPI (D18/D23).
 */
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <RF24.h>

// nRF24 on hardware VSPI
#define CE_PIN   26
#define CSN_PIN  27

// OLED on software SPI — completely separate bus
#define OLED_MOSI 13
#define OLED_SCLK 14
#define OLED_DC    2
#define OLED_RST   4
#define OLED_CS   -1

Adafruit_SSD1306 display(128, 64, OLED_MOSI, OLED_SCLK, OLED_DC, OLED_RST, OLED_CS);
RF24 radio(CE_PIN, CSN_PIN);

const uint8_t N_CH = 126;
uint16_t hits[N_CH];

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("[oled_scanner] boot");

  if (!display.begin(SSD1306_SWITCHCAPVCC)) {
    Serial.println("[FAIL] OLED");
    while (true) delay(1000);
  }
  Serial.println("[OK] OLED");

  if (!radio.begin()) {
    display.clearDisplay();
    display.setTextSize(2);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 20);
    display.print("nRF24");
    display.setCursor(0, 42);
    display.print("FAIL");
    display.display();
    Serial.println("[FAIL] nRF24");
    while (true) delay(1000);
  }
  radio.stopListening();
  radio.setPALevel(RF24_PA_MIN);
  radio.setDataRate(RF24_2MBPS);
  radio.setAutoAck(false);

  Serial.println("[OK] both peripherals alive");

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.print("Scanning...");
  display.display();
  delay(500);
}

void loop() {
  memset(hits, 0, sizeof(hits));

  unsigned long t0 = millis();
  while (millis() - t0 < 2000) {
    for (uint8_t ch = 0; ch < N_CH; ch++) {
      radio.setChannel(ch);
      radio.startListening();
      delayMicroseconds(130);
      radio.stopListening();
      if (radio.testCarrier() || radio.testRPD()) {
        if (hits[ch] < 65000) hits[ch]++;
      }
    }
  }

  // Top 5
  uint8_t top[5] = {255,255,255,255,255};
  for (uint8_t ch = 0; ch < N_CH; ch++) {
    for (uint8_t k = 0; k < 5; k++) {
      if (top[k] == 255 || hits[ch] > hits[top[k]]) {
        for (uint8_t j = 4; j > k; j--) top[j] = top[j-1];
        top[k] = ch;
        break;
      }
    }
  }

  uint16_t peak = hits[top[0]];
  if (peak == 0) return;

  Serial.printf("top: ");
  for (uint8_t k = 0; k < 5; k++) {
    if (top[k] == 255) break;
    Serial.printf("ch%02d=%d ", top[k], hits[top[k]]);
  }
  Serial.println();

  // --- OLED (separate bus, no interference) ---
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("2.4GHz Scanner");

  display.setCursor(0, 12);
  display.print("ch37 = WiFi ch6");

  uint8_t y = 26;
  for (uint8_t k = 0; k < 5; k++) {
    if (top[k] == 255) break;
    uint8_t bar = (uint32_t)hits[top[k]] * 80 / peak + 2;
    display.setCursor(0, y);
    display.printf("ch%02d", top[k]);
    display.fillRect(30, y + 1, bar, 6, SSD1306_WHITE);
    y += 10;
  }

  display.setCursor(0, 56);
  display.printf("up %lus", millis() / 1000);
  display.display();
}
