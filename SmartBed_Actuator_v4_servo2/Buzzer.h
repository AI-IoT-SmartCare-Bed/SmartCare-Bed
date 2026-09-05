#ifndef BUZZER_H
#define BUZZER_H

#include "Arduino.h"

#define BUZZER_PIN 6 // D3

inline void setupBuzzer() {
  pinMode(BUZZER_PIN, OUTPUT);
}

inline void playBuzzer() {
  tone(BUZZER_PIN, 1000); // 1000Hz 경고음 출력
}

inline void stopBuzzer() {
  noTone(BUZZER_PIN);
}

#endif