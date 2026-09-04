#include <Arduino.h>
#include <ESP32Servo.h>

#define SERVO_PIN_1 5
#define SERVO_PIN_2 6

Servo servo1;
Servo servo2;

int servoAngle1 = 0;   // 0 -> 90
int servoAngle2 = 90;  // 90 -> 0

unsigned long lastServoMove = 0;
unsigned long waitStartTime = 0;

int activeMotor = 0;   // 0: 정지, 1: 모터1, 2: 모터2
bool waitingToReturn = false;

void setup() {
  Serial.begin(115200);

  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);

  servo1.setPeriodHertz(50);
  servo1.attach(SERVO_PIN_1, 500, 2400);
  servo1.write(servoAngle1);

  servo2.setPeriodHertz(50);
  servo2.attach(SERVO_PIN_2, 500, 2400);
  servo2.write(servoAngle2);
}

void loop() {

  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input == "1") {
      activeMotor = 1;
      waitingToReturn = false;

      servoAngle1 = 0;
      servo1.write(servoAngle1);
    }
    else if (input == "2") {
      activeMotor = 2;
      waitingToReturn = false;

      servoAngle2 = 90;
      servo2.write(servoAngle2);
    }
    else if (input == "0") {
      activeMotor = 0;
      waitingToReturn = false;
    }
  }

  // ===== 모터1 =====
  if (activeMotor == 1) {

    if (!waitingToReturn) {

      if (millis() - lastServoMove >= 500) {
        lastServoMove = millis();

        if (servoAngle1 < 90) {
          servoAngle1 += 5;
          servo1.write(servoAngle1);
        }
        else {
          waitingToReturn = true;
          waitStartTime = millis();
        }
      }

    } else {

      if (millis() - waitStartTime >= 5000) {
        servoAngle1 = 0;
        servo1.write(servoAngle1);

        activeMotor = 0;
        waitingToReturn = false;
      }
    }
  }

  // ===== 모터2 =====
  else if (activeMotor == 2) {

    if (!waitingToReturn) {

      if (millis() - lastServoMove >= 500) {
        lastServoMove = millis();

        if (servoAngle2 > 0) {
          servoAngle2 -= 5;
          servo2.write(servoAngle2);
        }
        else {
          waitingToReturn = true;
          waitStartTime = millis();
        }
      }

    } else {

      if (millis() - waitStartTime >= 5000) {
        servoAngle2 = 90;
        servo2.write(servoAngle2);

        activeMotor = 0;
        waitingToReturn = false;
      }
    }
  }
}