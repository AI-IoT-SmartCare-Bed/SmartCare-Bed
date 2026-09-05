#ifndef LED_H
#define LED_H

#include "Arduino.h"

#define LED_PIN 2 // A1

inline void setupLed() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
}

inline void setLed(bool state) {
  digitalWrite(LED_PIN, state ? HIGH : LOW);
}

#endif