// ==========================================
// 1. 핀 번호 및 상수 설정
// ==========================================
// FSR 센서
const int fsrPin = 4; // GPIO4

// 초음파 센서
const int trigPin = 13;
const int echoPin = 14;
#define SOUND_SPEED 0.034

// 진동 센서
const int sensorPin = 17;

// ==========================================
// 2. 센서 데이터를 담을 '구조체(상자)' 만들기 
// ==========================================
struct SensorData {
  int fsr;
  float dist;
  int digitalState;
};

SensorData data; // 'data'라는 이름의 데이터 상자 생성

// 타이머 변수 (image_55f6d7.png 참고)
unsigned long lastRead = 0;

void setup() {
  Serial.begin(115200);
  
  // FSR 설정
  analogReadResolution(12); // ESP32-S3 12bit 설정 (0~4095)
  
  // 초음파 설정
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  
  // 디지털 센서 설정
  pinMode(sensorPin, INPUT);
}

// ==========================================
// 3. 초음파 거리 측정 전용 함수
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

// ==========================================
// 4. 모든 센서를 한 번에 읽어서 상자에 담는 함수
// ==========================================
void readAllSensors() {
  data.fsr = analogRead(fsrPin);
  data.dist = readDistance();
  data.digitalState = digitalRead(sensorPin);
}

// ==========================================
// 5. 메인 루프 (delay 없이 millis 사용)
// ==========================================
void loop() {
  // 현재 시간 - 마지막으로 읽은 시간이 1000ms(1초) 이상일 때만 실행
  if (millis() - lastRead >= 1000) {
    lastRead = millis(); // 마지막 읽은 시간 갱신
    
    readAllSensors(); // 센서 값 모두 읽기
    
    // 현재는 서버로 보내기 전이므로 시리얼 모니터에 출력해서 확인해봅니다.
    Serial.println("=== 1초마다 센서 읽기 ===");
    Serial.print("FSR 값: "); Serial.println(data.fsr);
    Serial.print("거리(cm): "); Serial.println(data.dist);
    Serial.print("진동 상태: "); Serial.println(data.digitalState);
    Serial.println("=========================\n");
  }
}