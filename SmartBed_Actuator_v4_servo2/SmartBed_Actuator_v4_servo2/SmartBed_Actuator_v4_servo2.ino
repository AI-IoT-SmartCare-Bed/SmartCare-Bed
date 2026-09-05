#include "Arduino.h"
#include <WiFi.h>
#include <PubSubClient.h>

// 분리된 헤더 파일들 포함
#include "Servomotor.h"
#include "Led.h"
#include "Oled.h"
#include "Buzzer.h"
#include "RgbLed.h"

// ===============================
// Wi-Fi & MQTT 설정
// ===============================
const char* ssid = "TOZGHM";
const char* password = "123456789@";

const char* mqtt_server = "192.168.25.96";
const int mqtt_port = 1883;

// 제어용 MQTT Topic
const char* control_topic = "bed/bed-01/control";

WiFiClient espClient;
PubSubClient client(espClient);

// 위험 상태 플래그
int warningState = 0;

// ===============================
// 비상정지 버튼 설정
// ===============================

// 비상정지 버튼이 연결된 GPIO 번호
// 실제 연결한 핀 번호에 맞게 변경
#define EMERGENCY_BUTTON_PIN 18

// 비상정지 상태
bool emergencyStopState = false;

// 버튼 디바운싱
bool lastButtonState = HIGH;
unsigned long lastDebounceTime = 0;
const unsigned long debounceDelay = 50;


// ===============================
// 비상정지 실행
// ===============================
void emergencyStop() {

  // 이미 비상정지 상태이면 다시 실행하지 않음
  if (emergencyStopState) {
    return;
  }

  emergencyStopState = true;

  Serial.println("================================");
  Serial.println("!!! 비상정지 작동 !!!");
  Serial.println("서보 원위치 복귀");
  Serial.println("================================");

  // 서보만 원위치로 복귀
  emergencyStopServo();

  // 위험 상태 유지
  warningState = 3;

  // 위험 표시 유지
  setLed(true);
  setOledWarning(true);
  setRgbWarning(true);
}


// ===============================
// 비상정지 버튼 확인
// ===============================
void checkEmergencyButton() {

  bool reading = digitalRead(EMERGENCY_BUTTON_PIN);

  // 버튼 상태가 변했으면 디바운싱 시작
  if (reading != lastButtonState) {
    lastDebounceTime = millis();
  }

  // 일정 시간 동안 상태가 유지되었는지 확인
  if ((millis() - lastDebounceTime) > debounceDelay) {

    // INPUT_PULLUP이므로 LOW = 버튼 눌림
    if (reading == LOW) {

      emergencyStop();
    }
  }

  lastButtonState = reading;
}


// ===============================
// MQTT 수신 콜백 함수
// ===============================
void callback(char* topic, byte* payload, unsigned int length) {

  String message = "";

  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  message.trim();

  Serial.print("[수신] Topic: ");
  Serial.print(topic);
  Serial.print(" | Message: ");
  Serial.println(message);


  // ==========================
  // 서보1 동작
  // ==========================
  if (message == "1") {

    // 비상정지 상태에서는 서보 동작 차단
    if (emergencyStopState) {

      Serial.println(">>> 비상정지 상태 - Servo 1 동작 차단");

    } else {

      startServo1();

      warningState = 1;

      setLed(true);
      setOledWarning(true);
      setRgbWarning(true);
    }
  }


  // ==========================
  // 서보2 동작
  // ==========================
  else if (message == "2") {

    // 비상정지 상태에서는 서보 동작 차단
    if (emergencyStopState) {

      Serial.println(">>> 비상정지 상태 - Servo 2 동작 차단");

    } else {

      startServo2();

      warningState = 2;

      setLed(true);
      setOledWarning(true);
      setRgbWarning(true);
    }
  }


  // ==========================
  // 정상 상태 복귀
  // ==========================
  else if (message == "0") {

    warningState = 0;

    // 비상정지 해제
    emergencyStopState = false;

    stopServo();

    setLed(false);
    stopBuzzer();
    setOledWarning(false);
    setRgbWarning(false);

    Serial.println(">>> 정상 상태 복귀");
  }
}


// ===============================
// Wi-Fi 연결
// ===============================
void setupWiFi() {

  Serial.print("Wi-Fi 연결 중");

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWi-Fi 연결 완료!");
  Serial.print("출력용 ESP32 IP: ");
  Serial.println(WiFi.localIP());
}


// ===============================
// MQTT 연결 및 토픽 구독
// ===============================
void reconnectMQTT() {

  while (!client.connected()) {

    Serial.print("MQTT 서버 연결 시도...");

    if (client.connect("SmartBed_Actuator_ESP32")) {

      Serial.println("연결 성공!");

      client.subscribe(control_topic);

      Serial.print("구독 토픽: ");
      Serial.println(control_topic);

    } else {

      Serial.print("실패, rc=");
      Serial.println(client.state());

      delay(2000);
    }
  }
}


// ===============================
// SETUP
// ===============================
void setup() {

  Serial.begin(115200);

  // 비상정지 버튼 설정
  // 버튼의 반대쪽은 GND에 연결
  pinMode(EMERGENCY_BUTTON_PIN, INPUT_PULLUP);

  setupOled();
  setupServo();
  setupLed();
  setupBuzzer();
  setupRgbLed();

  setRgbWarning(false);

  setupWiFi();

  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}


// ===============================
// LOOP
// ===============================
void loop() {

  // 비상정지 버튼을 가장 먼저 확인
  checkEmergencyButton();


  if (WiFi.status() != WL_CONNECTED) {
    setupWiFi();
  }


  if (!client.connected()) {
    reconnectMQTT();
  }


  client.loop();


  // 서보 상태 업데이트
  updateServo();


  // 부저 동작
  if (warningState == 1 ||
      warningState == 2 ||
      warningState == 3) {

    playBuzzer();
  }
}