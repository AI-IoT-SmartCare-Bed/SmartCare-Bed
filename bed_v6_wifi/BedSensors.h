// FSR 센서 핀을 배열로 묶어서 선언 (GPIO 1, 2, 3, 4)
const int fsrPins[4] = {1, 2, 3, 4};
// 4개의 FSR 센서 값을 저장할 배열 초기화
int fsrValues[4] = {0, 0, 0, 0};

// 진동 센서 등 디지털 입력 핀
const int sensorPin = 17; // D8
int digitalState = 0;

void setupBedSensors() {
  // ESP32-S3 12bit ADC 설정 (0~4095)
  analogReadResolution(12);
  
  // 디지털 센서 핀 입력 설정
  pinMode(sensorPin, INPUT);
}

void updateBedSensors() {
  // for문을 사용해 4개의 FSR 값을 한 번에 읽어서 배열에 저장
  for (int i = 0; i < 4; i++) {
    fsrValues[i] = analogRead(fsrPins[i]);
  }
  
  // 디지털 센서 값 읽기
  digitalState = digitalRead(sensorPin);
}