"""
subscriber.py
=============
우리(데이터·서버) 쪽의 수집기(subscriber)다.
MQTT 브로커를 구독하고 있다가, 센서 메시지가 오면 받아서 화면에 찍고 DB에 저장한다.

역할: [MQTT 브로커] --전달--> [이 구독자] --(화면 출력 + DB 저장)
전체 흐름:
    fake_publisher.py --> MQTT 브로커 --> subscriber.py(이 파일) --> TimescaleDB

실행: python subscriber.py   (Ctrl+C 로 중단)
주의: fake_publisher.py 보다 먼저 켜서 대기시켜 두는 게 좋다.
"""

import json
import psycopg2                       # ★추가: PostgreSQL(TimescaleDB) 접속용
import paho.mqtt.client as mqtt

# ── 접속 정보 ────────────────────────────────────────────────
# 발행자와 같은 브로커, 같은 토픽이어야 메시지가 배달된다.
BROKER = "localhost"
PORT = 1883
TOPIC = "bed/bed-01/sensor"

# ── DB 연결 ★추가 ────────────────────────────────────────────
# 도커로 띄운 smartcare DB에 접속. 접속값은 컨테이너 띄울 때 쓴 것과 동일.
conn = psycopg2.connect(
    host="localhost", port=5432,
    dbname="smartcare", user="postgres", password="smartcare123"
)
conn.autocommit = True               # INSERT를 매번 자동 저장(커밋)
cur = conn.cursor()                  # DB에 명령을 내리는 커서


# ── 콜백 1: 브로커 연결이 성공하면 자동으로 호출된다 ──────────
def on_connect(client, userdata, flags, rc):
    # rc(result code)가 0이면 정상 연결
    print("브로커 연결됨 (rc=%s). 구독 시작: %s" % (rc, TOPIC))
    # 이 토픽을 구독하겠다고 브로커에 등록. 이제 이 토픽 메시지가 오면 on_message 가 불린다.
    client.subscribe(TOPIC)


# ── 콜백 2: 구독 중인 토픽에 메시지가 도착할 때마다 자동 호출된다 ──
def on_message(client, userdata, msg):
    # msg.payload 는 bytes 타입 → 문자열로 디코드한 뒤 JSON 으로 파싱
    data = json.loads(msg.payload.decode())
    # 받은 내용을 보기 좋게 출력
    print("받음:", data)

    # ★추가: 받은 데이터를 sensor_reading 테이블에 저장
    # %s 자리표시자 + 값 튜플로 넘겨 SQL 인젝션을 방지한다(파라미터 바인딩).
    cur.execute(
        "INSERT INTO sensor_reading (time, bed_id, sensor_code, value, quality) "
        "VALUES (%s, %s, %s, %s, %s)",
        (data["ts"], data["bed_id"], data["sensor_code"], data["value"], data["quality"])
    )


# ── 클라이언트 생성 & 콜백 등록 ──────────────────────────────
client = mqtt.Client()
client.on_connect = on_connect      # 연결됐을 때 실행할 함수 지정
client.on_message = on_message      # 메시지 왔을 때 실행할 함수 지정

# 브로커에 연결
client.connect(BROKER, PORT)

print("구독자 대기 중... (Ctrl+C 로 중단)")

# 메시지를 계속 기다리는 무한 루프. 이게 있어야 프로그램이 안 꺼지고 계속 받는다.
client.loop_forever()