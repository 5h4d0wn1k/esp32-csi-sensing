/*
 * oled_hello.ino — bring-up test for the 6-pin SPI SSD1306 0.96" panel
 *
 * Wiring (see docs/HARDWARE_WIRING.md):
 *   GND->GND  VCC->3V3  D0(CLK)->GPIO18  D1(MOSI)->GPIO23  RES->GPIO4  DC->GPIO2
 *
 * Libraries (Arduino Library Manager):
 *   - Adafruit SSD1306
 *   - Adafruit GFX Library
 *
 * Success = banner + live uptime counter on the panel,
 *           "[OK] OLED online" on Serial @115200.
 */

#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define OLED_DC   2
#define OLED_RST  4
#define OLED_CS  -1        // 6-pin module: CS is grounded onboard

Adafruit_SSD1306 display(128, 64, &SPI, OLED_DC, OLED_RST, OLED_CS);

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n[oled_hello] boot");

  SPI.begin(18 /*SCK*/, 19 /*MISO unused*/, 23 /*MOSI*/);

  if (!display.begin(SSD1306_SWITCHCAPVCC)) {
    Serial.println("[FAIL] OLED init failed");
    Serial.println("  -> check: VCC on 5V rail");
    Serial.println("  -> check: D0->18, D1->23, RES->4, DC->2");
    Serial.println("  -> check: RES and DC not swapped");
    while (true) { delay(1000); }
  }

  Serial.println("[OK] OLED online — rendering test pattern");

  display.clearDisplay();
  display.display();
  delay(200);
}

void loop() {
  uint32_t up = millis() / 1000;

  display.clearDisplay();
  display.setTextSize(2);
  display.setCursor(8, 8);
  display.print("ESP32");
  display.setCursor(8, 28);
  display.print("CSI LAB");

  display.setTextSize(1);
  display.setCursor(0, 56);
  display.printf("uptime %lus  bringup OK", (unsigned long)up);
  display.display();

  delay(1000);
}
