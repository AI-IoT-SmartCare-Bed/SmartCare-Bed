#include <WiFi.h>

// ★여기에 공유기 이름과 비밀번호를 정확히 입력하세요★
const char* ssid = "KT_GIGA_A325";
const char* password = "0gb82xf264";

void setup() {
  // 시리얼 모니터 통신 속도 설정
  Serial.begin(115200);
  delay(1000); // 시리얼 모니터가 켜질 시간을 잠시 줍니다.

  Serial.println();
  Serial.println("=================================");
  Serial.print("다음 와이파이에 연결 시도 중: ");
  Serial.println(ssid);
  Serial.println("=================================");

  // 와이파이 연결 시작
  WiFi.begin(ssid, password);

  // 연결이 될 때까지 점(.)을 찍으며 무한 대기
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  // 와이파이가 성공적으로 연결되면 아래 메시지 출력
  Serial.println("");
  Serial.println("🎉 와이파이 연결 성공! 🎉");
  Serial.print("할당받은 IP 주소: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  // 테스트용이므로 loop 에서는 아무것도 하지 않습니다.
}