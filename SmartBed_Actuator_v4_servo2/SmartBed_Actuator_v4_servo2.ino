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

const char* mqtt_server = "3.34.139.68";
const int mqtt_port = 1883;

// 제어용 MQTT Topic
const char* control_topic = "bed/bed-01/control";

WiFiClient espClient;
PubSubClient client(espClient);

// 위험 상태 플래그
int warningState = 0;

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

    startServo1();

    warningState = 1;

    setLed(true);
    setOledWarning(true);
    setRgbWarning(true);
  }

  // ==========================
  // 서보2 동작
  // ==========================
  else if (message == "2") {

    startServo2();

    warningState = 2;

    setLed(true);
    setOledWarning(true);
    setRgbWarning(true);
  }

  // ==========================
  // 정상 상태 복귀
  // ==========================
  else if (message == "0") {

    warningState = 0;

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
  if (warningState == 1 || warningState == 2) {
    playBuzzer();
  }
}