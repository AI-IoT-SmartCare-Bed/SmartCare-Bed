#include "Arduino.h"
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// 센서 헤더
#include "RadarSensor.h"
#include "DistanceSensor.h"
#include "BedSensors.h"

// 지금은 액추에이터 사용 안 함
// #include "Actuators.h"


// ===============================
// Wi-Fi 설정
// ===============================

const char* ssid = "sol";
const char* password = "zxcvbnm123";


// ===============================
// MQTT 설정
// ===============================

// 데이터를 받을 노트북의 IP 주소
const char* mqtt_server = "172.20.10.7";

const int mqtt_port = 1883;

// 센서 데이터를 보낼 MQTT Topic
const char* sensor_topic = "bed/bed-01/sensor";


WiFiClient espClient;
PubSubClient client(espClient);

unsigned long lastRead = 0;


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

  Serial.println();

  Serial.println("Wi-Fi 연결 완료!");

  Serial.print("ESP32 IP 주소: ");

  Serial.println(WiFi.localIP());
}


// ===============================
// MQTT 연결
// ===============================

void reconnectMQTT() {

  while (!client.connected()) {

    Serial.print("MQTT 연결 시도...");

    if (client.connect("SmartBed_ESP32")) {

      Serial.println("연결 성공!");

    }

    else {

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


  // -------------------------------
  // 센서 초기화
  // -------------------------------

  setupRadar();

  setupDistance();

  setupBedSensors();


  // 액추에이터는 사용하지 않음
  // setupActuators();


  // -------------------------------
  // Wi-Fi 시작
  // -------------------------------

  setupWiFi();


  // -------------------------------
  // MQTT 서버 설정
  // -------------------------------

  client.setServer(mqtt_server, mqtt_port);


  Serial.println("Smart Bed Ready");
}


// ===============================
// LOOP
// ===============================

void loop() {


  // Wi-Fi가 끊겼으면 다시 연결
  if (WiFi.status() != WL_CONNECTED) {

    setupWiFi();
  }


  // MQTT가 끊겼으면 다시 연결
  if (!client.connected()) {

    reconnectMQTT();
  }


  client.loop();


  // ===============================
  // 레이더 센서 지속 업데이트
  // ===============================

  updateRadarData();


  // ===============================
  // 1초마다 센서 데이터 전송
  // ===============================

  if (millis() - lastRead >= 1000) {

    lastRead = millis();


    // 센서값 업데이트

    updateDistance();

    updateBedSensors();


    // ===============================
    // JSON 생성
    // ===============================

    StaticJsonDocument<384> doc;


    doc["bed_id"] = "bed-01";

    doc["fsr"] = fsrValue;

    doc["dist_cm"] = dist;

    doc["sw420"] = digitalState;

    doc["breath_rate"] = breathRate;

    doc["heart_rate"] = heartRate;


    char buf[384];

    serializeJson(doc, buf);


    // ===============================
    // MQTT로 전송
    // ===============================

    client.publish(sensor_topic, buf);


    // ===============================
    // 시리얼 모니터 확인
    // ===============================

    Serial.print("Sent via Wi-Fi MQTT: ");

    Serial.println(buf);
  }
}