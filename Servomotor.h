#ifndef SERVOMOTOR_H
#define SERVOMOTOR_H

#include "Arduino.h"
#include <ESP32Servo.h>

#define SERVO_PIN_1 5
#define SERVO_PIN_2 6

inline Servo servo1;
inline Servo servo2;

// Servo1 : 0 -> 90
inline int servoAngle1 = 0;

// Servo2 : 90 -> 0
inline int servoAngle2 = 90;

inline bool servo1Active = false;
inline bool servo2Active = false;

inline bool servo1Waiting = false;
inline bool servo2Waiting = false;

inline unsigned long servo1LastMove = 0;
inline unsigned long servo2LastMove = 0;

inline unsigned long servo1WaitStart = 0;
inline unsigned long servo2WaitStart = 0;

inline void setupServo() {

  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);

  servo1.setPeriodHertz(50);
  servo1.attach(SERVO_PIN_1, 500, 2400);
  servo1.write(0);

  servo2.setPeriodHertz(50);
  servo2.attach(SERVO_PIN_2, 500, 2400);
  servo2.write(90);
}

// MQTT에서 1 수신 시 호출
inline void startServo1() {

  servo1Active = true;
  servo1Waiting = false;

  servoAngle1 = 0;
  servo1.write(servoAngle1);
}

// MQTT에서 2 수신 시 호출
inline void startServo2() {

  servo2Active = true;
  servo2Waiting = false;

  servoAngle2 = 90;
  servo2.write(servoAngle2);
}

// MQTT에서 0 수신 시 호출
inline void stopServo() {

  // 즉시 원위치 복귀
  servoAngle1 = 0;
  servo1.write(servoAngle1);

  servoAngle2 = 90;
  servo2.write(servoAngle2);

  servo1Active = false;
  servo2Active = false;

  servo1Waiting = false;
  servo2Waiting = false;
}

inline void updateServo() {

  // ==========================
  // Servo 1
  // ==========================
  if (servo1Active) {

    if (!servo1Waiting) {

      if (millis() - servo1LastMove >= 500) {

        servo1LastMove = millis();

        if (servoAngle1 < 90) {

          servoAngle1 += 5;
          servo1.write(servoAngle1);

        } else {

          servo1Waiting = true;
          servo1WaitStart = millis();
        }
      }

    } else {

      if (millis() - servo1WaitStart >= 5000) {

        servoAngle1 = 0;
        servo1.write(servoAngle1);

        servo1Active = false;
        servo1Waiting = false;
      }
    }
  }

  // ==========================
  // Servo 2
  // ==========================
  if (servo2Active) {

    if (!servo2Waiting) {

      if (millis() - servo2LastMove >= 500) {

        servo2LastMove = millis();

        if (servoAngle2 > 0) {

          servoAngle2 -= 5;
          servo2.write(servoAngle2);

        } else {

          servo2Waiting = true;
          servo2WaitStart = millis();
        }
      }

    } else {

      if (millis() - servo2WaitStart >= 5000) {

        servoAngle2 = 90;
        servo2.write(servoAngle2);

        servo2Active = false;
        servo2Waiting = false;
      }
    }
  }
}

#endif