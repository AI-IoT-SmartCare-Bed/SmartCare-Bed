#include <WiFi.h>
#include <PubSubClient.h>
#include <ESP32Servo.h>

// ===============================
// 서보모터 설정
// ===============================
#define SERVO_PIN_3 5 // D2
#define SERVO_PIN_4 6 // D3

Servo servo3;
Servo servo4;

// Servo3 : 0 -> 90
int servoAngle3 = 0;

// Servo4 : 90 -> 0
int servoAngle4 = 90;

bool servo3Active = false;
bool servo4Active = false;

bool servo3Waiting = false;
bool servo4Waiting = false;

unsigned long servo3LastMove = 0;
unsigned long servo4LastMove = 0;

unsigned long servo3WaitStart = 0;
unsigned long servo4WaitStart = 0;

// ===============================
// Wi-Fi & MQTT 설정
// ===============================
const char* ssid = "TOZGHM";
const char* password = "123456789@";

const char* mqtt_server = "3.34.139.68";
const int mqtt_port = 1883;

const char* control_topic = "bed/bed-01/control";

WiFiClient espClient;
PubSubClient client(espClient);

// ===============================
// MQTT 수신 콜백
// ===============================
void callback(char* topic, byte* payload, unsigned int length) {

  String message = "";

  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  message.trim();

  Serial.print("[MQTT 수신] ");
  Serial.println(message);

  // ==========================
  // Servo 3 시작
  // ==========================
  if (message == "3") {

    servo3Active = true;
    servo3Waiting = false;

    servoAngle3 = 0;
    servo3.write(servoAngle3);
  }

  // ==========================
  // Servo 4 시작
  // ==========================
  else if (message == "4") {

    servo4Active = true;
    servo4Waiting = false;

    servoAngle4 = 90;
    servo4.write(servoAngle4);
  }

  // ==========================
  // 정상 상태 복귀
  // ==========================
  else if (message == "0") {

    // 즉시 원위치 복귀
    servoAngle3 = 0;
    servo3.write(servoAngle3);

    servoAngle4 = 90;
    servo4.write(servoAngle4);

    servo3Active = false;
    servo4Active = false;

    servo3Waiting = false;
    servo4Waiting = false;

    Serial.println(">>> 정상 상태 복귀");
  }
}

// ===============================
// WiFi 연결
// ===============================
void setupWiFi() {

  Serial.print("WiFi 연결 중");

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi 연결 완료");
  Serial.println(WiFi.localIP());
}

// ===============================
// MQTT 재연결
// ===============================
void reconnectMQTT() {

  while (!client.connected()) {

    Serial.print("MQTT 연결 시도...");

    if (client.connect("SmartBed_Actuator_ESP32_2nd")) {

      Serial.println("성공");

      client.subscribe(control_topic);

      Serial.print("구독 완료 : ");
      Serial.println(control_topic);

    } else {

      Serial.print("실패 rc=");
      Serial.println(client.state());

      delay(2000);
    }
  }
}

// ===============================
// Setup
// ===============================
void setup() {

  Serial.begin(115200);

  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);

  servo3.setPeriodHertz(50);
  servo3.attach(SERVO_PIN_3, 500, 2400);
  servo3.write(0);

  servo4.setPeriodHertz(50);
  servo4.attach(SERVO_PIN_4, 500, 2400);
  servo4.write(90);

  setupWiFi();

  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

// ===============================
// Loop
// ===============================
void loop() {

  if (WiFi.status() != WL_CONNECTED) {
    setupWiFi();
  }

  if (!client.connected()) {
    reconnectMQTT();
  }

  client.loop();

  // ==========================
  // Servo 3
  // ==========================
  if (servo3Active) {

    if (!servo3Waiting) {

      if (millis() - servo3LastMove >= 500) {

        servo3LastMove = millis();

        if (servoAngle3 < 90) {

          servoAngle3 += 5;
          servo3.write(servoAngle3);

        } else {

          servo3Waiting = true;
          servo3WaitStart = millis();
        }
      }

    } else {

      if (millis() - servo3WaitStart >= 5000) {

        servoAngle3 = 0;
        servo3.write(servoAngle3);

        servo3Active = false;
        servo3Waiting = false;
      }
    }
  }

  // ==========================
  // Servo 4
  // ==========================
  if (servo4Active) {

    if (!servo4Waiting) {

      if (millis() - servo4LastMove >= 500) {

        servo4LastMove = millis();

        if (servoAngle4 > 0) {

          servoAngle4 -= 5;
          servo4.write(servoAngle4);

        } else {

          servo4Waiting = true;
          servo4WaitStart = millis();
        }
      }

    } else {

      if (millis() - servo4WaitStart >= 5000) {

        servoAngle4 = 90;
        servo4.write(servoAngle4);

        servo4Active = false;
        servo4Waiting = false;
      }
    }
  }
}