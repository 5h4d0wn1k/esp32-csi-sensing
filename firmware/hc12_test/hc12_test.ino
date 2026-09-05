/*
 * hc12_test.ino — robust AT-mode test with retries
 * Wiring: HC-12 SET->GND, TXD->RX2(D16), RXD->TX2(D17), VCC->5V, GND->GND
 */
#define RX2_PIN 16
#define TX2_PIN 17

void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("\n[hc12_test] boot");

  Serial2.begin(9600, SERIAL_8N1, RX2_PIN, TX2_PIN);
  delay(1000);

  // Send AT 5 times with gaps — HC-12 needs time to power up
  for (int i = 1; i <= 5; i++) {
    Serial.printf("[attempt %d] sending AT...\n", i);
    Serial2.print("AT\r\n");
    delay(1000);

    String resp = "";
    while (Serial2.available()) resp += (char)Serial2.read();
    resp.trim();

    if (resp.length() > 0) {
      Serial.printf("[OK] response: %s\n", resp.c_str());
      break;
    } else {
      Serial.println("[..] no response yet");
    }
  }

  // Also try AT+R (restore defaults) and AT+V (version)
  const char* cmds[] = {"AT+V\r\n", "AT+RB\r\n", "AT+C001\r\n"};
  for (int i = 0; i < 3; i++) {
    delay(500);
    Serial2.print(cmds[i]);
    delay(800);
    String r = "";
    while (Serial2.available()) r += (char)Serial2.read();
    r.trim();
    if (r.length()) Serial.printf("[cmd] %s -> %s\n", cmds[i], r.c_str());
  }

  Serial.println("\n[done]");
}

void loop() { delay(10000); }
