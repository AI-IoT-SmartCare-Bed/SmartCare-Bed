const int trigPin = 13; // 초음파 쏘는 핀 A6 
const int echoPin = 14; // 초음파 받는 핀 A7

// 음속 (cm/us)
#define SOUND_SPEED 0.034

long duration;
float distanceCm;

void setup() {
  Serial.begin(115200); // ESP32는 보통 115200 통신 속도를 사용합니다.
  pinMode(trigPin, OUTPUT); // Trig는 출력 모드
  pinMode(echoPin, INPUT);  // Echo는 입력 모드
}

void loop() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);

  //  초음파 발사! (10마이크로초 동안 HIGH 신호 유지)
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  duration = pulseIn(echoPin, HIGH);

  distanceCm = duration * SOUND_SPEED / 2;

  Serial.println(distanceCm);

  delay(1000); 
}