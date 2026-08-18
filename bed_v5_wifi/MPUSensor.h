#include <Wire.h>

const int MPU_ADDR = 0x68;

// 가속도 데이터를 저장할 전역 변수
int16_t ax = 0;
int16_t ay = 0;
int16_t az = 0;

void setupMPU() {
  // SDA = GPIO11, SCL = GPIO12
  Wire.begin(11, 12);
  
  // MPU6050 깨우기 (Sleep 모드 해제)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B); // PWR_MGMT_1 레지스터
  Wire.write(0);    // 0을 기록해서 센서 활성화
  Wire.endTransmission(true);
}

void updateMPU() {
  // 가속도 데이터 시작 주소(0x3B) 지정
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);

  // 가속도 X, Y, Z 값 (각 2바이트씩 총 6바이트) 요청
  Wire.requestFrom(MPU_ADDR, 6, true);

  // 6바이트가 모두 들어왔는지 확인 후 변수에 저장
  if (Wire.available() >= 6) {
    ax = (Wire.read() << 8) | Wire.read();
    ay = (Wire.read() << 8) | Wire.read();
    az = (Wire.read() << 8) | Wire.read();
  }
}