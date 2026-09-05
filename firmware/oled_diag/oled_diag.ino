/*
 * oled_diag.ino — diagnostic: high-contrast test patterns
 * If the panel is alive but dim/black, this will show it.
 */
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define OLED_DC   2
#define OLED_RST  4
#define OLED_CS  -1

Adafruit_SSD1306 display(128, 64, &SPI, OLED_DC, OLED_RST, OLED_CS);

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("[diag] boot");

  SPI.begin(18, 19, 23);

  if (!display.begin(SSD1306_SWITCHCAPVCC)) {
    Serial.println("[FAIL] init");
    while (true) delay(1000);
  }
  Serial.println("[OK] init");

  // Max contrast + normal mode
  display.ssd1306_command(SSD1306_SETCONTRAST);
  display.ssd1306_command(0xFF);
  display.ssd1306_command(SSD1306_NORMALDISPLAY);

  Serial.println("[diag] step 1: fill white");
  display.clearDisplay();
  display.fillRect(0, 0, 128, 64, SSD1306_WHITE);
  display.display();
  delay(2000);

  Serial.println("[diag] step 2: checkerboard");
  for (int y = 0; y < 64; y += 8) {
    for (int x = 0; x < 128; x += 8) {
      if ((x / 8 + y / 8) % 2 == 0)
        display.fillRect(x, y, 8, 8, SSD1306_WHITE);
    }
  }
  display.display();
  delay(2000);

  Serial.println("[diag] step 3: big text");
  display.clearDisplay();
  display.setTextSize(3);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(10, 20);
  display.print("HELLO");
  display.display();
  delay(2000);

  Serial.println("[diag] step 4: invert ON");
  display.ssd1306_command(SSD1306_INVERTDISPLAY);
  delay(2000);
  display.ssd1306_command(SSD1306_NORMALDISPLAY);
  Serial.println("[diag] done");
}

void loop() {
  delay(10000);
}
