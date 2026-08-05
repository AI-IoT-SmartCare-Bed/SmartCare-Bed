#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h> 

// ==========================================
// 1. 와이파이 및 MQTT 서버 설정
// ==========================================
const char* ssid = "KT_GIGA_A325";
const char* password = "0gb82xf264";
const char* mqtt_server = "192.168.0.xxx"; // ★여기는 전민주님 IP로 변경 필요★

WiFiClient espClient;
PubSubClient mqtt(espClient);

// ==========================================
// 2. 센서 및 출력(액추에이터) 핀 설정
// ==========================================
// [입력 센서 핀]
const int fsrPin = 4;
const int trigPin = 13;
const int echoPin = 14;
const int sensorPin = 17;
#define SOUND_SPEED 0.034

// [출력 장치 핀] (빈 핀 번호로 임의 설정했습니다. 회로에 맞게 수정하세요)
const int ledPin = 5;      
const int speakerPin = 18; 
const int servoPin = 19;   

Servo myServo; // 서보모터 객체 생성

struct SensorData {
  int fsr;
  float dist;
  int digitalState;
};

SensorData data;
unsigned long lastRead = 0;

// ==========================================
// 3. 센서 읽기 함수
// ==========================================
float readDistance() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  return pulseIn(echoPin, HIGH) * SOUND_SPEED / 2;
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
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");
}

// ==========================================
// 5. 콜백 함수 (서버에서 명령이 도착하면 자동 실행됨)
// ==========================================
void callback(char* topic, byte* payload, unsigned int length) {
  // 도착한 메시지를 문자열(String)로 변환
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.print("서버 명령 도착: ");
  Serial.println(message);

  // 명령이 "1"인 경우: 켜고 움직이기
  if (message == "1") {
    digitalWrite(ledPin, HIGH);     // LED 켜기
    tone(speakerPin, 1000);         // 스피커 1000Hz 소리 재생 (삐-)
    myServo.write(60);              // 서보모터 60도로 회전
    Serial.println("-> [동작] LED 켜짐, 스피커 울림, 서보모터 60도");
  } 
  // (참고) 명령이 "0"인 경우: 다시 원상복구 시키는 기능 
  else if (message == "0") {
    digitalWrite(ledPin, LOW);      // LED 끄기
    noTone(speakerPin);             // 스피커 소리 끄기
    myServo.write(0);               // 서보모터 0도로 원복
    Serial.println("-> [동작] 모두 정지, 서보모터 0도");
  }
}

// ==========================================
// 6. 데이터 서버로 보내기
// ==========================================
void publishToServer() {
  if (mqtt.connected()) {
    StaticJsonDocument<256> doc;
    doc["bed_id"] = "bed-01";
    doc["fsr"] = data.fsr;
    doc["dist_cm"] = data.dist;
    doc["sw420"] = data.digitalState;
    
    char buf[256];
    serializeJson(doc, buf);
    mqtt.publish("bed/bed-01/sensor", buf);
  }
}

// ==========================================
// 7. 초기 설정 (Setup)
// ==========================================
void setup() {
  Serial.begin(115200);
  
  // 센서 핀 설정
  analogReadResolution(12);
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  pinMode(sensorPin, INPUT);

  // 출력 장치 핀 설정
  pinMode(ledPin, OUTPUT);
  pinMode(speakerPin, OUTPUT);
  
  // 서보모터 초기 세팅 (0도로 시작)
  myServo.attach(servoPin);
  myServo.write(0); 

  // 와이파이 및 서버 설정
  setup_wifi();
  mqtt.setServer(mqtt_server, 1883);
  
  // ★중요★ 서버에서 메시지가 오면 callback 함수를 실행하라고 알려줌
  mqtt.setCallback(callback); 
}

// ==========================================
// 8. 무한 반복 루프 (Loop)
// ==========================================
void loop() {
  // 연결이 끊기면 재연결
  if (!mqtt.connected()) {
    if (mqtt.connect("ESP32Client")) {
      Serial.println("MQTT 서버 연결 성공!");
      
      // ★중요★ 명령어 단톡방에 입장(구독)합니다.
      // 전민주님은 'bed/bed-01/command' 방으로 "1"을 보내야 합니다.// 1을 보내면 액팅 
      mqtt.subscribe("bed/bed-01/command"); 
    }
  }
  
  mqtt.loop(); // 새 메시지가 왔는지 계속 확인

  // 1초마다 센서 값 전송
  if (millis() - lastRead >= 1000) {
    lastRead = millis();
    readAllSensors();
    publishToServer();
  }
}