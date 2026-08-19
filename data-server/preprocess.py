"""
preprocess.py
=============
DB(sensor_reading)에 쌓인 원시 센서값을 읽어서 전처리한다.
  원시값 → 이상치 제거 → 이동평균(window=5) → 0~1 정규화
5개 센서(FSR, DIST, SW420, BREATH, HEART)를 각각 따로 전처리한다.

전처리 목적: 노이즈가 섞인 raw 데이터를 AI 모델 입력에 적합한 형태로 정제.
설계서 기준: 이상치 제거 → 이동평균(window=5) → 0~1 정규화.

실행: python preprocess.py
"""

import pandas as pd
import psycopg2

# ── 센서별 정상 범위 (이상치 판단 기준) ─────────────────────
# 이 범위를 벗어난 값은 센서 오류로 보고 제거한다.
# sensor_code 는 subscriber.py 저장 코드와 1:1 (v0.4 계약 = fsr 4모서리 개별 + pir + accel).
SENSOR_RANGE = {
    "FSR0":    (0, 4095),          # 압력 모서리0 (ADC 12bit)
    "FSR1":    (0, 4095),          # 압력 모서리1
    "FSR2":    (0, 4095),          # 압력 모서리2
    "FSR3":    (0, 4095),          # 압력 모서리3
    "DIST":    (0, 400),           # 거리 cm (HC-SR04 측정 한계)
    "SW420":   (0, 1),             # 진동 디지털 0/1
    "BREATH":  (0, 60),            # 호흡수/분
    "HEART":   (0, 200),           # 심박수/분
    "PIR":     (0, 1),             # 재실 0/1
    "ACCEL_X": (-32768, 32767),    # IMU 가속도 (MPU6050 raw int16)
    "ACCEL_Y": (-32768, 32767),
    "ACCEL_Z": (-32768, 32767),
}
WINDOW = 5   # 이동평균 창 크기 (설계서 기준)

# ── DB 연결 ──────────────────────────────────────────────────
conn = psycopg2.connect(
    host="localhost", port=5432,
    dbname="smartcare", user="postgres", password="smartcare123"
)


def preprocess_one(code):
    """센서 하나(code)에 대해 이상치제거 → 이동평균 → 정규화 수행."""
    # ① DB에서 해당 센서 데이터만 시간순으로 읽기
    df = pd.read_sql(
        "SELECT time, value FROM sensor_reading "
        "WHERE sensor_code = %(code)s ORDER BY time",
        conn, params={"code": code}
    )
    if df.empty:
        print(f"[{code}] 데이터 없음 — 건너뜀")
        return None

    before = len(df)

    # ② 이상치 제거 (센서별 정상 범위 밖 값 버림)
    lo, hi = SENSOR_RANGE[code]
    df = df[(df["value"] >= lo) & (df["value"] <= hi)].copy()

    # ③ 이동평균 (최근 WINDOW개 평균 → 노이즈 완화)
    df["ma"] = df["value"].rolling(window=WINDOW).mean()

    # ④ 0~1 정규화 (Min-Max). 값이 다양해야 정규화 의미가 있음.
    vmin, vmax = df["value"].min(), df["value"].max()
    if vmax == vmin:
        # 모든 값이 같으면(예: SW420이 전부 0) 나눗셈 불가 → 0으로 채움
        df["norm"] = 0.0
    else:
        df["norm"] = (df["value"] - vmin) / (vmax - vmin)

    print(f"[{code}] 원시 {before}건 → 이상치제거 후 {len(df)}건 "
          f"(min={vmin}, max={vmax})")
    return df


# ── 5개 센서 전부 전처리 ─────────────────────────────────────
results = {}
for code in SENSOR_RANGE.keys():
    df = preprocess_one(code)
    if df is not None:
        results[code] = df

# ── 결과 미리보기 (각 센서 마지막 5줄) ──────────────────────
for code, df in results.items():
    print(f"\n===== [{code}] 전처리 결과 (마지막 5줄) =====")
    print(df[["time", "value", "ma", "norm"]].tail(5).to_string(index=False))

conn.close()
