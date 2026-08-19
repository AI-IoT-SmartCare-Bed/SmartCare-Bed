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
# fsr 은 4모서리 배열이라 별도 처리(FSR0~FSR3). 아래는 스칼라 필드만.
SENSOR_MAP = {
    "dist_cm":     "DIST",     # 거리
    "sw420":       "SW420",    # 진동
    "breath_rate": "BREATH",   # 호흡
    "heart_rate":  "HEART",    # 심박
    "pir":         "PIR",      # 재실(PIR)
    "accel_x":     "ACCEL_X",  # IMU 가속도 X
    "accel_y":     "ACCEL_Y",  # IMU 가속도 Y
    "accel_z":     "ACCEL_Z",  # IMU 가속도 Z
}


# ── 콜백 1: 브로커 연결 성공 시 ──────────────────────────────
def on_connect(client, userdata, flags, rc):
    print("브로커 연결됨 (rc=%s). 구독 시작: %s" % (rc, TOPIC))
    client.subscribe(TOPIC)


# ── 콜백 2: 메시지 도착 시 ───────────────────────────────────
# 한 메시지가 잘못돼도 구독자 전체가 죽지 않도록 전부 try/except 로 감싼다.
# (예전엔 방어가 없어서 값 하나 이상하면 프로세스가 크래시-재시작 루프에 빠졌음)
def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
    except Exception as e:
        print("JSON 파싱 실패, 건너뜀:", e)
        return

    now = datetime.now(timezone.utc)   # 서버 수신 시각(ESP32는 RTC 없음)
    bed_id = data.get("bed_id", "unknown")

    # (sensor_code, value) 목록을 만든 뒤 한 줄씩 저장한다.
    rows = []

    # fsr 은 4모서리 배열([887,895,879,883]) → 모서리별로 FSR0~FSR3 개별 저장.
    # 무게중심(CoP) 계산에 4점이 다 필요하므로 합치지 않고 개별 보관.
    fsr = data.get("fsr")
    if isinstance(fsr, (list, tuple)):
        for i, v in enumerate(fsr):
            rows.append((f"FSR{i}", v))
    elif fsr is not None:                # 혹시 스칼라로 오면 FSR0 로 저장
        rows.append(("FSR0", fsr))

    # 나머지 스칼라 필드
    for field, code in SENSOR_MAP.items():
        if field in data and data[field] is not None:
            rows.append((code, data[field]))

    saved = 0
    for code, value in rows:
        try:
            fval = float(value)          # double precision 컬럼에 안전 캐스팅
        except (TypeError, ValueError):
            print(f"  ! {code} 값 무시(숫자 아님): {value!r}")
            continue
        try:
            cur.execute(
                "INSERT INTO sensor_reading (time, bed_id, sensor_code, value, quality) "
                "VALUES (%s, %s, %s, %s, %s)",
                (now, bed_id, code, fval, 100)
            )
            saved += 1
        except Exception as e:
            print(f"  ! INSERT 실패 {code}={fval}: {e}")
    print(f"받음 {bed_id}: {saved}개 저장")


# ── 클라이언트 생성 & 콜백 등록 ──────────────────────────────
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT)

print("구독자 대기 중... (Ctrl+C 로 중단)")
client.loop_forever()
