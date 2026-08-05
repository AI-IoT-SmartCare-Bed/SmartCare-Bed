const int fsrPin = 4; // GPIO4, A3

void setup() {
  Serial.begin(115200);
  analogReadResolution(12); // ESP32-S3 12bit 설정 (0~4095)
}

void loop() {
  int raw = analogRead(fsrPin); // 0 ~ 4095 값 읽어오기
   
  Serial.println(raw);

  delay(1000);
}