#include <60ghzbreathheart.h>

#define RXD2 18   // 레이더 TX → ESP32 RX
#define TXD2 21   // 레이더 RX → ESP32 TX

BreathHeart_60GHz radar = BreathHeart_60GHz(&Serial2);

int breathRate = 0;
int heartRate = 0;

void setupRadar() {
  // 레이더 UART 통신 시작
  Serial2.begin(115200, SERIAL_8N1, RXD2, TXD2);
}

void updateRadarData() {
  radar.Breath_Heart();
  if (radar.sensor_report != 0x00) {
    switch (radar.sensor_report) {
      case BREATHVAL:
        breathRate = radar.breath_rate;
        break;
      case HEARTRATEVAL:
        heartRate = radar.heart_rate;
        break;
    }
  }
}