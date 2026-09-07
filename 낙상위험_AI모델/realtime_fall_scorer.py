"""
realtime_fall_scorer.py
========================
subscriber.py가 계속 sensor_reading에 데이터를 저장하는 동안, 이 스크립트는
따로 돌면서 최신 데이터를 읽어 Random Forest 모델로 낙상 위험을 판정하고,
위험하면 event 테이블에 기록한다. + 위험 판정 시 다솔님의 액추에이터
ESP32(부저/LED/서보모터)에게도 MQTT로 직접 신호를 보낸다.
+ (신규) 장시간(기본 4시간) 동일 자세가 감지되면 액추에이터에 "5"(체위 변경
신호)를 보내고 event 테이블에도 기록한다(욕창 방지용, 낙상 위험과는 별개).

전체 흐름:
  [센서 ESP32] --MQTT--> subscriber.py --> sensor_reading 테이블
                                                |
                                                v  (이 스크립트가 주기적으로 폴링)
                                          realtime_fall_scorer.py
                                            |         |
                                            v         v
                                    event 테이블   [액추에이터 ESP32]
                                    (type=FALL_RISK) (부저/LED/서보)
                                            |
                                            v
                                  앱(이아인)이 구독해서 사용

2026-09-05 확인 완료:
  1) 브로커 — 박다솔님이 bed_v6_wifi.ino / SmartBed_Actuator_v4_servo2.ino의
     mqtt_server를 전민주 PC 로컬 IP로 변경 완료. 이 스크립트는 같은 PC에서
     돌기 때문에 ACTUATOR_BROKER="localhost"로 접속(같은 브로커).
  2) 방향 매핑 — 박다솔님 확인: servo1("1") = 오른쪽 보정, servo2("2") = 왼쪽 보정.
     아래 LEAN_TO_COMMAND에 반영함.
  → 위 두 가지가 확인되어 ENABLE_ACTUATOR_CONTROL = True로 켜짐.

  ※ 단, "FSR 값이 클수록 그쪽에 체중이 더 실린다"는 가정은 아직 실측으로
  검증되지 않았음(배선 방식에 따라 반대일 수 있음). 실제로 한쪽을 눌러보면서
  콘솔에 찍히는 lean 값이 맞게 나오는지 한 번은 확인해보는 게 좋음.

실행 전: pip install scikit-learn joblib psycopg2-binary paho-mqtt --break-system-packages
실행: python realtime_fall_scorer.py   (Ctrl+C 로 중단)
"""

import time
import json
from collections import deque, defaultdict

import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras
import joblib
import paho.mqtt.client as mqtt

# ── 설정 (DB / 모델) ──────────────────────────────────────────
DB = dict(host="localhost", port=5432, dbname="smartcare", user="postgres", password="smartcare123")
MODEL_PATH = "fall_risk_rf_model_v2.joblib"   # 09-05 재수집 데이터로 재학습한 v2 모델(정확도 91.4%)
BED_ID = "bed-01"
POLL_SEC = 3          # 몇 초마다 새 데이터를 확인할지
LOOKBACK_SEC = 8       # 매번 최근 몇 초 데이터를 가져올지 (rolling 계산용 여유분)
RISK_PROB_THRESHOLD = 0.6   # 이 확률 이상이면 "위험" 단계로 판단(민감도 조절용)
RISK_WARN_THRESHOLD = 0.3   # (신규 2026-09-07) 이 확률 이상이면 "경고" 단계 — 실측 검증 안 된 잠정값, 운영하면서 조정 필요

FSR_COLS = ["FSR0", "FSR1", "FSR2", "FSR3"]
NEEDED_CODES = FSR_COLS + ["ACCEL_X", "ACCEL_Y", "ACCEL_Z", "DIST", "PIR", "SW420", "HEART", "BREATH"]
FEATURES = [
    "fsr_mean", "fsr_std", "fsr_max", "fsr_min", "fsr_range",
    "accel_mag", "fsr_mean_roll_std", "accel_mag_roll_std",
    "DIST", "PIR", "SW420", "HEART", "BREATH",
]

# FSR 위치 매핑 (전민주 확인, 침대 위에서 봤을 때):
#   FSR0 = 오른쪽 아래(RB)   FSR1 = 오른쪽 위(RT)
#   FSR2 = 왼쪽 위(LT)       FSR3 = 왼쪽 아래(LB)
LEFT_FSR = ["FSR2", "FSR3"]
RIGHT_FSR = ["FSR0", "FSR1"]

# ── 설정 (액추에이터 MQTT 제어) ───────────────────────────────
# SmartBed_Actuator_v4_servo2.ino 기준: plain-text "0"/"1"/"2" 메시지,
# JSON 아님. 브로커/토픽도 subscriber.py의 로컬 브로커와 다름(원격 AWS).
ENABLE_ACTUATOR_CONTROL = True            # 브로커/방향 매핑 확인 완료 (2026-09-05)
ACTUATOR_BROKER = "localhost"            # 액추에이터 .ino가 전민주 PC 로컬 IP를 보도록 변경됨
ACTUATOR_PORT = 1883
ACTUATOR_TOPIC = "bed/bed-01/control"    # 액추에이터 .ino의 control_topic과 동일

# 박다솔님 확인(2026-09-05): "1"(servo1: 0→90) = 오른쪽 보정, "2"(servo2: 90→0) = 왼쪽 보정
LEAN_TO_COMMAND = {"right": "1", "left": "2"}

# ── 설정 (장시간 동일 자세 → 자동 체위 변경 신호) ──────────────
# "4시간 이상 자세(체압 분포)가 거의 안 바뀌면 살짝 움직이도록 액추에이터에 신호"
# ※ "5"는 새 명령 코드라서, 다솔님 액추에이터(SmartBed_Actuator_v4_servo2.ino)
#   callback()에 "5" 수신 시 동작(예: 서보를 살짝만 움직였다가 복귀)을
#   추가해줘야 실제로 동작함. 이 스크립트는 "5"를 보내는 부분까지만 구현.
STATIC_POSTURE_HOURS = 4
STATIC_POSTURE_SEC = STATIC_POSTURE_HOURS * 3600
REPOSITION_COMMAND = "5"

# "움직임"을 FSR 하나만으로 판단하면 두 가지 문제가 생김:
#   1) 팔다리만 움직이거나 몸을 살짝 뒤척여도 4모서리 무게중심(FSR)은 거의 안 변할 수 있음 → 놓침
#   2) FSR 노이즈로 매번 살짝씩 흔들리면 타이머가 계속 리셋돼서 진짜 안 움직였는데도 못 채울 수 있음
# 그래서 다른 센서도 같이 보고, 그중 하나라도 "움직임"을 가리키면 자세가 바뀐 것으로 본다.
STATIC_POSTURE_TOLERANCE = 30    # FSR 채널별 허용 오차(ADC 값 기준)
DIST_TOLERANCE_CM = 5            # 초음파 거리 허용 오차(cm) — 몸을 일으키는 등 자세 변화 포착용
# accel_mag_roll_std 임계값은 실측 데이터로 검증 안 된 추정치. 실제로 돌려보면서
# 항상 이 값을 넘어 계속 리셋되거나(너무 예민), 반대로 전혀 안 넘으면(너무 둔감) 조정할 것.
ACCEL_ROLL_STD_MOVE_THRESHOLD = 50.0
SW420_TRIGGERS_RESET = True      # 진동 센서(SW420)가 감지되면(=1) 그 자체로 "움직임"으로 간주

# ── 설정 (AI-06 생체이상 감지: 무호흡·심박이상, 신규 2026-09-07) ──────
# ※ 임상 검증된 기준이 아니라 상식적인 범위로 잡은 잠정값. 실측 데이터로
#   튜닝 필요(레이더 MR60BHA1 특성상 개인차·자세에 따라 오탐 가능성 있음).
APNEA_BREATH_MAX = 3            # 이 값 이하 호흡수(회/분)는 "무호흡 의심"으로 간주
APNEA_SUSTAIN_SEC = 15          # 위 상태가 이만큼 연속되면 실제로 이벤트 발생(순간 오차 방지)
HEART_MIN, HEART_MAX = 40, 130  # 이 범위를 벗어나는 심박수(bpm)는 "심박 이상"으로 간주
VITAL_SUSTAIN_SEC = 10          # 심박 이상이 이만큼 연속되면 이벤트 발생

posture_ref = {}  # bed_id -> {"fsr": np.array([FSR0..FSR3]), "dist": float, "since": timestamp}
vital_anomaly_state = {}  # bed_id -> {"apnea_since": ts|None, "heart_since": ts|None}


def _posture_has_moved(cur_fsr, ref, feat):
    """FSR / 초음파 거리 / 진동 센서 / IMU 변동성 중 하나라도 움직임을 가리키면 True."""
    if np.max(np.abs(cur_fsr - ref["fsr"])) > STATIC_POSTURE_TOLERANCE:
        return True
    if abs(feat["DIST"] - ref["dist"]) > DIST_TOLERANCE_CM:
        return True
    if SW420_TRIGGERS_RESET and feat["SW420"] >= 1:
        return True
    if feat["accel_mag_roll_std"] > ACCEL_ROLL_STD_MOVE_THRESHOLD:
        return True
    return False

actuator_client = None
if ENABLE_ACTUATOR_CONTROL:
    actuator_client = mqtt.Client()
    actuator_client.connect(ACTUATOR_BROKER, ACTUATOR_PORT)
    actuator_client.loop_start()
    print(f"액추에이터 브로커 연결됨: {ACTUATOR_BROKER}:{ACTUATOR_PORT} (topic={ACTUATOR_TOPIC})")

# 액추에이터는 "1"/"2" 수신 시 서보가 0→90(또는 90→0)까지 움직였다가 5초 뒤
# 자동으로 원위치 복귀하는 '1회성 동작'이라서, 위험 상태가 계속될 때마다
# 매 poll(3초)마다 다시 보내면 서보가 계속 리셋되며 반복 재생된다.
# → 상태(방향)가 실제로 바뀔 때만 보내도록 마지막 전송값을 기억해둔다.
last_command = defaultdict(lambda: "0")


def publish_actuator_command(bed_id, cmd):
    if not ENABLE_ACTUATOR_CONTROL:
        return
    if last_command[bed_id] == cmd:
        return  # 이미 같은 명령을 보낸 상태 → 재전송 안 함(서보 리셋 방지)
    actuator_client.publish(ACTUATOR_TOPIC, cmd)
    last_command[bed_id] = cmd
    print(f"  → 액추에이터로 '{cmd}' 전송 (상태 변화, topic={ACTUATOR_TOPIC})")


# 최근 값들을 들고 있는 버퍼 (rolling std를 폴링 경계와 무관하게 계산하기 위함)
history = defaultdict(lambda: deque(maxlen=5))  # bed_id -> deque of fsr_mean
history_accel = defaultdict(lambda: deque(maxlen=5))

clf = joblib.load(MODEL_PATH)
print(f"모델 로드 완료: {MODEL_PATH}")

conn = psycopg2.connect(**DB)
conn.autocommit = True
cur = conn.cursor()
print("DB 연결됨. 실시간 낙상 위험 판정 시작 (Ctrl+C로 중단)")


def fetch_latest_rows(bed_id, lookback_sec):
    """최근 lookback_sec초 동안의 sensor_reading을 wide 포맷으로 가져온다."""
    cur.execute(
        """
        SELECT time, sensor_code, value
        FROM sensor_reading
        WHERE bed_id = %s AND time >= NOW() - make_interval(secs => %s)
        ORDER BY time
        """,
        (bed_id, lookback_sec),
    )
    rows = cur.fetchall()
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=["time", "sensor_code", "value"])
    wide = df.pivot_table(index="time", columns="sensor_code", values="value", aggfunc="first")
    return wide


def compute_features(wide, bed_id):
    """가장 최근 시점 1행에 대한 feature 벡터 + 쏠림 방향을 만든다."""
    if wide is None or wide.empty:
        return None
    missing = [c for c in NEEDED_CODES if c not in wide.columns]
    if missing:
        return None  # 아직 12종 센서가 다 안 들어옴 (초기 몇 초는 스킵)

    latest = wide.iloc[-1]
    fsr_vals = latest[FSR_COLS].astype(float)
    fsr_mean = fsr_vals.mean()
    accel_mag = float(np.sqrt(latest["ACCEL_X"] ** 2 + latest["ACCEL_Y"] ** 2 + latest["ACCEL_Z"] ** 2))

    history[bed_id].append(fsr_mean)
    history_accel[bed_id].append(accel_mag)
    fsr_roll_std = float(np.std(history[bed_id])) if len(history[bed_id]) > 1 else 0.0
    accel_roll_std = float(np.std(history_accel[bed_id])) if len(history_accel[bed_id]) > 1 else 0.0

    feat = {
        "fsr_mean": fsr_mean,
        "fsr_std": fsr_vals.std(),
        "fsr_max": fsr_vals.max(),
        "fsr_min": fsr_vals.min(),
        "fsr_range": fsr_vals.max() - fsr_vals.min(),
        "accel_mag": accel_mag,
        "fsr_mean_roll_std": fsr_roll_std,
        "accel_mag_roll_std": accel_roll_std,
        "DIST": float(latest["DIST"]),
        "PIR": float(latest["PIR"]),
        "SW420": float(latest["SW420"]),
        "HEART": float(latest["HEART"]),
        "BREATH": float(latest["BREATH"]),
    }

    # 좌/우 쏠림 판정 (값이 클수록 압력이 큰 쪽이라고 가정 — FSR 배선 방식에 따라
    # 반대일 수도 있으니, 실제로 한쪽에 힘을 줘 보면서 검증해볼 것)
    left_val = latest[LEFT_FSR].astype(float).sum()
    right_val = latest[RIGHT_FSR].astype(float).sum()
    lean = "left" if left_val >= right_val else "right"

    return feat, latest.name, lean, fsr_vals  # (feature dict, 해당 시각, 쏠림 방향, FSR 4채널 원값)


def upsert_fall_event(bed_id, risk_prob, feat, lean, severity="warning", level="경고"):
    """활성(active) FALL_RISK 이벤트가 없으면 새로 만들고, 있으면 점수/단계만 갱신.
    (신규 2026-09-07) severity/level 인자 추가 — 정상/경고/위험 3단계 구분용."""
    cur.execute(
        "SELECT event_id FROM event WHERE bed_id=%s AND type='FALL_RISK' AND status='active'",
        (bed_id,),
    )
    existing = cur.fetchone()
    snapshot = json.dumps({"features": feat, "risk_prob": round(risk_prob, 3), "lean": lean, "level": level})
    title = "낙상 위험" if level == "위험" else "낙상 위험 경고"
    message = (
        "AI 모델이 낙상 위험 패턴을 감지했습니다." if level == "위험"
        else "AI 모델이 낙상 위험 신호를 감지했습니다(경고 단계, 지속 관찰 중)."
    )
    if existing:
        cur.execute(
            "UPDATE event SET risk_score=%s, severity=%s, title=%s, message=%s, snapshot=%s WHERE event_id=%s",
            (risk_prob, severity, title, message, snapshot, existing[0]),
        )
        print(f"  → 기존 FALL_RISK 이벤트 갱신 (risk_score={risk_prob:.2f}, level={level}, lean={lean})")
    else:
        cur.execute(
            """
            INSERT INTO event (bed_id, type, severity, risk_score, started_at, status, title, message, snapshot)
            VALUES (%s, 'FALL_RISK', %s, %s, NOW(), 'active', %s, %s, %s)
            """,
            (bed_id, severity, risk_prob, title, message, snapshot),
        )
        print(f"  → 새 FALL_RISK 이벤트 생성 (risk_score={risk_prob:.2f}, level={level}, lean={lean})")


def resolve_fall_event(bed_id):
    """위험 상태가 해소되면 활성 이벤트를 종료 처리."""
    cur.execute(
        "UPDATE event SET status='resolved', ended_at=NOW() "
        "WHERE bed_id=%s AND type='FALL_RISK' AND status='active'",
        (bed_id,),
    )
    if cur.rowcount:
        print("  → FALL_RISK 이벤트 해소(resolved) 처리")


def log_pressure_relief_event(bed_id, fsr_raw, feat, hours_static):
    """장시간 동일 자세 감지 → 체위 변경 신호를 보냈다는 기록을 남긴다(이력용, 즉시 resolved)."""
    snapshot = json.dumps({
        "fsr": {c: float(v) for c, v in fsr_raw.items()},
        "DIST": feat["DIST"], "SW420": feat["SW420"], "accel_mag_roll_std": feat["accel_mag_roll_std"],
        "hours_static": round(hours_static, 2),
    })
    cur.execute(
        """
        INSERT INTO event (bed_id, type, severity, started_at, ended_at, status, title, message, snapshot)
        VALUES (%s, 'PRESSURE_RELIEF', 'caution', NOW(), NOW(), 'resolved', %s, %s, %s)
        """,
        (bed_id, "장시간 동일 자세 감지",
         f"{hours_static:.1f}시간 동안 자세 변화가 없어 체위 변경 신호를 보냈습니다.", snapshot),
    )
    print(f"  → PRESSURE_RELIEF 이벤트 기록 ({hours_static:.1f}시간 경과)")


def check_static_posture(bed_id, fsr_raw, feat, ts):
    """FSR/거리/진동/IMU 중 어느 하나도 STATIC_POSTURE_SEC(기본 4시간) 동안
    움직임을 안 보이면 액추에이터에 '5'(체위 변경 신호)를 보내고 event에 기록한다."""
    cur_vals = fsr_raw.values.astype(float)
    ref = posture_ref.get(bed_id)

    if ref is None:
        posture_ref[bed_id] = {"fsr": cur_vals, "dist": feat["DIST"], "since": ts}
        return

    if _posture_has_moved(cur_vals, ref, feat):
        # 움직임 감지 — 기준값/타이머 리셋
        posture_ref[bed_id] = {"fsr": cur_vals, "dist": feat["DIST"], "since": ts}
        return

    elapsed_sec = (ts - ref["since"]).total_seconds()
    if elapsed_sec >= STATIC_POSTURE_SEC:
        hours_static = elapsed_sec / 3600
        publish_reposition_command(bed_id)
        log_pressure_relief_event(bed_id, fsr_raw, feat, hours_static)
        # 신호를 보낸 시점을 새 기준으로 삼아 타이머 재시작 (계속 안 움직이면 다시 4시간 후 재발동)
        posture_ref[bed_id] = {"fsr": cur_vals, "dist": feat["DIST"], "since": ts}


def publish_reposition_command(bed_id):
    if not ENABLE_ACTUATOR_CONTROL:
        return
    actuator_client.publish(ACTUATOR_TOPIC, REPOSITION_COMMAND)
    print(f"  → 액추에이터로 '{REPOSITION_COMMAND}' 전송 (장시간 동일 자세, topic={ACTUATOR_TOPIC})")


# ── (신규 2026-09-07) AI-06 생체이상 감지: 무호흡 의심 / 심박 이상 ──────────
def log_vital_anomaly_event(bed_id, kind, feat):
    """무호흡 의심(apnea) / 심박 이상(heart) 이벤트를 새로 만들거나 갱신한다.
    event 테이블 스키마 변경 없이 snapshot의 kind 값으로 종류를 구분한다."""
    cur.execute(
        "SELECT event_id, snapshot FROM event WHERE bed_id=%s AND type='VITAL_ANOMALY' AND status='active'",
        (bed_id,),
    )
    existing = None
    for eid, snap in cur.fetchall():
        try:
            if json.loads(snap or "{}").get("kind") == kind:
                existing = eid
                break
        except Exception:
            pass

    snapshot = json.dumps({"kind": kind, "HEART": feat["HEART"], "BREATH": feat["BREATH"]})
    title = "무호흡 의심" if kind == "apnea" else "심박 이상"
    message = (
        f"호흡수가 {feat['BREATH']:.0f}회/분으로 {APNEA_SUSTAIN_SEC}초 이상 낮게 유지되었습니다."
        if kind == "apnea" else
        f"심박수가 {feat['HEART']:.0f}bpm으로 정상 범위({HEART_MIN}~{HEART_MAX})를 벗어났습니다."
    )
    if existing:
        cur.execute("UPDATE event SET snapshot=%s WHERE event_id=%s", (snapshot, existing))
    else:
        cur.execute(
            """
            INSERT INTO event (bed_id, type, severity, started_at, status, title, message, snapshot)
            VALUES (%s, 'VITAL_ANOMALY', 'critical', NOW(), 'active', %s, %s, %s)
            """,
            (bed_id, title, message, snapshot),
        )
        print(f"  → VITAL_ANOMALY({kind}) 이벤트 생성: {message}")


def resolve_vital_anomaly_event(bed_id, kind):
    cur.execute(
        "SELECT event_id, snapshot FROM event WHERE bed_id=%s AND type='VITAL_ANOMALY' AND status='active'",
        (bed_id,),
    )
    for eid, snap in cur.fetchall():
        try:
            if json.loads(snap or "{}").get("kind") != kind:
                continue
        except Exception:
            continue
        cur.execute("UPDATE event SET status='resolved', ended_at=NOW() WHERE event_id=%s", (eid,))
        print(f"  → VITAL_ANOMALY({kind}) 이벤트 해소(resolved) 처리")


def check_vital_anomaly(bed_id, feat, ts):
    """호흡수가 너무 낮은 상태(무호흡 의심)·심박수가 정상 범위를 벗어난 상태가
    일정 시간 이상 이어지면 event 테이블에 VITAL_ANOMALY로 기록한다."""
    state = vital_anomaly_state.setdefault(bed_id, {"apnea_since": None, "heart_since": None})

    if feat["BREATH"] <= APNEA_BREATH_MAX:
        if state["apnea_since"] is None:
            state["apnea_since"] = ts
        elif (ts - state["apnea_since"]).total_seconds() >= APNEA_SUSTAIN_SEC:
            log_vital_anomaly_event(bed_id, "apnea", feat)
    else:
        if state["apnea_since"] is not None:
            resolve_vital_anomaly_event(bed_id, "apnea")
        state["apnea_since"] = None

    if not (HEART_MIN <= feat["HEART"] <= HEART_MAX):
        if state["heart_since"] is None:
            state["heart_since"] = ts
        elif (ts - state["heart_since"]).total_seconds() >= VITAL_SUSTAIN_SEC:
            log_vital_anomaly_event(bed_id, "heart", feat)
    else:
        if state["heart_since"] is not None:
            resolve_vital_anomaly_event(bed_id, "heart")
        state["heart_since"] = None


while True:
    try:
        wide = fetch_latest_rows(BED_ID, LOOKBACK_SEC)
        result = compute_features(wide, BED_ID)
        if result is None:
            print("데이터 부족 — 대기 중...")
        else:
            feat, ts, lean, fsr_raw = result
            X = pd.DataFrame([feat])[FEATURES]
            proba = clf.predict_proba(X)[0]
            classes = list(clf.classes_)
            risk_prob = proba[classes.index("fall_risk")]
            # (신규 2026-09-07) 정상/경고/위험 3단계 — 기존엔 위험/안전 이진 판정만 했음
            if risk_prob >= RISK_PROB_THRESHOLD:
                level = "위험"
            elif risk_prob >= RISK_WARN_THRESHOLD:
                level = "경고"
            else:
                level = "정상"

            print(f"[{ts}] 판정={level} (risk_prob={risk_prob:.2f}) fsr_mean={feat['fsr_mean']:.0f} lean={lean}")

            if level == "위험":
                upsert_fall_event(BED_ID, risk_prob, feat, lean, severity="critical", level=level)
                publish_actuator_command(BED_ID, LEAN_TO_COMMAND[lean])
            elif level == "경고":
                # 경고 단계는 이벤트로만 기록, 액추에이터는 아직 움직이지 않음(과잉반응 방지)
                upsert_fall_event(BED_ID, risk_prob, feat, lean, severity="warning", level=level)
                publish_actuator_command(BED_ID, "0")
            else:
                resolve_fall_event(BED_ID)
                publish_actuator_command(BED_ID, "0")

            # 낙상 위험과 별개로, 장시간 동일 자세인지도 매 poll마다 계속 체크
            check_static_posture(BED_ID, fsr_raw, feat, ts)
            # (신규 2026-09-07) 생체신호 이상(무호흡·심박이상)도 매 poll마다 계속 체크
            check_vital_anomaly(BED_ID, feat, ts)

    except Exception as e:
        print("오류:", e)

    time.sleep(POLL_SEC)
