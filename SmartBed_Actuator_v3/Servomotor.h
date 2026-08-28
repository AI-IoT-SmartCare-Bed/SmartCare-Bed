#ifndef SERVOMOTOR_H
#define SERVOMOTOR_H

#include "Arduino.h"
#include <ESP32Servo.h>

#define SERVO_PIN 5 // D2

inline Servo myServo;
inline int servoAngle = 0;
inline unsigned long lastServoMove = 0;

inline void setupServo() {
  ESP32PWM::allocateTimer(0);
  myServo.setPeriodHertz(50);
  myServo.attach(SERVO_PIN, 500, 2400);
  myServo.write(servoAngle);
}

inline void updateServo() {
  // 0.5초마다 5도씩 회전 (180도 도달 시 0도로 리셋)
  if (millis() - lastServoMove >= 500) {
    lastServoMove = millis();
    servoAngle = (servoAngle + 5) % 180;
    myServo.write(servoAngle);
  }
}

#endif