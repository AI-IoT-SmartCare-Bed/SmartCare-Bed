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
const char* ssid = "KT_GiGA_A325";
const char* password = "0gb82xf264";

const char* mqtt_server = "3.34.139.68";
const int mqtt_port = 1883;

// 제어용 MQTT Topic
const char* control_topic = "bed/bed-01/control";

WiFiClient espClient;
PubSubClient client(espClient);

// 위험 상태 플래그
bool isWarning = false;

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

  if (message == "1") {
    if (!isWarning) {
      isWarning = true;
      Serial.println(">>> [경고 발생] 위험 상태 진입!");
      
      setLed(true);          // 단색 LED 켜기
      setOledWarning(true);  // OLED "WARNING" 표출
      setRgbWarning(true);   // RGB LED 빨간색(Red) 켜기
    }
  } 
  else if (message == "0") {
    if (isWarning) {
      isWarning = false;
      Serial.println(">>> [상태 해제] 정상 상태 복귀");

      setLed(false);         // 단색 LED 끄기
      stopBuzzer();          // 부저 끄기
      setOledWarning(false); // OLED "NORMAL" 표출
      setRgbWarning(false);  // RGB LED 초록색(Green) 켜기
    }
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

  // 액추에이터 및 센서 초기화
  setupOled();   // OLED 초기화
  setupServo();  // 서보모터 초기화
  setupLed();    // 단색 LED 초기화
  setupBuzzer(); // 부저 초기화
  setupRgbLed(); // RGB LED 초기화

  // 초기 상태: 정상 상태(Normal)로 설정 (RGB LED 초록색 출력)
  setRgbWarning(false);

  // 네트워크 및 MQTT 설정
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

  client.loop(); // MQTT 수신 감지

  // 위험 상태(1 수신 시)일 때 서보모터 회전 및 부저 울림
  if (isWarning) {
    updateServo();
    playBuzzer();
  }
}