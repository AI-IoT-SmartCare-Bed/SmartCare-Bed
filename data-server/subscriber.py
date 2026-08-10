"""
subscriber.py
=============
MQTT 브로커를 구독하고, 받은 센서 메시지를 sensor_reading 테이블에 저장한다.

박다솔 ESP32는 한 메시지에 여러 센서값을 담아 보낸다(넓은 JSON).
우리 스키마는 '센서 하나당 한 줄'(긴 형태)이므로,
받은 JSON을 센서별로 쪼개서 여러 줄로 저장한다.

박다솔 JSON 예:
  {"bed_id":"bed-01","fsr":512,"dist_cm":30,"sw420":0,"breath_rate":15,"heart_rate":72}
→ 저장(한 메시지 = 5줄):
  (time, bed-01, FSR,    512)
  (time, bed-01, DIST,   30)
  (time, bed-01, SW420,  0)
  (time, bed-01, BREATH, 15)
  (time, bed-01, HEART,  72)

전체 흐름:
  ESP32(또는 fake_publisher) --> MQTT 브로커 --> subscriber(이 파일) --> TimescaleDB

실행: python subscriber.py   (Ctrl+C 로 중단)
"""

import json
import psycopg2
from datetime import datetime, timezone   # 수신 시각을 서버에서 찍기 위함
import paho.mqtt.client as mqtt

# ── 접속 정보 ────────────────────────────────────────────────
BROKER = "localhost"
PORT = 1883
TOPIC = "bed/bed-01/sensor"

# ── DB 연결 ──────────────────────────────────────────────────
conn = psycopg2.connect(
    host="localhost", port=5432,
    dbname="smartcare", user="postgres", password="smartcare123"
)
conn.autocommit = True
cur = conn.cursor()

# ── 박다솔 필드명 → 우리 sensor_code 매핑 ───────────────────
# 박다솔이 보내는 키(왼쪽)를 우리 테이블 sensor_code(오른쪽)로 변환.
SENSOR_MAP = {
    "fsr":         "FSR",     # 압력
    "dist_cm":     "DIST",    # 거리
    "sw420":       "SW420",   # 진동
    "breath_rate": "BREATH",  # 호흡
    "heart_rate":  "HEART",   # 심박
}


# ── 콜백 1: 브로커 연결 성공 시 ──────────────────────────────
def on_connect(client, userdata, flags, rc):
    print("브로커 연결됨 (rc=%s). 구독 시작: %s" % (rc, TOPIC))
    client.subscribe(TOPIC)


# ── 콜백 2: 메시지 도착 시 ───────────────────────────────────
def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    print("받음:", data)

    # 수신 시각을 서버에서 생성 (ESP32는 RTC가 없어 정확한 시각을 모름 → 서버 시각이 더 정확)
    now = datetime.now(timezone.utc)
    bed_id = data.get("bed_id", "unknown")

    # 넓은 JSON을 센서별로 쪼개서 각각 한 줄씩 저장
    saved = 0
    for field, code in SENSOR_MAP.items():
        if field not in data:      # 이번 메시지에 그 센서가 없으면 건너뜀(KeyError 방지)
            continue
        cur.execute(
            "INSERT INTO sensor_reading (time, bed_id, sensor_code, value, quality) "
            "VALUES (%s, %s, %s, %s, %s)",
            (now, bed_id, code, data[field], 100)   # quality 는 일단 100 고정
        )
        saved += 1
    print(f"  → {saved}개 센서값 저장")


# ── 클라이언트 생성 & 콜백 등록 ──────────────────────────────
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT)

print("구독자 대기 중... (Ctrl+C 로 중단)")
client.loop_forever()
