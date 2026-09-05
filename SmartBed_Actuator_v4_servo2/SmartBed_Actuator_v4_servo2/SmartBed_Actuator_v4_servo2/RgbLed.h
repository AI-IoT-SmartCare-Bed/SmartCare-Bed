#ifndef RGBLED_H
#define RGBLED_H

#include "Arduino.h"

// Geekble nano 핀 설정 (D7, D8, D9)
#define RGB_R_PIN 10 // D7
#define RGB_G_PIN 17 // D8
#define RGB_B_PIN 18 // D9

inline void setupRgbLed() {
  pinMode(RGB_R_PIN, OUTPUT);
  pinMode(RGB_G_PIN, OUTPUT);
  pinMode(RGB_B_PIN, OUTPUT);

  // 초기 상태 OFF
  digitalWrite(RGB_R_PIN, LOW);
  digitalWrite(RGB_G_PIN, LOW);
  digitalWrite(RGB_B_PIN, LOW);
}

// RGB 색상 직접 지정 함수 (0 또는 1)
inline void setRgbColor(bool r, bool g, bool b) {
  digitalWrite(RGB_R_PIN, r ? HIGH : LOW);
  digitalWrite(RGB_G_PIN, g ? HIGH : LOW);
  digitalWrite(RGB_B_PIN, b ? HIGH : LOW);
}

// 상태에 따른 RGB 제어 (경고: 빨간색 / 정상: 초록색)
inline void setRgbWarning(bool warning) {
  if (warning) {
    setRgbColor(true, false, false); // RED
  } else {
    setRgbColor(false, true, false); // GREEN
  }
}

#endif