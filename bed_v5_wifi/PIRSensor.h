const int pirPin = 5; //D2

// PIR 센서 상태를 저장할 변수 (0: 감지 없음, 1: 사람 감지)
int pirState = 0;

void setupPIRSensor() {
  
  pinMode(pirPin, INPUT);
}

void updatePIRSensor() {
  // PIR 센서 값 읽어서 변수에 저장 (HIGH 또는 LOW)
  pirState = digitalRead(pirPin);
}