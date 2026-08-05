"""
fake_publisher.py
==================
박다솔의 ESP32가 아직 없으니, 그 대신 "가짜 센서값"을 MQTT 브로커로
1초에 한 번씩 쏘는 테스트용 발행자(publisher)다.

역할: [가짜 ESP32] --publish--> [MQTT 브로커(Mosquitto)]
실제로는 이 자리에 박다솔의 ESP32가 들어오고, 우리가 정한 JSON 포맷/토픽으로
publish 하게 된다. 즉 이 파일은 W2에 박다솔 코드로 대체될 "임시 대역"이다.

실행: python fake_publisher.py   (Ctrl+C 로 중단)
"""

import time
import json
import random
import paho.mqtt.client as mqtt

# ── 브로커 접속 정보 ─────────────────────────────────────────
# 아까 docker 로 띄운 로컬 Mosquitto. 같은 노트북이라 localhost.
# 나중에 HiveMQ Cloud 로 바꾸려면 이 두 줄만 클라우드 주소로 교체하면 된다.
BROKER = "localhost"
PORT = 1883

# ── 토픽(우편함 주소) ────────────────────────────────────────
# "bed/<침대id>/sensor" 구조. 박다솔과 W2에 최종 확정할 대상.
# 지금은 이 값으로 개발한다. subscriber.py 의 TOPIC 과 반드시 같아야 한다.
TOPIC = "bed/bed-01/sensor"

# ── MQTT 클라이언트 생성 & 연결 ──────────────────────────────
client = mqtt.Client()
client.connect(BROKER, PORT)

print("가짜 발행 시작 (토픽:", TOPIC, ") — Ctrl+C 로 중단")

while True:
    # 보낼 메시지(payload). 우리 DB 의 sensor_reading 스키마와 똑같은 구조로 맞춘다.
    #   bed_id      : 어느 침대인지
    #   sensor_code : 센서 종류 (지금은 FSR 압력센서로 고정)
    #   value       : 측정값 (FSR 압력값 범위 0~4095 를 랜덤으로 흉내)
    #   quality     : 신뢰도 (일단 100 고정)
    #   ts          : 측정 시각 (UTC, ISO8601 형식)
    payload = {
        "bed_id": "bed-01",
        "sensor_code": "FSR",
        "value": random.randint(0, 4095),
        "quality": 100,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # dict 를 JSON 문자열로 바꿔서 토픽으로 발행
    client.publish(TOPIC, json.dumps(payload))
    print("보냄:", payload)

    time.sleep(1)  # 1초에 하나씩 (실제 센서는 더 빠르지만 데모는 이 정도가 보기 좋다)
