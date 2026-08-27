#ifndef OLED_H
#define OLED_H

#include "Arduino.h"
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// OLED 디스플레이 해상도 설정 (0.96인치 일반 규격)
#define SCREEN_WIDTH  128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1

// ESP32 I2C 핀 정의 (SDA = GPIO 21, SCL = GPIO 22)
#define OLED_SDA 11 // A4
#define OLED_SCL 12 // A5

inline Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

inline void setupOled() {
  // ESP32 I2C 핀 명시적 지정
  Wire.begin(OLED_SDA, OLED_SCL);

  // OLED 초기화 (I2C 주소는 일반적으로 0x3C 사용)
  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) { 
    Serial.println(F("OLED 연결 실패! SDA(21), SCL(22) 배선 및 I2C 주소를 확인하세요."));
  } else {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println("Actuator Ready");
    display.setCursor(0, 16);
    display.println("SDA:21 | SCL:22");
    display.display();
  }
}

inline void setOledWarning(bool warning) {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  if (warning) {
    display.setTextSize(2);
    display.setCursor(20, 25);
    display.println("WARNING");
  } else {
    display.setTextSize(2);
    display.setCursor(28, 25);
    display.println("NORMAL");
  }
  
  display.display();
}

#endif