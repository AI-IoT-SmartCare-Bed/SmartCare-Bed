"""
fake_publisher.py
=================
박다솔 ESP32가 없을 때 대신 쓰는 테스트용 발행자.
박다솔이 실제로 보내는 것과 '똑같은 포맷'으로 가짜 센서값을 쏜다.

박다솔 JSON 포맷(ESP32 코드 기준):
  {"bed_id":"bed-01","fsr":..,"dist_cm":..,"sw420":..,"breath_rate":..,"heart_rate":..}
  * 시각(ts)은 보내지 않는다 → 받는 쪽(subscriber)이 수신 시각을 찍는다.

실행: python fake_publisher.py   (Ctrl+C 로 중단)
"""

import time
import json
import random
import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883
TOPIC = "bed/bed-01/sensor"   # 박다솔 ESP32와 동일한 토픽

client = mqtt.Client()
client.connect(BROKER, PORT)

print("가짜 발행 시작 (박다솔 포맷) — Ctrl+C 로 중단")

while True:
    # 박다솔 ESP32와 동일한 필드 구성 (센서 여러 개를 한 메시지에 담음)
    payload = {
        "bed_id": "bed-01",
        "fsr": random.randint(0, 4095),         # 압력 0~4095
        "dist_cm": random.randint(5, 200),      # 거리 5~200cm
        "sw420": random.randint(0, 1),          # 진동 0/1
        "breath_rate": random.randint(10, 25),  # 호흡 10~25
        "heart_rate": random.randint(55, 100),  # 심박 55~100
    }
    # 박다솔 코드처럼 ts는 넣지 않는다.

    client.publish(TOPIC, json.dumps(payload))
    print("보냄:", payload)
    time.sleep(1)   # 1초에 한 번 (박다솔 ESP32도 1초 주기)
