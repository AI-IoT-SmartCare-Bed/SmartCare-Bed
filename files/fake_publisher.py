"""
fake_publisher.py
==================
박다솔의 ESP32가 아직 없으니, 그 대신 "가짜 센서값"을 MQTT 브로커로
1초에 한 번씩 쏘는 테스트용 발행자(publisher)다.

역할: [가짜 ESP32] --publish--> [MQTT 브로커(Mosquitto)]
실제로는 이 자리에 박다솔의 ESP32가 들어오고, 우리가 정한 JSON 포맷/토픽으로
publish 하게 된다. 즉 이 파일은 W2에 박다솔 코드로 대체될 "임시 대역"이다.

★ 2026-08-07 수정: 제작설계서 기준 침대에 붙는 센서는 FSR 하나가 아니라
  압력(FSR)·거리(초음파)·자세(IMU)·다점압력(로드셀)·재실(PIR)·생체신호(레이더 심박·호흡)
  총 6종(값 기준 7개 신호)이다. subscriber.py 와 DB(sensor_reading)는 sensor_code
  컬럼으로 어떤 센서든 받게 이미 설계돼 있으므로, 발행자도 실제 설계와 맞춰
  6종을 모두 흉내 내도록 확장했다.

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

# ── 센서 목록 및 값 생성기 ────────────────────────────────────
# 제작설계서 "하드웨어 설계도" / "핀 연결" / "테이블 정의" 기준 6종 센서.
# 각 sensor_code 마다 실제 부품 스펙에 맞는 그럴듯한 값 범위로 랜덤 발생시킨다.
# (회의 답변용) 값 범위를 실제 부품 사양에서 가져온 이유: AI 전처리 단계에서
# 센서별 이상치 판정 기준(허용 범위)이 달라야 하므로, 지금부터 그 범위를 맞춰둔다.
def gen_fsr():
    # FSR-402 압력센서. ESP32 12bit ADC 원값 그대로(무압 0 ~ 가압 4095).
    return random.randint(0, 4095)

def gen_distance():
    # HC-SR04 초음파. 데이터시트 측정 가능 거리 2~400cm.
    return round(random.uniform(2, 400), 1)

def gen_imu():
    # MPU6050 자세각(기울기). -90~90도 범위로 상체 기울기를 흉내.
    return round(random.uniform(-90, 90), 1)

def gen_loadcell():
    # 로드셀+HX711, 4모서리 합산 체중 분포. 0~150kg 범위로 흉내.
    return round(random.uniform(0, 150), 1)

def gen_pir():
    # HC-SR501 PIR. 움직임 감지 여부만 판단하는 디지털 센서라 0(없음)/1(감지) 이진값.
    return random.choice([0, 1])

def gen_hr():
    # MR60BHA1 비접촉 레이더의 심박수(bpm). 정상 성인 안정시 범위를 넓게 잡음.
    return random.randint(50, 120)

def gen_resp():
    # 같은 레이더 모듈의 호흡수(회/분).
    return random.randint(10, 30)

# sensor_code: (값 생성 함수, quality)
SENSORS = {
    "FSR": gen_fsr,
    "DISTANCE": gen_distance,
    "IMU": gen_imu,
    "LOADCELL": gen_loadcell,
    "PIR": gen_pir,
    "HR": gen_hr,
    "RESP": gen_resp,
}

# ── MQTT 클라이언트 생성 & 연결 ──────────────────────────────
client = mqtt.Client()
client.connect(BROKER, PORT)

print("가짜 발행 시작 (토픽:", TOPIC, ") — 센서 %d종 — Ctrl+C 로 중단" % len(SENSORS))

while True:
    # 한 번의 "측정 주기"마다 6종 센서값을 전부 만들어서 하나씩 발행한다.
    # 같은 주기에서 나온 값이니 타임스탬프(ts)는 주기당 하나로 통일한다.
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    for sensor_code, generator in SENSORS.items():
        payload = {
            "bed_id": "bed-01",
            "sensor_code": sensor_code,
            "value": generator(),
            "quality": 100,
            "ts": ts,
        }
        # dict 를 JSON 문자열로 바꿔서 토픽으로 발행
        client.publish(TOPIC, json.dumps(payload))
        print("보냄:", payload)

    time.sleep(1)  # 1초에 한 주기(=센서 6~7개 메시지)씩 (실제 센서는 더 빠르지만 데모는 이 정도가 보기 좋다)
