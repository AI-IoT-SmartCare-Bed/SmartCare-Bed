#include "Arduino.h"

// 헤더 파일들
#include "Servomotor.h"
#include "Led.h"
#include "Oled.h"
#include "Buzzer.h"
#include "RgbLed.h" // RGB LED 헤더 추가

// 단독 테스트용 상태 설정 (true: 경고 상태 / false: 정상 상태)
bool isWarning = false; 

void setup() {
  Serial.begin(115200);

  // 각 부품 초기화
  setupOled();   
  setupServo();
  setupLed();
  setupBuzzer();
  setupRgbLed(); // RGB LED 초기화

  // 테스트용 상태 적용
  if (isWarning) {
    setLed(true);          // 단색 LED On
    setOledWarning(true);  // OLED WARNING
    setRgbWarning(true);   // RGB LED 빨간색 출력
  } else {
    setLed(false);
    stopBuzzer();
    setOledWarning(false);
    setRgbWarning(false);  // RGB LED 초록색 출력
  }
}

void loop() {
  // 경고 상태 시 동작
  if (isWarning) {
    updateServo();
    playBuzzer();
  }
}