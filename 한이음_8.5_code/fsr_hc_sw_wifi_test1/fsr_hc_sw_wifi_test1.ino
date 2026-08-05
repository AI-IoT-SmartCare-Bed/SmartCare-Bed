#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ==========================================
// 1. 와이파이 및 MQTT 서버 설정 
// ==========================================
const char* ssid = "KT_GIGA_A325";       // 와이파이 이름 (2.4GHz만 가능)
const char* password = "0gb82xf264";      // 와이파이 비밀번호
const char* mqtt_server = "192.168.0.xxx"; // 서버 IP 주소

WiFiClient espClient;
PubSubClient mqtt(espClient);

// ==========================================
// 2. 센서 핀 설정 및 데이터 상자
// ==========================================
const int fsrPin = 4;
const int trigPin = 13;
const int echoPin = 14;
const int sensorPin = 17;

#define SOUND_SPEED 0.034

struct SensorData {
  int fsr;
  float dist;
  int digitalState;
};

SensorData data;
unsigned long lastRead = 0;

// ==========================================
// 3. 초음파 및 센서 읽기 함수
// ==========================================
float readDistance() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  long duration = pulseIn(echoPin, HIGH);
  return duration * SOUND_SPEED / 2;
}

void readAllSensors() {
  data.fsr = analogRead(fsrPin);
  data.dist = readDistance();
  data.digitalState = digitalRead(sensorPin);
}

// ==========================================
// 4. 와이파이 연결 함수
// ==========================================
void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  // 와이파이 연결될 때까지 대기
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

// ==========================================
// 5. 서버(단톡방)에 데이터 올리기 함수 
// ==========================================
void publishToServer() {
  // MQTT가 연결되어 있을 때만 전송
  if (mqtt.connected()) {
    StaticJsonDocument<256> doc;
    
    // 포장지에 예쁘게 데이터 담기
    doc["bed_id"] = "bed-01";
    doc["fsr"] = data.fsr;
    doc["dist_cm"] = data.dist;
    doc["sw420"] = data.digitalState;
    
    char buf[256];
    serializeJson(doc, buf); // 포장 완료
    
    // "bed/bed-01/sensor"방에 전송(publish)
    mqtt.publish("bed/bed-01/sensor", buf);
    
    Serial.println("서버로 데이터 전송 완료!");
    Serial.println(buf);
  }
}

// ==========================================
// 6. 초기 설정 (Setup)
// ==========================================
void setup() {
  Serial.begin(115200);
  
  // 센서 핀 설정
  analogReadResolution(12);
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  pinMode(sensorPin, INPUT);

  // 통신 설정 시작
  setup_wifi();
  mqtt.setServer(mqtt_server, 1883); // 보통 MQTT 포트는 1883을 사용합니다.
}

// ==========================================
// 7. 무한 반복 루프 (Loop)
// ==========================================
void loop() {
  // 서버와 연결이 끊어졌으면 다시 연결 시도
  if (!mqtt.connected()) {
    if (mqtt.connect("ESP32Client")) {
      Serial.println("MQTT 서버 연결 성공!");
    }
  }
  
  // MQTT 통신 유지 (카톡 백그라운드 새로고침 같은 역할)
  mqtt.loop();

  // 1초마다 센서 읽고 서버로 보내기
  if (millis() - lastRead >= 1000) {
    lastRead = millis();
    
    readAllSensors(); // 1. 센서 다 읽어서 상자에 담기
    publishToServer(); // 2. 상자 내용을 서버로 보내기
  }
}