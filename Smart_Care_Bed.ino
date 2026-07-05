/**
 * 스마트 케어 침대 - 낙상 감지 시스템
 * 압력센서와 초음파센서의 이중감지로 낙상 상황 감지
 */

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ESP32Servo.h>

// ========== OLED 화면 설정 ==========
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// ========== GPIO 핀 정의 ==========
// 입력 센서들
const int FSR_PIN = 4;           // 압력센서 (ADC)
const int TRIG_PIN = 13;         // 초음파 센서 TRIG
const int ECHO_PIN = 14;         // 초음파 센서 ECHO

// 출력 장치들
const int SERVO_PIN = 5;         // 서보모터
const int BUZZER_PIN = 6;        // 부저
const int LED_GREEN_PIN = 7;     // LED 초록
const int LED_RED_PIN = 15;      // LED 빨강

// ========== 임계값 설정 ==========
const int FSR_THRESHOLD = 600;      // 압력센서 임계값
const float DISTANCE_THRESHOLD = 25.0; // 초음파 거리 임계값 (cm)

// ========== 상태 정의 ==========
enum State {
  NORMAL = 0,
  DANGER = 1
};

State currentState = NORMAL;
State previousState = NORMAL;

// ========== 서보 제어 변수 ==========
Servo bedServo;
bool servoMoving = false;
unsigned long servoStopTime = 0;
const unsigned long SERVO_DURATION = 3000;

// ========== 초음파 센서 변수 ==========
#define SOUND_SPEED 0.034
long duration;
float distanceCm;

// ========== 설정 함수 ==========
void setup() {
  Serial.begin(115200);
  delay(100);
  
  Serial.println("\n========== 스마트 케어 침대 시스템 초기화 ==========");
  
  // GPIO 설정
  Serial.println("GPIO 설정 중");
  pinMode(FSR_PIN, INPUT);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(LED_GREEN_PIN, OUTPUT);
  pinMode(LED_RED_PIN, OUTPUT);
  
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(LED_GREEN_PIN, LOW);
  digitalWrite(LED_RED_PIN, LOW);
  Serial.println("GPIO 설정 완료");
  
  // I2C 및 OLED 초기화
  Serial.println("OLED 초기화 중");
  Wire.begin(11, 12);
  delay(50);
  
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED 초기화 실패");
  } else {
    Serial.println("OLED 초기화 성공");
    
    display.clearDisplay();
    display.setTextSize(2);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(5, 20);
    display.println("SYSTEM");
    display.setCursor(20, 40);
    display.println("START");
    display.display();
    delay(2000);
  }
  
  // 서보 초기화
  Serial.println("서보 초기화 중");
  bedServo.attach(SERVO_PIN);
  bedServo.write(90);
  Serial.println("서보 초기화 완료");
  
  // 초기 상태 설정
  Serial.println("초기 상태 설정 중");
  setStateNormal();
  
  Serial.println("========== 초기화 완료 ==========\n");
}

// ========== 메인 루프 ==========
void loop() {
  // 센서값 읽기
  int fsrValue = analogRead(FSR_PIN);
  float distance = measureDistance();
  
  // 서보 작동 상태 확인
  if (servoMoving) {
    unsigned long currentTime = millis();
    if (currentTime >= servoStopTime) {
      servoMoving = false;
      bedServo.write(90);
      Serial.println("서보 작동 완료, 복귀");
    } else {
      Serial.println("서보 작동 중, 센서값 무시");
      delay(100);
      return;
    }
  }
  
  // 이중감지 판정 (AND 로직)
  boolean fsrTriggered = (fsrValue >= FSR_THRESHOLD);
  boolean distanceTriggered = (distance <= DISTANCE_THRESHOLD && distance > 0);
  
  // 상태 결정
  if (fsrTriggered && distanceTriggered) {
    currentState = DANGER;
  } else {
    currentState = NORMAL;
  }
  
  // 상태 변화 처리
  if (currentState != previousState) {
    if (currentState == DANGER) {
      setStateDanger();
      activateServo();
    } else {
      setStateNormal();
    }
    previousState = currentState;
  }
  
  // 디버그 출력
  Serial.printf("FSR=%4d (조건:%s) | 거리=%.1fcm (조건:%s) | 상태=%s\n",
    fsrValue,
    fsrTriggered ? "ON" : "OFF",
    distance,
    distanceTriggered ? "ON" : "OFF",
    currentState == DANGER ? "위험" : "정상");
  
  delay(100);
}

// ========== 센서 함수 ==========

// 초음파 센서로 거리 측정
float measureDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  
  duration = pulseIn(ECHO_PIN, HIGH, 30000);
  distanceCm = duration * SOUND_SPEED / 2;
  
  return distanceCm;
}

// ========== 상태 관리 함수 ==========

// 정상 상태로 설정 (초록 LED, 부저 끔, OLED 표시)
void setStateNormal() {
  Serial.println("상태 변경: 정상");
  
  digitalWrite(LED_GREEN_PIN, HIGH);
  digitalWrite(LED_RED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
  
  displayNormal();
}

// 위험 상태로 설정 (빨강 LED, 부저 울림, OLED 표시)
void setStateDanger() {
  Serial.println("상태 변경: 위험 감지");
  
  digitalWrite(LED_GREEN_PIN, LOW);
  digitalWrite(LED_RED_PIN, HIGH);
  
  buzzerAlert();
  displayDanger();
}

// 부저를 3회 울림
void buzzerAlert() {
  for (int i = 0; i < 3; i++) {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(100);
    digitalWrite(BUZZER_PIN, LOW);
    delay(100);
  }
  Serial.println("부저 울림 완료");
}

// 서보모터 작동 시작 (3초간 침대판 복귀)
void activateServo() {
  Serial.println("서보 활성화");
  bedServo.write(0);
  servoMoving = true;
  servoStopTime = millis() + SERVO_DURATION;
}

// ========== 디스플레이 함수 ==========

// OLED에 정상 상태 표시
void displayNormal() {
  display.clearDisplay();
  display.setTextSize(2);
  display.setTextColor(SSD1306_WHITE);
  
  display.setCursor(20, 10);
  display.println("NORMAL");
  
  display.setCursor(20, 40);
  display.println("MODE");
  
  display.display();
}

// OLED에 위험 상태 표시
void displayDanger() {
  display.clearDisplay();
  display.setTextSize(2);
  display.setTextColor(SSD1306_WHITE);
  
  display.setCursor(15, 10);
  display.println("FALL");
  
  display.setCursor(10, 40);
  display.println("DETECTED");
  
  display.display();
}

// 임계값 조정:
// FSR_THRESHOLD: 정상값의 최대값에 마진값 추가
// DISTANCE_THRESHOLD: 침대 정상 거리에 마진값 추가
// 시리얼 모니터에서 센서값을 확인하고 필요시 수정
