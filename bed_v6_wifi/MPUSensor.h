#include <Wire.h>

const int MPU_ADDR = 0x68;

// 가속도 데이터를 저장할 전역 변수
int16_t ax = 0;
int16_t ay = 0;
int16_t az = 0;

// 자이로 데이터를 저장할 전역 변수 추가
int16_t gx = 0;
int16_t gy = 0;
int16_t gz = 0;

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

  // 가속도(6) + 온도(2) + 자이로(6) = 총 14바이트 요청
  Wire.requestFrom(MPU_ADDR, 14, true);

  // 14바이트가 모두 들어왔는지 확인 후 변수에 저장
  if (Wire.available() >= 14) {
    // 1. 가속도 X, Y, Z 읽기
    ax = (Wire.read() << 8) | Wire.read();
    ay = (Wire.read() << 8) | Wire.read();
    az = (Wire.read() << 8) | Wire.read();
    
    // 2. 온도 데이터 읽기 (사용하지 않더라도 순서를 맞추기 위해 읽어내야 함)
    int16_t temp = (Wire.read() << 8) | Wire.read();
    
    // 3. 자이로 X, Y, Z 읽기
    gx = (Wire.read() << 8) | Wire.read();
    gy = (Wire.read() << 8) | Wire.read();
    gz = (Wire.read() << 8) | Wire.read();
  }
}